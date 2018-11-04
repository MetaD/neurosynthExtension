from collections import OrderedDict
from string import punctuation
import pandas as pd
import neurosynth as ns
import numpy as np
import os
from datetime import datetime


class NsInfo(OrderedDict):
    """
    Handle information strings (e.g. NeuroSynth expressions and image names).
    """
    img_names = ['pA', 'pAgF', 'pFgA', 'uniformity-test_z', 'association-test_z']
    prior_img_names = ['pAgF_given_pF=', 'pFgA_given_pF=']
    fdr_img_names = ['uniformity-test_z_FDR_', 'association-test_z_FDR_']

    def __init__(self, *args, **kwargs):
        super(NsInfo, self).__init__(*args, **kwargs)

    @staticmethod
    def shorten_expr(expr):
        abbr = expr.split(' ', maxsplit=1)[0]
        return abbr.strip(punctuation)

    @staticmethod
    def get_num_from_img_name(image_name):
        if image_name in NsInfo.img_names:
            return {}
        for prior_name in NsInfo.prior_img_names:
            if prior_name in image_name:
                num = image_name[len(prior_name):]
                return {'prior': float(num)}
        for fdr_name in NsInfo.fdr_img_names:
            if fdr_name in image_name:
                num = image_name[len(fdr_name):]
                return {'fdr': float(num)}
        return {}

    def as_pandas_df(self):
        """
        Return the information as a pandas data frame
        """
        return pd.DataFrame(list(self.values()), index=list(self.keys()))


class MetaAnalysisPlus(ns.meta.MetaAnalysis):
    """
    An extension of the NeuroSynth MetaAnalysis class.
    """

    def __init__(self, info, dataset, images=None, *args, **kwargs):
        """
        :param info: a list of string tuples containing information regarding the
                     meta src, e.g. [('expression', 'social'), ('num_studies', 1000)]
        :param images: optionally initialize this object with existing images.
                       If specified, meta-analysis won't run, but an instance of this
                       class will be constructed with the existing images and info
        """
        if isinstance(info, MetaAnalysisPlus.Info):
            self.info = info
        else:
            self.info = MetaAnalysisPlus.Info(info)

        if images is None:
            super(MetaAnalysisPlus, self).__init__(dataset, *args, **kwargs)
        else:
            self.dataset = dataset
            self.images = images

    # Information #

    def __str__(self):
        return '\n' + str(self._get_images_with_info()) + '\n'

    def __repr__(self):
        return str(self)

    class Info(NsInfo):
        def __init__(self, *args, **kwargs):
            """
            Initialize with 'expression', and 'contrary expression' if comparing to
            another expression
            """
            super(NsInfo, self).__init__(*args, **kwargs)
            self.name = self.get_shorthand()

        def __str__(self):
            return '\n' + self.name + '\n' + str(self.as_pandas_df()) + '\n'

        def __repr__(self):
            return str(self)

        def set_name(self, name):
            self.name = name

        def get_shorthand(self):
            """
            Return a short description of the meta analysis (to be used for file names)
            """
            name = ''
            if 'expression' in self:
                name = NsInfo.shorten_expr(self['expression'])
                if 'contrary expression' in self:
                    name += '_vs_' + \
                            NsInfo.shorten_expr(self['contrary expression'])
            return name

    # Methods for File Output #

    def _get_images_with_info(self, image_names=None):
        """
        Get a pandas data frame of images prefixed with their information
        :param image_names: the names of images to be included in the result.
                            If None, all images will be returned.
        :return: a pandas data frame of images
        """
        images = self.images.keys()
        if image_names is not None:
            images = list(set(image_names) & images)  # find intersection
        info_df = self.info.as_pandas_df()
        info_df = info_df.append(pd.DataFrame([images], index=['voxel']))
        image_df = pd.DataFrame([self.images[img_name].tolist() for img_name in images]).T
        return pd.concat([info_df, image_df])

    @staticmethod
    def make_result_dir(path, dirname):
        outdir = os.path.join(path, dirname)
        if os.path.isdir(outdir):
            # add a current time if the same directory already exists
            current_time = str(datetime.now()).split('.')[0]
            outdir = os.path.join(path, dirname + ' ' + current_time)
        os.mkdir(outdir)
        return outdir

    def save_csv(self, filename, delimiter=',', image_names=None):
        """
        Save the info and images to a csv file.
        :param filename: (string) full path and name of the output csv
        :param image_names: images to be included in the csv
        """
        df = self._get_images_with_info(image_names)
        df.to_csv(filename, sep=delimiter, header=False)

    def save_images(self, prefix=None, postfix='', image_names=None, outpath='.'):
        images = self.images.keys()
        if image_names is not None:
            images = list(set(image_names) & images)  # find intersection
        for img_name in images:
            # file name
            filename = prefix if prefix is not None else self.info.name
            if len(filename) > 0 and filename[len(filename) - 1] != '_':
                filename += '_'
            if len(postfix) > 0 and postfix[0] != '_':
                postfix = '_' + postfix
            filename += img_name + postfix + '.nii.gz'
            # save image
            ns.imageutils.save_img(self.images[img_name],
                                   filename=os.path.join(outpath, filename),
                                   masker=self.dataset.masker)

    # Methods of operations done on lists of MetaAnalysisPlus objects #

    @classmethod
    def mean(cls, meta_list):
        """
        Calculate the mean of each image in the given list.
        Each object in the list should have the same info and image names.
        :param meta_list: a list of MetaAnalysisPlus objects
        :return: a MetaAnalysisPlus object that has the mean images
        """
        if len(meta_list) == 0:
            raise ValueError('Empty list')
        if len(meta_list) == 1:
            return meta_list[0]

        # calculate means
        mean_imgs = {}
        for img in meta_list[0].images:
            mean_imgs[img] = np.mean([meta.images[img] for meta in meta_list], axis=0)
        return cls(meta_list[0].info, meta_list[0].dataset, images=mean_imgs)

    @classmethod
    def conjunction(cls, meta_list, image_name, lower_thr=None, upper_thr=None,
                    expression=None, extra_info=()):
        """
        Given a list of meta-analysis results, compute a new image based on image_name,
        where the value at each voxel is the number of images in meta_list in which this
        voxel value passes the given threshold criterion.

        At least one of lower_thr and upper_thr must be specified.
        When lower threshold is the only threshold specified:
            In the returned image, the value at each voxel will be the count of given
            images where this voxel is GREATER than the given lower_thr
        When upper threshold is the only threshold specified:
            An image is counted when its voxel values are LESS than the given upper_thr
        When both lower and upper thresholds are specified:
            if lower_thr < upper_thr, an image is counted when its voxels are BOTH
            greater than lower_thr AND less than upper_thr;
            if lower_thr > upper_thr, an image is counted when its voxels are EITHER
            greater than lower_thr OR less than upper_thr.

        :return: a MetaAnalysisPlus object that has the conjunction image
        """
        if lower_thr is None and upper_thr is None:
            raise ValueError('Must specify at least one threshold')
        if lower_thr == upper_thr:
            raise ValueError('Lower and upper thresholds must be different')

        src_imgs = np.array([meta.images[image_name] for meta in meta_list])

        if upper_thr is None:
            conjunction = np.sum(src_imgs > lower_thr, axis=0)
            comp_name = '>' + str(lower_thr)
        elif lower_thr is None:
            conjunction = np.sum(src_imgs < upper_thr, axis=0)
            comp_name = '<' + str(upper_thr)
        else:
            if lower_thr < upper_thr:
                conjunction = np.sum((src_imgs > lower_thr) &
                                     (src_imgs < upper_thr), axis=0)
                comp_name = str(lower_thr) + '-' + str(upper_thr)
            else:
                conjunction = np.sum((lower_thr < src_imgs) |
                                     (src_imgs < upper_thr), axis=0)
                comp_name = '>' + str(lower_thr) + 'or' + '<' + str(upper_thr)

        info = [('based on', image_name), ('criterion', comp_name)]
        info += extra_info
        if expression:
            info = cls.Info(info)
            info.set_name(NsInfo.shorten_expr(expression) + '_' + image_name + comp_name)
        return cls(info, meta_list[0].dataset, images={'conjunction': conjunction})

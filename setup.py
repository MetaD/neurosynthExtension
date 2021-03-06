# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

version_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'nsplus', 'version.py')
exec(compile(open(version_file, 'rb').read(), version_file, 'exec'))

APP_NAME = 'NSplus'
OPTIONS = {
    'iconfile': os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'nsplus', 'res', 'icon.icns'),
    'packages': ['pandas', 'numpy', 'scipy', 'neurosynth', 'sklearn', 'matplotlib'],
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleVersion': __version__,
        'CFBundleShortVersionString': __version__,
        'NSHumanReadableCopyright': u'© 2018-2019 Meng Du & Matthew Lieberman. All Rights Reserved.'
    },
    'bdist_base': os.path.join(os.path.dirname(os.getcwd()), 'build'),
    'dist_dir': os.path.join(os.path.dirname(os.getcwd()), 'dist')
}

setup(
    name=APP_NAME,
    version=__version__,
    description='A Neurosynth-based meta-analysis tool',
    url='https://github.com/MetaD/NSplus',
    author='Meng Du',
    author_email='mengdu@umich.edu',
    # app=[os.path.join(os.path.dirname(os.path.realpath(__file__)), 'run.py')],
    include_package_data=True,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'neurosynth@git+https://github.com/neurosynth/neurosynth.git@948ce7edce15d7df693446e76834e0c23bfe8f11#egg=neurosynth',
        'pandas>=0.23.0',
        'scipy>=1.1.0',
        'numpy>=1.14.0',
        'matplotlib',
        'scikit-learn'
    ],
    entry_points={
        'console_scripts': [
             'nsplus=nsplus.gui:main_gui',
        ],
    },
    packages=find_packages(exclude=('data', 'res', 'tests', 'docs')),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta"
    ]
)

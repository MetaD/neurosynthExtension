from __future__ import absolute_import, print_function
from ..src.datasetplus import DatasetPlus
import os
from threading import Lock
from sys import version_info
if version_info.major == 2:
    import Tkinter as tk
    import tkMessageBox as messagebox
elif version_info.major == 3:
    import tkinter as tk
    from tkinter import messagebox


class _Singleton(type):
    """
    Metaclass for singletons. See https://stackoverflow.com/a/6798042/3290263
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton('SingletonMeta', (object,), {})):
    pass


class Global(Singleton):
    """
    A class that maintains the NeuroSynth dataset instance and the current app status
    """
    def __init__(self, root=None, app=None, **kwargs):
        self.root = root
        self.status = 'Ready'
        self.is_ready = False
        self.has_error = False
        self.history = []
        self.dataset = None
        self.status_mutex = Lock()
        self.roi_filename = None

        # output directory
        self.outdir = os.path.join(os.path.expanduser('~'), 'NeuroSynthPlus')
        if not os.path.isdir(self.outdir):
            os.mkdir(self.outdir)
        app.label_outdir.config(text=self.outdir)

        # GUI
        self.statusbar = tk.Frame(root, **kwargs)
        self.text_width = 80
        self.statusbar_label = tk.Label(root, text=self.status.ljust(self.text_width),
                                        bd=1, relief=tk.SUNKEN, anchor='w', padx=3,
                                        font=('Menlo', 12), bg='#6d6d6d', fg='#d6d6d6')
        self.statusbar_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _update_status(self, status, is_ready, is_error=False):  # not thread safe
        self.status = status
        self.has_error = is_error
        self.history.append(status)
        if len(status) > self.text_width:
            statusbar_text = status[:(self.text_width - 3)] + '...'
        else:
            statusbar_text = status.ljust(self.text_width)
        if is_error:
            text_color = '#ff0000'
        elif is_ready:
            text_color = '#90ee90'
        else:
            text_color = '#e3e3e3'
        self.statusbar_label.config(text=statusbar_text, fg=text_color)

    def update_status(self, status='Ready', is_ready=False, is_error=False, user_op=False):  # thread safe
        """
        :param status: string
        :param is_ready: (boolean) whether ready to run another task during the updated status
        :param is_error: (boolean) the text will show as red if True
        :param user_op: (boolean) whether a status change is requested by user.
                        If True and the current status is not 'Ready', the request will
                        be declined, in which case this function returns False and the
                        status bar shows a warning
        :return: (boolean) whether the status has been updated successfully
        """
        prev = False
        with self.status_mutex:
            if (not user_op) or self.is_ready:
                self._update_status(status, is_ready, is_error)
                self.is_ready = is_ready
            else:
                prev = self.status, self.has_error
                self._update_status('Another task is running... Please try again later',
                                    is_ready=False, is_error=True)

        def back_to_prev(prev_status, prev_has_error):
            # show error for 2 seconds and then go back to the previous status
            with self.status_mutex:
                if not self.is_ready:  # last task still running
                    self._update_status(prev_status, is_ready=False, is_error=prev_has_error)

        if prev:
            self.statusbar.after(2000, back_to_prev, *prev)

        return not bool(prev)

    def valid_options(self):
        if not os.path.isdir(self.outdir):
            messagebox.showerror('Error', 'Please select a valid output directory')
            return False
        if (self.roi_filename is not None) and (len(self.roi_filename) > 0) \
                and (not os.path.isfile(self.roi_filename)):
            messagebox.showerror('Error', 'Please select a valid roi file')
            return False
        return True

    def show_error(self, exception):
        self.update_status(status='Error: ' + str(exception), is_ready=True, is_error=True)
        self.is_ready = True
        raise exception

    def load_pkl_database(self):
        """
        Call this function after a Global instance has been initiated
        """
        try:
            self.update_status(status='Loading database...', is_ready=False)
            self.dataset = DatasetPlus.load_default_database()
            self.update_status(is_ready=True)
            self.root.event_generate('<<Database_loaded>>')  # trigger event
        except Exception as e:
            messagebox.showerror('Error: failed to load database', str(e))
            self.update_status(status='Error: failed to load database. ' + str(e),
                               is_ready=True, is_error=True)
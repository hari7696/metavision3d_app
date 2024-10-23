import logging
import customtkinter as ctk
import os
from multiprocessing import Process, Queue
from .timer import TimerApp
from log_listener import worker_configurer
from CTkMessagebox import CTkMessagebox
logger = logging.getLogger(__name__)
# logger = logging.getLogger(__name__)

class TissuePicker(ctk.CTkFrame):

    """
    This class is used for the Pooling step of the SAMI app
    """

    def __init__(self, master, file_handler, log_queue):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler    
        self.queue = Queue()
        self.check()
        # self.check_queue()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

    def refresh(self):
        pass

    def check(self):
        label = ctk.CTkLabel(self, text="Tissue Picker")
        label.grid(row=0, column=0)


import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging
from tkinter import filedialog, messagebox
import threading
# from sami_tk_utilities import open_file, open_multiple_files
import glob
from .file_handler import FileOpenbutton

logger = logging.getLogger(__name__)

class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame):
        super().__init__(master, )
        self.columnconfigure(0,weight=1)
        self.nav_frame = nav_frame
        
        
        # title = ctk.CTkLabel(nav_frame, text="SAMI", fg_color="gray30", corner_radius=6)
        # title.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        logger.debug("SAMI class initialized")

        # for the SAMI UI, we need to choose whether the processing needs to be done on single file or multiple files 
        
        file_type_variable = ctk.StringVar(value="Single/Multi file?")
        dropdown_file_type_single_multi = ctk.CTkOptionMenu(self.nav_frame,
                                                            values = ["Single file","Multi file"],
                                                            command=self.file_open, 
                                                            variable=file_type_variable)
        dropdown_file_type_single_multi.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")

    def file_open(self, choice):
        file_open = FileOpenbutton(self.nav_frame )
        file_open.file_opening_button(choice)
        file_open.grid(row=0,column=4,padx =(5,0), pady=(2,2),sticky="w")



    def progress_bar(self):
        """
        This bar is used to show the progress of the steps involved

        Each algorithm have its steps

        SAMI algo have following steps:
        step1 : visualization (common for every algoirhtm)
        step2 : Normalization
        step3 : Pooling
        step4 : Clustering
        step5 : Clusters Integration
        """
        pass
        
    
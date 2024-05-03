
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging
from tkinter import filedialog, messagebox
import threading
from sami_tk_utilities import open_file, open_multiple_files
import glob

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
                                                            command=self.file_opening_button, 
                                                            variable=file_type_variable)
        dropdown_file_type_single_multi.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")


        

    def file_opening_button(self, choice):
        """
        Button to open the file dialog to select the file

        if its single file type, It should display open file dialog
        if its multi file type, It should display open directory dialog
        """
        logging.debug(f"Choice is {choice}")
        logging.debug("'file_opening_button' : children count {}".format(len(list(self.nav_frame.winfo_children()))))
         
        

        if choice == "Multi file":
            self.f_open_btn = ctk.CTkButton(self.nav_frame, 
                                text="Open Folder", 
                                command=self.open_multiple_files)
            logging.debug("multi file type selected")
    

        elif choice == "Single file":
            
            self.f_open_btn = ctk.CTkButton(self.nav_frame, 
                                text="Open File", 
                                command=self.open_file)
            logging.debug("Single file type selected")

        self.f_open_btn.grid(row=0,column=4,padx =(5,0), pady=(10,10),sticky="w")

    def open_file(self):
        """
        Open file dialog,

        The moment the folder is opened, its starts reading the files via threading
        """
        self.filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if self.filepath:
            logging.debug(f"Filepath is {self.filepath}")
            self.folder = os.path.dirname(self.filepath)
            self.display_file_loading()
            # threading.Thread(target=self.load_file, args=(self.filepath,),
            #                   daemon=True).start()

    def open_multiple_files(self):

        """ Open folder dialog to select the folder containing the files"""

        self.files_path = filedialog.askopenfilenames(title="Select  multiple files")
        logging.debug(f"Folder path is {self.files_path}")
        # self.display_file_loading()
        # folder_path = os.path.join(self.folder_path,'*.csv')
        # folder_files = glob.glob(folder_path)
        # logging.debug(f"Folder files are {folder_files}")   


        # threading.Thread(target=self.load_file, args=(os.path.join(self.sami_folder,self.sami_multi_file_names[0]),), daemon=True).start()

    def display_file_loading(self): 
        # Displying the loading label
        self.loading_label = ctk.CTkLabel(self.nav_frame, text="Loading...")
        self.loading_label.grid(row=0, column=6, padx=(5, 0), pady=(10, 10), sticky="w")

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
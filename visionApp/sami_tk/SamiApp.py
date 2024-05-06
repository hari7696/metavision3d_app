
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
# from .process_steps import process_state

logger = logging.getLogger(__name__)

class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame):
        super().__init__(master, )
        self.columnconfigure(0,weight=1)
        self.nav_frame = nav_frame
        self.nav_frame.columnconfigure(0,weight=1)
        self.nav_frame.columnconfigure(2,weight=1)
        self.nav_frame.columnconfigure(4,weight=1)
        self.nav_frame.columnconfigure(6,weight=5)
    
        
        
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

        self.create_process_bar()
        logger.debug(f"Number of children in nav_frame: { len(self.nav_frame.winfo_children())}")
        logger.debug("Number of children in parent: {}".format(len(list(self.winfo_children()))))
        self.create_parent_tab_switch()
        self.create_visualization_dock()

    def file_open(self, choice):
        self.file_handler = FileOpenbutton(self.nav_frame)
        self.file_handler.file_opening_button(choice)
        self.file_handler.grid(row=0,column=4,padx =(5,0), pady=(2,2),sticky="w")

    def create_process_bar(self):
        
        self.process_step = ctk.CTkSegmentedButton(master=self.nav_frame,
                               values=["Visualization", 
                                   "Normalization",
                                   "Pooling",
                                   "Clustering", 
                                   "Clusters Integration", 
                                   "Markers",
                                   "Pathways"], 
                                   command=self.execute_selected_step)
        self.process_step.grid(row=0, column=6, padx=(25, 0), pady=(2, 2), sticky="w", columnspan=6)

    def execute_selected_step(self, choice):
        print(f"Processing step: {choice}") 

    def create_parent_tab_switch(self):
        
        self.parent_tab_switch = ctk.CTkTabview(self,bg_color="transparent")
        self.visualization_tab = self.parent_tab_switch.add("Visualization")
        self.visualization_tab.columnconfigure(0,weight=1)
        self.export_tab = self.parent_tab_switch.add("Export")
        self.parent_tab_switch.grid(row=0,column=0,sticky="nsew", padx=5, pady=1)   

    def create_visualization_dock(self):
        for widget in  self.visualization_tab.winfo_children():
            widget.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self.visualization_tab,bg_color="transparent")
        self.root_visualization_frame.grid(row=2,column=0,sticky="nsew")
        self.root_visualization_frame.columnconfigure((0,1),weight=1)
        self.slides_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.slides_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=1)
        self.slides_display_frame = ctk.CTkScrollableFrame(self.slides_frame,height = 450,width =300)
        self.slides_display_frame.grid(row =1,column=0, padx=5,pady=1,sticky ="ew")
        self.visualization_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.visualization_frame.grid(row=0,column=1,sticky="nsew",padx =5,pady=1)
        self.visualization_frame.columnconfigure(0,weight=1)
        self.tab_view = ctk.CTkTabview(self.visualization_frame,width = 500)
        self.tab_view.grid(row=0,column=0,sticky="nsew",padx =5)
        self.slide_tab = self.tab_view.add("Slide")
        self.slide_tab.columnconfigure(0,weight=1)
        self.norm_plot = self.tab_view.add("Norm Plot")
        self.norm_plot.columnconfigure(0,weight=1)
        
            
        self.animation_tab = self.tab_view.add("Animation")
        self.animation_tab.columnconfigure(0,weight=1)
        self.montage_tab = self.tab_view.add("Montage")
        self.montage_tab.columnconfigure(0,weight=1)
        self.tab_view.set("Slide")

        self.cluster_tab = self.tab_view.add("Cluster")
        self.cluster_tab.columnconfigure(0,weight=1)
        self.corr_plot_tab = self.tab_view.add("Corr-Plot")
        self.corr_plot_tab.columnconfigure(0,weight=1)
        self.corr_network_tab = self.tab_view.add("Corr-Network")
        self.corr_network_tab.columnconfigure(0,weight=1)

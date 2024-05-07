
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
        self.process_step = None
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        
        
        # title = ctk.CTkLabel(nav_frame, text="SAMI", fg_color="gray30", corner_radius=6)
        # title.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        logger.debug("SAMI class initialized")

        # for the SAMI UI, we need to choose whether the processing needs to be done on single file or multiple files 
        
        file_type_variable = ctk.StringVar(value="Single/Multi file?")
        self.dropdown_file_type_single_multi = ctk.CTkOptionMenu(self.nav_frame,
                                                            values = ["Single file","Multi file"],
                                                            command=self.file_open, 
                                                            variable=file_type_variable)
        self.dropdown_file_type_single_multi.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")

        self.create_process_bar()
        logger.debug(f"Number of children in nav_frame: { len(self.nav_frame.winfo_children())}")
        logger.debug("Number of children in parent: {}".format(len(list(self.winfo_children()))))
        self.create_parent_tab_switch()
        self.create_visualization_dock()
        self.create_left_visualization_dock()
        

    def file_open(self, choice):
        self.file_handler = FileOpenbutton(self.nav_frame)
        self.file_handler.file_opening_button(choice)
        self.file_handler.grid(row=0,column=4,padx =(5,0), pady=(2,2),sticky="w")
        #updating the process bar based on the file type selected
        self.create_process_bar()

    
    def create_process_bar(self):
        """Bar in the NavFrame to show the process steps
        This bar is gonna trigger the process steps 
        """ 
        # destroying the existing process bar, before creating a new one. The initial value of of process_step is None
        for widget in self.nav_frame.winfo_children():
            if widget == self.process_step:
                widget.destroy()

        logger.debug("value in dropdown:{}".format(self.dropdown_file_type_single_multi.get()))
        # multi file process steps
        values = ["Visualization", "Normalization", "Pooling", "Clustering", 
                  "Clusters Integration", "Markers", "Pathways"]

        if self.dropdown_file_type_single_multi.get() == "Single file":
            values  = ["Visualization", "Normalization", "Pooling",
                    "Clustering", "Markers"]
            
        self.process_step = ctk.CTkSegmentedButton(master=self.nav_frame,
                               values=values,
                                command=self.execute_selected_step)
        self.process_step.grid(row=0, column=6, padx=(25, 0), pady=(2, 2), sticky="w", columnspan=6)

    def create_parent_tab_switch(self):
        """ Parent Tab consists of Visualization and Export tabs"""

        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        self.parent_tab_switch = ctk.CTkTabview(self,bg_color="transparent")
        self.parent_tab_switch.columnconfigure(0,weight=1)
        self.parent_tab_switch.rowconfigure(0,weight=1)

        self.visualization_tab = self.parent_tab_switch.add("Visualization")
        self.export_tab = self.parent_tab_switch.add("Export")
        
        self.visualization_tab.columnconfigure(0,weight=1)
        self.visualization_tab.rowconfigure(0,weight=1)
        
        # it goes to parent frame row 1
        self.parent_tab_switch.grid(row=0,column=0,sticky="new", padx=5)   

    def create_visualization_dock(self):

        """Under the visualization tab, we have two frames, left and right frame
        Left frame is for displaying the files and color maps and right frame is for displaying the results"""
        
        for widget in  self.visualization_tab.winfo_children():
            widget.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self.visualization_tab,bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0,weight=1)
        self.root_visualization_frame.columnconfigure(1,weight=2)
        self.root_visualization_frame.rowconfigure(0,weight=1)


        # splitting the visaulization frame into two parts, left and right side
        self.left_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.right_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.left_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=1)
        self.right_frame.grid(row=0,column=1,sticky="nsew",padx=5,pady=1)
        self.root_visualization_frame.grid(row=0,column=0,sticky="nsew")
        

    def create_left_visualization_dock(self):

        """ This function deals with the left side of the visualization frame
        It consists of file selection and color map display frame and the scrollable frame
        """

        #file selection and color map display frame
        self.left_frame.columnconfigure(0,weight=1)
        self.left_frame.rowconfigure(0,weight=1)
        self.selection_frame = ctk.CTkFrame(self.left_frame)
        self.selection_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=1, columnspan =2)
        # self.file_selection_frame.columnconfigure(0,weight=1)
        self.selection_frame.rowconfigure(0,weight=1)

        # File dropdown
        self.var_file_name = ctk.CTkLabel(self.selection_frame,text="Select File: ")
        self.var_file_name.grid(row=0,column=0,padx=(5,0),pady=10, sticky="e")
        self.file_dropdown = ctk.CTkOptionMenu(master= self.selection_frame,
                                            values=["file1","file2"],
                                            #command=self.change_to_algo_ui
                                            )
        self.file_dropdown.grid(row=0,column=2,padx=(5,0),pady=10, sticky="e")
        
        # Color map dropdown
        self.var_color_map = ctk.CTkLabel(self.selection_frame,text="Select colorMap: ")
        self.var_color_map.grid(row=0,column=4,padx=(5,0),pady=10, sticky="e")
        self.color_map_dropdown = ctk.CTkOptionMenu(master= self.selection_frame,
                                            values=["color1","color2"],
                                            #command=self.change_to_algo_ui
                                            )
        self.color_map_dropdown.grid(row=0,column=6,padx=(5,0),pady=10, sticky="e")
        
        # scrollable frame on the left side of the visualization frame
        self.slides_display_frame = ctk.CTkScrollableFrame(self.left_frame, height=500)
        self.slides_display_frame.grid(row =1,column=0, padx=5,pady=1,sticky ="sew")

    def destroy_children_vis_tabs(self):
        for child in self.right_frame.winfo_children():
            child.destroy()

    def execute_selected_step(self, choice):

        """
        This functions acts as a key trigger for the process steps
        It controls the right framme of the visualization tab

        """

        logger.info(f"Processing step: {choice}") 
        self.destroy_children_vis_tabs()
        logger.debug("num children in vis_tabs:{}".format(len(self.right_frame.winfo_children())))
        
        # tabview visualization on the right frame
        self.right_frame.columnconfigure(0,weight=1)
        self.right_frame.rowconfigure(0,weight=1)
        self.vis_tabs = ctk.CTkTabview(self.right_frame) 
        self.vis_tabs.grid(row=0,column=0,sticky="nsew",padx =5)

        if choice == "Visualization": 
            self.region = self.vis_tabs.add("Region")
            self.animation = self.vis_tabs.add("Animation")
            # self.region.columnconfigure(0,weight=1)
            # self.animation.columnconfigure(0,weight=1)
            # self.norm_plot.columnconfigure(0,weight=1)
        elif choice == "Normalization":
            self.norm_plot = self.vis_tabs.add("Norm Plot")
            self.norma_regions = self.vis_tabs.add("Norm Regions")
            # self.norm_plot.columnconfigure(0,weight=1)
            # self.norma_regions.columnconfigure(0,weight=1)

        elif choice == "Pooling":
            self.pooling = self.vis_tabs.add("Pooling")
            # self.pooling.columnconfigure(0,weight=1)
        elif choice == "Clustering":
            self.clustering = self.vis_tabs.add("Clustering")
            # self.clustering.columnconfigure(0,weight=1)
        elif choice == "Clusters Integration":
            self.cluster_integration = self.vis_tabs.add("Cluster Integration")

        elif choice == "Markers":
            self.marker1 = self.vis_tabs.add("Marker1")
            self.marker2 = self.vis_tabs.add("Marker2")
        elif choice == "Pathways":
             self.pathway1 = self.vis_tabs.add("Pathway2")

        

        
        
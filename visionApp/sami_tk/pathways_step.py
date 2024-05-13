import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging
from multiprocessing import Process, Queue

from .compound_matrix import create_compound_matrix

# from .process_steps import process_state
import math
from pylab import Figure
import numpy as np
from waiting import wait
from PIL import Image, ImageTk

# from customtkinter import CTkImage
from .colormap import *
import io
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from .visualization_step import VisualizationStep
import matplotlib.animation as animation
import time
import threading
from SAMI.preprocessing import pooldata, csv2h5ad
import logging
from .timer import TimerApp
from SAMI.markers import Markers
from SAMI.pathway import Pathway
import scanpy as sc
from .utils import adata_filter
logger = logging.getLogger(__name__)

class PathwaysStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.makers_folder = os.path.join(*[file_handler.working_folder, 'results', 'markers'])
        self.pathways_folder = os.path.join(*[file_handler.working_folder, 'results', 'pathways'])
        self.queue = Queue()
        # self.sami_type = file_handler.file_type

        self.prepare_visualization_dock_type2()
        self.trigger_visz_functions_on_thread_run()
        # self.prep_cluster_int_options_tab()

    def prepare_visualization_dock_type2(self):
        """This visualization is used for the tabs 1. Pooling, 2. Clustering, 3. Clusters Integration, 4. Markers, 5. Pathways
        A separate tabview is created for this type of visualization, as it doesnt need left and right frames
        """

        for child in self.winfo_children():
            child.destroy()

        self.root_visualization_frame = ctk.CTkFrame(
            self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
        self.root_visualization_frame.rowconfigure(0, weight=1)
        # self.root_visualization_frame.rowconfigure(2, weight=5)
        # self.root_visualization_frame.rowconfigure(0, weight=5)
        self.root_visualization_frame.grid(row=0, column=0, sticky="nsew")

        self.vis_tabs = ctk.CTkTabview(self.root_visualization_frame)
        self.vis_tabs.columnconfigure(0, weight=1)
        self.vis_tabs.rowconfigure(0, weight=1)
        self.vis_tabs.grid(row=0, column=0, sticky="new", padx=5)

        self.markers_root_tab = self.vis_tabs.add("Pathways")
        self.markers_root_tab.columnconfigure(0, weight=1)
        self.markers_root_tab.rowconfigure(0, weight = 1)
        self.markers_root_tab.rowconfigure(1, weight = 20)

        #options panel
        self.options_panel = ctk.CTkFrame(self.markers_root_tab, bg_color="transparent")
        self.options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        self.prepare_options_panel()

        # viz_frame

        self.viz_frame = ctk.CTkFrame(self.markers_root_tab, bg_color="transparent")
        self.viz_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.viz_frame.columnconfigure(0, weight=2)
        self.viz_frame.columnconfigure(1, weight=1)

        # breaking down the viz_frame into 2 frames
        self.plot_dot_frame = ctk.CTkFrame(self.viz_frame, bg_color="transparent")
        self.plot_dot_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)

        self.network_frame = ctk.CTkFrame(self.viz_frame, bg_color="transparent")
        self.network_frame.grid(row=0, column=1, sticky="new", padx=5, pady=5)

        self.prepare_options_panel()
    
    def prepare_options_panel(self):

        self.options_panel.columnconfigure(0, weight=1)
        self.options_panel.columnconfigure(1, weight=5)
        self.options_panel.columnconfigure(2, weight=1)
        self.options_panel.columnconfigure(3, weight=1)
        self.options_panel.columnconfigure(4, weight=1)
        self.options_panel.columnconfigure(5, weight=1)
        self.options_panel.columnconfigure(6, weight=5)
        # self.options_panel.columnconfigure(7, weight=1)
        # self.options_panel.columnconfigure(8, weight=1)
        # self.options_panel.columnconfigure(9, weight=1)
        # self.options_panel.columnconfigure(10, weight=1)
        # self.options_panel.columnconfigure(11, weight=1)
        # self.options_panel.columnconfigure(12, weight=1)
        # self.options_panel.columnconfigure(13, weight=1)
        # self.options_panel.columnconfigure(14, weight=1)
        # self.options_panel.columnconfigure(15, weight=1)
        # self.options_panel.columnconfigure(16, weight=1)

        files = os.listdir(self.makers_folder)
        files = [file for file in files if ('_marker.csv') in file]
        logger.info(f"files: {files}")
        logger.info(f"markers folder: {self.makers_folder}")

        # file selection 1
        file_label = ctk.CTkLabel(self.options_panel, text="Select file:" )
        file_label.grid(row=0,column=0,padx=(2,0),pady=2,sticky="ew")    
        _ = tk.StringVar(value='choose file')
        self.file_selection = ctk.CTkComboBox(master= self.options_panel,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.file_selection.grid(row=0,column=1,padx=(2,0),pady=2,sticky="ew")


        # Omics selection
        region2_label = ctk.CTkLabel(self.options_panel, text="Select Omics :" )
        region2_label.grid(row=0,column=2,padx=(2,0),pady=2,sticky="ew")
        _ = tk.StringVar(value='choose omic')
        self.omics_selection = ctk.CTkComboBox(master= self.options_panel,
                                            values= ['metabolomics', 'glycomics', 'lipidomics'],
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 150
                                            )
        self.omics_selection.grid(row=0,column=3,padx=(2,0),pady=2,sticky="ew")

        # adding a Run button to run the markers generation
        self.run_button = ctk.CTkButton(self.options_panel, text="Generate Pathways", command=self.generate_pathways)
        self.run_button.grid(row=0,column=4,padx=(5,5),pady=2,sticky="ew")
        
        # timer button
        self.timer = TimerApp(self.options_panel)
        self.timer.grid(row=0,column=4,padx=(5,5),pady=2,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.options_panel, text="", text_color="yellow")
        self.time_constraint_label.grid(row=0,column=6,padx=(2,0),pady=2,sticky="w")

    def generate_pathways(self):
        
        logger.info("Generating markers button hit")
        # this function run the command of generating markers button
        self.selected_file = self.file_selection.get()
        logger.info(f"selected file: {self.selected_file}")
        print("selected file: ", self.selected_file)
        self.omics = self.omics_selection.get()

        self.timer.start_timer()
        self.time_constraint_label.configure(text="Note : Pathways generation takes roughly 3 minutes", text_color="yellow")
        # creating a process to run the markers generation
        logger.info("creating a process to run the markers generation")
        region = self.selected_file.rstrip('_marker.csv')
        print("region: ", region)
        maker_process = Process(target=self.pathways_actual_run, args=(region, self.omics, self.pathways_folder, self.makers_folder,self.queue))
        maker_process.start()

    @staticmethod
    def pathways_actual_run(selected_file,omics, pathways_folder, makers_folder, queue):
        pathway = Pathway(selected_file, omics, pathways_folder, makers_folder)
        pathway.findpathway()
        queue.put("pathways_done")
        logger.info("pathways done")


    
    def trigger_visz_functions_on_thread_run(self):

        if self.queue.qsize() > 0:

            signal = self.queue.get_nowait()
            if signal == "pathways_done":
                logger.info("pathways thread trigger received")
                # self.prepare_cluster_visualization()
                # self.dsplay_umpa_overlay()
                self.timer.stop_timer()
                self.timer.reset_timer()
                self.time_constraint_label.configure(text="Note : Pathway generation completed", text_color="green")
                # self.prepare_circular_tree_plot()
                # self.prepare_volcano_plot()
                # self.after(500, self.display_circular_plot())
                # self.after(500, self.display_volcano_plot())
            # Schedule the next queue check
            
        logger.info("checking the queue")
        self.after(10000, self.trigger_visz_functions_on_thread_run)

    # def prepare_circular_tree_plot(self):

    #     for child in self.circular_tree_frame.winfo_children():
    #         child.destroy() 

    #     self.circular_tree_frame.columnconfigure(0, weight=1)
    #     self.circular_tree_frame.rowconfigure(0, weight=1)
    #     self.circular_tree_frame.rowconfigure(1, weight=9)

    #     # circular options panel
    #     self.circular_options_panel = ctk.CTkFrame(self.circular_tree_frame, bg_color="transparent")
    #     self.circular_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
    #     # self.circular_options_panel.columnconfigure(0, weight=1)
    #     # self.circular_options_panel.columnconfigure(1, weight=1)
    #     # self.circular_options_panel.columnconfigure(2, weight=1)
    #     # self.circular_options_panel.rowconfigure(0, weight=1)

    #     # image frame
    #     self.circular_image_frame = ctk.CTkFrame(self.circular_tree_frame, bg_color="transparent")
    #     self.circular_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
    #     self.circular_image_frame.columnconfigure(0, weight=1)
    #     self.circular_image_frame.rowconfigure(0, weight=1)


    #     # creating a label to select top N clusters
    #     top_clusters_label = ctk.CTkLabel(self.circular_options_panel, text="Select top N: ")
    #     top_clusters_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    #     #entry box to take value
    #     self.top_n_entry = ctk.CTkEntry(self.circular_options_panel, width=50, placeholder_text= "5",)
    #     self.top_n_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
    #     self.top_n_entry.insert(0, "5")

    #     # button to run the function
    #     self.run_button = ctk.CTkButton(self.circular_options_panel, text="Run", command=self.display_circular_plot)
    #     self.run_button.grid(row=0, column=2, sticky="w", padx=(20,0), pady=5)
        

    # def display_circular_plot(self):
        
    #     if self.circular_image_label is not None:
    #         self.circular_image_label.destroy()

    #     logger.info("displaying circular plot")

    #     # get the value from top N entry
    #     top = int(self.top_n_entry.get())
    #     image_location = self.markers.circular_tree(clusters=None,top=top, show=False, workdir= self.makers_working_folder)
    #     # creating a label to display the image
    #     self.circular_image_label = ctk.CTkLabel(self.circular_image_frame , width=800, height=800)
    #     self.circular_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

    #     ctk_image1 = ctk.CTkImage(light_image=Image.open(image_location),
    #                                  dark_image=None, size = (800,800))
    #     self.circular_image_label.configure(image=ctk_image1)
    #     self.circular_image_label.image = ctk_image1
    
    # def prepare_volcano_plot(self):

    #     for child in self.volcano_frame.winfo_children():
    #         child.destroy()

    #     self.volcano_frame.columnconfigure(0, weight=1)
    #     self.volcano_frame.rowconfigure(0, weight=1)
    #     self.volcano_frame.rowconfigure(1, weight=9)

    #     # options panel 
    #     self.volocano_options_panel = ctk.CTkFrame(self.volcano_frame, bg_color="transparent")
    #     self.volocano_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
    #     # self.volocano_options_panel.columnconfigure(0, weight=1)
    #     # self.volocano_options_panel.columnconfigure(1, weight=1)
    #     # self.volocano_options_panel.columnconfigure(2, weight=1)
    #     # self.volocano_options_panel.rowconfigure(0, weight=1)

    #     # image fram
    #     self.volcano_image_frame = ctk.CTkFrame(self.volcano_frame, bg_color="transparent")
    #     self.volcano_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
    #     self.volcano_image_frame.columnconfigure(0, weight=1)
    #     self.volcano_image_frame.rowconfigure(0, weight=1)


    #     # creating a label to select top N clusters
    #     select_cluster_label = ctk.CTkLabel(self.volocano_options_panel, text="Select cluster: ")
    #     select_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    #     #entry box to take value
    #     self.cluster_selection = ctk.CTkEntry(self.volocano_options_panel, width=50, placeholder_text= "5",)
    #     self.cluster_selection.grid(row=0, column=1, sticky="w", padx=5, pady=5)
    #     self.cluster_selection.insert(0, "1")

    #     # button to run the function
    #     self.run_button = ctk.CTkButton(self.volocano_options_panel, text="Run", command=self.display_volcano_plot)
    #     self.run_button.grid(row=0, column=2, sticky="w", padx=(20,0), pady=5)

    # def display_volcano_plot(self):

    #     if self.volcano_image_label is not None:
    #         self.volcano_image_label.destroy()

    #     # get the value from top N entry
    #     cluster = int(self.cluster_selection.get())
    #     image_location = self.markers.volcano_plot(cluster, show=False, work_dir= self.makers_working_folder)
    #     # creating a label to display the image
    #     self.volcano_image_label = ctk.CTkLabel(self.volcano_image_frame , width=400, height=400)
    #     self.volcano_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

    #     ctk_image2 = ctk.CTkImage(light_image=Image.open(image_location),
    #                                  dark_image=None, size = (400,400))
    #     self.volcano_image_label.configure(image=ctk_image2)
    #     self.volcano_image_label.image = ctk_image2


    
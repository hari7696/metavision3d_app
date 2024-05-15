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
        self.plot_dot_image_label = None
        self.network_image_label = None
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
        self.options_panel.columnconfigure(1, weight=1)
        self.options_panel.columnconfigure(2, weight=1)
        self.options_panel.columnconfigure(3, weight=1)
        self.options_panel.columnconfigure(4, weight=1)
        self.options_panel.columnconfigure(5, weight=1)
        self.options_panel.columnconfigure(6, weight=1)
        # self.options_panel.rowconfigure(0, weight=1)
        self.options_panel.columnconfigure(7, weight=1)
        self.options_panel.columnconfigure(8, weight=1)
        self.options_panel.columnconfigure(9, weight=1)
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
                                            width = 150
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
        self.omics_selection.grid(row=0,column=3,padx=(2,5),pady=2,sticky="ew")

        # adding a Run button to run the markers generation
        self.run_button = ctk.CTkButton(self.options_panel, text="Generate Pathways", command=self.generate_pathways, width=80)
        self.run_button.grid(row=0,column=4,padx=(15,5),pady=2,sticky="ew")
        
        # timer button
        self.timer = TimerApp(self.options_panel)
        self.timer.grid(row=0,column=5,padx=(5,5),pady=2,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.options_panel, text="", text_color="yellow", width = 150)
        self.time_constraint_label.grid(row=0,column=6,padx=(5,5),pady=2,sticky="w")

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
        region = self.selected_file.replace('_marker.csv', '')
        region_specific_pathways_folder = os.path.join(self.pathways_folder, region)
        print("region: ", region)
        # checking the number of clusters in the selected file, need this number for the visualization prep
        temp_df = os.path.join(self.makers_folder, self.selected_file)
        self.num_clusters = pd.read_csv(temp_df)['cluster'].nunique()

        # for class referece
        self.pathway = Pathway(region, self.omics, region_specific_pathways_folder, self.makers_folder)

        # creating the pathway object inside the proces as well to avoid the pickling error/bottlenecks
        maker_process = Process(target=self.pathways_actual_run, args=(region, self.omics, region_specific_pathways_folder, self.makers_folder,self.queue))
        maker_process.start()
        
        #self.pathways_actual_run(region, self.omics, region_specific_pathways_folder, self.makers_folder,self.queue)
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
                self.prepare_plot_dot()
                self.prepare_network_plot()
                self.after(500, self.display_plot_plot())
                self.after(500, self.display_network_plot())
            # Schedule the next queue check
            
        logger.info("checking the queue")
        self.after(10000, self.trigger_visz_functions_on_thread_run)

    def prepare_plot_dot(self):

        for child in self.plot_dot_frame.winfo_children():
            child.destroy() 

        self.plot_dot_frame.columnconfigure(0, weight=1)
        self.plot_dot_frame.rowconfigure(0, weight=1)
        self.plot_dot_frame.rowconfigure(1, weight=9)

        # plot dot options panel
        self.plot_dot_options_panel = ctk.CTkFrame(self.plot_dot_frame, bg_color="transparent")
        self.plot_dot_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.circular_options_panel.columnconfigure(0, weight=1)
        # self.circular_options_panel.columnconfigure(1, weight=1)
        # self.circular_options_panel.columnconfigure(2, weight=1)
        # self.circular_options_panel.rowconfigure(0, weight=1)

        # plot_frame
        self.pot_image_frame = ctk.CTkFrame(self.plot_dot_frame, bg_color="transparent")
        self.pot_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.pot_image_frame.columnconfigure(0, weight=1)
        self.pot_image_frame.rowconfigure(0, weight=1)

        # creating a label to select cluster
        choose_cluster_label = ctk.CTkLabel(self.plot_dot_options_panel, text="choose cluster")
        choose_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        # self.cluster_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        # self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.cluster_entry.insert(0, "1")
        values = np.arange(0, self.num_clusters+1)
        values = [str(value) for value in values]
        _ = ctk.StringVar(value='choose cluster')
        self.cluster_entry = ctk.CTkComboBox(master= self.plot_dot_options_panel,
                                            values=values,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.cluster_entry.set("1")

        # creating a label to select top N clusters
        choose_top_n = ctk.CTkLabel(self.plot_dot_options_panel, text="select top N")
        choose_top_n.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.top_n_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        self.top_n_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.top_n_entry.insert(0, "20")

        # button to run the function
        self.run_button = ctk.CTkButton(self.plot_dot_options_panel, text="Run", command=self.display_plot_plot)
        self.run_button.grid(row=0, column=4, sticky="w", padx=(20,0), pady=5)
        
    def display_plot_plot(self):
        
        if self.plot_dot_image_label is not None:
            self.plot_dot_image_label.destroy()

        logger.info("displaying plot plot")
        # get the value from top N entry
        cluster = int(self.cluster_entry.get())
        top_n = int(self.top_n_entry.get())

        image_location = self.pathway.plot_dot(cluster=cluster,scale=30,height=10,top=top_n,show=False)
        # creating a label to display the image
        self.plot_dot_image_label = ctk.CTkLabel(self.pot_image_frame , text = "", width=1200, height=600)
        self.plot_dot_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image1 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (1200,600))
        self.plot_dot_image_label.configure(image=ctk_image1)
        self.plot_dot_image_label.image = ctk_image1
    
    def prepare_network_plot(self):

        for child in self.network_frame.winfo_children():
            child.destroy() 

        self.network_frame.columnconfigure(0, weight=1)
        self.network_frame.rowconfigure(0, weight=1)
        self.network_frame.rowconfigure(1, weight=9)

        # plot dot options panel
        self.network_options_panel = ctk.CTkFrame(self.network_frame, bg_color="transparent")
        self.network_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.circular_options_panel.columnconfigure(0, weight=1)
        # self.circular_options_panel.columnconfigure(1, weight=1)
        # self.circular_options_panel.columnconfigure(2, weight=1)
        # self.circular_options_panel.rowconfigure(0, weight=1)

        # plot_frame
        self.network_image_frame = ctk.CTkFrame(self.network_frame, bg_color="transparent")
        self.network_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.network_image_frame.columnconfigure(0, weight=1)
        self.network_image_frame.rowconfigure(0, weight=1)

        # creating a label to select cluster
        choose_cluster_label = ctk.CTkLabel(self.network_options_panel, text="choose cluster")
        choose_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        # self.cluster_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        # self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.cluster_entry.insert(0, "1")
        values = np.arange(0, self.num_clusters+1)
        values = [str(value) for value in values]
        _ = ctk.StringVar(value='choose cluster')
        self.network_cluster_entry = ctk.CTkComboBox(master= self.network_options_panel,
                                            values=values,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.network_cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.network_cluster_entry.set("1")

        # creating a label to select top N clusters
        choose_top_n = ctk.CTkLabel(self.network_options_panel, text="select top N")
        choose_top_n.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.network_top_n_entry = ctk.CTkEntry(self.network_options_panel, width=50, placeholder_text= "5",)
        self.network_top_n_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.network_top_n_entry.insert(0, "10")

        # button to run the function
        self.run_button_network = ctk.CTkButton(self.network_options_panel, text="Run", command=self.display_network_plot)
        self.run_button_network.grid(row=0, column=4, sticky="w", padx=(20,0), pady=5)
        
    def display_network_plot(self):

        if self.network_image_label is not None:
            self.network_image_label.destroy()

        # get the value from top N entry
        cluster = int(self.network_cluster_entry.get())
        top_n = int(self.network_top_n_entry.get())

        image_location = self.pathway.pathway_network(cluster=cluster,top=top_n,show=False)
        # creating a label to display the image
        self.network_image_label = ctk.CTkLabel(self.network_image_frame , text = "", width=600, height=600)
        self.network_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image2 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (800,600))
        self.network_image_label.configure(image=ctk_image2)
        self.network_image_label.image = ctk_image2

    
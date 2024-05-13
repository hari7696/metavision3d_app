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
from SAMI.clustering import Clusters, Cluster_Integration
logger = logging.getLogger(__name__)

class ClusterIntergrationStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler
        self.working_folder = os.path.join(*[file_handler.working_folder, 'results', 'clustering'])
        self.umap_overlay_label = None
        self.image_label = None
        self.queue = Queue()
        self.trigger_visz_functions_on_thread_run()
        self.prepare_visualization_dock_type2()
        self.prep_cluster_int_options_tab()




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
        
        self.cluster_int_tab = self.vis_tabs.add("cluster Intergration")
        self.cluster_int_tab.columnconfigure(0, weight=1)
        self.cluster_int_tab.rowconfigure(0, weight = 1)
        self.cluster_int_tab.rowconfigure(1, weight = 20)
        self.cluster_int_tab.rowconfigure(2, weight = 20)


        # cluster options tab
        self.cluster_int_options = ctk.CTkFrame(self.cluster_int_tab, bg_color="transparent")
        self.cluster_int_options.grid(row=0, column=0, sticky="nsw")
        # self.cluster_int_options.columnconfigure(0, weight=1)
        # self.cluster_int_options.rowconfigure(0, weight=1)

        # region1
        self.type1 = ctk.CTkFrame(self.cluster_int_tab, bg_color="transparent")
        self.type1.grid(row=1, column=0, sticky="nsew")
        self.type1.columnconfigure(0, weight=1)

        # region2
        self.type2 = ctk.CTkFrame(self.cluster_int_tab, bg_color="transparent")
        self.type2.grid(row=2, column=0, sticky="nsw")
        self.type2.columnconfigure(0, weight=5)

        # Intergrated cluster overlay umap
        self.cluster_overlay_umap = self.vis_tabs.add("Umpa Overlay")
        self.cluster_overlay_umap.columnconfigure(0, weight=1)
        self.cluster_overlay_umap.rowconfigure(0, weight = 1)

        self.umap_overlay_frame = ctk.CTkFrame(self.cluster_overlay_umap, bg_color="transparent")
        self.umap_overlay_frame.grid(row=0, column=0, sticky="nsew")
        self.umap_overlay_frame.columnconfigure(0, weight=1)
        self.umap_overlay_frame.rowconfigure(0, weight=1)


    def prep_cluster_int_options_tab(self):
        
        self.cluster_int_options.columnconfigure(0, weight=5)
        self.cluster_int_options.columnconfigure(1, weight=5)
        self.cluster_int_options.columnconfigure(2, weight=5)
        self.cluster_int_options.columnconfigure(3, weight=5)
        self.cluster_int_options.columnconfigure(4, weight=5)
        self.cluster_int_options.columnconfigure(5, weight=5)
        self.cluster_int_options.columnconfigure(6, weight=15)
        self.cluster_int_options.rowconfigure(0, weight=1)

        # getting the clustered files
        files = os.listdir(self.working_folder)
        files = [file for file in files if ('_pool') in file and ('h5ad' in file)]

        # region selection 1
        region1_label = ctk.CTkLabel(self.cluster_int_options, text="Select Region1 :" )
        region1_label.grid(row=0,column=0,padx=(5,0),pady=8,sticky="ew")
        
        _ = tk.StringVar(value='choose file')
        self.region1_selection = ctk.CTkComboBox(master= self.cluster_int_options,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.region1_selection.grid(row=0,column=1,padx=(10,0),pady=8,sticky="ew")

        # region selection 2
        region1_labe2 = ctk.CTkLabel(self.cluster_int_options, text="Select Region2 :" )
        region1_labe2.grid(row=0,column=2,padx=(20,0),pady=8,sticky="ew")
        
        _ = tk.StringVar(value='choose file')
        self.region2_selection = ctk.CTkComboBox(master= self.cluster_int_options,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.region2_selection.grid(row=0,column=3,padx=(10,0),pady=8,sticky="ew")

        self.cluster_button = ctk.CTkButton(self.cluster_int_options,text="Run Intergration",command=self.perform_clustering)
        self.cluster_button.grid(row=0,column=4,padx=(50,0),pady=8,sticky="ew")

        # timer button
        self.timer = TimerApp(self.cluster_int_options)
        self.timer.grid(row=0,column=5,padx=(100,0),pady=8,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.cluster_int_options, text="Note : cluster Integration takes roughly 10 minutes", text_color="yellow")
        self.time_constraint_label.grid(row=0,column=6,padx=(10,0),pady=8,sticky="ew")
    
    @staticmethod
    def splitname(adata):
        # name,_ = os.path.splitext(adata)
        # region, modality, resolution = name.split('_')
        # return region, modality, resolution
        # changed for GUI braoder handling
        name = adata.strip('.h5ad')
        #region, modality, resolution = name.split('_')
        resolution = name.split('_')[-1]
        modality = name.split('_')[-2]
        region = '_'.join(name.split('_')[:-2])
        logger.info(f"region : {region}, modality : {modality}, resolution : {resolution}")

        return region, modality, resolution
    
    def prepare_cluster_module(self, ):

        region1, modality1, res1 = self.splitname(self.region1_selection.get())
        region2, modality2, res2 = self.splitname(self.region2_selection.get())

        self.integrated_file1 = os.path.join(self.working_folder, f"{region1}_integrated.h5ad")
        self.integrated_file2 = os.path.join(self.working_folder, f"{region2}_integrated.h5ad")

        logger.info(f"path Integrated file 1 : {self.integrated_file1}")
        logger.info(f"path Integrated file 2 : {self.integrated_file2}")
        
        cluster_int = Cluster_Integration(self.region1_selection.get(), self.region2_selection.get(), self.working_folder)
        
        return cluster_int
    
    @staticmethod
    def cluster_Integration(queue, cluster_int, integrated_file1, integrated_file2):
        
        # checking whether the clustering is already performed or not
        if not (os.path.exists(integrated_file1) and os.path.exists(integrated_file2)):
            logger.info("didnt find any existing file, Performing Integration")
            cluster_int.integrate()
        else:
            logger.info("Clustering already done")
        # sending a message to the queue that thread is completed
        logger.info("sending signal to the queue")
        queue.put("cluster_int_done")
        logger.info("signal sent to the queue")
        logger.info("messages in queue : {}".format(queue.qsize()))

    def perform_clustering(self):
        self.timer.reset_timer()
        self.timer.start_timer()
        self.cluster_int = self.prepare_cluster_module()
        self.time_constraint_label.configure(text="Note : clustering usally takes roughly 10 minutes")
        clustering_process = Process(target=self.cluster_Integration, args=(self.queue, self.cluster_int, 
                                                                   self.integrated_file1, self.integrated_file2))
        clustering_process.start()


    def trigger_visz_functions_on_thread_run(self):

        try:
            logger.info("messages in queue : {}".format(self.queue.qsize()))
            signal = self.queue.get_nowait()
            if signal == "cluster_int_done":
                logger.info("thread trigger received")
                self.prepare_cluster_visualization()
                self.dsplay_umpa_overlay()
                self.timer.stop_timer()
                self.time_constraint_label.configure(text="Clustering Done")
        except Exception as e:
            logger.error(e)
        finally:
            # Schedule the next queue check
            self.after(10000, self.trigger_visz_functions_on_thread_run)
            logger.info("checking the queue")

    def prepare_cluster_visualization(self):

        logging.info("Preparing cluster visualization")

        for child in self.type1.winfo_children():
            child.destroy() 

        for child in self.type2.winfo_children():
            child.destroy() 

        # region1 display
        region1_label = ctk.CTkLabel(self.type1, text="Region 1 :")
        region1_label.grid(row=0, column=0, padx=(5,0), pady=8, sticky="w")

        region, _, _ = self.splitname(self.region1_selection.get())
        image_location1, self.n_clusters = self.cluster_int.plot_umap_cluster(region ,size=50,show=False)

        self.image_label1 = ctk.CTkLabel(self.type1, width=1400, height=400 )
        self.image_label1.grid(row=1, column=0, sticky="w", )
        self.image_label1.columnconfigure(0, weight=1)
        self.image_label1.rowconfigure(0, weight=1)

        ctk_image1 = ctk.CTkImage(light_image=Image.open(image_location1),
                                     dark_image=None, size = (1400,400))

        self.image_label1.configure(image=ctk_image1)
        self.image_label1.image = ctk_image1 

        # region2 display   

        region2_label = ctk.CTkLabel(self.type2, text="Region 2 :")
        region2_label.grid(row=0, column=0, padx=(5,0), pady=8, sticky="w")

        region, _, _ = self.splitname(self.region2_selection.get())
        image_location2, self.n_clusters = self.cluster_int.plot_umap_cluster(region ,size=50,show=False)

        self.image_label2 = ctk.CTkLabel(self.type2, width=1400, height=400 )
        self.image_label2.grid(row=1, column=0, sticky="w", )
        self.image_label2.columnconfigure(0, weight=1)
        self.image_label2.rowconfigure(0, weight=1)

        ctk_image2 = ctk.CTkImage(light_image=Image.open(image_location2),
                                     dark_image=None, size = (1400,400))

        self.image_label2.configure(image=ctk_image2)
        self.image_label2.image = ctk_image2 



    # def prepare_specific_cluster_vis(self):

    #     # a row to select the cluster
    #     for child in self.specific_cluster.winfo_children():
    #         child.destroy()

    #     label = ctk.CTkLabel(self.specific_cluster, text="Select Cluster :")
    #     label.grid(row=0, column=1, padx=(5,0), pady=8, sticky="ew")

    #     _ = tk.StringVar(value='choose cluster to display')
    #     # a combo box to select the cluster
    #     clusters = [str(i) for i in range(self.n_clusters)]
    #     self.cluster_selection = ctk.CTkComboBox(master= self.specific_cluster,
    #                         values=clusters,
    #                         variable=_,
    #                         button_color="#b5b8b0",
    #                         command=self.display_specific_cluster
    #                         )
    #     self.cluster_selection.grid(row=0,column=2,padx=(10,0),pady=8,sticky="ew")

    def dsplay_umpa_overlay(self):

        logging.info("Displaying Umap Overlay")
        
        for child in self.umap_overlay_frame.winfo_children(): 
            child.destroy()

        # a label for the image
        self.umap_overlay_label = ctk.CTkLabel(self.umap_overlay_frame, width=1000, height=700)
        self.umap_overlay_label.grid(row=0, column=0, sticky="ew", )
        self.umap_overlay_label.columnconfigure(0, weight=1)
        self.umap_overlay_label.rowconfigure(0, weight=1)

        # attaching image to the label
        image_location = self.cluster_int.plot_overlap_umap(show=False)
        ctk_image = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (1000,700))
        self.umap_overlay_label.configure(image=ctk_image)
        self.umap_overlay_label.image = ctk_image

       


        

        





        







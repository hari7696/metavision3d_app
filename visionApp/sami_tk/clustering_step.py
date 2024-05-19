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
# import queue
# from .visualization_step import VisualizationStep
import matplotlib.animation as animation
import time
import threading
from SAMI.preprocessing import pooldata, csv2h5ad
import logging
from .timer import TimerApp
from SAMI.clustering import Clusters
from .display_image import ImageDisaplay
logger = logging.getLogger(__name__)

class ClusteringStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler
        self.prepare_visualization_dock_type2()
        self.prep_cluster_options_tab()
        self.cluster_image_label = None
        self.image_label = None
        self.queue = Queue()
        # self.trigger_visz_functions_on_thread_run()



    def prepare_visualization_dock_type2(self):
        """This visualization is used for the tabs 1. Pooling, 2. Clustering, 3. Clusters Integration, 4. Markers, 5. Pathways
        A separate tabview is created for this type of visualization, as it doesnt need left and right frames
        """

        for child in self.winfo_children():
            child.destroy()

        self.root_visualization_frame = ctk.CTkFrame(
            self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
        # self.root_visualization_frame.columnconfigure(1,weight=2)
        self.root_visualization_frame.rowconfigure(0, weight=1)
        self.root_visualization_frame.grid(row=0, column=0, sticky="nsew")

        self.vis_tabs = ctk.CTkTabview(self.root_visualization_frame)
        self.vis_tabs.columnconfigure(0, weight=1)
        self.vis_tabs.rowconfigure(0, weight=1)
        self.vis_tabs.grid(row=0, column=0, sticky="new", padx=5)
        
        self.cluster_tab = self.vis_tabs.add("Clustering")
        self.cluster_tab.columnconfigure(0, weight=1)
        self.cluster_tab.rowconfigure((0), weight = 1)
        self.cluster_tab.rowconfigure((1), weight = 20)
        self.cluster_tab.rowconfigure((2), weight = 7)


        # cluster options tab
        self.cluster_options = ctk.CTkFrame(self.cluster_tab, bg_color="transparent")
        self.cluster_options.grid(row=0, column=0, sticky="nsw")
        # self.cluster_options.columnconfigure(0, weight=1)
        # self.cluster_options.rowconfigure(0, weight=1)

        # cluster visualization tab
        self.cluster_visualization = ctk.CTkFrame(self.cluster_tab, bg_color="transparent")
        self.cluster_visualization.grid(row=1, column=0, sticky="nsew")
        self.cluster_visualization.columnconfigure(0, weight=1)

        # specific cluster tab
        self.specific_cluster = ctk.CTkFrame(self.cluster_tab, bg_color="transparent")
        self.specific_cluster.grid(row=2, column=0, sticky="nsw")

        # self.specific_cluster.rowconfigure(1, weight=1)
        # self.specific_cluster.columnconfigure(1, weight=1)
        # self.specific_cluster.columnconfigure(2, weight=1)


    def prep_cluster_options_tab(self):
        
        self.cluster_options.columnconfigure(0, weight=1)
        self.cluster_options.columnconfigure(1, weight=5)
        self.cluster_options.columnconfigure(2, weight=5)
        self.cluster_options.columnconfigure(3, weight=5)
        self.cluster_options.columnconfigure(4, weight=5)
        self.cluster_options.columnconfigure(5, weight=5)
        self.cluster_options.columnconfigure(5, weight=15)
        self.cluster_options.rowconfigure(0, weight=1)


        file_name_label = ctk.CTkLabel(self.cluster_options, text="Select File :" )
        file_name_label.grid(row=0,column=0,padx=(5,0),pady=8,sticky="ew")
        
        _ = tk.StringVar(value='choose file')

        path = os.path.join(self.file_handler.working_folder, 'pooled_data')
        files = os.listdir(path)
        # print(files)
        #files = [file for file in files if '_pool' in file]

        self.file_selection = ctk.CTkComboBox(master= self.cluster_options,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 200
                                            )
        self.file_selection.grid(row=0,column=1,padx=(10,0),pady=8,sticky="ew")

        # write a label for resolution
        resolution_label = ctk.CTkLabel(self.cluster_options, text="Resolution :")
        resolution_label.grid(row=0,column=2,padx=(10,0),pady=8,sticky="ew")
        self.resolution = ctk.CTkEntry(self.cluster_options,placeholder_text="1",width=100)
        self.resolution.grid(row=0,column=3,padx=(10,0),pady=8,sticky="ew")
        self.resolution.insert(0, "1")

        self.cluster_button = ctk.CTkButton(self.cluster_options,text="Run Clustering",command=self.perform_clustering)
        self.cluster_button.grid(row=0,column=4,padx=(100,0),pady=8,sticky="ew")

        # timer button
        self.timer = TimerApp(self.cluster_options)
        self.timer.grid(row=0,column=5,padx=(200,0),pady=8,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.cluster_options, text="Note : clustering usally takes roughly 10 minutes", text_color="yellow")
        self.time_constraint_label.grid(row=0,column=6,padx=(10,0),pady=8,sticky="ew")

    def prepare_cluster_module(self, ):
        selected_file = self.file_selection.get()
        region = '_'.join(selected_file.split('_')[:-1])
        modality = selected_file.split('_')[-1].split('.')[0] 
        # print(region, modality)   
        res = float(self.resolution.get())
        # print(res)
        file_location = os.path.join(*[self.file_handler.working_folder, 'results', 'clustering'])
        clustered_file = os.path.join(file_location,f'{region}_{modality}_{res}.h5ad')
        cluster = Clusters(region, 
                               modality,
                               res,
                               os.path.join(self.file_handler.working_folder, 'pooled_data'),
                               os.path.join(self.file_handler.working_folder))
        
        return cluster, clustered_file
    @staticmethod
    def clustering(queue, cluster, clustered_file):
        
        response_dict = {}
        # checking whether the clustering is already performed or not
        if not os.path.exists(clustered_file):
            logger.info("didnt any existing file, Performing clustering ")
            cluster.clustering()
        else:
            logger.info("Clustering already done")

        image_location, n_clusters = cluster.plot_umap_cluster(size=50,show=False)
        response_dict['image_location'] = image_location
        response_dict['n_clusters'] = n_clusters

        # sending a message to the queue that thread is completed
        queue.put(response_dict)

    def perform_clustering(self):
        self.timer.reset_timer()
        self.timer.start_timer()
        cluster, clustered_file = self.prepare_cluster_module()
        self.time_constraint_label.configure(text="Note : clustering usally takes roughly 10 minutes")
        self.clustering_process = Process(target=self.clustering, args=(self.queue, cluster,clustered_file ))
        self.clustering_process.start()
        self.trigger_visz_functions_on_thread_run()

    def trigger_visz_functions_on_thread_run(self):

        if not self.queue.empty():
            logger.info("thread trigger received")
            message = self.queue.get()
            self.image_location = message['image_location']
            self.n_clusters = message['n_clusters']
            self.cluster, _ = self.prepare_cluster_module()
            self.prepare_cluster_visualization()
            self.prepare_specific_cluster_vis()
            self.timer.stop_timer()
            self.time_constraint_label.configure(text="Clustering Done")
        if self.clustering_process.is_alive():
            self.after(100, self.trigger_visz_functions_on_thread_run)
        else:
            self.clustering_process.join()

    def prepare_cluster_visualization(self):

        # if self.image_label is not None:
        #     self.image_label.destroy()

        # self.image_label = ctk.CTkLabel(self.cluster_visualization, width=1400, height=450 )
        # self.image_label.grid(row=0, column=0, sticky="nsew", )
        # self.image_label.columnconfigure(0, weight=1)
        # self.image_label.rowconfigure(0, weight=1)

        # ctk_image = ctk.CTkImage(light_image=Image.open(self.image_location),
        #                              dark_image=None, size = (1400,450))

        # self.image_label.configure(image=ctk_image)
        # self.image_label.image = ctk_image 
        for children in self.cluster_visualization.winfo_children():
            children.destroy()

        self.image_display = ImageDisaplay(self.cluster_visualization, self.image_location)
        self.image_display.grid(row=0, column=0, sticky="nsew", )
        self.image_display.columnconfigure(0, weight=1)
        self.image_display.rowconfigure(0, weight=1)

        


    def prepare_specific_cluster_vis(self):

        self.specific_cluster.columnconfigure(0, weight=1)
        self.specific_cluster.columnconfigure(1, weight=1)
        self.specific_cluster.columnconfigure(2, weight=1)
        self.specific_cluster.rowconfigure(0, weight=1)

        for child in self.specific_cluster.winfo_children():
            child.destroy()

        self.frame1 = ctk.CTkFrame(self.specific_cluster)
        self.frame1.grid(row=0, column=0, sticky="nsew", padx=(3,3), pady=(3,3))
        # self.frame1.columnconfigure(0, weight=1)
        # self.frame1.rowconfigure(0, weight=1)

        self.frame2 = ctk.CTkFrame(self.specific_cluster)
        self.frame2.grid(row=0, column=1, sticky="nsew", padx=(3,3), pady=(3,3))
        # self.frame2.columnconfigure(0, weight=1)
        # self.frame2.rowconfigure(0, weight=1)

        self.frame3 = ctk.CTkFrame(self.specific_cluster)
        self.frame3.grid(row=0, column=2, sticky="nsew", padx=(3,3), pady=(3,3))
        # self.frame3.columnconfigure(0, weight=1)
        # self.frame3.rowconfigure(0, weight=1)

        specific_cluster1 = SpecificCluster(self.frame1, self.cluster, self.n_clusters, 0)
        specific_cluster1.grid(row=0, column=0, sticky="nsew")

        specific_cluster2 = SpecificCluster(self.frame2, self.cluster, self.n_clusters, 1)
        specific_cluster2.grid(row=0, column=1, sticky="nsew")

        specific_cluster3 = SpecificCluster(self.frame3, self.cluster, self.n_clusters, 2)
        specific_cluster3.grid(row=0, column=2, sticky="nsew")


       
class SpecificCluster(ctk.CTkFrame):
    def __init__(self, master, cluster, n_clusters, initial_choice=0):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=10)
        self.cluster = cluster
        self.initial_choice = initial_choice
        self.n_clusters = n_clusters
        self.queue = Queue()    
        
        self.cluster_image_label = None

        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")

        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.grid(row=1, column=0, sticky="nsew")


        self.cluster_image_label = ctk.CTkLabel(self.image_frame, text = '', width=630, height=350)
        self.cluster_image_label.grid(row=1, column=0, sticky="ew", )
        self.cluster_image_label.columnconfigure(0, weight=1)
        self.cluster_image_label.rowconfigure(0, weight=1)

        self.loading_label = ctk.CTkLabel(self.nav_frame, text="", text_color="yellow", width = 80)
        self.loading_label.grid(row=0, column=2, padx=(5,0), pady=8, sticky="w")
        self.after(500, self.prepare_specific_cluster_vis())
    
    def prepare_specific_cluster_vis(self):

        # a row to select the cluster
        label = ctk.CTkLabel(self.nav_frame, text="Select Cluster :")
        label.grid(row=0, column=0, padx=(5,0), pady=8, sticky="w")

        _ = tk.StringVar(value='choose cluster to display')
        # a combo box to select the cluster
        clusters = [str(i) for i in range(self.n_clusters)]
        self.cluster_selection = ctk.CTkComboBox(self.nav_frame,
                            values=clusters,
                            variable=_,
                            button_color="#b5b8b0",
                            command=self.display_specific_cluster
                            )
        self.cluster_selection.grid(row=0,column=1,padx=(10,0),pady=8,sticky="w")
        self.cluster_selection.set(str(self.initial_choice))
        self.display_specific_cluster(self.initial_choice)

        # label = ctk.CTkLabel(self.nav_frame, text="Select Cluster :")
        # label.grid(row=0, column=2, padx=(5,0), pady=8, sticky="w")

    def display_specific_cluster(self, choice):

        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()
        
        self.image_getter = Process(target=self.trigger_process_for_specific_cluster, args=(self.cluster, int(choice), 50, False, self.queue))
        self.image_getter.start()
        self.check_queue()

    def check_queue(self):
        if not self.queue.empty():
            image_data = self.queue.get()
            image_temp = Image.open(io.BytesIO(image_data))
            self.display_image(image_temp)
        if self.image_getter.is_alive():
            self.after(100, self.check_queue)
        else:
            self.image_getter.join()

    @staticmethod
    def trigger_process_for_specific_cluster(cluster, choice, size, show=False, queue=None):
        image_path = cluster.plot_select_cluster(choice,size=50,show=False)
        image = Image.open(image_path)
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            image_data = output.getvalue()
        queue.put(image_data)

    def display_image(self, image_data):

        ctk_image = ctk.CTkImage(light_image=image_data,
                                     dark_image=None, size = (400,300))
        self.cluster_image_label.configure(image=ctk_image)
        self.cluster_image_label.image = ctk_image

        self.loading_label.configure(text="")
        

        

        





        







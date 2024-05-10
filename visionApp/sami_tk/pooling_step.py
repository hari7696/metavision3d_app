import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging

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
logger = logging.getLogger(__name__)

class PoolingStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler    
        self.prepare_visualization_dock_type2()
        self.creating_pooling_tab()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

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
        self.vis_tabs.grid(row=0, column=0, sticky="new", padx=5)
        self.vis_tabs.columnconfigure(0, weight=1)
        self.vis_tabs.rowconfigure(0, weight=1)
        # self.pooling_tab = self.vis_tabs.add("Pooling")

        # self.pooling_tab.columnconfigure(0, weight=1)
        # self.pooling_tab.rowconfigure(0, weight=1)
        # self.pooling_tab.grid(row=0, column=0, sticky="nsew")

    def creating_pooling_tab(self):

        self.pooling_tab = self.vis_tabs.add("Pooling")
        # self.pooling_tab.columnconfigure(0, weight=1)
        # self.pooling_tab.rowconfigure(0, weight=1)
        # self.pooling_frame = ctk.CTkFrame(self.pooling_tab)
        # self.pooling_frame.grid(row=0, column=0, sticky="new")
        # self.pooling_frame.columnconfigure(0, weight=1)
        # # self.pooling_frame.columnconfigure((0,1,2), weight=(1,1,1))
        # self.pooling_frame.rowconfigure(0, weight=1)

        # writing a ahead label about functionalty
        self.head_label = ctk.CTkLabel(self.pooling_tab, text="Pooling of the matrix" , font=("Arial", 20))
        self.head_label.grid(row=0, column=0, sticky="nw", padx=5, pady=5)

        # making a button to start the pooling  
        self.pooling_button = ctk.CTkButton(self.pooling_tab, text="Start Pooling", command=self.start_pooling, width=70)
        self.pooling_button.grid(row=1, column=0, sticky="nw", padx=5, pady=5)

    def start_pooling(self):
        
        logger.info("Pooling started")  
        # csv2had conversion
        working_dir = self.file_handler.working_folder
        data_saving_path = os.path.join(working_dir, 'pooled_data')
        
        if not os.path.exists(data_saving_path):
            os.makedirs(data_saving_path)
        logger.info("csv2h5ad started")
        # pooldata()
        csv2h5ad(working_dir, r'^\w+norm\.pq', data_saving_path, split=True)

        logger.info("OMICS started")
        # pooling omics data
        pooldata(working_dir, r'^\w+norm\.pq', data_saving_path, split=True)

        files = os.listdir(data_saving_path)
        str = ""
        for file in files:
            file_name = os.path.basename(file)
            if '_pool' in file_name:
                str = str + file_name + "\n"
        

        self.status_label = ctk.CTkLabel(self.pooling_tab, text="Pooling Completed \n The Following files are generated \n\n{}".format(str), font = ("Arial", 15))
        self.status_label.grid(row=2, column=0, sticky="nsew", padx=0, pady=10)

        self.status_label = ctk.CTkLabel(self.pooling_tab, text="Switch to next step for clustering", font = ("Arial", 18))
        self.status_label.grid(row=3, column=0, sticky="nsew", padx=0, pady=20)

        logger.info("Pooling completed")







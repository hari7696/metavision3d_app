import logging
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
from .compound_matrix import create_compound_matrix
import math
from pylab import Figure
import numpy as np
from waiting import wait
from PIL import Image, ImageTk
import io
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from multiprocessing import Process, Queue
import time
import threading
from SAMI.preprocessing import pooldata, csv2h5ad
from .timer import TimerApp
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
        self.queue = Queue()
        self.prepare_visualization_dock_type2()
        self.creating_pooling_tab()
        # self.check_queue()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

    def refresh(self):
        pass

    def prepare_visualization_dock_type2(self):
        """This visualization is used for the tabs 1. Pooling, 2. Clustering, 3. Clusters Integration, 4. Markers, 5. Pathways
        A separate tabview is created for this type of visualization, as it doesnt need left and right frames
        """

        for child in self.winfo_children():
            child.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
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
        self.pooling_tab.columnconfigure(0, weight=1)
        self.pooling_tab.rowconfigure(0, weight=1)
        self.pooling_frame = ctk.CTkFrame(self.pooling_tab)
        self.pooling_frame.grid(row=0, column=0, sticky="new")
        self.pooling_frame.columnconfigure(0, weight=10)
        self.pooling_frame.columnconfigure(1, weight=3)
        self.pooling_frame.columnconfigure(2, weight=10)
        # self.pooling_frame.columnconfigure((0, 1), weight=1)
        # self.pooling_frame.columnconfigure((0,1,2), weight=(1,1,1))
        # self.pooling_frame.rowconfigure(0, weight=1)

        # breaking own the pooling frame
        # self.pooling_options_frame = ctk.CTkFrame(self.pooling_frame)
        # self.pooling_options_frame.grid(row=0, column=0, sticky="nw", padx=5, pady=5)
        # self.pooling_options_frame.columnconfigure(0, weight=1)
        # self.pooling_options_frame.rowconfigure((0,1,2, 3, 4) ,weight=1)

        # display files
        # display_file_frame = ctk.CTkFrame(self.pooling_frame) 
        # display_file_frame.grid(row=0, column=1, sticky="nw", padx=5, pady=5)



        # writing a ahead label about functionalty
        self.head_label = ctk.CTkLabel(self.pooling_frame, text="Omics Pooling" , font=("Arial", 20))
        self.head_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        # self.head_label.columnconfigure(0, weight=1)
        # self.head_label.rowconfigure(0, weight=1)

        # making a button to start the pooling  
        self.pooling_button = ctk.CTkButton(self.pooling_frame, text="Start Pooling", command=self.spin_seperate_process_for_pooling, width=40)
        self.pooling_button.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # adding a timer
        self.timer = TimerApp(self.pooling_frame)
        self.timer.grid(row=2, column=1, sticky="ew", padx=5, pady=(5, 5))

        # adding a status label
        self.status_label = ctk.CTkLabel(self.pooling_frame, text="", font = ("Arial", 15), width = 80)
        self.status_label.grid(row=3, column=1, sticky="ew", padx=0, pady=10)

        # adding a label to display the files generated
        self.files_label = ctk.CTkLabel(self.pooling_frame, text="", font = ("Arial", 15), width = 300, height = 300)
        self.files_label.grid(row=4, column=1, sticky="ew", padx=0, pady=10, )



    def spin_seperate_process_for_pooling(self):
        self.timer.reset_timer()
        self.timer.start_timer()
        self.status_label.configure(text= "Omics Pooling started")    
        self.process = Process(target=self.start_pooling, args=(self.file_handler.working_folder, self.queue))
        self.process.start()
        self.check_queue()

    def check_queue(self):
        if not self.queue.empty():
            messgae = self.queue.get()
            # print(messgae)
            self.status_label.configure(text= "Omics pooling completed", text_color="green")
            self.files_label.configure(text= messgae)
            self.timer.stop_timer()
        if self.process.is_alive():
            self.master.after(500, self.check_queue)
        else:
            self.process.join()

        # print("checking")
        
    @staticmethod   
    def start_pooling(working_dir, queue):
        
        logger.info("Pooling started")  

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
        queue.put(str)
        logger.info("Pooling completed")









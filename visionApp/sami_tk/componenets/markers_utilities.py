import customtkinter as ctk
import tkinter as tk
from PIL import Image
from multiprocessing import Queue, Process
from .multiselect_dropdown import DropDownMulitSelect
import io
import logging
import numpy as np
import scanpy as sc
from CTkTable import CTkTable
from log_listener import worker_configurer
logger = logging.getLogger(__name__)


class TableApp(ctk.CTkToplevel):
    def __init__(self, matrix_values):
        super().__init__()
        self.title('Dry App')
        self.updated_values= None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        value = matrix_values 

        # scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=500, height=200)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")

        self.table = CTkTable(master=self.scrollable_frame, row=24, column=2, values=value, write=1, width= 250)
        self.table.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # test_button 
        button = ctk.CTkButton(self, text="apply", command=self.upd_values)
        button.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")


    def upd_values(self):
        self.updated_values = self.table.values
        self.destroy()


class DisplayFileInformation(ctk.CTkFrame):

    def __init__(self, master, dict_files, file_number, mode , log_queue=None):
        super().__init__(
            master,
        )
        self.dict_files = dict_files
        self.file_number = file_number
        self.log_queue = log_queue
        self.mode = mode
        self.clustermap_tab = None
        self.region_tab = None
        self.create_layout()
        

    def create_layout(self):

        for i in range(10):
            self.columnconfigure(i, weight=1)

        region_label = ctk.CTkLabel(self, text=f"File {self.file_number} :" )
        region_label.grid(row=0,column=0,padx=(2,4),pady=2,sticky="ew")

        # file selection dropdown
        self.file_name_dropdown = ctk.CTkComboBox(self, width=250, values=list(self.dict_files.keys()), command= self.on_file_name_change)
        self.file_name_dropdown.grid(row=0,column=1,padx=(4,2),pady=2,sticky="ew")
        self.file_name_dropdown.set("")

        # region_selection_
        self.region_selection = ctk.CTkLabel(self, text="Region Selection")
        self.region_selection.grid(row=0,column=2,padx=(10,4),pady=2,sticky="ew")

        # region selection dropdown
        self.region_selection_dropdown = ctk.CTkButton(self, text="Regions", command=self.create_multiselect_dropdown,  fg_color='transparent', border_width=1)
        self.region_selection_dropdown.grid(row=0, column=3, padx=(2,4),pady=2,sticky="ew")

        # region selection text box
        self.selected_values_label = ctk.CTkTextbox(self, height=50, width=300)
        self.selected_values_label.grid(
            row=0, column=4, sticky="ew", padx=(5, 15), pady=(5, 5)
        )
        self.selected_values_label.insert("0.0", "selected values will appear here")

        if self.file_number == 1:
            # clustermap button
            self.clustermap_button = ctk.CTkButton(self, text="Cluster Map", command=self.clusters_comparison,  fg_color='transparent', border_width=1)   
            self.clustermap_button.grid(row=0,column=5,padx=(5,5),pady=2,sticky="ew")
        else:
                        # clustermap button
            self.clustermap_button = ctk.CTkButton(self, text="",  fg_color='transparent', border_width=0)   
            self.clustermap_button.grid(row=0,column=5,padx=(5,5),pady=2,sticky="ew")
            self.clustermap_button.configure(state="disabled")
    
        # a button to display the cluster map
        # self.temp_button = ctk.CTkButton(self, text="Temp", command=self.temp)clear
        
        # self.temp_button.grid(row=0, column=6, padx=(2, 0), pady=2, sticky="ew")

    def clusters_comparison(self):

        if self.clustermap_tab is None or not self.clustermap_tab.winfo_exists():
            self.clustermap_tab = TableApp( self.matrix)
            self.update()
            self.after(100, self.clustermap_tab.focus())
        else:
            self.clustermap_tab.focus()

    def create_multiselect_dropdown(self):
        if self.region_tab is None or not self.region_tab.winfo_exists():
            self.region_tab = DropDownMulitSelect(
                self, self.lst_unique_regions, self.selected_values_label
            )
            self.update()
            self.after(100, self.region_tab.focus())
            
        else:
            self.region_tab.focus()


    def on_file_name_change(self, file_name):

        clustered_file = self.dict_files[file_name]
        adata = sc.read(clustered_file)
        self.lst_unique_regions = list(adata.obs['region'].unique())
        logger.info(f"unique regions: {self.lst_unique_regions}")
        self.lst_clusters = np.sort([int(item) for item in adata.obs['leiden'].unique()])
        self.highest_cluster = self.lst_clusters[-1]

        # on file selection change
        # on file selection change, updating the cluter map default values
        self.matrix = []

        if self.mode == "single":
            for cluster in self.lst_clusters:
                rest_clusters = [str(c) for c in self.lst_clusters if c != cluster]
                rest_clusters = ",".join(rest_clusters)
                self.matrix.append([str(cluster), rest_clusters])
        else:

            for cluster in self.lst_clusters:
                self.matrix.append([str(cluster), str(cluster)])

    def get_values(self):

        if self.file_number ==1:

            if self.region_tab is None:
                regions = self.lst_unique_regions
            else:
                regions = self.region_tab.selected_values

            if self.clustermap_tab is None:
                clusters = self.matrix
            else:
                clusters = self.clustermap_tab.updated_values

            return  self.file_name_dropdown.get(), regions, clusters, self.highest_cluster
        else:
            if self.region_tab is None:
                regions = self.lst_unique_regions
            else:
                regions = self.region_tab.selected_values
            return  self.file_name_dropdown.get(), regions, None, self.highest_cluster




            







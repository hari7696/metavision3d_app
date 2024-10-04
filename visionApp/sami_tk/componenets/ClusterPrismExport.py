import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import os
import logging
from multiprocessing import Process, Queue
from PIL import Image
from sami_tk.colormap import *
from CTkTable import CTkTable
import io
import logging
from .timer import TimerApp
from SAMI.clustering import Clusters
from PRISM.ColumnTable import ColumnTable
from PRISM.NestedTable import NestedTable
from .display_image import ImageDisaplay
from log_listener import worker_configurer
import scanpy as sc
import pandas as pd 
from CTkMessagebox import CTkMessagebox
from .scrollable_multi_select import ScrollableWindowMulitSelect
import copy 
import sys
logger = logging.getLogger(__name__)
# logger = logging.getLogger(__name__)

class ClusterPrismExport(ctk.CTkFrame):
    def __init__(self, master, log_queue, clustered_file, postnorm_file):
        super().__init__(
            master,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.log_queue = log_queue
        self.clustered_file = clustered_file
        self.postnorm_file = postnorm_file
        self.prism_table_value = []
        self.prism_table_value.append(["Table Name", "Clusters", "Regions", "Compounds"])
        self.dict_df = {}
        # metric that keeps track of the maximum number of groups in terms of visualization sake, not literal
        self.prism_metric = 0
        # self.trigger_visz_functions_on_thread_run()
        logger.info("ClusterPrismExport started")
        self.set_templates_dir()
        self.prepare_widgets()
        self.writing_status_queue = Queue()
        self.prism_write_queue = Queue()
        self.raw_writing_status_queue = Queue()

    def set_templates_dir(self):

        try :
            base_path = sys._MEIPASS
            self.templates_dir = os.path.join(base_path, 'templates')
        except Exception as e:
            self.templates_dir = r'C:\Users\ghari\Documents\OPS\UI\prism_export_dry\templates'

        logger.info(f"Templates dir is {self.templates_dir}")
        


        
    def prepare_widgets(self):

        # if not self.is_clustering_ran:
        #     CTkMessagebox(title="Message", message="Please run clustering to export", icon="warning")
        #     return
        
        self.prism_frame = ctk.CTkFrame(self)
        self.prism_frame.grid(row=0, column=0, sticky="nsew")
        self.prism_frame.rowconfigure(0, weight=1)
        self.prism_frame.columnconfigure(0, weight=1)
        self.prism_frame.columnconfigure(1, weight=1)
        self.prism_frame.columnconfigure(2, weight=1)
        self.prism_frame.columnconfigure(3, weight=1)
        
        # for i in range(3):
        #     self.prism_frame.columnconfigure(i, weight=1)

        self.rowconfigure(0, weight=1)

        self.prism_export_label = ctk.CTkLabel(self.prism_frame, text="Prism Export", width=100, font=("Arial", 18))
        self.prism_export_label.grid(row=0, column=0, sticky="nsew", columnspan=3)
        self.prism_export_label.columnconfigure(0, weight=1)



        self.df_clusters = self.hd5adtodf()

        self.lst_compounds = self.df_clusters.columns[4:]
        # logger.info(f"Compounds are {self.lst_compounds}")
        self.lst_cluster_ids  = list(np.sort((self.df_clusters['cluster_id'].astype(int).unique())))
        # logger.info(f"Clusters are {self.lst_cluster_ids}")
        # logger.info(f"Regions are {self.lst_regions}")
        self.lst_regions = list(self.df_clusters['region'].unique())
        
        
        # scrillable frame for clusters
        # a label for the clusters
        
        label = ctk.CTkLabel(self.prism_frame, text="Select Clusters :")
        label.grid(row=1, column=0, padx=(5,0), pady=8, sticky="w")
        self.scrollable_frame_clusters = ScrollableWindowMulitSelect(self.prism_frame, self.lst_cluster_ids)
        self.scrollable_frame_clusters.grid(row=2, column=0, sticky="nsew")

        # for regions
        label = ctk.CTkLabel(self.prism_frame, text="Select Region:")
        label.grid(row=1, column=1, padx=(5,0), pady=8, sticky="w")
        self.scrollable_frame_regions = ScrollableWindowMulitSelect(self.prism_frame, self.lst_regions)
        self.scrollable_frame_regions.grid(row=2, column=1, sticky="nsew")
        

        # scrillable frame for compounds
        # a label for the compounds
        label = ctk.CTkLabel(self.prism_frame, text="Select Compounds :")
        label.grid(row=1, column=2, padx=(5,0), pady=8, sticky="w")
        self.scrollable_frame_compounds = ScrollableWindowMulitSelect(self.prism_frame, self.lst_compounds)
        self.scrollable_frame_compounds.grid(row=2, column=2, sticky="nsew")
        
        # Adding a third frame to display selected Table names
        label = ctk.CTkLabel(self.prism_frame, text="Select Tables :")
        label.grid(row=1, column=3, padx=(5,0), pady=8, sticky="w")
        self.scrollable_table_frame = ctk.CTkScrollableFrame(self.prism_frame, width= 800)
        self.scrollable_table_frame.grid(row=2, column=3, sticky="nsew")

        # Add table frame
        self.add_table_frame = ctk.CTkFrame(self.prism_frame)
        self.add_table_frame.grid(row=3, column=0, columnspan = 8 ,sticky="nsew")
        
        # label
        _  = ctk.CTkLabel(self.add_table_frame, text="Tabe Name:")
        _.grid(row=0, column=0, padx=(5,10), pady=8, sticky="w")
        
        # entry box
        self.table_name = ctk.CTkEntry(self.add_table_frame, placeholder_text="Enter Table Name", width=300)
        self.table_name.grid(row=0, column=1, padx=(15,15), pady=8, sticky="w")
        
        # add button
        self.add_table_button = ctk.CTkButton(self.add_table_frame, text="Add Table", command=self.add_table)
        self.add_table_button.grid(row=0, column=2, padx=(5,0), pady=8, sticky="w")
        
        # clear tables
        self.clear_table_button = ctk.CTkButton(self.add_table_frame, text="Clear Tables", command=self.clear_table)
        self.clear_table_button.grid(row=0, column=3, padx=(5,0), pady=8, sticky="w")
        

        #### button frame
        
        self.button_frame = ctk.CTkFrame(self.prism_frame)
        self.button_frame.grid(row=4, column=0, columnspan = 8 ,sticky="nsew", pady=(5,5), padx=(5,5))
        for i in range(12):
            self.button_frame.columnconfigure(i, weight=1)
        self.button_frame.rowconfigure(0, weight=1)
        
        # checkbox for the Harmony data
        # self.harmony_var = ctk.CTkCheckBox(self.button_frame, text="Harmony Data", command= self.update_df)
        # self.harmony_var.grid(row=2, column=0, padx=(5,0), pady=8, sticky="w")
        # self.harmony_var.deselect()

        # Export to excel button
        self.export_excel_button = ctk.CTkButton(self.button_frame, text="Export to Excel", command=lambda: self.export_to_excel("general"))
        self.export_excel_button.grid(row=2, column=1, padx=(5,0), pady=8, sticky="w")

        # Format 
        # label
        _  = ctk.CTkLabel(self.button_frame, text="Prism Format :")
        _.grid(row=2, column=2, padx=(5,0), pady=8, sticky="w")
        
        # a dropdown for the format
        self.prsim_format = ctk.CTkComboBox(self.button_frame, values=["Columnar", "Group"], button_color="#b5b8b0")
        self.prsim_format.grid(row=2, column=3, padx=(10,0), pady=8, sticky="w")
        
        #prism export button
        self.export_prism_button = ctk.CTkButton(self.button_frame, text="Export to Prism", command=self.export_to_prism)
        self.export_prism_button.grid(row=2, column=4, padx=(5,0), pady=8, sticky="w")

        # adding a button for full raw export
        self.export_full_raw_button = ctk.CTkButton(self.button_frame, text="Export Full Raw", command=self.raw_export_csv)
        self.export_full_raw_button.grid(row=2, column=5, padx=(5,0), pady=8, sticky="w")


        # progress bar
        self.progress_bar = ctk.CTkProgressBar(self.button_frame, width = 100, mode = "indeterminate")
        self.progress_bar.grid(row=2, column=6, padx=(0, 0), pady=(10, 10), sticky="e")



    def update_df(self):
        logger.info("Updating the dataframe")
        self.df_clusters = self.hd5adtodf().copy(deep=True)
        
    def export_to_prism(self):
        
        self.export_prism_button.configure(state="disabled")
        self.progress_bar.start()
        file_path = filedialog.asksaveasfilename(defaultextension=".pzfx")
        if file_path:
            filtered_df = self.filter_dataframe()
            format = self.prsim_format.get()
            temp_dict_df = copy.deepcopy(self.dict_df)  
            
            try:

                if format == "Columnar":

                    for table_name, df in temp_dict_df.items():
                        logger.info(f"Preparing the dataframe for {table_name}")
                        temp_dict_df[table_name], num_clusters = self.prepare_df_for_columnar_prism(df)
                    logger.info("Dataframes are prepared")
                    ct = ColumnTable(temp_dict_df)
                    if not file_path.endswith('.pzfx'):
                        file_path = file_path + '.pzfx'
                    
                    group_num = self.prism_metric   
                    if group_num >15 or group_num < 2:
                        group_num = 15

                    source =  os.path.join(self.templates_dir,  "group{}.pzfx".format(str(group_num)))
                    destination = file_path
                    self.write_prims_file(ct, source, destination)
                    # CTkMessagebox(title="Message", message="Prism export complete", icon="info", option_1 = "Ok")
                    
                elif format == "Group":
                    for table_name, df in temp_dict_df.items():
                        logger.info(f"Preparing the dataframe for {table_name}")
                        temp_dict_df[table_name] = self.prepare_df_for_nested_prism(df)
                    logger.info("Dataframes are prepared")
                    nt = NestedTable(temp_dict_df)

                    self.write_prims_file(nt, os.path.join(self.templates_dir, "nested_template.pzfx") ,file_path )
                    # nt.to_xml( os.path.join(self.templates_dir, "nested_template.pzfx"), file_path)
                    # CTkMessagebox(title="Message", message="Prism export complete", icon="info", option_1 = "Ok")
            except Exception as e :
                logger.error(f"Error in prism export: {e}")
                CTkMessagebox(title="Message", message=f"Prism export failed, take a scrrenshort and save it : {e} ", icon="warning", option_1 = "Ok")
            finally:
                self.export_prism_button.configure(state="normal")
                self.progress_bar.stop()


    def write_prims_file(self, tree, source, destination):

        writing_process = Process(target=self.actual_write_prims_file, args=(tree, source, destination, self.prism_write_queue))
        logger.info("started the prism write process")
        self.progress_bar.start()
        writing_process.start()
        self.check_for_prism_write_completion()


    def check_for_prism_write_completion(self):

        logger.info("checking prism write status")
        if not self.prism_write_queue.empty():
            status = self.prism_write_queue.get()
            if status == "Done":
                CTkMessagebox(title="Message", message="Prism export complete", icon="info", option_1 = "Ok")
                logger.info("Prism export complete, meessage recieved")
                self.export_prism_button.configure(state="normal")
                self.progress_bar.stop()
                return True
        else:
            self.after(1000, self.check_for_prism_write_completion)

    @staticmethod
    def actual_write_prims_file( tree, source, destination, queue):
        tree.to_xml(source, destination)
        queue.put("Done")

    
    @staticmethod       
    def prepare_df_for_columnar_prism(df):
        
        lst_df = []
        num_clusters = len(set(df["cluster_id"]))
        for cluster in np.sort(list(set(df["cluster_id"]))):
            logger.info(df.columns)
            tempdf = df[df['cluster_id'] == cluster].copy(deep=True)

            # checking the region and creating dataframe for each region
            lst_df_holder = []
            for region in tempdf['region'].unique():
                tempdf_region = tempdf[tempdf['region'] == region].copy(deep=True)
                tempdf_region.drop(columns = ['region', 'cluster_id'], inplace = True)
                tempdf_region.reset_index(drop=True, inplace=True)
                if 'index' in tempdf_region.columns:
                    tempdf_region.drop(columns = ['index'], inplace = True)
                tempdf_region.columns = [f"{region}__{col}" for col in tempdf_region.columns]
                lst_df_holder.append(tempdf_region)
            
            tempdf = pd.concat(lst_df_holder, axis = 1)
            new_colums =  {col : f"C{cluster}_{col}" for col in tempdf.columns}
            tempdf = tempdf.rename(columns = new_colums)   
            tempdf.reset_index(drop=True, inplace=True)
            if 'index' in tempdf.columns:
                tempdf.drop(columns = ['index'], inplace = True)
            lst_df.append(tempdf)
        combined_df =  pd.concat(lst_df, axis = 1)
        
        cols_order = list(combined_df.columns)
        cols_order.sort(key=lambda x: (x.split('__')[-1], x.split('__')[0].split('_')[-1]))
        
        logger.info(f"prepared dataframe for prism columnar export")

        return combined_df[cols_order], num_clusters
    
    @staticmethod
    def prepare_df_for_nested_prism(df):
        #returns a dictionary of dataframes
        nested_dict_df = {}
        for cluster in np.sort(list(set(df["cluster_id"]))):
            tempdf = df[df['cluster_id'] == cluster].copy(deep=True)

            lst_df_holder = []
            for region in tempdf['region'].unique():
                tempdf_region = tempdf[tempdf['region'] == region].copy(deep=True)
                tempdf_region.drop(columns = ['region', 'cluster_id'], inplace = True)
                tempdf_region.reset_index(drop=True, inplace=True)
                if 'index' in tempdf_region.columns:
                    tempdf_region.drop(columns = ['index'], inplace = True)
                tempdf_region.columns = [f"{region}__{col}" for col in tempdf_region.columns]

                cols_order = list(tempdf_region.columns)
                cols_order.sort(key = lambda x : x.split('__')[-1])
                lst_df_holder.append(tempdf_region[cols_order])

            tempdf = pd.concat(lst_df_holder, axis = 1)
            tempdf.reset_index(drop=True, inplace=True)
            if 'index' in tempdf.columns:
                tempdf.drop(columns = ['index'], inplace = True)
            nested_dict_df[f"Cluster_{cluster}"] = tempdf
        logger.info(f"prepared dataframe for prism nested export")
            
        return nested_dict_df
            
            
        
    def add_table(self):    

        self.add_table_button.configure(state="disabled")
        
        df, selected_clusters , selected_regions, selected_compounds = self.filter_dataframe()
        self.prism_metric = max(self.prism_metric , len(selected_clusters) * len(selected_regions))

        str_selected_clusters = ", ".join(map(str, selected_clusters))
        if len(selected_clusters) > 20:
            str_selected_clusters = ", ".join(map(str, selected_clusters[:20])) + "......."
        str_selected_regions = ", ".join(map(str, selected_regions))
        if len(selected_regions) > 20:
            str_selected_regions = ", ".join(map(str, selected_regions[:20])) + "......."
        str_selected_compounds = ", ".join(map(str, selected_compounds))
        if len(selected_compounds) > 20:
            str_selected_compounds = ", ".join(map(str, selected_compounds[:20])) + "......."   
        
        # entry checks
        if self.table_name.get() == "":
            CTkMessagebox(title="Message", message="Please enter a table name", icon="warning", option_1 = "Ok")
            self.add_table_button.configure(state="normal")
            return
        
        if len(selected_clusters) == 0:
            CTkMessagebox(title="Message", message="Please select atleast one cluster", icon="warning", option_1 = "Ok")
            self.add_table_button.configure(state="normal")
            return
        
        if len(selected_regions) == 0:
            CTkMessagebox(title="Message", message="Please select atleast one region", icon="warning", option_1 = "Ok")
            self.add_table_button.configure(state="normal")
            return
        
        if len(selected_compounds) == 0:
            CTkMessagebox(title="Message", message="Please select atleast one compound", icon="warning", option_1 = "Ok")
            self.add_table_button.configure(state="normal")
            return

        self.prism_table_value.append([self.table_name.get(),
                                       str_selected_clusters,
                                       str_selected_regions,
                                       str_selected_compounds])
        self.dict_df[self.table_name.get()] = df 
        
        if hasattr(self, 'table'):
            self.table.destroy()
        self.table = CTkTable(master=self.scrollable_table_frame, row=0, column=0, values = self.prism_table_value, wraplength = 150)
        self.table.grid(row=0, column=0, sticky="nsew")
        self.add_table_button.configure(state="normal")
        
    def clear_table(self):
        self.add_table_button.configure(state="normal")
        self.dict_df = {}
        self.prism_table_value = []
        self.prism_metric = 0
        if hasattr(self, 'table'):
            self.table.destroy()
        self.table = CTkTable(master=self.scrollable_table_frame, row=0, column=0, values = [" "], wraplength = 300)
        self.table.grid(row=0, column=0, sticky="nsew")
        self.table.update()
        self.after(300, self.update())
        self.after(300, self.table.update())

    def raw_export_csv(self):
        logger.info("Exporting full raw data")
        file_path2 = filedialog.asksaveasfilename(defaultextension=".csv")
        if file_path2:
            self.export_full_raw_button.configure(state="disabled")
            self.progress_bar.start()
            raw_writing_process = Process(target=self.write_csv, args=(self.df_clusters, file_path2, self.raw_writing_status_queue))
            raw_writing_process.start()
            logger.info("Starting the csv writing process")
            self.check_for_csv_writing_status()

    def check_for_csv_writing_status(self):
        
        logger.info("Checking for csv writing status")
        if not self.raw_writing_status_queue.empty():
            status = self.raw_writing_status_queue.get()
            # logger.info(f"Status is {status}")
            if status == "Done":
                CTkMessagebox(title="Message", message="CSV export complete", icon="info", option_1 = "Ok")
                logger.info("CSV export complete")
                self.export_full_raw_button.configure(state="normal")
                self.progress_bar.stop()
                return True
        else:
            self.after(1000, self.check_for_csv_writing_status)

    @staticmethod
    def write_csv(df, file_path, status_queue):
        df.to_csv(file_path, index=False)
        status_queue.put("Done")
        
    def export_to_excel(self, type):

        # temp_df = pd.concat(self.dict_df.values(), axis = 0)
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if file_path:
            self.progress_bar.start()
            writing_process = Process(target=self.write_excel, args=(self.dict_df, file_path, self.writing_status_queue))
            logger.info("Starting the excel writing process")
            self.check_for_excel_writing_status()
            writing_process.start()
            self.export_excel_button.configure(state="disabled")
            

    def check_for_excel_writing_status(self):
        
        logger.info("Checking for excel writing status")
        if not self.writing_status_queue.empty():
            status = self.writing_status_queue.get()
            logger.info(f"Status is {status}")
            if status == "Done":
                self.progress_bar.stop()
                CTkMessagebox(title="Message", message="Excel export complete", icon="info", option_1 = "Ok")
                logger.info("Excel export complete")
                self.export_excel_button.configure(state="normal")
                return True
        else:
            self.after(1000, self.check_for_excel_writing_status)

    @staticmethod
    def write_excel(dict_df, file_path, status_queue):
        with pd.ExcelWriter(file_path) as writer: 
            for key, value in dict_df.items():
                value.to_excel(writer, index=False, sheet_name = key)
        status_queue.put("Done")

    def filter_dataframe(self):
        selected_compounds = []
        filtered_df = self.df_clusters.copy(deep=True)
        selected_clusters = self.scrollable_frame_clusters.get_selected_files().copy()
        selected_clusters = [int(cluster) for cluster in selected_clusters]
        selected_compounds = list(self.scrollable_frame_compounds.get_selected_files().copy())
        selected_regions = list(self.scrollable_frame_regions.get_selected_files().copy())
        # logger.info(f"Selected clusters are {selected_compounds}")
        # logger.info(f"Selected regions are {selected_regions}")
        selected_compounds.append('cluster_id')
        selected_compounds.append('region')
        # logger.info(f"Selected compounds before are {selected_compounds}")
        # logger.info(f"Selected compounds are {selected_compounds, self.scrollable_frame_compounds.get_selected_files()}")
        filtered_df['cluster_id'] = filtered_df['cluster_id'].astype(int)   
        # logger.info(f"Selected clusters are {selected_clusters}")
        filtered_df = filtered_df[filtered_df['cluster_id'].isin(selected_clusters)]
        filtered_df = filtered_df[filtered_df['region'].isin(selected_regions)]
        filtered_df = filtered_df[selected_compounds]
        logger.info(f"filtered_Df_columns {filtered_df.columns}")
        selected_compounds.remove('cluster_id')
        selected_compounds.remove('region')
        return filtered_df.copy(), selected_clusters , selected_regions, selected_compounds
    
    def hd5adtodf(self):

        # if hasattr(self, 'harmony_var') and self.harmony_var.get() == 1:
        logger.info("Harmony data is selected")
        adata = sc.read(self.clustered_file)
        data = adata.to_df().reset_index(drop=True)
        spatial = pd.DataFrame(adata.obsm['spatial'], columns=['x', 'y'])
        spatial['region'] = adata.obs['region'].reset_index(drop=True)
        cluster = adata.obs['leiden'].reset_index(drop=True)
        df = pd.concat([spatial, cluster, data], axis=1)
        df.rename(columns={'leiden': 'cluster_id'}, inplace=True)
        # else: 
        #     logger.info("Harmony data is not selected")
        #     posrt_norm_adata = sc.read(self.postnorm_file)
        #     clustered_adata = sc.read(self.clustered_file)

        #     data = posrt_norm_adata.to_df().reset_index(drop=True)
        #     spatial = pd.DataFrame(posrt_norm_adata.obsm['spatial'], columns=['x', 'y'])
        #     spatial['region'] = posrt_norm_adata.obs['region'].reset_index(drop=True)

        #     # using clustered data for the cluster id
        #     cluster_id = clustered_adata.obs['leiden'].reset_index(drop=True)
        #     df = pd.concat([spatial, cluster_id, data], axis=1)
        #     df.rename(columns={'leiden': 'cluster_id'}, inplace=True)

        return df
        
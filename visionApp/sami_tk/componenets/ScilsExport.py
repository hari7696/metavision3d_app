import tkinter as tk
import customtkinter as ctk
import os
import logging
from multiprocessing import Process, Queue
import logging
from .timer import TimerApp
from SAMI.clustering import Cluster_Integration
from .display_image import ImageDisaplay
from .cluster_int_selective_clusters import ClusterIntSelectiveClusters
from .timer import TimerApp
from PIL import Image
import scanpy as sc
import anndata
import pickle
import sys
from tkinter import filedialog
from CTkMessagebox import CTkMessagebox
from SCILS.scils_export_r2py import run_scils_export

logger = logging.getLogger(__name__)

class ScilsExportStep(ctk.CTkFrame):

    def __init__(self, master, file_handler, log_queue):
        super().__init__(
            master,
        )
        # self.columnconfigure(0, weight=1)
        # self.rowconfigure(0, weight=1)
        self.log_queue    = log_queue
        self.messgae_queue = Queue()

        try:
            self.base_path = os.path.join(sys._MEIPASS , 'templates')
        except Exception:
            self.base_path = os.path.join(*[os.getcwd(), 'visionApp', 'SCILS'])

        self.create_widgets()
        logger.info("Scils export step created")

    def refresh(self):
        pass

    def create_widgets(self):
        
        # creating a parent frame
        self.parent_frame = ctk.CTkFrame(self)
        self.parent_frame.grid(row=0, column=0, padx=(0, 0), pady=(10, 10), sticky="nsew")
        self.parent_frame.columnconfigure(0, weight=1)
        self.parent_frame.columnconfigure(1, weight=1)
        self.parent_frame.columnconfigure(2, weight=5)
        # self.parent_frame.rowconfigure(0, weight=1)
        self.create_export_pane()

    import pickle

    @staticmethod   
    def pickle_object(obj, file_path):
        """
        Serialize the given object and save it to the specified file path.
        
        :param obj: The object to be pickled.
        :param file_path: The file path where the pickled object will be saved.
        """
        with open(file_path, 'wb') as file:
            pickle.dump(obj, file)

    @staticmethod
    def unpickle_object(file_path):
        """
        Load and deserialize an object from the specified file path.
        
        :param file_path: The file path from where the object will be unpickled.
        :return: The deserialized object.
        """
        with open(file_path, 'rb') as file:
            return pickle.load(file)

    def create_export_pane(self):

        # a lablel for the export pane
        self.lbl_export = ctk.CTkLabel(self.parent_frame, text="Scils Export", font=('Arial', 22))
        self.lbl_export.grid(row=0, column=0, padx=(0, 0), pady=(20, 20), columnspan=2)

        #  a lable 
        ctk.CTkLabel(self.parent_frame, text="Select scils file path").grid(row=1, column=0, padx=(0, 20), pady=(10, 10), sticky="e")

        # a button to select the scils file path
        self.btn_select_scils_file_path = ctk.CTkButton(self.parent_frame, text="Scils File Path", 
                                                        command=self.select_scils_file_path, fg_color='transparent', border_width=1, width = 150)
        
        self.btn_select_scils_file_path.grid(row=1, column=1, padx=(0, 0), pady=(10, 10), sticky="e")
        
        self.scile_file_path_label = ctk.CTkLabel(self.parent_frame, text="")
        self.scile_file_path_label.grid(row=1, column=2, padx=(15, 0), pady=(10, 10), sticky="w")


        # a button to export the scils file
        ctk.CTkLabel(self.parent_frame, text="Scils export save path").grid(row=2, column=0, padx=(0, 20), pady=(10, 10), sticky="e")
        self.btn_export_scils = ctk.CTkButton(self.parent_frame, text="Export Scils", 
                                                        command=self.select_export_scils_file_path, fg_color='transparent', border_width=1, width = 150)
        self.btn_export_scils.grid(row=2, column=1, padx=(0, 0), pady=(10, 10), sticky="e")

        self.scile_export_file_path_label = ctk.CTkLabel(self.parent_frame, text="")
        self.scile_export_file_path_label.grid(row=2, column=2, padx=(15, 0), pady=(10, 10), sticky="w")

        # 
        ctk.CTkLabel(self.parent_frame, text="Peaklist name").grid(row=3, column=0, padx=(0, 20), pady=(10, 10), sticky="e")
        # a box to take peaklist name
        self.entry_peaklist_name = ctk.CTkEntry(self.parent_frame, width = 200)
        self.entry_peaklist_name.grid(row=3, column=1, padx=(0, 0), pady=(10, 10), sticky="e")
        # self.entry_peaklist_name.insert(0, "")

        # a box to take license key
        ctk.CTkLabel(self.parent_frame, text="License Key").grid(row=4, column=0, padx=(0, 20), pady=(10, 10), sticky="e")
        self.entry_license_key = ctk.CTkEntry(self.parent_frame, width = 200)
        self.entry_license_key.grid(row=4, column=1, padx=(0, 0), pady=(10, 10), sticky="e")
        
        if os.path.exists(os.path.join(self.base_path, "license_key.pkl")):
            license_key = self.unpickle_object(os.path.join(self.base_path, "license_key.pkl"))[0]
            self.entry_license_key.insert(0, license_key)

        # self.entry_license_key.insert(0, "130-2448274819-17")

        # a button to export the scils file
        self.btn_export_scils = ctk.CTkButton(self.parent_frame, text="Export Scils", 
                                                        command=self.export_scils)
        
        self.btn_export_scils.grid(row=5, column=1, padx=(0, 0), pady=(10, 10), sticky="e")

        # circular progress bar
        self.progress_bar = ctk.CTkProgressBar(self.parent_frame, width = 50, mode = "indeterminate")
        self.progress_bar.grid(row=6, column=1, padx=(0, 0), pady=(10, 10), sticky="e")

        self.status_label = ctk.CTkLabel(self.parent_frame, text="", width= 200)
        self.status_label.grid(row=6, column=0, padx=(0, 0), pady=(10, 10), sticky="e")

        # adding a textbox to display notes
        self.R_output_textbox = ctk.CTkTextbox(self.parent_frame, width = 10000)
        self.R_output_textbox.grid(row=8, column=0, padx=(0, 0), pady=(10, 10), sticky="w", columnspan=3)
        

        _ = ctk.CTkLabel(self.parent_frame, text="Note: Scils application need to be installed with valid license in the system to export the file.", text_color= "yellow")
        _.grid(row=9, column=0, padx=(0, 0), pady=(10, 10), sticky="w", columnspan=3)


    def select_scils_file_path(self):

        file_path = filedialog.askopenfilename(defaultextension=".slx")
        if file_path:
            self.scils_file_path = file_path
            logger.info(f"Scils file path selected: {file_path}")
            self.scile_file_path_label.configure(text=file_path)


    def select_export_scils_file_path(self):

        file_path = filedialog.asksaveasfilename()
        if file_path:
            if not file_path.endswith(".csv"):
                file_path = file_path + ".csv"
            self.scils_export_file_path = file_path
            logger.info(f"Scils export file path selected: {file_path}")
            self.scile_export_file_path_label.configure(text=file_path)

    def export_scils(self):

        # making a dictionary of the parameters
        params = {
            "scils_file_path": self.scils_file_path,
            "save_path": self.scils_export_file_path,
            "peaklist_name": self.entry_peaklist_name.get(),
            "license_key": self.entry_license_key.get()
        }

        # running the scils export
        # usig multiprocessing
        self.progress_bar.start()
        self.status_label.configure(text="Processing ...")
        logger.info("Scils file export process started")
        self.export_process = Process(target=run_scils_export, args=(params, self.log_queue, self.messgae_queue))
        self.export_process.start()
        self.check_export_status()

        #caching the license key
        self.pickle_object([self.entry_license_key.get()], os.path.join(self.base_path, "license_key.pkl"))

    def check_export_status(self):

        if not self.messgae_queue.empty():
            mess = self.messgae_queue.get()
            messgae = mess['message']
            if messgae == "success":
                CTkMessagebox(title="Info", message="Export completed", option_1= "OK")
                r_output_file = mess['output_file']
                self.write_r_output(r_output_file)
                self.status_label.configure(text="Export completed")
            elif messgae == "failed":
                CTkMessagebox(title="Error", message="Export failed please check output at bottom for more details", option_1= "OK", icon="cancel")
                self.status_label.configure(text="Export failed")
            self.progress_bar.stop()
            
        if self.export_process.is_alive():
            self.master.after(500, self.check_export_status)
        else:
            self.export_process.join()

    def write_r_output(self, r_output_file):
            
            self.R_output_textbox.delete("0.0", "end")  # delete all text
            self.R_output_textbox.insert(tk.END, "Script Output: \n")
            with open(r_output_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    self.R_output_textbox.insert(tk.END, line)







        



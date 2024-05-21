
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
from Metavision_tk import MetaVision3DApp
from sami_tk.SamiApp import SAMIApp
import logging
import sys
import logging
import re
sys.path.append('SAMI')
# Set up logging configuration
# from multiprocessing_logging import install_mp_handler

# class FilteredLogs(logging.Filter):
#     def filter(self, record):
#         if re.search(r'Embedded R', record.getMessage()):
#             return False
#         return True

# logging.basicConfig(filename='file.log', 
#                     level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s', filemode='w')
# logging.getLogger().addFilter(FilteredLogs())
# install_mp_handler()
from logger_tt import setup_logging    

setup_logging(full_context=1, log_path = 'file.log' , 
              config_path = r'C:\Users\ghari\Documents\OPS\UI\metavision3d_app\visionApp\log_config.yaml', use_multiprocessing = True)

class VisionApp(ctk.CTk):

    """DO NOT CHNAGE THIS TEMPLATE, you may update change_to_algo_ui() if new algorithm is added"""

    def __init__(self):
        super().__init__()
        self.title("MetaVision3D")
        self.geometry("1350x710")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        # self.rowconfigure(1,weight=9)
        
        # the Parent, we need to pass to all the algorithm UI classes
        self.parent_frame = ctk.CTkFrame(self)
        self.parent_frame.grid(row=0,column=0,columnspan=2,sticky="nsew")
        self.parent_frame.columnconfigure(0,weight=1)
        self.parent_frame.rowconfigure(0,weight=1)
        self.parent_frame.rowconfigure(1,weight=10)

        self.nav_frame = ctk.CTkFrame(self.parent_frame)
        self.nav_frame.grid(row=0,column=0,sticky="new")
        self.nav_frame.columnconfigure(0,weight=1)
        self.nav_frame.columnconfigure(1,weight=1)
        self.nav_frame.columnconfigure(2,weight=1)
        self.nav_frame.columnconfigure(3,weight=1)
        self.nav_frame.columnconfigure(4,weight=15)
        self.nav_frame.rowconfigure(0,weight=1)

        # self.nav_frame.columnconfigure(5,weight=1)
        
        # self.nav_frame.rowconfigure(0,weight=1)

        algo_default_value = ctk.StringVar(value="Select the ALgorithm")
        self.algo_selection_dropdown = ctk.CTkOptionMenu(master= self.nav_frame,
                                            values=["3D file","SAMI"],
                                            command=self.change_to_algo_ui,
                                            variable=algo_default_value,
                                            )
        self.algo_selection_dropdown.grid(row=0,column=0,padx=(5,5),pady=10, sticky="w")

        self.write_num_children_to_logs()

    def write_num_children_to_logs(self):

        def count_all_children(widget):
            """
            Recursively counts all descendants of a given widget.
            """
            count = len(widget.winfo_children())
            for child in widget.winfo_children():
                count += count_all_children(child)
            return count

        # Assuming self.parent_frame is your root widget from which you want to start counting
        total_children = count_all_children(self.parent_frame)

        logging.info("Frequent_checker :: Total children {}".format(str(total_children)))
        self.after(10000, self.write_num_children_to_logs)
        

    def destroy_children(self):
        """
        Only frames that are gonna stay between switching the algorithms is the NavFrame and the algo_selection_dropdown widget in it
        """
        for child in self.parent_frame.winfo_children():
            if child != self.nav_frame:
                child.destroy()
            
        for child in self.nav_frame.winfo_children():
            if child != self.algo_selection_dropdown:
                child.destroy()


    def change_to_algo_ui(self, choice):
        """
        Switching to respective UI based on the choice
        """

        if choice == "3D file":
            # Destroy all widgets in the parent frame except nav_frame

            self.destroy_children()
            logging.info("num children in parent_frame {}".format(str(len(self.parent_frame.winfo_children()))))
            self.meta_app = MetaVision3DApp(self.parent_frame, self.nav_frame, self.algo_selection_dropdown)
            self.meta_app.grid(row=1, column=0, sticky="nsew")

        elif choice == "SAMI":
            # Destroy all widgets in the parent frame except nav_frame and dropdown bar in it
            self.destroy_children()
            logging.info("num children in parent_frame {}".format(str(len(self.parent_frame.winfo_children()))))
            self.sami_ap = SAMIApp(self.parent_frame, self.nav_frame, self.algo_selection_dropdown)
            self.sami_ap.grid(row=1, column=0, sticky="nsew", pady=(5,0), padx=(0,0),)


if __name__ == "__main__":
    app = VisionApp()
    app.mainloop()


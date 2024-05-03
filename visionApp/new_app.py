
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
from Metavision_tk import MetaVision3DApp
from Sami_tk import SAMIApp
import logging
# Set up logging configuration
logging.basicConfig(filename='../app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')




class VisionApp(ctk.CTk):

    """DO NOT CHNAGE THIS TEMPLATE, you may update change_to_algo_ui() if new algorithm is added"""

    def __init__(self):
        super().__init__()
        self.title("MetaVision3D")
        self.geometry("1350x710")
        self.columnconfigure(0,weight=1)
        
        # the Parent, we need to pass to all the algorithm UI classes
        self.parent_frame = ctk.CTkFrame(self)
        self.parent_frame.grid(row=0,column=0,columnspan=2,sticky="ew")

        self.nav_frame = ctk.CTkFrame(self.parent_frame)
        self.nav_frame.grid(row=1,column=0,columnspan=2,sticky="ew")

        algo_default_value = ctk.StringVar(value="Select the ALgorithm")
        self.algo_selection_dropdown = ctk.CTkOptionMenu(master= self.nav_frame,
                                            values=["3D file","SAMI"],
                                            command=self.change_to_algo_ui,
                                            variable=algo_default_value,

                                            )
        self.algo_selection_dropdown.grid(row=0,column=0,padx=(5,0),pady=10)


        

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
            logging.info("num children {}".format(str(len(self.parent_frame.winfo_children()))))
            self.parent_frame = MetaVision3DApp(self.parent_frame, self.nav_frame)
            # self.parent_frame.grid(row=0, column=0, sticky="nsew")

        elif choice == "SAMI":
            # Destroy all widgets in the parent frame except nav_frame and dropdown bar in it
            self.destroy_children()
            logging.info("num children {}".format(str(len(self.parent_frame.winfo_children()))))
            self.parent_frame = SAMIApp(self.parent_frame, self.nav_frame)
            # self.parent_frame.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = VisionApp()
    app.mainloop()


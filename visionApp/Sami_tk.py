
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging
logger = logging.getLogger(__name__)

class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame):
        super().__init__(master, )
        self.columnconfigure(0,weight=1)
        title = ctk.CTkLabel(nav_frame, text="SAMI", fg_color="gray30", corner_radius=6)
        title.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        logger.info("SAMI class initialized")
    
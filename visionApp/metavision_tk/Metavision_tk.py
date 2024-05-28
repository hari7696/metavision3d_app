
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging
logger = logging.getLogger(__name__)

class MetaVision3DApp(ctk.CTkFrame):

    def __init__(self, master, nav_frame, algo_drop_down):
        super().__init__(master, )
        self.columnconfigure(0,weight=1)
        title = ctk.CTkLabel(nav_frame, text="MetaVision", fg_color="gray30", corner_radius=6)
        title.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        logger.info("Metavision class initialized")
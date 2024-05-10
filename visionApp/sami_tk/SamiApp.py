import tkinter as tk
import customtkinter as ctk
import pandas as pd
import os
import logging
from tkinter import filedialog, messagebox
import threading

# from sami_tk_utilities import open_file, open_multiple_files
import glob
from .file_handler import FileOpenbutton
from .compound_matrix import create_compound_matrix

# from .process_steps import process_state
import math
from pylab import Figure
import numpy as np
from waiting import wait
from PIL import Image, ImageTk
from customtkinter import CTkImage
from .colormap import *
import io
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .visualization_step import VisualizationStep
from .normalization_step import NormalizationStep
from .pooling_step import PoolingStep
import sys
sys.path.append('../SAMI')
logger = logging.getLogger(__name__)


class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.nav_frame = nav_frame
        self.nav_frame.columnconfigure(0, weight=1)
        self.nav_frame.columnconfigure(2, weight=1)
        self.nav_frame.columnconfigure(4, weight=1)
        self.nav_frame.columnconfigure(6, weight=5)
        self.process_step = None
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # title = ctk.CTkLabel(nav_frame, text="SAMI", fg_color="gray30", corner_radius=6)
        # title.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        logger.debug("SAMI class initialized")

        # for the SAMI UI, we need to choose whether the processing needs to be done on single file or multiple files

        file_type_variable = ctk.StringVar(value="Single/Multi file?")
        self.dropdown_file_type_single_multi = ctk.CTkOptionMenu(
            self.nav_frame,
            values=["Single file", "Multi file"],
            command=self.file_open,
            variable=file_type_variable,
        )
        self.dropdown_file_type_single_multi.grid(
            row=0, column=2, padx=(5, 0), pady=(2, 2), sticky="w"
        )

        self.create_process_bar()
        logger.debug(
            f"Number of children in nav_frame: { len(self.nav_frame.winfo_children())}"
        )
        logger.debug(
            "Number of children in parent: {}".format(len(list(self.winfo_children())))
        )
        self.create_parent_tab_switch()
        # self.create_visualization_dock()
        # self.create_left_visualization_dock()

    def file_open(self, choice):
        self.file_handler = FileOpenbutton(self.nav_frame)
        self.file_handler.file_opening_button(choice)
        self.file_handler.grid(row=0, column=4, padx=(5, 0), pady=(2, 2), sticky="w")
        # updating the process bar based on the file type selected
        self.create_process_bar()

    def create_process_bar(self):
        """Bar in the NavFrame to show the process steps
        This bar is gonna trigger the process steps
        """
        # destroying the existing process bar, before creating a new one. The initial value of of process_step is None
        for widget in self.nav_frame.winfo_children():
            if widget == self.process_step:
                widget.destroy()

        logger.debug(
            "value in dropdown:{}".format(self.dropdown_file_type_single_multi.get())
        )
        # multi file process steps
        values = [
            "Visualization",
            "Normalization",
            "Pooling",
            "Clustering",
            "Clusters Integration",
            "Markers",
            "Pathways",
        ]

        if self.dropdown_file_type_single_multi.get() == "Single file":
            values = [
                "Visualization",
                "Normalization",
                "Pooling",
                "Clustering",
                "Markers",
            ]

        self.process_step = ctk.CTkSegmentedButton(
            master=self.nav_frame, values=values, command=self.execute_selected_step
        )
        self.process_step.grid(
            row=0, column=6, padx=(25, 0), pady=(2, 2), sticky="w", columnspan=6
        )

    def create_parent_tab_switch(self):
        """Parent Tab consists of Visualization and Export tabs"""

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.parent_tab_switch = ctk.CTkTabview(self, bg_color="transparent")
        self.parent_tab_switch.columnconfigure(0, weight=1)
        self.parent_tab_switch.rowconfigure(0, weight=1)

        self.visualization_tab = self.parent_tab_switch.add("Visualization")
        self.export_tab = self.parent_tab_switch.add("Export")

        self.visualization_tab.columnconfigure(0, weight=1)
        self.visualization_tab.rowconfigure(0, weight=1)

        # it goes to parent frame row 1
        self.parent_tab_switch.grid(row=0, column=0, sticky="new", padx=5)


    def execute_selected_step(self, choice):
        """
        This functions acts as a key trigger for the process steps
        It controls the right framme of the visualization tab

        """

        logger.info(f"Processing step: {choice}")
        # tabview visualization on the right frame

        if choice == "Visualization":

            self.vis_step = VisualizationStep(self.visualization_tab, self.file_handler)
            self.vis_step.columnconfigure(0, weight=1)
            self.vis_step.rowconfigure(0, weight=1)
            self.vis_step.grid(row=0, column=0, sticky="nsew")

        elif choice == "Normalization":

            self.norm_step = NormalizationStep(self.visualization_tab, self.file_handler)
            self.norm_step.columnconfigure(0, weight=1)
            self.norm_step.rowconfigure(0, weight=1)
            self.norm_step.grid(row=0, column=0, sticky="nsew")
            # self.norm_plot.columnconfigure(0,weight=1)
            # self.norma_regions.columnconfigure(0,weight=1)

        elif choice == "Pooling":
            self.pooling_step = PoolingStep(self, self.file_handler)
            self.pooling_step.columnconfigure(0, weight=1)  
            self.pooling_step.rowconfigure(0, weight=1)
            self.pooling_step.grid(row=0, column=0, sticky="nsew")

            # self.pooling.columnconfigure(0,weight=1)

        elif choice == "Clustering":
            self.prepare_visualization_dock_type2()
            self.clustering = self.vis_tabs2.add("Clustering")
            self.view_clusters = self.vis_tabs2.add("View Clusters")
            self.view_selective_clusters = self.vis_tabs2.add("View Selective Clusters")
            # self.clustering.columnconfigure(0,weight=1)
        elif choice == "Clusters Integration":
            self.prepare_visualization_dock_type2()
            self.intergration = self.vis_tabs2.add("Integration")
            self.compare_clusters = self.vis_tabs2.add("Compare Integrations")
            self.overlay_umap = self.vis_tabs2.add("Overlay uMap")

        elif choice == "Markers":
            self.prepare_visualization_dock_type2()
            self.markers = self.vis_tabs2.add("Markers")
            self.circular_tree = self.vis_tabs2.add("Circular Tree")
            self.volcano_plot = self.vis_tabs2.add("Volcano Plot")

        elif choice == "Pathways":
            self.prepare_visualization_dock_type2()
            self.pathway = self.vis_tabs2.add("Pathways")
            self.plot_dot = self.vis_tabs2.add("Plot Dot")
            self.pathway_network = self.vis_tabs2.add("Pathway Network")

    def handle_choice_visualization(self, choice):
        pass

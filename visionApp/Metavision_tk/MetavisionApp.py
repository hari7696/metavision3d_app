# MetaVisionApp.py
from functools import partial
import io
import math
from optparse import Option
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np
import pandas as pd
import os
import logging
import time 
import threading
from scipy.ndimage import zoom

from colormap import new_cmap1,new_cmap2
import MetaVision3D.MetaNorm3D as algo_meta3d_norm
from MetaVision3D.MetaAlign3D import MetaAlign3D
import MetaVision3D.evaluate as algo_meta3d_evaluate
import MetaVision3D.MetaInterp3D  as algo_meta3d_interp
import MetaVision3D.MetaAtlas3D as algo_meta3d_atlas
from MetaVision3D.MetaImpute3D import MetaImpute3D
from MetaVision3D.MetaAtlas3D import MetaAtlas3D
import nibabel as nib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk, ImageFilter
from vedo import Volume,show,Plotter

from tkinter import filedialog


logger = logging.getLogger(__name__)

class MetaVision3DApp(ctk.CTkFrame):

    def __init__(self, master, nav_frame):
        super().__init__(master, )

        self.nav_frame = nav_frame
        self.columnconfigure(0,weight=1)

        self.open_file_frame = ctk.CTkFrame(self.nav_frame)
        self.open_file_frame.grid(row=0,column=1, padx=5, pady=5, sticky="ew")
        self.open_file_frame.columnconfigure(8,weight=1)
        
        # open_file_btn = ctk.CTkButton(self.open_file_frame, text="Select CSV File", command=self.open_file)
        open_file_btn = ctk.CTkButton(self.open_file_frame, text="Select CSV File", command=self.open_file)
        open_file_btn.grid(row=0,column=0,padx=10, pady=5,sticky="w")
        # open_file_btn.grid(row=0,column=0,padx=(5, 50), pady=5,sticky="w")
        self.cmap_switch_var = ctk.StringVar(value="gray")
        logger.info("Metavision class initialized")  

        self.create_parent_tab_switch()
        self.create_visualization_dock()
        self.cmap_switch_var = ctk.StringVar(value="gray")
        self.show_cmap_switch()
        # self.show_cmap_switch.grid(row=2,column=0,sticky="e",pady=5)
        self.cmap_cbox.configure(state="normal")
        self.compound_matrix=None
        self._3d_tab_exists = False  # Add a flag to track the 3D tab
    
    def open_file(self):
        # if self.slides_display_frame.winfo_exists():
        #     for widget in self.slides_display_frame.winfo_children():
        #         widget.destroy()  
        # if self.slide_tab.winfo_exists():
        #     for widget in self.slide_tab.winfo_children():
        #         widget.destroy()
        # Destroy the 3D tab if it exists
        # if self._3d_tab_exists:
        #     self.tab_view.delete("3D view")
        #     self._3d_tab_exists = False  # Reset the flag
        # if hasattr(self, 'norm_plot_frame') and self.norm_plot_frame is not None:
        #     self.norm_plot_frame.destroy()

        self.filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if self.filepath:
            # print(self.filepath)
            self.display_file_loading()

            self.file_directory = os.path.dirname(self.filepath)
            logger.info(f"Selected directory: {self.file_directory}")

            # Extract the file name from the file path
            self.file_name = os.path.basename(self.filepath)
            logger.info(f"Selected file: {self.file_name}")

            # parts = file_name.split('_')
            # self.group = parts[-1] if len(parts) > 1 else file_name
            self.group = os.path.splitext(self.file_name)[0]

            threading.Thread(target=self.load_file, args=(self.filepath,), daemon=True).start()

    def display_file_loading(self):
        if hasattr(self, 'loading_label') and self.loading_label is not None:
            self.loading_label.destroy()

        self.loading_label = ctk.CTkLabel(self.open_file_frame, text="Loading...")
        self.loading_label.grid(row=0, column=1, padx=(5, 0), pady=(10, 10), sticky="w")

    def load_file(self, filepath):
        self.df = pd.read_csv(filepath, index_col=False)
        self.df = self.df.rename(columns={'region': 'tissue_id'})
        self.tissue_ids = self.df['tissue_id'].unique().tolist()
        logger.info(f"Tissue id's: {self.tissue_ids}")
        self.molecule_names = self.df.columns[1:].tolist()
        self.is_roi=False
        remove_values = ["spotId", "raster", "x", "y", "z", "Date", "Class", "tissue_id","roi"]
        self.molecule_names = [option for option in self.molecule_names if option not in remove_values]

        # Ensure previous widgets are destroyed before creating new ones
        self.destroy_previous_widgets()
        self.create_molecule_dropdown()
        self.create_export_tab()

        if hasattr(self, 'loading_label') and self.loading_label is not None:
            self.loading_label.destroy()

    def destroy_previous_widgets(self):
        if hasattr(self, 'molecule_dropdown') and self.molecule_dropdown is not None:
            self.molecule_dropdown.destroy()
        if hasattr(self, 'process_steps_frame') and self.process_steps_frame is not None:
            self.process_steps_frame.destroy()
        if hasattr(self, 'export_moelcule_options_frame') and self.export_moelcule_options_frame is not None:
            self.export_moelcule_options_frame.destroy()
        if hasattr(self, 'export_tissue_options_frame') and self.export_tissue_options_frame is not None:
            self.export_tissue_options_frame.destroy()    
        if hasattr(self, 'export_norm_options_frame') and self.export_norm_options_frame is not None:
            self.export_norm_options_frame.destroy()             
        if hasattr(self, 'export_output_options_frame') and self.export_output_options_frame is not None:
            self.export_output_options_frame.destroy()                              
        if hasattr(self, 'molecules_cbox_frame') and self.molecules_cbox_frame is not None:
            self.molecules_cbox_frame.destroy()
        if hasattr(self, 'tissue_cbox_frame') and self.tissue_cbox_frame is not None:
            self.tissue_cbox_frame.destroy()

    def create_molecule_dropdown(self):
        if self.molecule_names:
            self.molecule_dropdown_label = ctk.CTkLabel(self.open_file_frame,text="Tissues/Molecules:")
            self.molecule_dropdown_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
            
            self.molecule_dropdown = ctk.CTkComboBox(self.open_file_frame, values=["None"] + self.molecule_names if any(isinstance(x, float) and np.isnan(x) for x in self.molecule_names) else self.molecule_names)
            self.molecule_dropdown.grid(row=0, column=2, padx=10, pady=5, sticky="w")
            
            # Process selection dropdown
            self.process_selection = ctk.CTkComboBox(self.open_file_frame, values=["Select Process", "Impute", "Interpolate", "Both"], command=self.update_interpolation_entry)
            self.process_selection.grid(row=0, column=3, padx=10, pady=5)
    
            # Interpolation (Slices) label and entry
            self.slices_label = ctk.CTkLabel(self.open_file_frame, text="Slices:")
            self.slices_label.grid_remove()  # Hide by default
            
            self.slices_entry = ctk.CTkEntry(self.open_file_frame, placeholder_text="Enter number of slices", width=100)
            self.slices_entry.insert(0, "1")
            self.slices_entry.grid_remove()  # Hide by default
    
            # Imputation (Radius) label and entry
            self.radius_label = ctk.CTkLabel(self.open_file_frame, text="Radius:")
            self.radius_label.grid_remove()  # Hide by default
            
            self.radius_entry = ctk.CTkEntry(self.open_file_frame, placeholder_text="Enter radius", width=100)
            self.radius_entry.insert(0, "1")
            self.radius_entry.grid_remove()  # Hide by default        
    
            # Run button positioned at the rightmost side
            self.process_button = ctk.CTkButton(self.open_file_frame, text="Run", command=self.run_pipeline)
            self.process_button.grid(row=0, column=9, padx=10, pady=5, sticky="e")

    def update_interpolation_entry(self, selected_process):
        selected_process = self.process_selection.get()
    
        # Reset all fields first
        self.slices_label.grid_remove()
        self.slices_entry.grid_remove()
        self.radius_label.grid_remove()
        self.radius_entry.grid_remove()
    
        # Show the appropriate fields based on the selection
        if selected_process == "Interpolate":
            self.slices_label.grid(row=0, column=4, padx=5, pady=5)
            self.slices_entry.grid(row=0, column=5, padx=5, pady=5)
        elif selected_process == "Impute":
            self.radius_label.grid(row=0, column=4, padx=5, pady=5)
            self.radius_entry.grid(row=0, column=5, padx=5, pady=5)
        elif selected_process == "Both":
            self.slices_label.grid(row=0, column=4, padx=5, pady=5)
            self.slices_entry.grid(row=0, column=5, padx=5, pady=5)
            self.radius_label.grid(row=0, column=6, padx=5, pady=5)
            self.radius_entry.grid(row=0, column=7, padx=(5, 100), pady=5)

    def run_pipeline(self):
        # step = self.process_step_var.get()
        logger.info("Resetting the process")
        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()  
        for widget in self.slide_tab.winfo_children():
            widget.destroy()
        
        if self._3d_tab_exists:
            self.tab_view.delete("3D view")
            self._3d_tab_exists = False  # Reset the flag
        logging.info("Destroying the 3D tab")
        if hasattr(self, 'norm_plot_frame') and self.norm_plot_frame is not None:
            self.norm_plot_frame.destroy()
        if hasattr(self, 'ani_ax') and self.ani_ax is not None:
            self.ani_ax.clear()
        if hasattr(self, 'ani_fig') and self.ani_fig is not None:
            self.ani_fig.clear()
        if hasattr(self, 'animation_canvas_widget') and self.animation_canvas_widget is not None:
            self.animation_canvas_widget.destroy()
        if hasattr(self, 'animation_slider') and self.animation_slider is not None:
            self.animation_slider.destroy()
        
        self.molecule_dropdown.configure(state="disabled")
        self.process_button.configure(state="disabled")
        logger.info("Starting the first step - visualization process")
        logger.info("Calling the start_initial_visualization process")
        self.start_initial_visualization()
        logger.info("start_initial_visualization is completed")
        logger.info("Starting the normalization process")
        logger.info("Calling the start_normalization process")
        self.start_normalization()
        logger.info("start_normalization is completed")
        logger.info("Starting the alignment process")
        self.start_allignment()
        logger.info("start_allignment is completed")
        logger.info("Starting the selected process: Interpolate/Impute/Both")
        self.handle_process_selection()
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        logger.info(f"Displaying_individual_images")
        self.display_norm_plot(self.compound_matrix)
        logger.info(f"Displaying_norm_plot")
        self.after(500,self.display_animation())
        self.molecule_dropdown.configure(state="normal")
        self.process_button.configure(state="normal")

    def handle_process_selection(self):
        selected_process = self.process_selection.get()
        if selected_process == "Select Process":
            messagebox.showinfo("Success", "Alignment is done. Please select a process if you would like to continue with imputation/interpolation.")
            return
        self.run_selected_process(selected_process)    

    def run_selected_process(self, selected_process):
        if selected_process == "Impute":
            self.start_imputation()
        elif selected_process == "Interpolate":
            self.start_interp()
        elif selected_process == "Both":
            self.start_imputation()
            self.start_interp()
        else:
            messagebox.showerror("Error", "Invalid process selected. Please select a valid process.")

    def start_initial_visualization(self):
        self.cmap_cbox.configure(state="normal")
        selected_moelcule = self.molecule_dropdown.get()
        logger.info(f"Selected Molecule: {selected_moelcule}")
        meta_visualize = MetaAlign3D(self.group, self.df, selected_moelcule, self.molecule_names[0],  self.filepath, reverse=True)   
        logger.info("MetaAlign3D is completed in start_initial_visualization")
        self.compound_matrix = meta_visualize.create_compound_matrix()
        logger.info(f"self.compound_matrix is created")
        time.sleep(1)
        logger.info(f"Sum of compound_matrix: {self.compound_matrix.sum()}")
        # self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        # logger.info(f"Displaying_individual_images")
        # self.display_norm_plot(self.compound_matrix)
        # logger.info(f"Displaying_norm_plot")
        # self.after(500,self.display_animation())

    def start_normalization(self):
        self.compound = self.molecule_dropdown.get()
        logger.info(self.compound)
        logger.info("Calling MetaNorm3D in start_normalization process")
        meta_norm = algo_meta3d_norm.MetaNorm3D(self.df, first_feature=self.molecule_names[0])
        logger.info("MetaNorm3D is completed in start_normalization process")
        self.norm_df = meta_norm.totalsum_norm()
        logger.info(f"totalsum norm df head: {self.norm_df.head}")
        self.data = meta_norm.section_norm()
        logger.info(f"section norm df head: {self.data.head()}")
        selected_moelcule = self.molecule_dropdown.get()
        logger.info(f"Calling MetaAlign3D in start_normalization process")
        meta_normalize = MetaAlign3D(self.group, self.data, selected_moelcule, self.molecule_names[0], self.filepath, reverse=True) 
        logger.info("MetaAlign3D is completed in start_normalization process")  
        self.compound_matrix = meta_normalize.create_compound_matrix()
        logger.info(f"Sum of compound_matrix: {self.compound_matrix.sum()}")
        # self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        # logger.info(f"Displaying_individual_images")
        # self.display_norm_plot(self.compound_matrix)
        # logger.info(f"Displaying_norm_plot")
        # self.display_animation()
        # logger.info(f"Displaying_animation")

    def start_allignment(self):
        selected_moelcule = self.molecule_dropdown.get()
        logger.info(f"Calling MetaAlign3D in start_allignment process")
        meta_align = MetaAlign3D(self.group, self.data, selected_moelcule, self.molecule_names[0], self.filepath, reverse=True)
        logger.info("MetaAlign3D is completed in start_allignment process")
        self.compound_matrix = meta_align.create_compound_matrix()
        self.compound_matrix = meta_align.seq_align()
        logger.info(f"Sum of compound_matrix: {self.compound_matrix.sum()}")    
        # self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        # logger.info(f"Displaying_individual_images")
        # self.display_norm_plot(self.compound_matrix)
        # logger.info(f"Displaying_norm_plot")
        # self.display_animation()
        # logger.info(f"Displaying_animation")
        self.create_3d_tab()
        logger.info(f"3D tab created")

        # self.allign_rad.configure(state="disabled")  # Disable the "Align" button after alignment
        # self.interp_rad.configure(state="normal")
        # self.process_step_var.set(4)  # Set to 4 to allow imputation/interpolation selection

    def start_imputation(self):
        radius_text = self.radius_entry.get().strip()
        if (not radius_text.isdigit()) or int(radius_text) < 0:
            messagebox.showerror("Error", "Please enter a non-negative integer for Radius")
            return
        radius = int(radius_text)
        # Ensure the compound_matrix is available before starting the imputation process
        # if self.compound_matrix is None:
        #     messagebox.showerror("Error", "Compound matrix is not available. Please complete the alignment process first.")
        #     return
        logger.info("Starting the Imputation process")
        meta_impute = MetaImpute3D(self.compound_matrix, radius)
        logger.info("MetaImpute3D is completed in start_imputation process")
        self.compound_matrix = meta_impute.seq_impute()
        logger.info(f"Sum of compound_matrix: {self.compound_matrix.sum()}")
        # self.display_individual_images(self.cmap_switch_var.get(), self.compound_matrix)
        # logger.info(f"Displaying_individual_images")
        # self.display_norm_plot(self.compound_matrix)
        # logger.info(f"Displaying_norm_plot")
        # self.display_animation()
        # logger.info(f"Displaying_animation")
        # self.interp_rad.configure(state="disabled")  

    def start_interp(self):
        slices_text = self.slices_entry.get().strip()
        if (not slices_text.isdigit()) or int(slices_text) < 0:
            messagebox.showerror("Error", "Please enter a non-negative integer for Slices")
            return
        slices = int(slices_text)
        logger.info("Starting the Interpolation process")
        meta_interp = algo_meta3d_interp.MetaInterp3D(self.compound_matrix, slices)
        logger.info("MetaInterp3D is completed in start_interp process")
        self.compound_matrix = meta_interp.interp()
        logger.info(f"Sum of compound_matrix: {self.compound_matrix.sum()}")
        # self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        # logger.info(f"Displaying_individual_images")
        # self.display_norm_plot(self.compound_matrix)
        # logger.info(f"Displaying_norm_plot")
        # self.display_animation()
        # logger.info(f"Displaying_animation")
        # self.interp_rad.configure(state="disabled")
 
    def reset_process(self):
        logger.info("Resetting the process")
        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()  
        for widget in self.slide_tab.winfo_children():
            widget.destroy()
        logger.info("Destroying the widgets in the slide tab")
        # Destroy the 3D tab if it exists
        if self._3d_tab_exists:
            self.tab_view.delete("3D view")
            self._3d_tab_exists = False  # Reset the flag
        logging.info("Destroying the 3D tab")
        if hasattr(self, 'norm_plot_frame') and self.norm_plot_frame is not None:
            self.norm_plot_frame.destroy()
        self.ani_ax.clear()
        self.ani_fig.clear()
        self.animation_canvas_widget.destroy()
        self.animation_slider.destroy()

        self.molecule_dropdown.configure(state="normal")
        self.process_button.configure(state="normal") # Enable the Run button

        self.process_selection.set("Select Process")
        self.slices_label.grid_remove()  # Hide by default

        self.slices_entry.delete(0, "end")      
        self.slices_entry.insert(0, "1")
        self.slices_entry.grid_remove()  # Hide by default

        # Imputation (Radius) label and entry
        self.radius_label.grid_remove()  # Hide by default
        
        self.radius_entry.delete(0, "end")
        self.radius_entry.insert(0, "1")
        self.radius_entry.grid_remove()  # Hide by default    

        logger.info("Reset process completed")

    def create_parent_tab_switch(self):

        self.parent_tab_switch = ctk.CTkTabview(self,bg_color="transparent")
        self.visualization_tab = self.parent_tab_switch.add("Visualization")
        self.visualization_tab.columnconfigure(0,weight=1)
        self.export_tab = self.parent_tab_switch.add("Export")
        self.parent_tab_switch.grid(row=0,column=0,sticky="nsew", padx=5, pady=1) 

    def create_visualization_dock(self):
        for widget in  self.visualization_tab.winfo_children():
            widget.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self.visualization_tab,bg_color="transparent")
        self.root_visualization_frame.grid(row=2,column=0,sticky="nsew")
        self.root_visualization_frame.columnconfigure((0,1),weight=1)
        self.slides_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.slides_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=5)
        self.slides_display_frame = ctk.CTkScrollableFrame(self.slides_frame,height = 550,width =600)
        self.slides_display_frame.grid(row =1,column=0, padx=5,pady=5,sticky ="ew")
        self.visualization_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.visualization_frame.grid(row=0,column=1,sticky="nsew",padx =5,pady=5)
        self.visualization_frame.columnconfigure(0,weight=1)
        self.tab_view = ctk.CTkTabview(self.visualization_frame,width = 500)
        self.tab_view.grid(row=0,column=0,sticky="nsew",padx =5)
        self.tab_view.columnconfigure(0, weight=1)

        self.slide_tab = self.tab_view.add("Slide")
        self.slide_tab.columnconfigure(0,weight=1)
        self.norm_plot = self.tab_view.add("Norm Plot")
        self.norm_plot.columnconfigure(0,weight=1)     
        self.animation_tab = self.tab_view.add("Animation")
        self.animation_tab.columnconfigure(0,weight=1)
        self.tab_view.set("Slide")


    def create_export_tab(self):
        self.export_tab.columnconfigure((0,1),weight=1)
        self.molecule_checkboxes = []
        self.molecule_vars =[]
        self.tissue_checkboxes=[]
        self.tissue_vars = []
        self.create_norm_options()
        threading.Thread(target=self.create_molecule_checkboxes, args=(), daemon=True).start()
        threading.Thread(target=self.create_tissue_checkboxes, args=(), daemon=True).start()
        self.create_export_output_options()

    def create_molecule_checkboxes(self):
        self.export_moelcule_options_frame = ctk.CTkFrame(self.export_tab)
        self.export_moelcule_options_frame.grid(row=1,column=0,padx=5,pady=5)
        self.molecules_total_var = ctk.StringVar(value = f'Total: {len(self.molecule_names)}')
        self.molecules_total_label = ctk.CTkLabel(self.export_moelcule_options_frame, textvariable=self.molecules_total_var)
        self.molecules_total_label.grid(row=0,column=0,padx=5,pady=5,sticky="e")
        self.molecules_selected_count_var = ctk.StringVar(value= "Selected : 0")
        self.molecules_selected_count_label= ctk.CTkLabel(self.export_moelcule_options_frame,textvariable =self.molecules_selected_count_var)
        self.molecules_selected_count_label.grid(row=0,column=1,padx=5,pady=5)
        self.select_all_moclecules_var = ctk.BooleanVar(value=0)
        self.select_all_molecules_cbox = ctk.CTkCheckBox(self.export_moelcule_options_frame,text="Select All",variable=self.select_all_moclecules_var,command = self.update_all_molecules)
        self.select_all_molecules_cbox.grid(row=0,column=2,padx =5,pady=5)
        self.molecules_cbox_frame = ctk.CTkScrollableFrame(self.export_tab,label_text="Molecules",border_width=2,border_color="#3a423c")
        self.molecules_cbox_frame.grid(row=2,column=0,padx=8,pady=5,sticky="ew")
        for idx,option in enumerate(self.molecule_names):
            var = ctk.IntVar(value =idx)
            cbox = ctk.CTkCheckBox(self.molecules_cbox_frame,text=option,command = self.update_selected_molecules)
            cbox.grid(row=idx,column=0,padx=2,pady=2,sticky="w")
            self.molecule_checkboxes.append(cbox)

    def update_all_molecules(self):
        if self.select_all_moclecules_var.get() == 1:
            for cbox in self.molecule_checkboxes:
                cbox.select()
            self.update_selected_molecules()
        else:
            for cbox in self.molecule_checkboxes:
                cbox.deselect()
            self.update_selected_molecules()

    def update_selected_molecules(self):
        i=0
        for cbox in self.molecule_checkboxes:
            if cbox.get() ==1:
                i=i+1
        self.molecules_selected_count_var.set(f'Selected: {i}')

    def create_tissue_checkboxes(self):
        self.export_tissue_options_frame = ctk.CTkFrame(self.export_tab)
        self.export_tissue_options_frame.grid(row=1,column=1,padx=5,pady=5)
        self.tissue_total_var = ctk.StringVar(value = f'Total: {len(self.tissue_ids)}')
        self.tissue_total_label = ctk.CTkLabel(self.export_tissue_options_frame, textvariable=self.tissue_total_var)
        self.tissue_total_label.grid(row=0,column=0,padx=5,pady=5,sticky="e")
        self.tissue_selected_count_var = ctk.StringVar(value= "Selected : 0")
        self.tissue_selected_count_label= ctk.CTkLabel(self.export_tissue_options_frame,textvariable =self.tissue_selected_count_var)
        self.tissue_selected_count_label.grid(row=0,column=1,padx=5,pady=5)
        self.select_all_tissue_var = ctk.BooleanVar(value=0)
        self.select_all_tissue_cbox = ctk.CTkCheckBox(self.export_tissue_options_frame,text="Select All",variable=self.select_all_tissue_var,command = self.update_all_tissues)
        self.select_all_tissue_cbox.grid(row=0,column=2,padx =5,pady=5)
        self.tissue_cbox_frame = ctk.CTkScrollableFrame(self.export_tab,label_text="Tissues",border_width=2,border_color="#3a423c")
        self.tissue_cbox_frame.grid(row=2,column=1,padx=8,pady=5,sticky="ew")
        for idx,option in enumerate(self.tissue_ids):
            # var = ctk.IntVar(value =idx)
            cbox = ctk.CTkCheckBox(self.tissue_cbox_frame,text=option,command=self.update_selected_tissues)
            cbox.grid(row=idx,column=0,padx=2,pady=2,sticky="w")
            self.tissue_checkboxes.append(cbox)

    def update_selected_tissues(self):
        i=0
        for cbox in self.tissue_checkboxes:
            if cbox.get() ==1:
                i=i+1
        self.tissue_selected_count_var.set(f'Selected: {i}') 

    def update_all_tissues(self):
        if self.select_all_tissue_var.get() == 1:
            for cbox in self.tissue_checkboxes:
                cbox.select()
            self.update_selected_tissues()
        else:
            for cbox in self.tissue_checkboxes:
                cbox.deselect()
            self.update_selected_tissues()

    def change_output_label(self):
        if self.export_file_option.get() ==2 :
            self.output_folder_label.configure(text = "Enter output folder name:")
        else :
            self.output_folder_label.configure(text = "Enter output file name:")

    def create_export_output_options(self):
        self.export_output_options_frame = ctk.CTkFrame(self.export_tab)
        self.export_output_options_frame.grid(row=3,column=0,padx=5,pady=5) 
        self.export_file_option = ctk.IntVar(value=1)
        rad1 = ctk.CTkRadioButton(self.export_output_options_frame,text ="Single CSV",variable= self.export_file_option,value=1,command=self.change_output_label)
        rad1.grid(row=0,column=0,padx=5,pady=5)
        rad2 = ctk.CTkRadioButton(self.export_output_options_frame, text = "Multiple CSVs",variable = self.export_file_option,value =2,command = self.change_output_label)
        rad2.grid(row=0,column=1,padx=5,pady=5)
        self.select_output_dir_button = ctk.CTkButton(self.export_output_options_frame,text="Select output directory",command=self.open_output_dir_select_dialog)
        self.select_output_dir_button.grid(row=1,column=0,padx =5,pady=3,sticky="e")
        self.selected_output_dir_label = ctk.CTkLabel(self.export_output_options_frame,text="")
        self.selected_output_dir_label.grid(row=1,column=1,sticky="w",padx=3,pady=3)
        self.output_folder_label = ctk.CTkLabel(self.export_output_options_frame,text="Enter output file name:")
        self.output_folder_label.grid(row =2,column=0,sticky="e",padx=5,pady=3)
        self.output_folder_entry =ctk.CTkEntry(self.export_output_options_frame)
        self.output_folder_entry.grid(row=2,column=1,sticky="w",padx=3,pady=3)
        self.export_files_button = ctk.CTkButton(self.export_output_options_frame, text = "Export",fg_color="#0ccc36",command=self.export_files)
        self.export_files_button.grid(row=3,column=0) 

    def open_output_dir_select_dialog(self):
        self.output_directory = filedialog.askdirectory(title="Select Output Folder")
        self.selected_output_dir_label.configure(text = self.output_directory)

    def export_files(self):
        # print(self.export_file_option.get())
        selected_molecules = []
        selected_tissues = []
        for cbox in self.molecule_checkboxes:
            if cbox.get() ==1 :
                selected_molecules.append(cbox.cget("text"))
        for cbox in self.tissue_checkboxes:
            if cbox.get()==1:
                selected_tissues.append(cbox.cget("text"))
        logger.info(selected_tissues)

        if self.export_norm_option.get()==1:
            filtered_df = self.df[self.df['tissue_id'].isin(selected_tissues)]
        else:
            filtered_df = self.norm_df[self.norm_df['tissue_id'].isin(selected_tissues)]

        if self.export_file_option.get() == 2:
            for tissue in selected_tissues:
                # Filter the dataframe for each tissue
                tissue_df = filtered_df[filtered_df['tissue_id'] == tissue] 

                # Select only the columns for selected molecules and the tissue_ids
                export_df = tissue_df[['tissue_id'] + selected_molecules]    

                # Create a folder for the tissue if it doesn't exist
                logger.info(f"Output directory:{self.output_directory}")
                # print(self.output_folder_entry.get())
                tissue_folder = os.path.join(os.path.join(self.output_directory,self.output_folder_entry.get()), str(tissue))
                if not os.path.exists(tissue_folder):
                    os.makedirs(tissue_folder)
                
                for molecule in selected_molecules:
                    # print("here2")
                    # Select only the columns for the current molecule and the tissue_ids
                    export_df = tissue_df[['tissue_id', molecule]]
                    
                    # Define the output CSV file path for the current molecule
                    output_csv_path = os.path.join(tissue_folder, f'{molecule}.csv')
                    
                    # Export the filtered dataframe to a CSV file for the current molecule
                    export_df.to_csv(output_csv_path, index=False)
        else :
            # Prepare the DataFrame for selected molecules across all selected tissues
            export_df = filtered_df[['tissue_id'] + selected_molecules]

            # Define the output CSV file path for the consolidated data
            output_csv_path = os.path.join(self.output_directory, str(self.output_folder_entry.get()) + '.csv' )
             
            # Export the consolidated dataframe to a single CSV file
            export_df.to_csv(output_csv_path, index=False)

    def create_norm_options(self):
        self.export_norm_options_frame = ctk.CTkFrame(self.export_tab)
        self.export_norm_options_frame.grid(row=0,column=0,columnspan=2,padx=5,pady=5)
        self.export_norm_option=ctk.IntVar(value=1)
        self.select_norm_label = ctk.CTkLabel(self.export_norm_options_frame,text = "Select Normalization:")
        self.select_norm_label.grid(row=0,column=0)
        rad_norm_1 = ctk.CTkRadioButton(self.export_norm_options_frame,text ="None",variable= self.export_norm_option,value=1)
        rad_norm_1.grid(row=0,column=1,padx=5,pady=5)
        rad_norm_2 = ctk.CTkRadioButton(self.export_norm_options_frame, text = "Total Sum Norm",variable = self.export_norm_option,value =2)
        rad_norm_2.grid(row=0,column=2,padx=5,pady=5)

    def display_individual_images(self, choice,data):
        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()        
        slices, rows, cols = data.shape
        N = round(math.sqrt(slices))
        grid_rows = slices/6
        grid_cols = 6
        if grid_rows * grid_cols < slices:
            grid_rows += 1

        # Create a frame for each image and store it for later processing
        self.vmax = np.percentile(data[data != 0], 99)
        self.frames = []
        for i in range(slices):
            frame = ctk.CTkFrame(self.slides_display_frame,width = 84,height = 48,border_width =2,border_color = "#474644")
            frame.grid(row=i // grid_cols, column=i % grid_cols,padx =2,pady=2)
            # print(data[i])
            self.frames.append((frame, data[i],i))

        # Schedule the image processing after the window is rendered
        self.after(100, self.process_images)

    def process_images(self):
        for frame, image_array, id in self.frames:
            self.display_image_in_frame(image_array, frame,id)

    def display_image_in_frame(self, image_array, frame,id):
       
        fig = Figure(figsize=(4, 4), dpi=150)
        ax = fig.add_subplot(111)
        ax.set_facecolor('black')
        fig.patch.set_facecolor('black')
        if self.cmap_cbox.get()=="magma":
            im = ax.imshow(image_array, cmap=new_cmap1,vmin=0, vmax=self.vmax)
        elif self.cmap_cbox.get()=="viridis":
            im = ax.imshow(image_array, cmap= new_cmap2,vmin=0, vmax=self.vmax)
        else:
            im = ax.imshow(image_array,cmap="gray")
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, facecolor=fig.get_facecolor(), edgecolor='none')
        buf.seek(0)
        resized_image = Image.open(buf)

        # Resize the image to fit the frame
        frame_width = frame.winfo_width()
        frame_height = frame.winfo_height()
        aspect_ratio = resized_image.width / resized_image.height
        new_height = int(frame_width / aspect_ratio)
        resized_image = resized_image.resize((frame_width, new_height))

        # Convert the resized image to a Tkinter PhotoImage
        photo = ImageTk.PhotoImage(resized_image)

        # Create a Label to display the image
        label = tk.Label(frame, image=photo, text="")
        label.image = photo  # Keep a reference
        label.grid(row=0, column=0, padx=2, pady=2)
        label.bind("<Button-1>", partial(self.on_label_click, id=id))

    def on_label_click(self,event,id):
        logger.info(f"Selected slide: {id}") 
        fig = Figure(figsize=(6.5, 5))
        ax = fig.add_subplot(111)

        # Add a Matplotlib canvas to the Tkinter frame
        for widget in self.slide_tab.winfo_children():
            widget.destroy()
        self.slide_tab_frame = ctk.CTkFrame(self.slide_tab)
        self.slide_tab_frame.grid(row=0,column=0,sticky="nsew")
        canvas = FigureCanvasTkAgg(fig, master=self.slide_tab_frame)
        canvas.get_tk_widget().grid(row=0,column=0)
        matrix = self.compound_matrix[id]
        if  self.cmap_switch_var.get() == "gray" :    
            im = ax.imshow(matrix, cmap="gray")
        elif self.cmap_switch_var.get() == "magma" :
            im = ax.imshow(self.compound_matrix[id], cmap=new_cmap1)
            cbar = fig.colorbar(im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5)
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(['low', 'high'])
        elif self.cmap_switch_var.get()== "viridis":
            im = ax.imshow(self.compound_matrix[id], cmap=new_cmap2)
            cbar = fig.colorbar(im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5)
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(['low', 'high'])
        ax.axis('off')

    def display_norm_plot(self,compound_matrix):
        self.norm_plot_frame = ctk.CTkScrollableFrame(self.norm_plot,height =500,width =400)
        self.norm_plot_frame.columnconfigure(0,weight=1)
        self.norm_plot_frame.grid(row=0,column=0,sticky="nsew")
        fig = algo_meta3d_evaluate.norm_boxplot(compound_matrix)
        canvas = FigureCanvasTkAgg(fig, master=self.norm_plot_frame)  # A tk.DrawingArea
        canvas.draw()
        canvas.get_tk_widget().grid(row=0,column=0)

    def update_animation_plot(self,frame):
        # frame = int(float(self.animation_slider.get()))
        self.ani_ax.clear()
        if self.cmap_cbox.get()=="magma":
            self.ani_ax.imshow(self.compound_matrix[frame],cmap=new_cmap1,vmin=0,vmax=self.vmax)
        elif self.cmap_cbox.get()=="viridis":
            self.ani_ax.imshow(self.compound_matrix[frame],cmap=new_cmap2,vmin=0,vmax=self.vmax)
        elif self.cmap_cbox.get()=="gray":
            self.ani_ax.imshow(self.compound_matrix[frame],cmap="gray")
        self.current_frame = frame

    def display_animation(self):
        self.ani_fig, self.ani_ax = plt.subplots()
        self.current_frame = 0
        self.ani = animation.FuncAnimation(self.ani_fig, self.update_animation_plot, frames=len(self.compound_matrix), interval=100)

        # Embed the plot in the Tkinter window
        self.animation_canvas = FigureCanvasTkAgg(self.ani_fig, master=self.animation_tab)
        self.animation_canvas_widget = self.animation_canvas.get_tk_widget()
        self.animation_canvas_widget.grid(row=0,column=0)
        self.animation_slider = ctk.CTkSlider(self.animation_tab,from_=0,to=len(self.compound_matrix)-1,command=self.animation_slider_changed)
        self.animation_slider.grid(row=1,column=0)

    def animation_slider_changed(self,event):
        frame = int(float(self.animation_slider.get()))
        if frame != self.current_frame:
            self.update_animation_plot(frame)
            self.ani.event_source.stop()
            self.animation_canvas.draw()

    def show_cmap_switch(self):
        self.cmap_frame = ctk.CTkFrame(self.slides_frame,bg_color="transparent")
        self.cmap_frame.grid(row=0,column=0,sticky="e",pady=5)
        self.cmap_label = ctk.CTkLabel(self.cmap_frame,text="Set Colormap:")
        self.cmap_label.grid(row=0,column=2,sticky="e")
        self.cmap_cbox = ctk.CTkComboBox(self.cmap_frame,values=["gray","magma","viridis"],command=lambda choice: self.display_individual_images(choice,self.compound_matrix),variable=self.cmap_switch_var,state="disabled")
        self.cmap_cbox.grid(row=0,column=3,sticky="e",padx=(5,0))

    def generate_3d_file(self):   
        self.resolution = 1
        try:
            self.thickness = int(self.thickness_entry_var.get().strip())
            if self.thickness < 0:
                raise ValueError("Negative value not allowed")
            logger.info(f"Thickness {self.thickness}")
        except ValueError:
            messagebox.showerror("Error", "Only non negative integer values are allowed for Thickness")
            return

        try:
            self.gap = int(self.gap_entry_var.get().strip())
            if self.gap < 0:
                raise ValueError("Negative value not allowed")
            logger.info(f"Gap {self.gap}")
        except ValueError:
            messagebox.showerror("Error", "Only non negative integer values are allowed for Gap")
            return

        try:
            slices_text = self.slices_entry.get().strip()
            if slices_text == "":
                self.slices = 0  # Default to 0 if no value is entered
            else:
                self.slices = int(slices_text)
            logger.info(f"Slices {self.slices}")   
        except ValueError:
            messagebox.showerror("Error", "Only positive integer values are allowed for Slices")
            return

        atlas_data = MetaAtlas3D(self.compound_matrix, self.resolution, self.thickness, self.gap, self.slices)
        self.nii_data= atlas_data.create_nii()

    def create_3d_tab(self):
        self._3d_tab= self.tab_view.add("3D view")
        self._3d_tab.columnconfigure(0,weight=1)

        self.res_frame = ctk.CTkFrame(self._3d_tab)
        self.res_frame.grid(row=0,column=0,sticky="w", padx=5, pady=5)

        self.thickness_entry_label = ctk.CTkLabel(self.res_frame,text="Thickness")
        self.thickness_entry_label.grid(row=0,column=1,padx=5,pady=5,sticky="w")
        self.thickness_entry_var = ctk.StringVar(value="1")
        self.thickness_entry = ctk.CTkEntry(self.res_frame,textvariable=self.thickness_entry_var)
        self.thickness_entry.grid(row=1,column=1,padx=5,pady=5,sticky="w") 

        self.gap_entry_label = ctk.CTkLabel(self.res_frame,text="Gap")
        self.gap_entry_label.grid(row=0,column=2,padx=5,pady=5,sticky="w")
        self.gap_entry_var = ctk.StringVar(value="0")
        self.gap_entry = ctk.CTkEntry(self.res_frame,textvariable=self.gap_entry_var)
        self.gap_entry.grid(row=1,column=2,padx=5,pady=5,sticky="w") 

        self.nii_modes_frame = ctk.CTkFrame(self._3d_tab)
        self.nii_modes_frame.grid(row=1,column=0,sticky="w", padx=5, pady=5)

        self.nii_mode_var = ctk.IntVar(value=1)
        rad_mode_1 = ctk.CTkRadioButton(self.nii_modes_frame,text ="Original",variable= self.nii_mode_var,value=1,command=self.change_nii_view_option)
        rad_mode_1.grid(row=0,column=0,padx=5,pady=5,sticky="w")    
        rad_mode_2 = ctk.CTkRadioButton(self.nii_modes_frame, text = "Maximum",variable = self.nii_mode_var,value =2,command = self.change_nii_view_option)
        rad_mode_2.grid(row=0,column=1,padx=5,pady=5, sticky="w")  

        self.nii_max_percentile_frame = ctk.CTkFrame(self.nii_modes_frame)
        self.nii_max_percentile_frame.grid(row=1,column=1,sticky="w",padx=5,pady=5)
        self.nii_max_percentile_label = ctk.CTkLabel(self.nii_max_percentile_frame,text="Maximum percentile:")
        self.nii_max_percentile_label.grid(row=0,column=0,padx=5,pady=5, sticky="w")
        self.nii_max_percentile_var = ctk.StringVar(value ="99.0")
        self.nii_max_percentile =ctk.CTkEntry(self.nii_max_percentile_frame,textvariable=self.nii_max_percentile_var)
        self.nii_max_percentile.grid(row=0,column=1,padx=5,pady=5, sticky="w")

        # Initially hide the frame
        self.nii_max_percentile_frame.grid_forget()

        self.nii_3d_view_button = ctk.CTkButton(self._3d_tab,text="View in 3D",command = self.display_3d)
        self.nii_3d_view_button.grid(row=2,column=0, padx=5, pady=5, sticky="w")

        self.save_frame = ctk.CTkFrame(self._3d_tab)
        self.save_frame.grid(row=3,column=0,sticky="w",padx=5,pady=5)

        self.nii_save_dir_button = ctk.CTkButton(self.save_frame,text="Select output folder",command=self.open_nii_output_dir_select_dialog)
        self.nii_save_dir_button.grid(row=0,column=0,padx =5,pady=5,sticky="w")
        self.selected_nii_output_dir_label = ctk.CTkLabel(self.save_frame,text="")
        self.selected_nii_output_dir_label.grid(row=0,column=1,sticky="w",padx=5, pady=5,)
        self.nii_file_entry = ctk.CTkEntry(self.save_frame,placeholder_text="Enter the 3d file name to save")
        self.nii_file_entry.grid(row=0,column=2,padx=5, pady=5,sticky="w")
        self.nii_file_save_button = ctk.CTkButton(self.save_frame,text="Save",command=self.save_nii_file)
        self.nii_file_save_button.grid(row=0,column=3,sticky="w",padx=5, pady=5)

        self._3d_tab_exists = True  # Mark the 3D tab as created

    def open_nii_output_dir_select_dialog(self):
        self.nii_output_directory = filedialog.askdirectory(title="Select Output Folder")
        # if self.output_directory is None:

        self.selected_nii_output_dir_label.configure(text = self.nii_output_directory)

    def change_nii_view_option(self):
        self.nii_3d_view_button.grid_forget()
        if self.nii_mode_var.get() ==1:
            self.nii_max_percentile_frame.grid_forget()
            self.nii_3d_view_button.grid(row=2,column=0, sticky="w")    
        else:
            self.nii_max_percentile_frame.grid(row=1,column=1)
            self.nii_3d_view_button.grid(row=2,column=0, sticky="w") 

    def save_nii_file(self):
        self.generate_3d_file()
        self.max_nii_data= np.copy(self.nii_data.get_fdata())
        if self.nii_mode_var.get()==1:
            nib.save(self.nii_data, os.path.join(self.nii_output_directory,str(self.nii_file_entry.get())) + '.nii.gz')
        else:
            self.max_nii_image = nib.Nifti1Image(self.max_nii_data, self.nii_data.affine)
            nib.save(self.max_nii_image,os.path.join(self.nii_output_directory,str(self.nii_file_entry.get())) + '.nii.gz')

    def display_3d(self):
        self.generate_3d_file()

        # Get the header information
        affine_matrix = self.nii_data.affine.copy()
        
        # Adjust the z-axis scaling (3rd axis) in the affine matrix for slice thickness
        logger.info(f"Affine matrix: {affine_matrix}")
        # affine_matrix[2, 2]= (self.thickness+self.gap)/((1+self.slices)*50)
        affine_matrix[2, 2] *= self.thickness
        voxel_spacing = (affine_matrix[0, 0], affine_matrix[1, 1], affine_matrix[2, 2])
        logger.info(f"Affine Matrix after adjustment: {affine_matrix}")
        
        if self.nii_mode_var.get() == 1:
            volume_data = self.nii_data.get_fdata()

            if self.gap > 0:
                volume_data = self.insert_gaps_between_slices(volume_data,self.gap)
            
            # Flip the volume along the y-axis
            volume_data_flipped = np.flip(volume_data, axis=1)
            volume = Volume(volume_data_flipped)

            # Set opacity and colormap
            volume.alpha([0, 0.01, 0.1, 0.2, 0.3, 0.8, 0.85, 0.9, 0.95, 1])
            volume.cmap("magma")

            # Apply the adjusted affine matrix to the volume - Set the voxels size in the 3 dimensions.
            volume.spacing(voxel_spacing)

            self.plotter = Plotter()
            if not self.plotter.renderers:
                self.plotter += volume
            else:
                self.plotter.clear()
                self.plotter += volume

            self.plotter.show(interactive=False)
        
        else:
            # Load and threshold the volume data
            self.max_nii_data = np.copy(self.nii_data.get_fdata())
            threshold = np.percentile(self.max_nii_data, float(self.nii_max_percentile_var.get()))
            mask = self.max_nii_data < threshold
            self.max_nii_data[mask] = 0
            self.max_nii_data[~mask] = 1

            if self.gap > 0:
                self.max_nii_data = self.insert_gaps_between_slices(self.max_nii_data, self.gap)

            # Flip the volume along the y-axis
            volume_data_flipped = np.flip(self.max_nii_data, axis=1)
            volume = Volume(volume_data_flipped)

            # Apply the adjusted affine matrix to the volume
            volume.spacing(voxel_spacing)

            # Create and display the plot
            self.plotter1 = Plotter()
            if not self.plotter1.renderers:
                self.plotter1 += volume
            else:
                self.plotter1.clear()
                self.plotter1 += volume

            self.plotter1.show(interactive=False)

    def insert_gaps_between_slices(self, volume_data, gap):
        """
        Inserts empty slices between each z-slice in the volume data.
        :param volume_data: The original 3D volume data.
        :param gap: The number of empty slices to insert between each z-slice.
        :return: Modified 3D volume data with gaps.
        """
        # Get the shape of the original data
        x_dim, y_dim, z_dim = volume_data.shape
        
        # Create a new array with the size adjusted for gaps
        new_z_dim = z_dim + (z_dim - 1) * gap  
        new_volume_data = np.zeros((x_dim, y_dim, new_z_dim))
        
        # Copy the original slices into the new array with gaps
        for z in range(z_dim):
            new_volume_data[:, :, z * (gap + 1)] = volume_data[:, :, z]
        
        return new_volume_data

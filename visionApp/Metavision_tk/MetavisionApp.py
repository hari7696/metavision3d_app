
from functools import partial
import io
import math
from optparse import Option
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

from colormap import new_cmap1,new_cmap2
import MetaVision3D.MetaNorm3D as algo_meta3d_norm
import MetaVision3D.MetaAlign3D as algo_meta3d_align
import MetaVision3D.evaluate as algo_meta3d_evaluate
import MetaVision3D.MetaInterp3D  as algo_meta3d_interp
import MetaVision3D.MetaAtlas3D as algo_meta3d_atlas
import MetaVision3D.MetaImpute3D as algo_meta3d_impute
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

        open_file_btn = ctk.CTkButton(nav_frame, text="Select CSV File", command=self.open_file)
        open_file_btn.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        self.cmap_switch_var = ctk.StringVar(value="gray")
        logger.info("Metavision class initialized")  

        self.create_parent_tab_switch()
        self.create_visualization_dock()
        self.cmap_switch_var = ctk.StringVar(value="gray")
        self.show_cmap_switch()
        # self.show_cmap_switch.grid(row=2,column=0,sticky="e",pady=5)
        self.cmap_cbox.configure(state="normal")
        self.compound_matrix=None

    
    def open_file(self):
        self.filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if self.filepath:
            print(self.filepath)
            self.display_file_loading()
            threading.Thread(target=self.load_file, args=(self.filepath,), daemon=True).start()

    def display_file_loading(self):
        self.loading_label = ctk.CTkLabel(self.nav_frame, text="Loading...")
        self.loading_label.grid(row=0, column=3, padx=(5, 0), pady=(10, 10), sticky="w")

    def load_file(self, filepath):
        self.df = pd.read_csv(filepath, index_col=False)
        self.df = self.df.rename(columns={'region': 'tissue_id'})
        self.tissue_ids = self.df['tissue_id'].unique().tolist()
        print(self.tissue_ids)
        self.molecule_names = self.df.columns[1:].tolist()
        self.is_roi=False
        remove_values = ["spotId", "raster", "x", "y", "z", "Date", "Class", "tissue_id","roi"]
        self.molecule_names = [option for option in self.molecule_names if option not in remove_values]
        self.create_molecule_dropdown()
        self.create_export_tab()

    def create_molecule_dropdown(self):
        if self.molecule_names:
            print(type(self.molecule_names))
            self.molecule_dropdown = ctk.CTkComboBox(self.nav_frame, values=["None"] + self.molecule_names if any(isinstance(x, float) and np.isnan(x) for x in self.molecule_names) else self.molecule_names)
            self.molecule_dropdown.grid(row=0, column=3, padx=5, pady=(10, 10), sticky="w")
            # self.process_steps_label = ctk.CTkLabel(self.nav_frame,text="Process Steps:")
            # self.process_steps_label.grid(row=0,column=4,sticky="w",padx=(20,5))
            self.process_steps_frame = ctk.CTkFrame(self.nav_frame)
            self.process_steps_frame.grid(row=0,column=5)
            self.process_step_var = ctk.IntVar(value=1)
            self.visualize_process_rad = ctk.CTkRadioButton(self.process_steps_frame,text ="Visualize",variable= self.process_step_var,value=1)
            self.visualize_process_rad.grid(row=0,column=0,padx=3,pady=3)
            arrow_label1 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
            arrow_label1.grid(row=0,column=1,padx=(0,10))
            self.normalize_process_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Normalize", variable=self.process_step_var,value=2,state="disabled")
            self.normalize_process_rad.grid(row=0,column=2,padx=3,pady=3)
            arrow_label2 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
            arrow_label2.grid(row=0,column=3,padx=(0,10))
            self.allign_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Align",variable=self.process_step_var,value=3,state="disabled")
            self.allign_rad.grid(row=0,column=4,padx=(3,0),pady=3)
            arrow_label3 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
            arrow_label3.grid(row=0,column=5,padx=(0,10))
            #self.interp_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Interp",variable=self.process_step_var,value=4,state="disabled")
            #self.interp_rad.grid(row=0,column=6,padx=(3,0),pady=3)    
             
            # Dropdown for selecting Impute, Interp, or both
            self.process_selection = ctk.CTkComboBox(self.process_steps_frame, values=["Select Process", "Impute", "Interp", "Both"])
            self.process_selection.grid(row=0, column=6, padx=3, pady=3)
            self.process_selection.bind("<<ComboboxSelected>>", self.handle_process_selection_change)

            self.interp_scale_entry = ctk.CTkEntry(self.process_steps_frame, placeholder_text="Enter extra slices between")
            self.interp_scale_entry.grid(row=0, column=7)
            self.interp_scale_entry.insert(0, "2")
            self.interp_scale_entry.grid_remove()  # Hide by default

       
            self.process_button = ctk.CTkButton(self.process_steps_frame, text="Run", command=self.start_selected_process)
            self.process_button.grid(row=0, column=8, padx=3, pady=3)

    def handle_process_selection_change(self, event=None):
        selected_process = self.process_selection.get()
        if selected_process in ["Interp", "Both"]:
            self.interp_scale_entry.grid()
        else:
            self.interp_scale_entry.grid_remove()

    def start_selected_process(self):
        if self.process_step_var.get()==1:            
            self.visualize_process_rad.configure(state="disabled")
            self.normalize_process_rad.select()
            self.start_initial_visualization()
        elif self.process_step_var.get()==2:
            self.normalize_process_rad.configure(state="disabled")
            self.allign_rad.select()
            self.start_normalization()
        # elif self.process_step_var.get()==3:
        #     self.allign_rad.configure(state="disabled")
        #     self.interp_rad.select()
        #     self.start_allignment()
        #     self.process_button.grid_forget()
        #     self.interp_scale_entry = ctk.CTkEntry(self.process_steps_frame,placeholder_text="Enter extra slices between")
        #     self.interp_scale_entry.grid(row=0,column=7)
        #     self.interp_scale_entry.insert(0,"2")
        #     self.process_button.grid(row=0,column=8)
        # elif self.process_step_var.get()==4:
        #     self.interp_rad.configure(state="disabled")
        #     self.process_button.configure(state="disabled")
        #     self.start_interp()
        elif self.process_step_var.get() == 3:
            self.allign_rad.configure(state="disabled")
            self.start_allignment()
            self.handle_process_selection()
        elif self.process_step_var.get() == 4:
            self.handle_process_selection()    

    def handle_process_selection(self):
        selected_process = self.process_selection.get()
        if selected_process == "Select Process":
            messagebox.showerror("Error", "Alignment is done. Please select a process if you would like to continue with imputation/interpolation.")
            return

        if selected_process in ["Interp", "Both"]:
            self.interp_scale_entry.grid()
        else:
            self.interp_scale_entry.grid_remove()
            
        self.process_button.configure(command=lambda: self.run_selected_process(selected_process))
        self.process_button.grid(row=0, column=8)

    def run_selected_process(self, selected_process):
        if selected_process == "Impute":
            self.start_imputation()
        elif selected_process == "Interp":
            self.start_interp()
        elif selected_process == "Both":
            self.start_imputation()
            self.start_interp()
        else:
            messagebox.showerror("Error", "Invalid process selected. Please select a valid process.")
        self.process_button.configure(state="disabled")


    def start_initial_visualization(self):
        self.cmap_cbox.configure(state="normal")
        self.compound_matrix = algo_meta3d_align.create_compound_matrix(self.df,col=self.molecule_dropdown.get(),reverse=True)
        time.sleep(1)
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.after(500,self.display_animation())

    def start_normalization(self):
        self.compound = self.molecule_dropdown.get()
        print(self.molecule_names[0])
        meta_norm = algo_meta3d_norm.MetaNorm3D(self.df, self.compound,first_feature=self.molecule_names[0])
        self.norm_df = meta_norm.totalsum_norm()
        self.data = meta_norm.section_norm()
        self.compound_matrix = algo_meta3d_align.create_compound_matrix(self.data,reverse=True)
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()

    def start_allignment(self):
        meta_align = algo_meta3d_align.MetaAlign3D(self.data)
        self.compound_matrix = meta_align.create_compound_matrix(reverse=True)
        self.compound_matrix = meta_align.seq_align()
        # self.compound_matrix = meta_align.seq_align()
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()
        self.generate_3d_file()
        self.create_3d_tab()
        self.allign_rad.configure(state="disabled")  # Disable the "Align" button after alignment
        self.process_step_var.set(4)  # Set to 4 to allow imputation/interpolation selection

    def start_imputation(self):
        # Ensure the compound_matrix is available before starting the imputation process
        if self.compound_matrix is None:
            messagebox.showerror("Error", "Compound matrix is not available. Please complete the alignment process first.")
            return
        meta_impute = algo_meta3d_impute.MetaImpute3D(self.compound_matrix)
        self.compound_matrix = meta_impute.seq_impute()
        self.display_individual_images(self.cmap_switch_var.get(), self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()
        self.generate_3d_file()
        # self.create_3d_tab()


    def start_interp(self):
        try:
            int(self.interp_scale_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Only Integer values are allowed")
        meta_interp = algo_meta3d_interp.MetaInterp3D(self.compound_matrix,int(self.interp_scale_entry.get()))
        self.compound_matrix = meta_interp.interp()
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()
        self.generate_3d_file()
    
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
        # self.montage_tab = self.tab_view.add("Montage")
        # self.montage_tab.columnconfigure(0,weight=1)
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
        rad1 = ctk.CTkRadioButton(self.export_output_options_frame,text ="Single File",variable= self.export_file_option,value=1,command=self.change_output_label)
        rad1.grid(row=0,column=0,padx=5,pady=5)
        rad2 = ctk.CTkRadioButton(self.export_output_options_frame, text = "Multi Files",variable = self.export_file_option,value =2,command = self.change_output_label)
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
        print(self.export_file_option.get())
        selected_molecules = []
        selected_tissues = []
        for cbox in self.molecule_checkboxes:
            if cbox.get() ==1 :
                selected_molecules.append(cbox.cget("text"))
        for cbox in self.tissue_checkboxes:
            if cbox.get()==1:
                selected_tissues.append(cbox.cget("text"))
        print(selected_tissues)

        if self.export_norm_option.get()==1:
            filtered_df = self.df[self.df['tissue_id'].isin(selected_tissues)]
        else:
            filtered_df = self.norm_df[self.norm_df['tissue_id'].isin(selected_tissues)]

        if self.export_file_option.get() == 2:
            for tissue in selected_tissues:
                print("here1")
                # Filter the dataframe for each tissue
                tissue_df = filtered_df[filtered_df['tissue_id'] == tissue] 

                # Select only the columns for selected molecules and the tissue_ids
                export_df = tissue_df[['tissue_id'] + selected_molecules]    

                # Create a folder for the tissue if it doesn't exist
                print(self.output_directory)
                print(self.output_folder_entry.get())
                tissue_folder = os.path.join(os.path.join(self.output_directory,self.output_folder_entry.get()), str(tissue))
                if not os.path.exists(tissue_folder):
                    os.makedirs(tissue_folder)
                
                for molecule in selected_molecules:
                    print("here2")
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
        print(id) 
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
        atlas_data = algo_meta3d_atlas.MetaAtlas3D(self.compound_matrix)
        self.nii_data= atlas_data.create_nii()
        
    def create_3d_tab(self):
        self._3d_tab= self.tab_view.add("3D view")
        self._3d_tab.columnconfigure(0,weight=1)
        self.nii_modes_frame = ctk.CTkFrame(self._3d_tab)
        self.nii_modes_frame.grid(row=0,column=0,columnspan=2,sticky="w")
        self.nii_mode_var = ctk.IntVar(value=1)
        rad_mode_1 = ctk.CTkRadioButton(self.nii_modes_frame,text ="Original",variable= self.nii_mode_var,value=1,command=self.change_nii_view_option)
        rad_mode_1.grid(row=0,column=0,padx=5,pady=5)
        rad_mode_2 = ctk.CTkRadioButton(self.nii_modes_frame, text = "Maximum",variable = self.nii_mode_var,value =2,command = self.change_nii_view_option)
        rad_mode_2.grid(row=0,column=1,padx=5,pady=5)
        self.nii_3d_view_button = ctk.CTkButton(self._3d_tab,text="View in 3D",command = self.display_3d)
        self.nii_3d_view_button.grid(row=1,column=0)
        self.nii_max_percentile_frame = ctk.CTkFrame(self._3d_tab)
        self.nii_max_percentile_label = ctk.CTkLabel(self.nii_max_percentile_frame,text="Maximum percentile:")
        self.nii_max_percentile_label.grid(row=0,column=0)
        self.nii_max_percentile_var = ctk.StringVar(value ="99.0")
        self.nii_max_percentile =ctk.CTkEntry(self.nii_max_percentile_frame,textvariable=self.nii_max_percentile_var)
        self.nii_max_percentile.grid(row=0,column=1)
        self.nii_save_dir_button = ctk.CTkButton(self._3d_tab,text="Select output directory",command=self.open_nii_output_dir_select_dialog)
        self.nii_save_dir_button.grid(row=2,column=0,padx =5,pady=3,sticky="w")
        self.selected_nii_output_dir_label = ctk.CTkLabel(self._3d_tab,text="")
        self.selected_nii_output_dir_label.grid(row=2,column=1,sticky="w",padx=3,pady=3)
        self.nii_file_entry = ctk.CTkEntry(self._3d_tab,placeholder_text="Enter the 3d file name to save")
        self.nii_file_entry.grid(row=3,column=0)
        self.nii_file_save_button = ctk.CTkButton(self._3d_tab,text="Save",command=self.save_nii_file)
        self.nii_file_save_button.grid(row=3,column=1,sticky="w")

    def open_nii_output_dir_select_dialog(self):
        self.nii_output_directory = filedialog.askdirectory(title="Select Output Folder")
        # if self.output_directory is None:

        self.selected_nii_output_dir_label.configure(text = self.nii_output_directory)

    def change_nii_view_option(self):
        self.nii_3d_view_button.grid_forget()
        if self.nii_mode_var.get() ==1:
            self.nii_max_percentile_frame.grid_forget()
            self.nii_3d_view_button.grid(row=1,column=0)
        else:
            self.nii_max_percentile_frame.grid(row=1,column=0)
            self.nii_3d_view_button.grid(row=1,column=1) 

    def display_3d(self):
        if self.nii_mode_var.get()==1:
            # volume = Volume(self.nii_data.get_fdata())
            volume_data = self.nii_data.get_fdata()
            volume_data_flipped = np.flip(volume_data, axis=1)  # Flip along the y-axis
            volume = Volume(volume_data_flipped)
            volume.alpha([0,0.01,0.1,0.2,0.3,0.8,0.85,0.9,0.95,1])
            volume.cmap("magma")
            self.plotter = Plotter()
            if not self.plotter.renderers:
                self.plotter += volume  # Add volume if not already added
            else:
                self.plotter.clear()  # Clear existing actors
            self.plotter += volume  # Re-add the volume or update it

            self.plotter.show(interactive=False)
            # self.setup_rotation(self.plotter, volume)
            #self.plotter.show() 
        else:
            self.max_nii_data= np.copy(self.nii_data.get_fdata())
            threshold = np.percentile(self.max_nii_data, float(self.nii_max_percentile_var.get()))
            mask = self.max_nii_data < threshold
            self.max_nii_data[mask] = 0
            self.max_nii_data[~mask] = 1
            volume_data_flipped = np.flip(self.max_nii_data, axis=1)  # Flip along the y-axis
            volume = Volume(volume_data_flipped)
            # volume = Volume(self.max_nii_data)
            self.plotter1 = Plotter()
            if not self.plotter1.renderers:
                self.plotter1 += volume  # Add volume if not already added
            else:
                self.plotter1.clear()  # Clear existing actors
            self.plotter1 += volume  # Re-add the volume or update it

            self.plotter1.show(interactive=False)
            # self.setup_rotation(self.plotter1, volume)
            #self.plotter1.show()
        
    def save_nii_file(self):
        if self.nii_mode_var.get()==1:
            nib.save(self.nii_data, os.path.join(self.nii_output_directory,str(self.nii_file_entry.get())) + '.nii.gz')
        else:
            self.max_nii_image = nib.Nifti1Image(self.max_nii_data, self.nii_data.affine)
            nib.save(self.max_nii_image,os.path.join(self.nii_output_directory,str(self.nii_file_entry.get())) + '.nii.gz')

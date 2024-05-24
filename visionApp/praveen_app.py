
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext, Checkbutton, IntVar, Entry, Label,ttk
import pandas as pd
import tkinter.ttk as ttk
import os
import threading
from PIL import Image, ImageTk
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
from vedo import Volume,show,Plotter
# import vtkmodules.all as vtk
# from vtkmodules.util.numpy_support import numpy_to_vtk
# from vtkmodules.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
import io

from visionApp.sami_tk.colormap import new_cmap1,new_cmap2
import MetaVision3D.utils as algo_meta3d_utils
import MetaVision3D.MetaNorm3D as algo_meta3d_norm
import MetaVision3D.MetaAlign3D as algo_meta3d_align
import MetaVision3D.MetaImpute3D as algo_meta3d_impute
import MetaVision3D.MetaInterp3D  as algo_meta3d_interp
import MetaVision3D.MetaAtlas3D as algo_meta3d_atlas
import MetaVision3D.visualize as algo_meta3d_visualize 
import MetaVision3D.evaluate as algo_meta3d_evaluate
import nibabel as nib
import math
from pylab import Figure
import SAMI.utils as algo_sami_utils
import SAMI.preprocessing as algo_sami_preprocessing
import SAMI.correlation as algo_sami_correlation
import SAMI.clustering as algo_sami_clustering
import SAMI.markers as algo_sami_markers
# from SAMI.pathway import *
import SAMI.norm as algo_sami_norm
# from SAMI.clustermapping import *
import glob
import warnings
import numpy as np
import scanpy as sc
warnings.filterwarnings("ignore")
import logging
import pickle
logging.basicConfig(filename='old_app.log', 
                    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s', filemode='w')




class MetaVision3dApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MetaVision3D")
        self.geometry("1350x710")
        self.columnconfigure(0,weight=1)
        self.create_top_dock()
        self.create_tab_switch()
        self.create_visualization_dock()
        self.cmap_switch_var = ctk.StringVar(value="gray")
        self.compound_matrix=None
        self.show_cmap_switch()

        self.df = None
        self.tissue_ids = []
        self.molecule_names = []
        
        self.export_window = None

    def create_top_dock(self):
        self.top_parent_frame = ctk.CTkFrame(self)
        self.top_parent_frame.grid(row=0,column=0,columnspan=2,sticky="ew")
        self.top_frame = ctk.CTkFrame(self.top_parent_frame)
        self.top_frame.grid(row=1,column=0,columnspan=2,sticky="ew")
        self.file_type_var = ctk.StringVar(value="3D file")
        self.file_type_cbox= ctk.CTkOptionMenu(self.top_frame,values=["Normal File","3D file","SAMI"],variable=self.file_type_var,command=lambda choice: self.change_file_ui())
        self.file_type_cbox.grid(row=0,column=0,padx=(5,0),pady=10)
        self.open_file_btn = ctk.CTkButton(self.top_frame, text="Open CSV File", command=self.open_file)
        self.open_file_btn.grid(row=0,column=2,padx =(5,0), pady=(10,10),sticky="w")

    def change_file_ui(self):
        # self.open_file_btn.grid_forget()
        # self.run_button = ctk.CTkButton(self.top_frame,text="Run", command = self.display_cor_cluster)
        # self.run_button.grid(row=0,column=1,padx =(5,0), pady=(10,10),sticky="w")
        # self.select_folder_btn = ctk.CTkButton(self.top_frame,text="Select Folder",command=self.open_sami_select_folder)
        # self.select_folder_btn.grid(row=0,column=1)
        if self.file_type_cbox.get() == "SAMI":
            self.sami_note_label = ctk.CTkLabel(self.top_parent_frame,text="Note: In case of single file it can be a single omics or all. In case of multi files each file must be of different omics",text_color="#cdf52f")
            self.sami_note_label.grid(row=0,column=0,sticky="e")
            self.sami_file_option_menu = ctk.CTkOptionMenu(self.top_frame,values = ["Single file","Multi file"],command=lambda choice: self.change_sami_file_ui(choice))
            self.sami_file_option_menu.grid(row=0,column=1,padx=(3,0),pady=10)
            self.open_folder_btn = ctk.CTkButton(self.top_frame, text="Open Folder", command=self.open_folder)
        elif self.file_type_cbox.get() == "3D file":
            self.sami_note_label.grid_forget()
            self.sami_file_option_menu.grid_forget()
            self.open_folder_btn.grid_forget()
            self.open_file_btn.grid(row=0,column=2,padx =(5,0), pady=(10,10),sticky="w")
        # self.open_file_btn.grid_forget()
        # self.open_folder_btn = ctk.CTkButton(self.top_frame, text="Open Folder", command=self.open_folder)
        # self.open_folder_btn.grid(row=0,column=2,padx =(5,0), pady=(10,10),sticky="w")
        self.create_visualization_dock()
        self.show_cmap_switch()
    
    def change_sami_file_ui(self,choice):
        if choice == "Multi file":
            print("here")
            self.open_file_btn.grid_forget()
            print("here1")
            self.open_folder_btn.grid(row=0,column=2,padx =(5,0), pady=(10,10),sticky="w")
            print("here2")
        elif choice == "Single file":
            self.open_folder_btn.grid_forget()
            self.open_file_btn.grid(row=0,column=2,padx =(5,0), pady=(10,10),sticky="w")
            
    

    def open_file(self):
        self.filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if self.filepath:
            print(self.filepath)
            self.folder = os.path.dirname(self.filepath)
            self.display_file_loading()
            threading.Thread(target=self.load_file, args=(self.filepath,), daemon=True).start()

    def open_folder(self):
        self.sami_folder = filedialog.askdirectory(title="Select  Folder")
        print(self.sami_folder)
        folder_path = os.path.join(self.sami_folder,'*.csv')
        sami_multi_files = glob.glob(folder_path)
        self.sami_multi_file_names = [os.path.basename(path) for path in sami_multi_files]
        self.sami_multi_file_names = [string for string in self.sami_multi_file_names if not "norm" in string]
        if self.sami_file_option_menu.get()== "Multi file":
            self.sami_multi_file_cbox = ctk.CTkComboBox(self.cmap_frame,values= self.sami_multi_file_names,command= lambda choice: self.load_sami_selected_file())
            self.sami_multi_file_cbox.grid(row=0,column=1,sticky="w",padx =3,pady=3)
        self.display_file_loading()
        threading.Thread(target=self.load_file, args=(os.path.join(self.sami_folder,self.sami_multi_file_names[0]),), daemon=True).start()

    def load_sami_selected_file(self):
        if self.process_step_var.get()==1:
            print("here4")
            self.molecule_dropdown.grid_forget()
            self.display_file_loading()
            self.df = pd.read_csv(os.path.join(self.sami_folder,self.sami_multi_file_cbox.get()), index_col=False)
            self.df = self.df.rename(columns={'region': 'tissue_id'})
            self.tissue_ids = self.df['tissue_id'].unique().tolist()
            print(self.tissue_ids)
            self.molecule_names = self.df.columns[1:].tolist()
            remove_values = ["spotId", "raster", "x", "y", "z", "Date", "Class", "tissue_id","roi"]
            self.molecule_names = [option for option in self.molecule_names if option not in remove_values]
            self.molecule_dropdown.configure(values=self.molecule_names)
            self.molecule_dropdown.set(self.molecule_names[0])
            self.molecule_dropdown.grid(row=0, column=3, padx=5, pady=(10, 10), sticky="w")
            
            self.loading_label.grid_forget()
        elif self.process_step_var.get()==2:
            self.molecule_dropdown.grid_forget()
            self.display_file_loading()
            self.df = pd.read_csv(os.path.join(self.sami_folder,self.sami_multi_file_cbox.get()), index_col=False)
            self.df = self.df.rename(columns={'region': 'tissue_id'})
            self.tissue_ids = self.df['tissue_id'].unique().tolist()
            self.molecule_names = self.df.columns[1:].tolist()
            remove_values = ["spotId", "raster", "x", "y", "z", "Date", "Class", "tissue_id","roi"]
            self.molecule_names = [option for option in self.molecule_names if option not in remove_values]
            self.molecule_dropdown.configure(values=self.molecule_names)
            self.molecule_dropdown.grid(row=0, column=3, padx=5, pady=(10, 10), sticky="w")
            # self.molecule_var.set(self.molecule_names[0])
            self.molecule_dropdown.set(self.molecule_names[0])
            self.compound_matrix = algo_meta3d_align.create_compound_matrix_sami(self.df,col=self.molecule_dropdown.get(),reverse=True)
            self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
            self.display_norm_plot(self.compound_matrix)
            self.after(500,self.display_animation())
            self.loading_label.grid_forget()

            
        # threading.Thread(target=self.load_file, args=(os.path.join(self.sami_folder,self.sami_multi_file_cbox.get()),), daemon=True).start()

    def display_file_loading(self):
        self.loading_label = ctk.CTkLabel(self.top_frame, text="Loading...")
        self.loading_label.grid(row=0, column=3, padx=(5, 0), pady=(10, 10), sticky="w")

    def load_file(self, filepath):
        self.df = pd.read_csv(filepath, index_col=False)
        self.df = self.df.rename(columns={'region': 'tissue_id'})
        self.tissue_ids = self.df['tissue_id'].unique().tolist()
        print(self.tissue_ids)
        self.molecule_names = self.df.columns[1:].tolist()
        self.is_roi=False
        if "roi" in self.molecule_names and self.file_type_cbox.get()=="SAMI":
            print("roi")
            self.is_roi = True
            self.create_roi_switch()
        remove_values = ["spotId", "raster", "x", "y", "z", "Date", "Class", "tissue_id","roi"]
        self.molecule_names = [option for option in self.molecule_names if option not in remove_values]
        # print(self.molecule_names)
        self.create_molecule_dropdown()
        self.create_export_tab()
        # self.create_export_button()
    
    def create_molecule_dropdown(self):
        if self.molecule_names:
            # self.molecule_var = ctk.StringVar(value='PI_36_4_')  # Default value set
            print(type(self.molecule_names))
            self.molecule_dropdown = ctk.CTkComboBox(self.top_frame,  values=["None"]+self.molecule_names if any(isinstance(x, float) and np.isnan(x) for x in self.molecule_names) else self.molecule_names,command= lambda choice: self.change_molecule_visualization())
            self.molecule_dropdown.grid(row=0, column=3, padx=5, pady=(10, 10), sticky="w")
            self.process_steps_label = ctk.CTkLabel(self.top_frame,text="Process Steps:")
            self.process_steps_label.grid(row=0,column=4,sticky="w",padx=(20,5))
            self.process_steps_frame = ctk.CTkFrame(self.top_frame)
            self.process_steps_frame.grid(row=0,column=5)
            self.process_step_var = ctk.IntVar(value=1)
            self.visualize_process_rad = ctk.CTkRadioButton(self.process_steps_frame,text ="Visualize",variable= self.process_step_var,value=1)
            self.visualize_process_rad.grid(row=0,column=0,padx=3,pady=3)
            arrow_label1 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
            arrow_label1.grid(row=0,column=1,padx=(0,10))
            self.normalize_process_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Normalize", variable=self.process_step_var,value=2,state="disabled")
            self.normalize_process_rad.grid(row=0,column=2,padx=3,pady=3)
            if self.file_type_cbox.get() == "3D file":
                arrow_label2 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
                arrow_label2.grid(row=0,column=3,padx=(0,10))
                self.allign_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Allign",variable=self.process_step_var,value=3,state="disabled")
                self.allign_rad.grid(row=0,column=4,padx=(3,0),pady=3)
                arrow_label3 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
                arrow_label3.grid(row=0,column=5,padx=(0,10))
                self.interp_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Interp",variable=self.process_step_var,value=4,state="disabled")
                self.interp_rad.grid(row=0,column=6,padx=(3,0),pady=3)
            else:
                arrow_label2 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
                arrow_label2.grid(row=0,column=3,padx=(0,10))
                self.split_to_h5ad_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Split to h5ad",variable = self.process_step_var,value=5,state="disabled")
                self.split_to_h5ad_rad.grid(row=0,column=4,padx=(3,0),pady=3)
                arrow_label3 = ctk.CTkLabel(self.process_steps_frame,text= '\u27A1',font=("Arial", 20))
                arrow_label3.grid(row=0,column=5,padx=(0,10))
                self.cluster_rad = ctk.CTkRadioButton(self.process_steps_frame,text="Clustering",variable=self.process_step_var,value=6,state="disabled")
                self.cluster_rad.grid(row=0,column=6,padx=(3,0),pady=3)
                

            self.process_button =ctk.CTkButton(self.process_steps_frame,text="Run",command = self.start_selected_process)
            self.process_button.grid(row=0,column=7,padx=3,pady=3)
            # self.process_info_label = ctk.CTkLabel(self.process_steps_frame,text=" ", text_color="#e2f026")
            # self.process_info_label.grid(row=0,column=6)

    def start_selected_process(self):
        if self.process_step_var.get()==1:            
            self.visualize_process_rad.configure(state="disabled")
            self.normalize_process_rad.select()
            self.start_initial_visulazation()
            # threading.Thread(target=self.start_initial_visulazation, args=(), daemon=True).start()
            # self.afterself.display_animation()
        elif self.process_step_var.get()==2:
            self.normalize_process_rad.configure(state="disabled")
            if self.file_type_cbox.get()=="SAMI":
                self.create_sami_normalization_tab()
                
                self.split_to_h5ad_rad.select()
                if self.sami_file_option_menu.get() == "Mulit file":
                    self.sami_multi_file_cbox.configure(state="disabled")
            else:
                self.allign_rad.select()
                self.start_normalization()
        elif self.process_step_var.get()==3:
            self.allign_rad.configure(state="disabled")
            self.interp_rad.select()
            self.start_allignment()
            
            # self.process_button.grid_forget()
            # self.generate_3d_button = ctk.CTkButton(self.process_steps_frame,text="Generate 3D file",command=self.generate_3d_file)
            # self.generate_3d_button.grid(row=0,column=5,padx=3,pady=3)
            # self.generate_3d_file()
            self.process_button.grid_forget()
            self.interp_scale_entry = ctk.CTkEntry(self.process_steps_frame,placeholder_text="Enter extra slices between")
            self.interp_scale_entry.grid(row=0,column=7)
            self.interp_scale_entry.insert(0,"2")
            self.process_button.grid(row=0,column=8)

        elif self.process_step_var.get()==4:
            self.interp_rad.configure(state="disabled")
            self.process_button.configure(state="dsiabled")
            self.start_interp()
        elif self.process_step_var.get()==5:
            self.split_to_h5ad_rad.configure(state="disabled")
            self.cluster_rad.select()
            self.start_split_to_h5ad()
        elif self.process_step_var.get()==6:
            self.cluster_rad.configure(state="disabled")
            self.process_button.configure(state="disabled")
            self.start_clustering()

    
    def start_initial_visulazation(self):
        
        
        # threading.Thread(target=self.change_process_label_text, args=("Processing....",), daemon=True).start()
        # threading.Thread(target=self.change_process_label_text, args=("Creating Compound matrix....",), daemon=True).start()
        self.cmap_cbox.configure(state="normal")
        # self.process_info_label.configure(text="reating Compound matrix....")
        logging.info("Creating Compound matrix....")
        logging.info("data shape: {}".format(self.df.shape))
        logging.info("data columns: {}".format(self.df.columns))
        self.df.to_csv("temp.csv")
        if self.file_type_cbox.get()=="SAMI" and self.molecule_dropdown.get()=="None":
            logging.info("create_compound_matrix_sami_skeleton")
            print(self.roi_switch.get())
            self.compound_matrix = algo_meta3d_align.create_compound_matrix_sami_skeleton(self.df,col=self.molecule_names[0],roi= self.roi_switch.get(),reverse=True)
        elif self.file_type_cbox.get()=="SAMI":
            logging.info("create_compound_matrix_sami")
            self.compound_matrix = algo_meta3d_align.create_compound_matrix_sami(self.df,col=self.molecule_dropdown.get(),roi=False,reverse=True)
        else:
            self.compound_matrix = algo_meta3d_align.create_compound_matrix(self.df,col=self.molecule_dropdown.get(),reverse=True)
        # threading.Thread(target=self.change_process_label_text, args=("Displaying the images......",), daemon=True).start()
        # self.process_info_label.configure(text="Displaying the images......")
        time.sleep(1)
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.after(500,self.display_animation())
        # threading.Thread(target=self.display_animation, args=(), daemon=True).start()
        # threading.Thread(target=self.change_process_label_text, args=(" ",), daemon=True).start()
        # self.generate_3d_file()
        # self.create_3d_tab()
        # self.display_montage(self.compound_matrix)
        # self.process_info_label.configure(text=" fgsgrg")

    def start_normalization(self):
        self.compound = self.molecule_dropdown.get()
        print(self.molecule_names[0])
        meta_norm = algo_meta3d_norm.MetaNorm3D(self.df, self.compound,first_feature=self.molecule_names[0])
        # self.after(0,lambda: self.change_slides_label_text("Performing Total Sum Normalization...."))
        self.norm_df = meta_norm.totalsum_norm()
        # self.after(0,lambda: self.change_slides_label_text("Performing Section Normalization...."))
        self.data = meta_norm.section_norm()
        # self.after(0,lambda: self.change_slides_label_text("Creating compound matrix...."))
        if self.file_type_cbox.get()=="SAMI":
            self.compound_matrix = algo_meta3d_align.create_compound_matrix_sami(self.data,reverse=True)
        else:
            self.compound_matrix = algo_meta3d_align.create_compound_matrix(self.data,reverse=True)

        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()
        # self.display_montage(self.compound_matrix)

    def start_allignment(self):
        meta_align = algo_meta3d_align.MetaAlign3D(self.data)
        # self.compound_matrix = meta_align.create_compound_matrix(reverse=True)
        # self.after(0,lambda: self.change_slides_label_text("Creating compound matrix..."))
        self.compound_matrix = meta_align.create_compound_matrix(reverse=True)
        # self.after(0,lambda: self.change_slides_label_text("Performing Allignment...."))
        self.compound_matrix = meta_align.seq_align()
        self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()
        self.generate_3d_file()
        self.create_3d_tab()

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


    def generate_3d_file(self):
        # self.generate_3d_button.configure(state="disabled")
        # self._3d_tab= self.tab_view.add("3D view")
        # self.create_3d_tab()
        
        
        atlas_data = algo_meta3d_atlas.MetaAtlas3D(self.compound_matrix)
        self.nii_data= atlas_data.create_nii()
        # nib.save(self.nii_data, 'testimg.nii.gz')
        # mesh = Volume(self.nii_data.get_fdata())
        # show(mesh)
        
        '''
        self._3d_frame= vtkTkRenderWindowInteractor(self._3d_tab, width=300, height=300)
        self._3d_frame.grid(row=0,column=0)
        self.renderer = vtk.vtkRenderer()
        self._3d_frame.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self._3d_frame.GetRenderWindow().GetInteractor()
        # win_id = self._3d_tab.winfo_id()

        # plotter = Plotter(bg='w', size=(300, 300))
        # plotter.embedInto(win_id)


        
        
        self.renderer.AddVolume(volume)
        self.interactor.Initialize()
        self.interactor.Start()

        # Now, instead of using 'c' during instantiation, we apply color mapping afterwards
        # Apply a colormap (here 'jet') and opacity gradient directly
        volume.color('jet').alpha([0, 0.5, 0.9, 0.7])

        plotter.add(volume)
        plotter.show(interactive=False)
        plotter.interactor.Initialize()
        plotter.interactor.Start()
        '''

    def create_3d_tab(self):
        self._3d_tab= self.tab_view.add("3D view")
        self._3d_tab.columnconfigure(0,weight=1)
        # self.nii_tab_view = ctk.CTkTabview(self._3d_tab)
        # self.nii_tab_view.grid(row=0,column=0,sticky="nsew")
        # self.original_nii_tab = self.nii_tab_view.add("Original")
        # self.maximum_nii_tab = self.nii_tab_view.add("Maximum")

        # self.view_3d_original_button= ctk.CTkButton(self.original_nii_tab,text="View in 3D",command = self.view_original_3d)
        # self.view_3d_original_button.grid(row=0,column=0)
        # self.3d_orginal_directory_button = 
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
        # self.display_nii_view_options()
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
            volume = Volume(self.nii_data.get_fdata())
            volume.alpha([0,0.01,0.1,0.2,0.3,0.8,0.85,0.9,0.95,1])
            volume.cmap("magma")
            self.plotter = Plotter()
            if not self.plotter.renderers:
                self.plotter += volume  # Add volume if not already added
            else:
                self.plotter.clear()  # Clear existing actors
            self.plotter += volume  # Re-add the volume or update it

            self.plotter.show() 
            # show(self.volume)
            # threading.Thread(target=self.run_volume, args=(), daemon=True).start()
        else:
            # max_value = self.nii_data.max()
            self.max_nii_data= np.copy(self.nii_data.get_fdata())
            threshold = np.percentile(self.max_nii_data, float(self.nii_max_percentile_var.get()))
            mask = self.max_nii_data < threshold
            self.max_nii_data[mask] = 0
            self.max_nii_data[~mask] = 1
            volume = Volume(self.max_nii_data)
            self.plotter1 = Plotter()
            if not self.plotter1.renderers:
                self.plotter1 += volume  # Add volume if not already added
            else:
                self.plotter1.clear()  # Clear existing actors
            self.plotter1 += volume  # Re-add the volume or update it

            self.plotter1.show()

    def run_volume(self):
        show(self.volume)
    def save_nii_file(self):
        if self.nii_mode_var.get()==1:
            nib.save(self.nii_data, os.path.join(self.nii_output_directory,str(self.nii_file_entry.get())) + '.nii.gz')
        else:
            nib.save(self.max_nii_data,os.path.join(self.nii_output_directory,str(self.nii_file_entry.get())) + '.nii.gz')

    def change_molecule_visualization(self):
        
        if self.file_type_cbox.get()=="SAMI" and self.process_step_var.get()==2:
            self.compound_matrix = algo_meta3d_align.create_compound_matrix_sami(self.df,col=self.molecule_dropdown.get(),reverse=True)
            self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)


    def create_sami_normalization_tab(self):
        self.sami_normalization_tab = self.tab_view.add("Normalizaton")
        self.sami_normalization_tab.columnconfigure((0,1,2),weight=1)
        if self.sami_file_option_menu.get()=="Multi file":
            self.norm_files_cbox = ctk.CTkComboBox(self.sami_normalization_tab,values=self.sami_multi_file_names+["All"],command = lambda choice: self.change_normfile_indices())
            self.norm_files_cbox.grid(row=0,column=0,sticky="w")
        self.first_compound_label = ctk.CTkLabel(self.sami_normalization_tab,text="Select index of first compound in csv file")
        self.first_compound_label.grid(row=1,column=0,sticky="w")
        formatted_values = [f"{i}-{col}" for i, col in enumerate(self.df.columns)]
        print(formatted_values)
        self.first_compound_idx_cbox = ctk.CTkComboBox(self.sami_normalization_tab,values=formatted_values)
        self.first_compound_idx_cbox.grid(row=1,column=1,sticky="w")
        # if self.sami_file_option_menu.get()=="Multi file":
        #     self.first_compoud_note_label = ctk.CTkLabel(self.sami_normalization_tab,text="Note: This integer value should be same for all files")
        self.row_norm_label = ctk.CTkLabel(self.sami_normalization_tab,text="Select row norm:")
        self.row_norm_label.grid(row=2,column=0,sticky="w")
        self.row_norm_cbox = ctk.CTkComboBox(self.sami_normalization_tab,values=['None','SumNorm', 'MedianNorm', 'CompNorm', 'SamplePQN', 'GroupPQN', 'SpecNorm', 'GroupMedianPQN'])
        self.row_norm_cbox.grid(row=2,column=1,sticky="w")
        self.trans_norm_label = ctk.CTkLabel(self.sami_normalization_tab,text="Select trans norm:")
        self.trans_norm_label.grid(row=3,column=0,sticky="w")
        self.trans_norm_cbox = ctk.CTkComboBox(self.sami_normalization_tab,values=['None','LogTrans1', 'LogTrans2', 'SquareRootTrans', 'CubeRootTrans'])
        self.trans_norm_cbox.grid(row=3,column=1,sticky="w")
        self.scale_norm_label = ctk.CTkLabel(self.sami_normalization_tab,text="Select scale norm:")
        self.scale_norm_label.grid(row=4,column=0,sticky="w")
        self.scale_norm_cbox = ctk.CTkComboBox(self.sami_normalization_tab,values=['None','MeanCenter', 'AutoNorm', 'ParetoNorm', 'RangeNorm'])
        self.scale_norm_cbox.grid(row=4,column=1,sticky="w")
        self.sami_normalize_btn = ctk.CTkButton(self.sami_normalization_tab,text="Run Normalization",command = self.start_sami_normalization)
        self.sami_normalize_btn.grid(row=5,column=0,padx=5,pady=5,sticky="w")
        self.sami_norm_save_btn = ctk.CTkButton(self.sami_normalization_tab,text="Save",command=self.save_sami_norm_file)
        self.sami_norm_save_btn.grid(row=6,column=0,padx=5,sticky="w")
        self.tab_view.set("Normalizaton")
            
    
    def change_normfile_indices(self):
        print("a")
        if self.sami_file_option_menu == "Multi file":
            dff = pd.read_csv(os.path.join(self.sami_folder,self.norm_files_cbox.get()),nrows=0)
            columns = dff.columns.tolist()
            formatted_values = [f"{i}-{col}" for i, col in enumerate(columns)]
            self.first_compound_idx_cbox.configure(values=formatted_values)

        

    def save_sami_norm_file(self):
        # print(self.filepath)
        if self.sami_file_option_menu.get()=="Single file":
            if self.filepath.endswith("raw.csv"):
                new_path = self.filepath.replace("raw.csv", "norm.csv")
            else:
                new_path = self.filepath.replace(".csv", "_norm.csv")
            self.df_norm = self.df_norm.rename(columns={'tissue_id': 'region'})
            self.df_norm.to_csv(new_path,index=False)
        elif self.sami_file_option_menu.get()=="Multi file" and self.norm_files_cbox.get()!="All":
            if self.norm_files_cbox.get().endswith("raw.csv"):
                new_path = self.norm_files_cbox.get().replace("raw.csv", "norm.csv")
            else:
                new_path = self.norm_files_cbox.get().replace(".csv", "_norm.csv")
            self.df_norm = self.df_norm.rename(columns={'tissue_id': 'region'})
            self.df_norm.to_csv(os.path.join(self.sami_folder, new_path),index=False)

    def start_sami_normalization(self):
        if self.sami_file_option_menu.get()=="Multi file": 
            if self.norm_files_cbox.get()== "All":
                for file in self.sami_multi_file_names:
                    self.df = pd.read_csv(os.path.join(self.sami_folder,file), index_col=False)
                    self.df = self.df.rename(columns={'region': 'tissue_id'})
                    first_compound_index = int(self.first_compound_idx_cbox.get().split('-')[0])
                    self.df_norm = algo_sami_norm.Normalization(self.df, first_compound_idx=first_compound_index, rowNorm=self.row_norm_cbox.get(), transNorm=self.trans_norm_cbox.get(), c=1, log_base=2)
                    # self.compound_matrix = create_compound_matrix(self.df_norm,col=self.molecule_var.get(),reverse=True)
                    if file.endswith("raw.csv"):
                        new_path = file.replace("raw.csv", "norm.csv")
                    else:
                        new_path = file.replace(".csv", "_norm.csv")
                    self.df_norm = self.df_norm.rename(columns={'tissue_id': 'region'})
                    self.df_norm.to_csv(os.path.join(self.sami_folder,new_path),index=False)
                messagebox.showinfo("Success", "Normalizatin done for all files and are saved")
        else:
            if self.sami_file_option_menu.get() == "Single file":
                self.df = pd.read_csv(self.filepath, index_col=False)
            else:
                self.df = pd.read_csv(os.path.join(self.sami_folder,self.norm_files_cbox.get()), index_col=False)
            self.df = self.df.rename(columns={'region': 'tissue_id'})
            first_compound_index = int(self.first_compound_idx_cbox.get().split('-')[0])
            self.df_norm = algo_sami_norm.Normalization(self.df, first_compound_idx=first_compound_index, rowNorm=self.row_norm_cbox.get(), transNorm=self.trans_norm_cbox.get(), c=1, log_base=2)
            self.compound_matrix = algo_meta3d_align.create_compound_matrix_sami(self.df_norm,col=self.molecule_dropdown.get(),reverse=True)   
            self.display_individual_images(self.cmap_switch_var.get(),self.compound_matrix)
            self.display_norm_plot(self.compound_matrix)
            self.after(500,self.display_animation())

    def start_split_to_h5ad(self):
        if self.sami_file_option_menu.get()== "Single file":
            os.makedirs(os.path.join(os.path.dirname(self.filepath),'h5ad'),exist_ok=True)
            algo_sami_preprocessing.csv2h5ad(data_path=os.path.dirname(self.filepath),pattern=r'^\w+norm\.csv',split=True)
            
        else:
        
            os.makedirs(os.path.join(self.sami_folder,'h5ad'),exist_ok=True)
            algo_sami_preprocessing.csv2h5ad(data_path=self.sami_folder,pattern=r'^\w+norm\.csv',split=True)
            algo_sami_preprocessing.pooldata(data_path=self.sami_folder,pattern=r'^\w+norm\.csv',split=True) 
        messagebox.showinfo("Success", "H5AD files got created")


    def start_clustering(self):
        self.tab_view.set("Cluster")
        self.create_cluster_tab()
        # clusters = Clusters('brain2','glycomics',0.3)
        
        
        # clusters.clustering() 
        # fig = clusters.plot_umap_cluster(show=True)
        # self.cluster_image_frame = ctk.CTkScrollableFrame(self.cluster_tab,orientation="horizontal",width=450,height=400)
        # self.cluster_image_frame.grid(row=0,column=0,sticky="nsew")
        # canvas = FigureCanvasTkAgg(fig, master=self.cluster_image_frame)  # A tk.DrawingArea
        # canvas.draw()
        # canvas.get_tk_widget().grid(row=0,column=0)

    def create_cluster_tab(self):
        self.select_cluster_label = ctk.CTkLabel(self.cluster_tab,text="Select file:")
        self.select_cluster_label.grid(row=0,column=0)
        if self.sami_file_option_menu.get() == "Single file":
            folder_path= os.path.join(os.path.dirname(self.filepath),'*.h5ad')#r'C:\Users\dprav\OneDrive\Desktop\MetaAPP\MetaVision3D\modules\test\*.h5ad'
        else:
            folder_path= os.path.join(os.path.join(self.sami_folder,"h5ad"),'*.h5ad')#r'C:\Users\dprav\OneDrive\Desktop\MetaAPP\MetaVision3D\modules\test\*.h5ad'

        h5ad_files = glob.glob(folder_path)
        h5ad_files_names = [os.path.basename(path) for path in h5ad_files]
        self.cluster_file_cbox = ctk.CTkComboBox(self.cluster_tab,values=h5ad_files_names)
        self.cluster_file_cbox.grid(row=0,column=1)
        self.cluster_resolution_label = ctk.CTkLabel(self.cluster_tab,text="Enter resolution")
        self.cluster_resolution_label.grid(row=1,column=0)
        self.cluster_resolution_entry = ctk.CTkEntry(self.cluster_tab)
        self.cluster_resolution_entry.grid(row=1,column=1)
        self.run_cluster_btn = ctk.CTkButton(self.cluster_tab,text="Run Cluster",command = self.run_cluster)
        self.run_cluster_btn.grid(row=1,column=3)
        
        self.cluster_image_frame = ctk.CTkScrollableFrame(self.cluster_tab,orientation="horizontal",width=450,height=400)
        self.cluster_image_frame.grid(row=3,column=0,columnspan=3,sticky="nsew")

    def run_cluster(self):
        region = self.cluster_file_cbox.get().split(".")[0].split("_")[0]
        modality = self.cluster_file_cbox.get().split(".")[0].split("_")[1]
        if self.sami_file_option_menu.get()=="Single file":
            data_folder = os.path.dirname(self.filepath)
        else:
            data_folder = self.sami_folder
        self.clusters = Clusters(region,modality,float(self.cluster_resolution_entry.get()),data_folder=data_folder)
        self.clusters.clustering()
        # fig = clusters.plot_umap_cluster(show=True)
        self.create_cluster_plot_options()

    def create_cluster_plot_options(self):
        self.cluster_plot_label = ctk.CTkLabel(self.cluster_tab,text="Select plot")
        self.cluster_plot_label.grid(row=2,column=0)
        self.cluster_plot_cbox = ctk.CTkComboBox(self.cluster_tab,values=['Cluster plot','Umap cluster plot','Selected cluster plot'])
        self.cluster_plot_cbox.grid(row=2,column=1)
        self.cluster_plot_btn = ctk.CTkButton(self.cluster_tab,text="Plot",command = self.plot_cluster)
        self.cluster_plot_btn.grid(row=2,column=2)

    def plot_cluster(self):
        if self.cluster_plot_cbox.get()=="Cluster plot":
            for widget in  self.cluster_image_frame.winfo_children():
                widget.destroy()
            fig = self.clusters.plot_cluster()
            canvas = FigureCanvasTkAgg(fig, master=self.cluster_image_frame)  # A tk.DrawingArea
            canvas.draw()
            canvas.get_tk_widget().grid(row=0,column=0)
        elif self.cluster_plot_cbox.get()=="Umap cluster plot":
            for widget in  self.cluster_image_frame.winfo_children():
                widget.destroy()
            fig = self.clusters.plot_umap_cluster()
            canvas = FigureCanvasTkAgg(fig, master=self.cluster_image_frame)  # A tk.DrawingArea
            canvas.draw()
            canvas.get_tk_widget().grid(row=0,column=0)

    

    def create_export_button(self):
        self.top_frame.columnconfigure(3,weight=1)
        self.export_button = ctk.CTkButton(self.top_frame,text="Export",fg_color="#04ba3d",command = self.open_export_window)
        self.export_button.grid(row=0,column=3,sticky="e",padx=5)

    def create_tab_switch(self):
        self.tab_switch_var = ctk.StringVar(value="Visualization")
        self.tab_switch = ctk.CTkTabview(self,bg_color="transparent")
        self.tab_switch.grid(row=2,column=0,sticky="nsew")
        self.visualization_tab = self.tab_switch.add("Visualization")
        self.visualization_tab.columnconfigure(0,weight=1)
        self.export_tab = self.tab_switch.add("Export")
        # self.create_export_tab()
        

    def create_visualization_dock(self):
        for widget in  self.visualization_tab.winfo_children():
            widget.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self.visualization_tab,bg_color="transparent")
        self.root_visualization_frame.grid(row=2,column=0,sticky="nsew")
        self.root_visualization_frame.columnconfigure((0,1),weight=1)
        self.slides_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.slides_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=5)
        if self.file_type_cbox.get()== "SAMI":
            self.slides_display_frame = ctk.CTkScrollableFrame(self.slides_frame,height = 450,width =300)
        else:
            self.slides_display_frame = ctk.CTkScrollableFrame(self.slides_frame,height = 450,width =600)
        self.slides_display_frame.grid(row =1,column=0, padx=5,pady=5,sticky ="ew")
        self.visualization_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.visualization_frame.grid(row=0,column=1,sticky="nsew",padx =5,pady=5)
        self.visualization_frame.columnconfigure(0,weight=1)
        self.tab_view = ctk.CTkTabview(self.visualization_frame,width = 500)
        self.tab_view.grid(row=0,column=0,sticky="nsew",padx =5)
        self.slide_tab = self.tab_view.add("Slide")
        self.slide_tab.columnconfigure(0,weight=1)
        self.norm_plot = self.tab_view.add("Norm Plot")
        self.norm_plot.columnconfigure(0,weight=1)
        
            
        self.animation_tab = self.tab_view.add("Animation")
        self.animation_tab.columnconfigure(0,weight=1)
        self.montage_tab = self.tab_view.add("Montage")
        self.montage_tab.columnconfigure(0,weight=1)
        self.tab_view.set("Slide")
        if self.file_type_cbox.get() == "SAMI":
            self.cluster_tab = self.tab_view.add("Cluster")
            self.cluster_tab.columnconfigure(0,weight=1)
            self.corr_plot_tab = self.tab_view.add("Corr-Plot")
            self.corr_plot_tab.columnconfigure(0,weight=1)
            self.corr_network_tab = self.tab_view.add("Corr-Network")
            self.corr_network_tab.columnconfigure(0,weight=1)




    def show_cmap_switch(self):
        self.cmap_frame = ctk.CTkFrame(self.slides_frame,bg_color="transparent")
        self.cmap_frame.grid(row=0,column=0,sticky="e",pady=5)
        self.cmap_label = ctk.CTkLabel(self.cmap_frame,text="Set Colormap:")
        self.cmap_label.grid(row=0,column=2,sticky="e")
        self.cmap_cbox = ctk.CTkComboBox(self.cmap_frame,values=["gray","magma","viridis"],command=lambda choice: self.display_individual_images(choice,self.compound_matrix),variable=self.cmap_switch_var,state="disabled")
        self.cmap_cbox.grid(row=0,column=3,sticky="e",padx=(5,0))

    def create_roi_switch(self):
        self.roi_switch = ctk.CTkSwitch(self.cmap_frame,text="ROI",command = self.change_roi_visualization)
        self.roi_switch.grid(row=0,column=0)
    def change_roi_visualization(self):
        self.start_initial_visulazation()

    def start_process(self):
        self.compound = self.molecule_dropdown.get()
        meta_norm = algo_meta3d_norm.MetaNorm3D(self.df, self.compound)
        self.norm_df = meta_norm.totalsum_norm()
        data = meta_norm.section_norm()
        meta_align = algo_meta3d_align.MetaAlign3D(data)
        self.compound_matrix = meta_align.create_compound_matrix(reverse=True)
        print("compound matrix done")
        self.display_individual_images(self.compound_matrix)
        self.display_norm_plot(self.compound_matrix)
        self.display_animation()

    def destroy_slides_frame(self):
        for widget in  self.slides_display_frame.winfo_children():
            widget.destroy()
        self.slides_frame_loading_label = ctk.CTkLabel(self.slides_display_frame,text="Processing....",fg_color="#e2f026")
        self.slides_frame_loading_label.grid(row=0,column=0)

    def change_process_label_text(self,newText):
        self.process_info_label.configure(text=newText)

    def display_individual_images(self, choice,data):
        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()
        # self.display_montage(data)
        
        slices, rows, cols = data.shape
        N = round(math.sqrt(slices))

        if self.file_type_cbox.get()=="SAMI":
            grid_rows = slices/3
            grid_cols = 3
        else:
            grid_rows = slices/6
            grid_cols = 6
        if grid_rows * grid_cols < slices:
            grid_rows += 1

        with open('image_array.pkl', 'wb') as f:
            pickle.dump(data, f)

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

        # Pickle the image_array


        for frame, image_array, id in self.frames:
            self.display_image_in_frame(image_array, frame,id)
        # self.show_cmap_switch()
        

    def display_image_in_frame(self, image_array, frame,id):
        '''
        image_scaled = image_array - np.min(image_array)
        # print(np.max(image_scaled))
        image_scaled = image_scaled / np.max(image_scaled) * 255
        image_scaled = image_scaled.astype(np.uint8)
        if self.cmap_switch_var.get() == "magma" :
            cmap = plt.get_cmap(new_cmap1)
            colored_image = cmap(image_scaled)
            colored_image = (colored_image * 255).astype(np.uint8)
            image = Image.fromarray(colored_image)
        elif self.cmap_switch_var.get()=="viridis":
            cmap = plt.get_cmap(new_cmap2)
            colored_image = cmap(image_scaled)
            colored_image = (colored_image * 255).astype(np.uint8)
            image = Image.fromarray(colored_image)
        else:
            image = Image.fromarray(image_scaled)
        frame_width = frame.winfo_width()
        frame_height = frame.winfo_height()

        # # Resize the image
        aspect_ratio = image.width / image.height
        new_height = int(frame_width / aspect_ratio)
        resized_image = image.resize((frame_width, new_height))
        '''
        fig = Figure(figsize=(1, 0.57), dpi=100)
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
        photo = ImageTk.PhotoImage(resized_image)

        # Create a label to display the image
        label = ctk.CTkLabel(frame, image=photo, text="")
        label.image = photo  # Keep a reference
        label.grid(row=0, column=0, padx=2, pady=2)
        label.bind("<Button-1>", partial(self.on_label_click, id=id))
    
    def on_label_click(self,event,id):
        print(id) 
        fig = Figure(figsize=(7.7, 4.4))
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


        # Turn off axis labels and ticks
        ax.axis('off')


    def display_norm_plot(self,compound_matrix):
        self.norm_plot_frame = ctk.CTkScrollableFrame(self.norm_plot,height =400,width =400)
        self.norm_plot_frame.columnconfigure(0,weight=1)
        self.norm_plot_frame.grid(row=0,column=0,sticky="nsew")
        fig = algo_meta3d_evaluate.norm_boxplot(compound_matrix)
        canvas = FigureCanvasTkAgg(fig, master=self.norm_plot_frame)  # A tk.DrawingArea
        canvas.draw()
        canvas.get_tk_widget().grid(row=0,column=0)

    def display_montage(self,d,originSelect='lower'):
        self.montage_frame = ctk.CTkScrollableFrame(self.montage_tab,height =400,width =400)
        self.montage_frame.columnconfigure(0,weight=1)
        self.montage_frame.grid(row=0,column=0,sticky="nsew")
        if self.file_type_cbox.get() == "SAMI":
            slices = len(d)
            rows,cols = d[0].shape
        else:
            slices, rows, cols = d.shape
        N = round(math.sqrt(slices))
        im_cols = N
        im_rows = N

        if im_rows * im_cols < slices:
            im_rows += 1
        if self.file_type_cbox.get() == "SAMI":
            d2 = np.zeros((int(im_rows * rows), int(im_cols * cols)), dtype=d[0].dtype)
        else:
            d2 = np.zeros((int(im_rows * rows), int(im_cols * cols)), dtype=d.dtype)
        ii = 0
        for ri in range(im_rows):
            for ci in range(im_cols):
                if ii >= slices:
                    break
                if self.file_type_cbox.get() == "SAMI":
                    d2[ri*rows:(ri+1)*rows, ci*cols:(ci+1)*cols] = d[ii]
                else:
                    d2[ri*rows:(ri+1)*rows, ci*cols:(ci+1)*cols] = d[ii, :, :]
                ii += 1

        fig = Figure(figsize=(7, 7), dpi=100)
        ax = fig.add_subplot(111)
        if self.cmap_cbox.get()=="magma":
            im=ax.imshow(np.flipud(d2), origin=originSelect, cmap=new_cmap1)
            cbar = fig.colorbar(im,ax=ax,ticks=[0,np.percentile(d[d != 0], 99)],shrink=0.5)
            cbar.mappable.set_clim(vmin=0,vmax=np.percentile(d[d != 0], 99))
            cbar.ax.set_yticklabels(['low', 'high'])
        elif self.cmap_cbox.get()=="viridis":
            im=ax.imshow(d2, origin=originSelect, cmap=new_cmap2)
            cbar = fig.colorbar(im,ax=ax,ticks=[0,np.percentile(d[d != 0], 99)],shrink=0.5)
            cbar.mappable.set_clim(vmin=0,vmax=np.percentile(d[d != 0], 99))
            cbar.ax.set_yticklabels(['low', 'high'])
        else:
            ax.imshow(d2, origin=originSelect, cmap="gray")
        ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=self.montage_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0,column=0)
        
        

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

    def create_export_tab(self):
        self.export_tab.columnconfigure((0,1),weight=1)
        self.molecule_checkboxes = []
        self.molecule_vars =[]
        self.tissue_checkboxes=[]
        self.tissue_vars = []
        self.create_norm_options()
        threading.Thread(target=self.create_molecule_checkboxes, args=(), daemon=True).start()
        threading.Thread(target=self.create_tissue_checkboxes, args=(), daemon=True).start()
        #self.create_molecule_checkboxes()
        #self.create_tissue_checkboxes()
        self.create_export_output_options()

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
        # if self.output_directory is None:

        self.selected_output_dir_label.configure(text = self.output_directory)
    
    def change_output_label(self):
        if self.export_file_option.get() ==2 :
            self.output_folder_label.configure(text = "Enter output folder name:")
        else :
            self.output_folder_label.configure(text = "Enter output file name:")

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
    
    def display_cor_cluster(self):
        data_path = './datasets/'
        adata1=sc.read(data_path+'brain2_metabolomics.h5ad')
        adata2=sc.read(data_path+'brain2_lipidomics.h5ad')
        print("here")
        corr = algo_sami_correlation.calculate_corr(adata1,adata2)
        print("here1")
        fig= algo_sami_correlation.corr_plot(adata1,adata2,'m.z.256.995','m.z.862.606',xomic='Metabolite',yomic='Lipid')
        canvas = FigureCanvasTkAgg(fig, master=self.corr_plot_tab)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0,column=0)
        adata = sc.read(data_path+'brain2_pool.h5ad') #load pool dataset (triple-omics) of brain2
        data = algo_sami_correlation.adata_filter(adata,abundance=0,prevalence=0.95).to_df() #filter out m.z with prevalence smaller than 0.95

        corr_matrix = data.corr() ## calculate correlation intra and inter omics
        corr_df = pd.DataFrame(data=corr_matrix, index=data.columns, columns=data.columns)
        fig1 = algo_sami_correlation.corr_network(adata,corr_df)
        canvas1 = FigureCanvasTkAgg(fig1, master=self.corr_network_tab)
        canvas1.draw()
        canvas1.get_tk_widget().grid(row=0,column=0)

        # cluster('brain1_pool.h5ad',res=1.4)
        # fig2=plot_cluster('brain1_pool_1.4.h5ad')
        # canvas2 = FigureCanvasTkAgg(fig2, master=self.cluster_tab)
        # canvas2.draw()
        # canvas2.get_tk_widget().grid(row=0,column=0)

        
        
if __name__ == "__main__":
    app = MetaVision3dApp()
    app.mainloop()
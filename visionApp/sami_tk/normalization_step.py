import tkinter as tk
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import pandas as pd
import os
import logging

# from tkinter import filedialog, messagebox
# import threading
# from sami_tk_utilities import open_file, open_multiple_files
# import glob
# from .file_handler import FileOpenbutton
from .compound_matrix import create_compound_matrix

# from .process_steps import process_state
import math
from pylab import Figure
import numpy as np
from waiting import wait
from PIL import Image, ImageTk
import queue
# from customtkinter import CTkImage
from .colormap import *
import io
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox
# from .visualization_step import VisualizationStep
import matplotlib.animation as animation
import time
import threading
import sys
sys.path.append('../SAMI')
# sys.path.append(r'C:\Users\ghari\Documents\OPS\UI\metavision3d_app\visionApp\SAMI')
# rest of the code...
from SAMI.norm import create_norm_dataset_gui
from .timer import TimerApp

logger = logging.getLogger(__name__)

class NormalizationStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.right_frame = None
        self.norm_slides = None
        self.normalized_coumpount_matrix = None
        self.queue = queue.Queue()  
        self.normalized_data = {}

        self.file_handler = file_handler
        self.pre_norm_label = None
        self.post_norm_label = None
        self.create_visualization_dock_type1()
        self.prepare_visualization_dock_type1()
        self.create_normalization_tab()
        # self.check_for_normalization_thread_signal()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

    def refresh(self):
        pass

    def create_visualization_dock_type1(self):
        """Under the visualization tab, we have two frames, left and right frame
        Left frame is for displaying the files and color maps and right frame is for displaying the results
        """

        for widget in self.winfo_children():
            widget.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
        self.root_visualization_frame.columnconfigure(1, weight=2)
        self.root_visualization_frame.rowconfigure(0, weight=1)

        # splitting the visaulization frame into two parts, left and right side
        self.left_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.right_frame = ctk.CTkFrame(self.root_visualization_frame)

        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=1)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=1)
        self.root_visualization_frame.grid(row=0, column=0, sticky="nsew")

    def create_left_visualization_dock_type1(self):
        """This function deals with the left side of the visualization frame
        It consists of file selection and color map display frame and the scrollable frame
        """

        # file selection and color map display frame
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.rowconfigure(0, weight=1)
        self.left_frame.rowconfigure(1, weight=10)

        self.selection_frame = ctk.CTkFrame(self.left_frame)
        self.selection_frame.grid(
            row=0, column=0, sticky="nsew", padx=5, pady=1,)
        # self.file_selection_frame.columnconfigure(0,weight=1)
        # self.selection_frame.rowconfigure(0, weight=1)
        # self.selection_frame.columnconfigure((0,1,2,3,4,5, 6, 7 , 8), weight=1)
        

        # File dropdown
        self.var_file_name = ctk.CTkLabel(self.selection_frame, text="Select File: ")
        self.var_file_name.grid(row=0, column=0, padx=(5, 5), pady=10, sticky="e")

        # waiting till the input files are ready
        wait(
            lambda: self.file_handler.is_files_read,
            timeout_seconds=600,
            waiting_for="File reading",
        )
        default_value = ctk.StringVar(value="Select Dataset")
        self.file_dropdown = ctk.CTkOptionMenu(
            master=self.selection_frame,
            values=self.file_handler.base_files,
            command=self.update_frame_with_file,
            variable=default_value,
            width= 180
        )
        self.file_dropdown.grid(row=0, column=1, padx=(5, 5), pady=10, sticky="e")

        # Color map dropdown
        self.var_color_map = ctk.CTkLabel(
            self.selection_frame, text="Select colorMap: "
        )
        self.var_color_map.grid(row=0, column=2, padx=(5, 5), pady=10, sticky="e")
        default_value2 = ctk.StringVar(value="gray")
        self.color_map_dropdown = ctk.CTkOptionMenu(
            master=self.selection_frame,
            values=["gray", "magma", "viridis"],
            command=self.update_frame_with_selected_color_map,
            variable=default_value2,
        )
        self.color_map_dropdown.grid(row=0, column=3, padx=(5, 5), pady=10, sticky="e")

        #molecule dropdown
        self.var_molecule = ctk.CTkLabel(self.selection_frame, text="Select Molecule:")
        self.var_molecule.grid(row=0, column=4, padx=(5, 5), pady=10, sticky="e")
        # a dropdown to select the molecule
        default_value3 = ctk.StringVar(value="Select Molecule")
        self.molecule_dropdown = ctk.CTkComboBox(
            master=self.selection_frame,
            values=[],#self.file_handler.molecule_name[self.file_dropdown.get()],
            command=self.update_frame_with_molecule,
            variable=default_value3,
        )
        self.molecule_dropdown.grid(row=0, column=5, padx=(5, 5), pady=10, sticky="e")

        # loading label
        self.loading_label = ctk.CTkLabel(self.selection_frame,text="", font = ("Arial", 14), width = 65, )
        self.loading_label.grid(row=0,column=6,padx=(5, 5), pady=10, sticky="e")

        # scrollable frame on the left side of the visualization frame
        self.slides_display_frame = ctk.CTkScrollableFrame(self.left_frame, height=500)
        self.slides_display_frame.grid(row=1, column=0, padx=5, pady=1, sticky="new")

        # loading label
        # self.display_processing()
        # self.loading_label = ctk.CTkLabel(self.left_frame,text="NOT Loading....", font = ("Arial", 24))
        # self.loading_label.grid(row=2,column=0,padx=5,pady=1,sticky ="sew")

    def create_right_visualization_dock_type1(self):
        """This function deals with the right side of the visualization frame
        It consists of tabview for the visualization results
        """
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        self.vis_tabs = ctk.CTkTabview(self.right_frame)
        self.vis_tabs.grid(row=0, column=0, sticky="nsew", padx=5)
        self.normalization = self.vis_tabs.add("Normalisation")
        self.norm_plot = self.vis_tabs.add("Norm Plot") 
        self.norm_slides = self.vis_tabs.add("Normalised Slides")
        self.comparison = self.vis_tabs.add("Comparison")


        self.norm_slides.columnconfigure(0, weight=1)
        self.norm_slides.rowconfigure(0, weight=1)

        # self.comparison.columnconfigure(0, weight=1)
        # self.comparison.rowconfigure(0, weight=1)

        self.norm_plot.columnconfigure(0, weight=1)
        self.norm_plot.rowconfigure(0, weight=1)

        self.normalization.columnconfigure(0, weight=1)
        self.normalization.rowconfigure(0, weight=1)

    def prepare_visualization_dock_type1(self):
        """This visualization is used for the tabs 1. Visualization and 2. Normalization
        This view have left and right visualization frames"""

        self.create_visualization_dock_type1()
        self.create_left_visualization_dock_type1()
        self.create_right_visualization_dock_type1()


    def create_normalization_tab(self):
        """This function deals with the Normalization tab
        It consists of a frame for the slides and a frame for the animation
        """

        for widget in self.normalization.winfo_children():
            widget.destroy()

        # self.normalization.columnconfigure(0, weight=1)
        # self.normalization.columnconfigure(0, weight=1)
        # self.normalization.rowconfigure(0, weight=1)

        self.norm_frame = ctk.CTkFrame(self.normalization)
        self.norm_frame.grid(row=0, column=0, sticky="nsew")
        # self.norm_frame.columnconfigure((0,1,2), weight=1)
        # self.norm_frame.rowconfigure(0, weight=1)
        # self.norm_frame.columnconfigure(0, weight=1)
        # self.norm_frame.rowconfigure(0, weight=1)

        # two drop downs, and a run button
        #creating a dropwodn from rownorm
        label1 = ctk.CTkLabel(self.norm_frame, text="RowNorm :" )
        label1.grid(row=0,column=0,padx=(5,0),pady=8,sticky="w")

        norm_default_value = ctk.StringVar(value="SumNorm :")
        self.algo_selection_dropdown = ctk.CTkComboBox(master= self.norm_frame,
                                            values=['SumNorm'],
                                            variable=norm_default_value,button_color="#b5b8b0"
                                            )
        self.algo_selection_dropdown.grid(row=0,column=1,padx=(0,0),pady=8,sticky="w")
        

        # creating a dropdown for transnorm
        label2 = ctk.CTkLabel(self.norm_frame, text="transNorm :")
        label2.grid(row=1,column=0,padx=(5,0),pady=8,sticky="w")

        norm_default_value2 = ctk.StringVar(value="LogTrans2")
        self.algo_selection_dropdown2 = ctk.CTkComboBox(master= self.norm_frame,
                                            values=['LogTrans2'],  
                                            variable=norm_default_value2, button_color="#b5b8b0"
                                            )
        self.algo_selection_dropdown2.grid(row=1,column=1,padx=(0,0),pady=8,sticky="w")

        # creating a run button
        self.run_button = ctk.CTkButton(master=self.norm_frame, text="Run Normalization", command=self.onlick_run_normalization, width=70)
        self.run_button.grid(row=2,column=0,padx=(60,0),pady=8,sticky="w")

        # creating a label to show the timer
        self.timer = TimerApp(self.norm_frame)
        self.timer.grid(row=3,column=0,padx=(60,0),pady=8,sticky="w")

        # creating a label to show the normalization is in processing
        self.norm_done_label = ctk.CTkLabel(self.norm_frame, text="", font = ("Arial", 14) , width= 600, height=80)
        self.norm_done_label.grid(row=4,column=0,padx=(0,0),pady=8,sticky="w", rowspan = 3, columnspan = 3)
        
 

    def run_normalization(self):

        # waiting till the input files are read
        wait(
            lambda: self.file_handler.is_files_read,
            timeout_seconds=600,
            waiting_for="File reading",
        )

        # running normalization
        self.normalized_data[self.file_dropdown.get()] = create_norm_dataset_gui(self.file_handler.input_data_raw[self.file_dropdown.get()],
                                                               self.file_handler.working_folder,
                                                               self.file_dropdown.get(),
                                                                rowNorm = self.algo_selection_dropdown.get(),
                                                                transNorm = self.algo_selection_dropdown2.get()
                                                               )

        self.compound_matrix, self.compound_matrix_high_res, self.dict_id_to_tissue_name = create_compound_matrix(
            self.file_handler.input_data_raw[self.file_dropdown.get()],
            self.file_handler.molecule_name[self.file_dropdown.get()][0],
            roi=False,
            reverse=True,
        )
        
        self.norm_compound_matrix, self.normalised_compound_matrix_high_res, _ = create_compound_matrix( 
                                                            self.normalized_data[self.file_dropdown.get()],
                                                            self.file_handler.molecule_name[self.file_dropdown.get()][0],
                                                            roi=False,
                                                            reverse=True,
                                                            )
        self.queue.put("Normalization_done")
        
        # writing a ctk label to show the normalization is done

    def onlick_run_normalization(self):

        if self.file_dropdown.get() == "Select Dataset":
            CTkMessagebox(title="Info", message="Please select a dataset on the left panel")
        else:
            self.norm_done_label.configure(text="Normalization is running")
            self.timer.reset_timer()
            self.timer.start_timer()
            #creating a thread to run the normalization
            threading.Thread(target=self.run_normalization, args=(), daemon=True).start()
            self.check_for_normalization_thread_signal()
    
    def check_for_normalization_thread_signal(self):
        

        if not self.queue.empty():
            message = self.queue.get()
            if message == 'Normalization_done':
                logger.info("Normaliztion done, trigger received")
                # print("HIT")
                self.norm_done_label.configure(text="Normalization is completed. \n\
                                               Make sure, you run the omics pooling once you are done with Normalization\n\
                                               Otherwise, the Next steps, will not use the latest normalized data", font = ("Arial", 14))
                self.display_norm_plot(self.compound_matrix_high_res, self.normalised_compound_matrix_high_res )
                self.timer.stop_timer()   
        else:
            # Schedule the next queue check
            self.after(1000, self.check_for_normalization_thread_signal)

    def update_frame_with_file(self, choice):

        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()
    

        # time.sleep(3)
        wait(
            lambda: self.file_handler.is_files_read,
            timeout_seconds=600,
            waiting_for="File reading",
        )
        #dynamically updating the molecule dropdown
        self.molecule_dropdown.configure(values= self.file_handler.molecule_name[self.file_dropdown.get()])
        self.molecule_dropdown.set(self.file_handler.molecule_name[self.file_dropdown.get()][0])
        self.compound_matrix, self.compound_matrix_high_res , self.dict_id_to_tissue_name = create_compound_matrix(
            self.file_handler.input_data_raw[self.file_dropdown.get()],
            self.molecule_dropdown.get(),
            roi=False,
            reverse=True,
        )
        # time.sleep(5)
        self.create_frames_in_slides_display_frame(self.compound_matrix_high_res)
        self.loading_label.configure(text="")
        

    def update_frame_with_selected_color_map(self, choice):


        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()
        self.create_frames_in_slides_display_frame(self.compound_matrix_high_res)
        self.loading_label.configure(text="")
        

    def update_frame_with_molecule(self, choice):
        
        if self.file_dropdown.get() not in self.normalized_data.keys():
            CTkMessagebox(title="Info", message="Please run the normilsation to display normalized iamges")
        else:

            self.loading_label.configure(text="Loading...", text_color="yellow")
            self.update()
            self.compound_matrix, self.compound_matrix_high_res , self.dict_id_to_tissue_name  = create_compound_matrix(
                self.file_handler.input_data_raw[self.file_dropdown.get()],
                choice,
                roi=False,
                reverse=True,
            )

            self.norm_compound_matrix, self.normalised_compound_matrix_high_res, _ = create_compound_matrix( 
                                                        self.normalized_data[self.file_dropdown.get()],
                                                        choice,
                                                        roi=False,
                                                        reverse=True,
                                                        )

            self.create_frames_in_slides_display_frame(self.compound_matrix_high_res)
            self.display_norm_plot(self.compound_matrix_high_res, self.normalised_compound_matrix_high_res)
            self.loading_label.configure(text="")

    def create_frames_in_slides_display_frame(self, data):

        logger.info("creating frames in slides display frame")
        logger.info("number children in slides display frame : {}".format(len(self.slides_display_frame.winfo_children()) ))

        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()
        # self.display_montage(data)
        logger.info("num children in slides after destruction in disaply frame : {}".format(len(self.slides_display_frame.winfo_children()) ))

        slices, rows, cols = data.shape
        N = round(math.sqrt(slices))

        grid_rows = slices / 3
        grid_cols = 3

        if grid_rows * grid_cols < slices:
            grid_rows += 1

        # Create a frame for each image and store it for later processing
        self.vmax = np.percentile(data[data != 0], 99)
        self.frames = []
        for i in range(slices):
            frame = ctk.CTkFrame(
                self.slides_display_frame,
                width=100,
                height=80,
                border_width=2,
                border_color="#474644",
            )
            frame.grid(row=i // grid_cols, column=i % grid_cols, padx=2, pady=2, sticky="nsew") 
            # print(data[i])
            self.frames.append((frame, data[i], i))

        # Schedule the image processing after the window is rendered
        self.after(100, self.process_images)
        # self.after(500, self.display_animation())

    def process_images(self):
        for frame, image_array, id in self.frames:
            self.display_image_in_frame(image_array, frame, id)
        # self.show_cmap_switch()

    def display_image_in_frame(self, image_array, frame, id):

        fig = Figure(figsize=(2, 1.1), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_facecolor("black")
        fig.patch.set_facecolor("black")
        if self.color_map_dropdown.get() == "magma":
            im = ax.imshow(image_array, cmap=new_cmap1, vmin=0, vmax=self.vmax)
        elif self.color_map_dropdown.get() == "viridis":
            im = ax.imshow(image_array, cmap=new_cmap2, vmin=0, vmax=self.vmax)
        else:
            im = ax.imshow(image_array, cmap="grey")
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            pad_inches=0,
            facecolor=fig.get_facecolor(),
            edgecolor="none",
        )
        buf.seek(0)
        resized_image = Image.open(buf)
        photo = ImageTk.PhotoImage(resized_image)

        # Create a label to display the image
        label = ctk.CTkLabel(frame, image=photo, text="")
        label.image = photo  # Keep a reference
        label.grid(row=0, column=0, padx=4, pady=4)
        label.bind("<Button-1>", partial(self.on_label_click_main, id=id))

        label_tissue  = ctk.CTkLabel(frame, text=str(self.dict_id_to_tissue_name[id]), height = 14)
        label_tissue.grid(row=1, column=0, padx=2, pady=0)

    def on_label_click_main(self, event, id):

        if self.file_dropdown.get() not in self.normalized_data.keys():
            CTkMessagebox(title="Info", message="Please run the normilsation to display normalized iamges")
        else:
            self.on_label_click(event, id)
            self.on_label_click_pre_post_norm_comparison(event, id)

    def on_label_click(self, event, id):

        matrix = self.normalised_compound_matrix_high_res[id]
        # print(matrix.shape)
        scale_factor = 1  # Adjust this factor to scale the image size up
        dpi = 300  # Increasing the DPI for better resolution and larger image
        # Calculate the figure size based on the image dimensions and scaling factor
        height, width = matrix.shape
        figsize = (width / float(dpi) * scale_factor, height / float(dpi) * scale_factor)
        # Create the figure with the adjusted size and dpi
        fig = Figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(111)
        # ax = fig.add_subplot(111)
        # ax.set_facecolor('white')

        # 

        # Clear existing widgets in the container
        for widget in self.norm_slides.winfo_children():
            widget.destroy()

        # Create a frame to hold the canvas
        self.slide_tab_frame = ctk.CTkFrame(self.norm_slides)
        self.slide_tab_frame.grid(row=0, column=0, sticky="nsew")
        self.slide_tab_frame.columnconfigure(0, weight=1)
        self.slide_tab_frame.rowconfigure(0, weight=1)

        # Add the canvas to the frame
        canvas = FigureCanvasTkAgg(fig, master=self.slide_tab_frame)
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

        # Determine the colormap based on user selection
        cmap = self.color_map_dropdown.get()
        cmap_options = {"gray": "gray", "magma": new_cmap1, "viridis": new_cmap2}
        cmap = cmap_options.get(cmap, "gray")

        # Display the image
        im = ax.imshow(matrix, cmap=cmap, aspect='equal')
        #ax.set_title(self.dict_id_to_tissue_name[id], fontsize=12, color='black')

        # Add color bar if applicable
        if cmap in ["magma", "viridis"]:
            cbar = fig.colorbar(
                im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
            )
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(["low", "high"])

        # Turn off axis labeling to maximize space for the image
        ax.axis("off")
        fig.tight_layout(pad=0)  # This reduces the padding around the image

        # Draw the canvas
        canvas.draw()

        image_label = ctk.CTkLabel(self.norm_slides, text= "Tissue : "+str(self.dict_id_to_tissue_name[id]), font=("Arial", 16))
        image_label.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
    

    def on_label_click_pre_post_norm_comparison(self,  event, id):
        # print("comparison", id)

        #num children in comparison frame
        logger.info("num children in comparison frame : {}".format(len(self.comparison.winfo_children())))

        # Add a Matplotlib canvas to the Tkinter frame
        for widget in self.comparison.winfo_children():
            if widget != self.pre_norm_label or widget != self.post_norm_label:
                widget.destroy()

        logger.info("num children in comparison frame after destruction : {}".format(len(self.comparison.winfo_children())))
        
        # creatded a parent frame for the comparison tab
        self.comp_parent_frame = ctk.CTkFrame(self.comparison)
        self.comp_parent_frame.grid(row=0, column=0, sticky="nsew")
        self.comp_parent_frame.columnconfigure(0, weight=1)
        self.comp_parent_frame.rowconfigure((0,1,2,3, 4), weight=1)
        # self.comp_parent_frame.rowconfigure(0, weight=1)

        self.image_label = ctk.CTkLabel(self.comp_parent_frame, text=str(self.dict_id_to_tissue_name[id]), font=("Arial", 16))
        self.image_label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        #creating a label for pre normalization
        #if self.pre_norm_label is None:
        self.pre_norm_label = ctk.CTkLabel(self.comp_parent_frame, text="Pre Normalization", font = ("Arial", 12))
        self.pre_norm_label.grid(row=1,column=0,padx=(5,0),pady=8,sticky="w")
        #creating a frame for pre normalization
        self.pre_norm_frame = ctk.CTkFrame(self.comp_parent_frame)
        self.pre_norm_frame.grid(row=2, column=0, sticky="w")
        self.pre_norm_frame.columnconfigure(0, weight=1)
        self.pre_norm_frame.rowconfigure(0, weight=1)

        #creating a label for post normalization
        #if self.post_norm_label is None:
        self.post_norm_label = ctk.CTkLabel(self.comp_parent_frame, text="Post Normalization", font = ("Arial", 12))
        self.post_norm_label.grid(row=3,column=0,padx=(5,0),pady=8,sticky="w")
        #creating a frame for post normalization
        self.post_norm_frame = ctk.CTkFrame(self.comp_parent_frame)
        self.post_norm_frame.grid(row=4, column=0, sticky="w")
        self.post_norm_frame.columnconfigure(0, weight=1)
        self.post_norm_frame.rowconfigure(0, weight=1)

        # creating a label with the tissue name

        # Prenormalizaton frame
        matrix = self.compound_matrix_high_res[id]
        # print(matrix.shape)
        scale_factor = 0.6  # Adjust this factor to scale the image size up
        dpi = 300  # Increasing the DPI for better resolution and larger image
        # Calculate the figure size based on the image dimensions and scaling factor
        height, width = matrix.shape
        figsize = (width / float(dpi) * scale_factor, height / float(dpi) * scale_factor)
        # Create the figure with the adjusted size and dpi
        fig = Figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(111)

        # Add the canvas to the frame
        canvas = FigureCanvasTkAgg(fig, master=self.pre_norm_frame)
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        # Determine the colormap based on user selection
        cmap = self.color_map_dropdown.get()
        cmap_options = {"gray": "gray", "magma": new_cmap1, "viridis": new_cmap2}
        cmap = cmap_options.get(cmap, "gray")

        # Display the image
        im = ax.imshow(matrix, cmap=cmap, aspect='equal')
        #ax.set_title(self.dict_id_to_tissue_name[id], fontsize=12, color='black')

        # Add color bar if applicable
        if cmap in ["magma", "viridis"]:
            cbar = fig.colorbar(
                im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
            )
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(["low", "high"])

        # Turn off axis labeling to maximize space for the image
        ax.axis("off")
        fig.tight_layout(pad=0)  # This reduces the padding around the image
        canvas.draw()


        # POST Normalization frame
        matrix = self.normalised_compound_matrix_high_res[id]
        # print(matrix.shape)
        scale_factor = 0.6  # Adjust this factor to scale the image size up
        dpi = 300  # Increasing the DPI for better resolution and larger image
        # Calculate the figure size based on the image dimensions and scaling factor
        height, width = matrix.shape
        figsize = (width / float(dpi) * scale_factor, height / float(dpi) * scale_factor)
        # Create the figure with the adjusted size and dpi
        fig2 = Figure(figsize=figsize, dpi=dpi)
        ax2 = fig2.add_subplot(111)

        # Add the canvas to the frame
        canvas2 = FigureCanvasTkAgg(fig2, master=self.post_norm_frame)
        canvas2.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        # Determine the colormap based on user selection
        cmap = self.color_map_dropdown.get()
        cmap_options = {"gray": "gray", "magma": new_cmap1, "viridis": new_cmap2}
        cmap = cmap_options.get(cmap, "gray")

        # Display the image
        im = ax2.imshow(matrix, cmap=cmap, aspect='equal')
        #ax.set_title(self.dict_id_to_tissue_name[id], fontsize=12, color='black')

        # Add color bar if applicable
        if cmap in ["magma", "viridis"]:
            cbar = fig.colorbar(
                im, ax=ax2, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
            )
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(["low", "high"])

        # Turn off axis labeling to maximize space for the image
        ax2.axis("off")
        fig2.tight_layout(pad=0)  # This reduces the padding around the image
        canvas2.draw()
    #     return fig
    
    def generate_boxplot_directly(self, matrix, ax, title):
        import numpy as np
        matrix_reshape = matrix.reshape(matrix.shape[0], -1)

        non_zero_list = []
        for row in matrix_reshape:
            non_zero_row = row[np.nonzero(row)]
            non_zero_list.append(non_zero_row)

        ax.boxplot(non_zero_list, vert=False, showfliers=False)
        ax.invert_yaxis()
        ax.set_title(title, fontweight='bold', fontsize=12)
        ax.set_xlabel('Intensity', fontweight='bold', fontsize=12)
        ax.set_ylabel('Slice', fontweight='bold', fontsize=12)
        ax.tick_params(axis='both', which='both', labelsize=10)
        labels = ax.get_xticklabels() + ax.get_yticklabels()
        labels = [label.set_fontweight('bold') for label in labels]
                
    def display_norm_plot(self, matrix, norm_matrix):

        for widget in self.norm_plot.winfo_children():
            widget.destroy()

        self.norm_plot_frame = ctk.CTkScrollableFrame(self.norm_plot,height =600,width =400)
        self.norm_plot_frame.columnconfigure(0,weight=1)
        self.norm_plot_frame.rowconfigure(0,weight=1)
        self.norm_plot_frame.grid(row=0,column=0,sticky="nsew")
        # data_fig = self.generate_boxplot(matrix)
        # normalised_data_fig = self.generate_boxplot(norm_matrix)

        combined_fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        # Generate plots directly on the axes
        self.generate_boxplot_directly(matrix, ax1, "Original Data")
        self.generate_boxplot_directly(norm_matrix, ax2, "Normalized Data")
        canvas = FigureCanvasTkAgg(combined_fig, master=self.norm_plot_frame)  # A tk.DrawingArea
        canvas.draw()
        canvas.get_tk_widget().grid(row=0,column=0)


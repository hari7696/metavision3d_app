
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
from .compound_matrix import create_compound_matrix_sami_skeleton
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


logger = logging.getLogger(__name__)

class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame):
        super().__init__(master, )
        self.columnconfigure(0,weight=1)
        self.nav_frame = nav_frame
        self.nav_frame.columnconfigure(0,weight=1)
        self.nav_frame.columnconfigure(2,weight=1)
        self.nav_frame.columnconfigure(4,weight=1)
        self.nav_frame.columnconfigure(6,weight=5)
        self.process_step = None
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        self.right_frame = None
        
        
        # title = ctk.CTkLabel(nav_frame, text="SAMI", fg_color="gray30", corner_radius=6)
        # title.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")
        logger.debug("SAMI class initialized")

        # for the SAMI UI, we need to choose whether the processing needs to be done on single file or multiple files 
        
        file_type_variable = ctk.StringVar(value="Single/Multi file?")
        self.dropdown_file_type_single_multi = ctk.CTkOptionMenu(self.nav_frame,
                                                            values = ["Single file","Multi file"],
                                                            command=self.file_open, 
                                                            variable=file_type_variable)
        self.dropdown_file_type_single_multi.grid(row=0,column=2,padx =(5,0), pady=(2,2),sticky="w")

        self.create_process_bar()
        logger.debug(f"Number of children in nav_frame: { len(self.nav_frame.winfo_children())}")
        logger.debug("Number of children in parent: {}".format(len(list(self.winfo_children()))))
        self.create_parent_tab_switch()
        # self.create_visualization_dock()
        # self.create_left_visualization_dock()
        

    def file_open(self, choice):
        self.file_handler = FileOpenbutton(self.nav_frame)
        self.file_handler.file_opening_button(choice)
        self.file_handler.grid(row=0,column=4,padx =(5,0), pady=(2,2),sticky="w")
        #updating the process bar based on the file type selected
        self.create_process_bar()

    
    def create_process_bar(self):
        """Bar in the NavFrame to show the process steps
        This bar is gonna trigger the process steps 
        """ 
        # destroying the existing process bar, before creating a new one. The initial value of of process_step is None
        for widget in self.nav_frame.winfo_children():
            if widget == self.process_step:
                widget.destroy()

        logger.debug("value in dropdown:{}".format(self.dropdown_file_type_single_multi.get()))
        # multi file process steps
        values = ["Visualization", "Normalization", "Pooling", "Clustering", 
                  "Clusters Integration", "Markers", "Pathways"]

        if self.dropdown_file_type_single_multi.get() == "Single file":
            values  = ["Visualization", "Normalization", "Pooling",
                    "Clustering", "Markers"]
            
        self.process_step = ctk.CTkSegmentedButton(master=self.nav_frame,
                               values=values,
                                command=self.execute_selected_step)
        self.process_step.grid(row=0, column=6, padx=(25, 0), pady=(2, 2), sticky="w", columnspan=6)

    def create_parent_tab_switch(self):
        """ Parent Tab consists of Visualization and Export tabs"""

        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        self.parent_tab_switch = ctk.CTkTabview(self,bg_color="transparent")
        self.parent_tab_switch.columnconfigure(0,weight=1)
        self.parent_tab_switch.rowconfigure(0,weight=1)

        self.visualization_tab = self.parent_tab_switch.add("Visualization")
        self.export_tab = self.parent_tab_switch.add("Export")
        
        self.visualization_tab.columnconfigure(0,weight=1)
        self.visualization_tab.rowconfigure(0,weight=1)
        
        # it goes to parent frame row 1
        self.parent_tab_switch.grid(row=0,column=0,sticky="new", padx=5)   

    def create_visualization_dock_type1(self):

        """Under the visualization tab, we have two frames, left and right frame
        Left frame is for displaying the files and color maps and right frame is for displaying the results"""
        
        for widget in  self.visualization_tab.winfo_children():
            widget.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self.visualization_tab,bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0,weight=1)
        self.root_visualization_frame.columnconfigure(1,weight=2)
        self.root_visualization_frame.rowconfigure(0,weight=1)


        # splitting the visaulization frame into two parts, left and right side
        self.left_frame = ctk.CTkFrame(self.root_visualization_frame)
        self.right_frame = ctk.CTkFrame(self.root_visualization_frame)

        self.left_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=1)
        self.right_frame.grid(row=0,column=1,sticky="nsew",padx=5,pady=1)
        self.root_visualization_frame.grid(row=0,column=0,sticky="nsew")
        

    def create_left_visualization_dock_type1(self):

        """ This function deals with the left side of the visualization frame
        It consists of file selection and color map display frame and the scrollable frame
        """

        #file selection and color map display frame
        self.left_frame.columnconfigure(0,weight=1)
        self.left_frame.rowconfigure(0,weight=1)
        self.selection_frame = ctk.CTkFrame(self.left_frame)
        self.selection_frame.grid(row=0,column=0,sticky="nsew",padx=5,pady=1, columnspan =2)
        # self.file_selection_frame.columnconfigure(0,weight=1)
        self.selection_frame.rowconfigure(0,weight=1)

        # File dropdown
        self.var_file_name = ctk.CTkLabel(self.selection_frame,text="Select File: ")
        self.var_file_name.grid(row=0,column=0,padx=(5,0),pady=10, sticky="e")
        
        # waiting till the input files are ready
        wait(lambda: self.file_handler.is_files_read, timeout_seconds=600, waiting_for="File reading")

        self.file_dropdown = ctk.CTkOptionMenu(master= self.selection_frame,
                                            values = self.file_handler.base_files,
                                            command=self.update_frame_with_file,
                                            )
        self.file_dropdown.grid(row=0,column=2,padx=(5,0),pady=10, sticky="e")
        
        # Color map dropdown
        self.var_color_map = ctk.CTkLabel(self.selection_frame,text="Select colorMap: ")
        self.var_color_map.grid(row=0,column=4,padx=(5,0),pady=10, sticky="e")
        self.color_map_dropdown = ctk.CTkOptionMenu(master= self.selection_frame,
                                            values=["grey","magma", "viridis"],
                                            command=self.on_click_color_map,
                                            )
        self.color_map_dropdown.grid(row=0,column=6,padx=(5,0),pady=10, sticky="e")
        
        # scrollable frame on the left side of the visualization frame
        self.slides_display_frame = ctk.CTkScrollableFrame(self.left_frame, height=500)
        self.slides_display_frame.grid(row =1,column=0, padx=5,pady=1,sticky ="sew")

    def create_right_visualization_dock_type1(self):
            
            """ This function deals with the right side of the visualization frame
            It consists of tabview for the visualization results
            """
            self.right_frame.columnconfigure(0,weight=1)
            self.right_frame.rowconfigure(0,weight=1)
            self.vis_tabs = ctk.CTkTabview(self.right_frame) 
            self.vis_tabs.grid(row=0,column=0,sticky="nsew",padx =5)

    def destroy_children_vis_tabs(self):
        if self.right_frame is not None:
            for child in self.visualization_tab.winfo_children():
                child.destroy()

    def prepare_visualization_dock_type1(self):

        """ This visualization is used for the tabs 1. Visualization and 2. Normalization
        This view have left and right visualization frames"""

        self.destroy_children_vis_tabs()
        self.create_visualization_dock_type1()
        self.create_left_visualization_dock_type1()
        self.create_right_visualization_dock_type1()

    
    def prepare_visualization_dock_type2(self):

        """This visualization is used for the tabs 1. Pooling, 2. Clustering, 3. Clusters Integration, 4. Markers, 5. Pathways
            A separate tabview is created for this type of visualization, as it doesnt need left and right frames
        """

        for child in self.visualization_tab.winfo_children():
            child.destroy()

        self.root_visualization_frame2 = ctk.CTkFrame(self.visualization_tab,bg_color="transparent")
        self.root_visualization_frame2.columnconfigure(0,weight=1)
        # self.root_visualization_frame.columnconfigure(1,weight=2)
        self.root_visualization_frame2.rowconfigure(0,weight=1)
        self.root_visualization_frame2.grid(row=0,column=0,sticky="nsew")

        self.vis_tabs2 = ctk.CTkTabview(self.root_visualization_frame2) 
        self.vis_tabs2.grid(row=0,column=0,sticky="nsew",padx =5)
        self.vis_tabs2.columnconfigure(0,weight=1)
        self.vis_tabs2.rowconfigure(0,weight=1)


    def update_frame_with_file(self, choice):

        wait(lambda: self.file_handler.is_files_read, timeout_seconds=600, waiting_for="File reading")
        logging.info(f"file_inspection: {self.file_handler.input_data_raw[choice].columns}")
        logging.info(f"chosen molecule: {self.file_handler.molecule_name[choice][0]}")

        self.compound_matrix = create_compound_matrix_sami_skeleton(self.file_handler.input_data_raw[choice],
                                                                    self.file_handler.molecule_name[choice][0]
                                                                    , roi=False,reverse=True)
        self.create_frames_in_slides_display_frame( self.compound_matrix)
        

        

        print(f"Selected file: {choice}")
        pass

    def on_click_color_map(self, choice):
        print(f"Selected color map: {choice}")
        pass

    def execute_selected_step(self, choice):

        """
        This functions acts as a key trigger for the process steps
        It controls the right framme of the visualization tab

        """

        logger.info(f"Processing step: {choice}") 
        # tabview visualization on the right frame

        if choice == "Visualization": 

            self.prepare_visualization_dock_type1()
            self.slide = self.vis_tabs.add("Slide")
            self.animation = self.vis_tabs.add("Animation")


            # self.region.columnconfigure(0,weight=1)
            # self.animation.columnconfigure(0,weight=1)
            # self.norm_plot.columnconfigure(0,weight=1)
        
        elif choice == "Normalization":

            self.prepare_visualization_dock_type1()
            self.normalization= self.vis_tabs.add("Normalization")
            self.norm_plot = self.vis_tabs.add("Norm Slides")
            self.pre_post_norm = self.vis_tabs.add("Pre-Post norm comparison")
            # self.norm_plot.columnconfigure(0,weight=1)
            # self.norma_regions.columnconfigure(0,weight=1)

        elif choice == "Pooling":
            self.prepare_visualization_dock_type2()
            self.pooling = self.vis_tabs2.add("Pooling")
            #self.pooling.columnconfigure(0,weight=1)

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

    
    def create_frames_in_slides_display_frame(self,data):
        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()
        # self.display_montage(data)
        
        slices, rows, cols = data.shape
        N = round(math.sqrt(slices))

        grid_rows = slices/3
        grid_cols = 3

        if grid_rows * grid_cols < slices:
            grid_rows += 1

        # Create a frame for each image and store it for later processing
        self.vmax = np.percentile(data[data != 0], 99)
        self.frames = []
        for i in range(slices):
            frame = ctk.CTkFrame(self.slides_display_frame,width = 160,height = 80,border_width =2,border_color = "#474644")
            frame.grid(row=i // grid_cols, column=i % grid_cols,padx =2,pady=2)
            # print(data[i])
            self.frames.append((frame, data[i],i))

        # Schedule the image processing after the window is rendered
        self.after(100, self.process_images)

    def process_images(self):
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
        fig = Figure(figsize=(1, 0.57), dpi=150)
        ax = fig.add_subplot(111)
        ax.set_facecolor('black')
        fig.patch.set_facecolor('black')
        if self.color_map_dropdown.get()=="magma":
            im = ax.imshow(image_array, cmap=new_cmap1,vmin=0, vmax=self.vmax)
        elif self.color_map_dropdown.get()=="viridis":
            im = ax.imshow(image_array, cmap= new_cmap2,vmin=0, vmax=self.vmax)
        else:
            im = ax.imshow(image_array,cmap="viridis")
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
    


    # def create_frames_in_slides_display_frame (self,data):
    #     for widget in self.slides_display_frame.winfo_children():
    #         widget.destroy()
    #     # self.display_montage(data)
        
    #     slices, rows, cols = data.shape
    #     N = round(math.sqrt(slices))

    #     grid_rows = int(slices/3)
    #     grid_cols = 3

    #     if grid_rows * grid_cols < slices:
    #         grid_rows += 1

    #     # Create a frame for each image and store it for later processing
    #     self.vmax = np.percentile(data[data != 0], 99)
    #     self.frames = []
    #     for i in range(slices):
    #         frame = ctk.CTkFrame(self.slides_display_frame,width = 84,height = 48,border_width =2,border_color = "#474644")
    #         frame.grid(row=i // grid_cols, column=i % grid_cols,padx =2,pady=2)
    #         # print(data[i])
    #         self.frames.append((frame, data[i],i))

    #     # Schedule the image processing after the window is rendered
    #     self.after(100, self.process_images)

    # def process_images(self):
    #     for frame, image_array, id in self.frames:
    #         self.display_image_in_frame(image_array, frame,id)
    #     # self.show_cmap_switch()
        

    # def display_image_in_frame(self, image_array, frame,id):
    #     '''
    #     Display the image in the given frame
    #     '''
    #     fig = Figure(figsize=(1, 0.57), dpi=100)
    #     ax = fig.add_subplot(111)
    #     ax.set_facecolor('black')
    #     fig.patch.set_facecolor('black')
    #     if self.color_map_dropdown.get()=="magma":
    #         im = ax.imshow(image_array, cmap=new_cmap1,vmin=0, vmax=self.vmax)
    #     elif self.color_map_dropdown.get()=="viridis":
    #         im = ax.imshow(image_array, cmap= new_cmap2,vmin=0, vmax=self.vmax)
    #     else:
    #         im = ax.imshow(image_array,cmap="gray")
    #     buf = io.BytesIO()
    #     fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, facecolor=fig.get_facecolor(), edgecolor='none')
    #     buf.seek(0)
    #     resized_image = CTkImage.open(buf)
    #     photo = ImageTk.PhotoImage(resized_image)

    #     # Create a label to display the image
    #     label = ctk.CTkLabel(frame, image=photo, text="")
    #     label.image = photo  # Keep a reference
    #     label.grid(row=0, column=0, padx=2, pady=2)
    #     label.bind("<Button-1>", partial(self.on_label_click, id=id))
    
    def on_label_click(self,event,id):
        print(id) 
        pass
    #     # fig = Figure(figsize=(7.7, 4.4))
    #     # ax = fig.add_subplot(111)

    #     # # Add a Matplotlib canvas to the Tkinter frame
    #     # for widget in self.slide_tab.winfo_children():
    #     #     widget.destroy()
    #     # self.slide_tab_frame = ctk.CTkFrame(self.slide_tab)
    #     # self.slide_tab_frame.grid(row=0,column=0,sticky="nsew")
    #     # canvas = FigureCanvasTkAgg(fig, master=self.slide_tab_frame)
    #     # canvas.get_tk_widget().grid(row=0,column=0)
    #     # matrix = self.compound_matrix[id]
    #     # if  self.cmap_switch_var.get() == "gray" :    
    #     #     im = ax.imshow(matrix, cmap="gray")
    #     # elif self.cmap_switch_var.get() == "magma" :
    #     #     im = ax.imshow(self.compound_matrix[id], cmap=new_cmap1)
    #     #     cbar = fig.colorbar(im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5)
    #     #     cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
    #     #     cbar.ax.set_yticklabels(['low', 'high'])
    #     # elif self.cmap_switch_var.get()== "viridis":
    #     #     im = ax.imshow(self.compound_matrix[id], cmap=new_cmap2)
    #     #     cbar = fig.colorbar(im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5)
    #     #     cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
    #     #     cbar.ax.set_yticklabels(['low', 'high'])


    #     # # Turn off axis labels and ticks
    #     # ax.axis('off')



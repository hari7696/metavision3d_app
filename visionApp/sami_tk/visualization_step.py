import customtkinter as ctk
import logging
from .compound_matrix import create_compound_matrix
import math
from pylab import Figure
import numpy as np
from waiting import wait
from PIL import Image, ImageTk
from .colormap import *
import io
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

class VisualizationStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.right_frame = None
        self.slide = None

        self.file_handler = file_handler
        self.create_visualization_dock_type1()
        self.prepare_visualization_dock_type1()
        self.isrendering = False

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

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
            row=0, column=0, sticky="nsew", padx=5, pady=1)
        # self.file_selection_frame.columnconfigure(0,weight=1)
        # self.selection_frame.rowconfigure(0, weight=1)

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
        self.file_dropdown = ctk.CTkComboBox(
            master=self.selection_frame,
            values=self.file_handler.base_files,
            command=self.update_frame_with_file,
            variable=default_value,
        )
        self.file_dropdown.grid(row=0, column=1, padx=(5, 5), pady=10, sticky="e")

        # Color map dropdown
        self.var_color_map = ctk.CTkLabel(
            self.selection_frame, text="Select colorMap: "
        )
        self.var_color_map.grid(row=0, column=2, padx=(5, 5), pady=10, sticky="e")
        default_value2 = ctk.StringVar(value="gray")
        self.color_map_dropdown = ctk.CTkComboBox(
            master=self.selection_frame,
            values=["gray", "magma", "viridis"],
            command=self.update_frame_with_selected_color_map,
            variable=default_value2,
        )
        self.color_map_dropdown.grid(row=0, column=3, padx=(5, 0), pady=10, sticky="e")

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
        self.molecule_dropdown.grid(row=0, column=5, padx=(5, 0), pady=10, sticky="e")

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
        self.slide = self.vis_tabs.add("Tissues")
        # self.animation = self.vis_tabs.add("Animation")

    def prepare_visualization_dock_type1(self):
        """This visualization is used for the tabs 1. Visualization and 2. Normalization
        This view have left and right visualization frames"""

        # self.destroy_children_vis_tabs()
        self.create_visualization_dock_type1()
        self.create_left_visualization_dock_type1()
        self.create_right_visualization_dock_type1()

    # def display_processing(self):
    #     """ The onclick function will perofrm once its entirely executed, it would not display anything intermediate like 'loading or processing'"""

    #     self.loading_label = ctk.CTkLabel(self.left_frame,text="NOT Loading....", font = ("Arial", 24))
    #     self.loading_label.grid(row=2,column=0,padx=5,pady=1,sticky ="sew")

    # def loading_label_update(self):
    #     self.loading_label.configure(text = "Loading....")

    # def update_frame_handler(self, choice):
    #     self.loading_label_update()
    #     self.update_frame_with_file(choice)

    def update_frame_with_file(self, choice):

        # threading.Thread(target=self.loading_label_update, args= (),daemon=True).start()

        wait(
            lambda: self.file_handler.is_files_read,
            timeout_seconds=600,
            waiting_for="File reading",
        )
        logging.info(f"file_inspection: {self.file_handler.input_data_raw[self.file_dropdown.get()].columns}")
        logging.info(f"chosen molecule: {self.file_handler.molecule_name[self.file_dropdown.get()][0]}")

        #dynamically updating the molecule dropdown
        self.molecule_dropdown.configure(values= self.file_handler.molecule_name[self.file_dropdown.get()])
        self.molecule_dropdown.set(self.file_handler.molecule_name[self.file_dropdown.get()][0])
        self.compound_matrix, self.dict_id_to_tissue_name = create_compound_matrix(
            self.file_handler.input_data_raw[self.file_dropdown.get()],
            self.molecule_dropdown.get(),
            roi=False,
            reverse=True,
        )

        # time.sleep(5)
        self.create_frames_in_slides_display_frame(self.compound_matrix)


    def update_frame_with_selected_color_map(self, choice):

        self.create_frames_in_slides_display_frame(self.compound_matrix)

    
    def update_frame_with_molecule(self, choice):
        self.compound_matrix = create_compound_matrix(
            self.file_handler.input_data_raw[self.file_dropdown.get()],
            choice,
            roi=False,
            reverse=True,
        )

        # time.sleep(5)
        self.create_frames_in_slides_display_frame(self.compound_matrix)

    def create_frames_in_slides_display_frame(self, data):
        for widget in self.slides_display_frame.winfo_children():
            widget.destroy()
        # self.display_montage(data)

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
                width=220,
                height=140,
                border_width=4,
                border_color="#474644",
            )
            frame.grid(row=i // grid_cols, column=i % grid_cols, padx=3, pady=3, sticky="nsew") 
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
        label.bind("<Button-1>", partial(self.on_label_click, id=id))

        label_tissue  = ctk.CTkLabel(frame, text="Tissue: "+str(self.dict_id_to_tissue_name[id]), height = 14)
        label_tissue.grid(row=1, column=0, padx=2, pady=0)

        #         # Create a hover label
        # hover_label = ctk.CTkLabel(frame, text="")
        # hover_label.grid(row=0, column=0, padx=2, pady=2)
        # hover_label.bind("<Enter>", partial(self.on_hover_enter, id = id))
        # hover_label.bind("<Leave>", partial(self.on_hover_leave, id = id))

    # def on_hover_enter(self, event):
    #     # Code to execute when the mouse enters the hover label
    #     self.hover_label.configure(text="Hovering")

    # def on_hover_leave(self, event):
    #     # Code to execute when the mouse leaves the hover label
    #     self.hover_label.configure(text="")
    

    def on_label_click(self, event, id):
        #print(id)
        fig = Figure(figsize=(6, 6), dpi=100)
        ax = fig.add_subplot(111)

        # Add a Matplotlib canvas to the Tkinter frame
        for widget in self.slide.winfo_children():
            widget.destroy()
        self.slide_tab_frame = ctk.CTkFrame(self.slide)
        self.slide_tab_frame.grid(row=0, column=0, sticky="nsew")
        self.slide_tab_frame.columnconfigure(0, weight=1)
        self.slide_tab_frame.rowconfigure(0, weight=1)
        canvas = FigureCanvasTkAgg(fig, master=self.slide_tab_frame)
        canvas.get_tk_widget().grid(row=0, column=0)
        matrix = self.compound_matrix[id]
        if self.color_map_dropdown.get() == "gray":
            im = ax.imshow(matrix, cmap="gray")
        elif self.color_map_dropdown.get() == "magma":
            im = ax.imshow(self.compound_matrix[id], cmap=new_cmap1)
            cbar = fig.colorbar(
                im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
            )
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(["low", "high"])
        elif self.color_map_dropdown.get() == "viridis":
            im = ax.imshow(self.compound_matrix[id], cmap=new_cmap2)
            cbar = fig.colorbar(
                im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
            )
            cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            cbar.ax.set_yticklabels(["low", "high"])
        else:
            im = ax.imshow(matrix, cmap="gray")

        # Turn off axis labels and ticks
        ax.axis("off")

    # def display_animation(self):

    #     for children in self.animation.winfo_children():
    #         children.destroy()

    #     self.ani_fig, self.ani_ax = plt.subplots(figsize=(6, 6), dpi=100)
    #     self.current_frame = 0
    #     self.ani = animation.FuncAnimation(
    #         self.ani_fig,
    #         self.update_animation_plot,
    #         frames=len(self.compound_matrix),
    #         interval=100,
    #     )

    #     # Embed the plot in the Tkinter window
    #     self.animation_canvas = FigureCanvasTkAgg(self.ani_fig, master=self.animation)
    #     self.animation_canvas_widget = self.animation_canvas.get_tk_widget()
    #     self.animation_canvas_widget.grid(row=0, column=0)
    #     self.animation_slider = ctk.CTkSlider(
    #         self.animation,
    #         from_=0,
    #         to=len(self.compound_matrix) - 1,
    #         command=self.animation_slider_changed,
    #     )
    #     self.animation_slider.grid(row=1, column=0)
    #     self.animation_slider.columnconfigure(0, weight=1)
    #     self.animation_slider.columnconfigure(0, weight=1)

    # def animation_slider_changed(self, event):
    #     frame = int(float(self.animation_slider.get()))
    #     if frame != self.current_frame:
    #         self.update_animation_plot(frame)
    #         self.ani.event_source.stop()
    #         self.animation_canvas.draw()

    # def update_animation_plot(self, frame):
    #     # frame = int(float(self.animation_slider.get()))
    #     self.ani_ax.clear()
    #     if self.color_map_dropdown.get() == "magma":
    #         self.ani_ax.imshow(
    #             self.compound_matrix[frame], cmap=new_cmap1, vmin=0, vmax=self.vmax
    #         )
    #     elif self.color_map_dropdown.get() == "viridis":
    #         self.ani_ax.imshow(
    #             self.compound_matrix[frame], cmap=new_cmap2, vmin=0, vmax=self.vmax
    #         )
    #     else:
    #         self.ani_ax.imshow(self.compound_matrix[frame], cmap="gray")
    #     self.current_frame = frame

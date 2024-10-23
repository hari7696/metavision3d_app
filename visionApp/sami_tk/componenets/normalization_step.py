import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import os
import pandas as pd
import logging
from .compound_matrix import create_compound_matrix
from multiprocessing import Process, Queue
import math
from pylab import Figure
import numpy as np
from waiting import wait
from PIL import Image, ImageTk
import queue
from sami_tk.colormap import *
import io
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import sys
sys.path.append('../SAMI')
from SAMI.norm import create_norm_dataset_gui
from .timer import TimerApp
from log_listener import worker_configurer
logger = logging.getLogger(__name__)

class NormalizationStep(ctk.CTkFrame):
    """This class deals with the Normalization step"""

    def __init__(self, master, file_handler,log_queue = None):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
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


        norm_dir = os.path.join(*[self.file_handler.working_folder, 'normalised_data'])
        if not os.path.exists(norm_dir):
            os.mkdir(norm_dir)

        # making a tracker file to keep track of the normalization
        self.tracker_file = os.path.join(*[self.file_handler.working_folder, 'normalised_data', 'Normalisation_tracker.csv'])

        if os.path.exists(self.tracker_file):
            self.tracker_df = pd.read_csv(self.tracker_file)
        else:
            self.tracker_df = pd.DataFrame(columns=['time_stamp','file', 'rowNorm', 'transNorm', 'compnorm', ])

        # self.check_for_normalization_thread_signal()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

    def refresh(self):
        """
        Between the tabs switches, some components needs to be refreshed, this function is used to refresh the components
        before gridding the selected step into the main window, the refresh function is called from the SAMIApp class
        """
        pass

    def create_visualization_dock_type1(self):
        """
        Under the normilization tab, we have two frames, left and right frame
        Left frame is for displaying the files, color maps and right frame is for displaying the results
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
        self.normalization = self.vis_tabs.add("Normalization")
        self.norm_plot = self.vis_tabs.add("Norm Plot") 
        self.norm_slides = self.vis_tabs.add("Normalised Slides")
        self.comparison = self.vis_tabs.add("Comparison")


        self.norm_slides.columnconfigure(0, weight=1)
        self.norm_slides.rowconfigure(0, weight=1)

        # self.comparison.columnconfigure(0, weight=1)
        # self.comparison.rowconfigure(0, weight=1)

        self.norm_plot.columnconfigure(0, weight=1)
        self.norm_plot.rowconfigure(0, weight=1)

        # self.normalization.columnconfigure(0, weight=1)
        # self.normalization.rowconfigure(0, weight=1)

    def prepare_visualization_dock_type1(self):
        """This visualization is used for the tabs 1. Visualization and 2. Normalization
        This view have left and right visualization frames"""

        self.create_visualization_dock_type1()
        self.create_left_visualization_dock_type1()
        self.create_right_visualization_dock_type1()

        logger.info("Visualization dock type 1 is prepared")


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
        self.norm_frame.grid(row=0, column=0, sticky="w")
        self.norm_frame.columnconfigure(0, weight=1)
        self.norm_frame.columnconfigure(1, weight=1)
        self.norm_frame.columnconfigure(2, weight=10)
        # self.norm_frame.columnconfigure((0,1,2), weight=1)
        # self.norm_frame.rowconfigure(0, weight=1)
        # self.norm_frame.columnconfigure(0, weight=1)
        # self.norm_frame.rowconfigure(0, weight=1)
        # label_unused = ctk.CTkLabel(self.norm_frame, text="", font = ("Arial", 24), width= 500, height= 500)
        # label_unused.grid(row=0,column=2,padx=(5,0),pady=8,sticky="w")
        # two drop downs, and a run button
        #creating a dropwodn from rownorm
        label1 = ctk.CTkLabel(self.norm_frame, text="RowNorm :" )
        label1.grid(row=0,column=0,padx=(5,0),pady=8,sticky="w")

        norm_default_value = ctk.StringVar(value="SumNorm")
        self.algo_selection_dropdown = ctk.CTkComboBox(master= self.norm_frame,
                                            values=['SumNorm', 'CompNorm', "None"],
                                            variable=norm_default_value,button_color="#b5b8b0",
                                            command= self.update_normalize_with_dropdown
                                            )
        self.algo_selection_dropdown.grid(row=0,column=1,padx=(0,0),pady=8,sticky="w")
        self.algo_selection_dropdown.set("SumNorm")
        # dummy_label1 = ctk.CTkLabel(self.norm_frame, text="", font = ("Arial", 14), width= 1000)
        # dummy_label1.grid(row=0,column=2,padx=(5,0),pady=8,sticky="w")
        

        # creating a dropdown for transnorm
        label2 = ctk.CTkLabel(self.norm_frame, text="transNorm :")
        label2.grid(row=1,column=0,padx=(5,0),pady=8,sticky="w")

        norm_default_value2 = ctk.StringVar(value="LogTrans2")
        self.algo_selection_dropdown2 = ctk.CTkComboBox(master= self.norm_frame,
                                            values=['LogTrans2', "None"],  
                                            variable=norm_default_value2, button_color="#b5b8b0"
                                            )
        self.algo_selection_dropdown2.set("LogTrans2")
        self.algo_selection_dropdown2.grid(row=1,column=1,padx=(0,0),pady=8,sticky="w")

        # dummy_label2 = ctk.CTkLabel(self.norm_frame, text="", font = ("Arial", 14), width= 1000)
        # dummy_label2.grid(row=1,column=2,padx=(5,0),pady=8,sticky="w")

        label3 = ctk.CTkLabel(self.norm_frame, text="Normalize with :")
        label3.grid(row=2,column=0,padx=(5,0),pady=8,sticky="w")
        norm_default_value3 = ctk.StringVar(value="None")
        self.algo_selection_dropdown3 = ctk.CTkComboBox(master= self.norm_frame,
                                            values=['None'],  
                                            variable=norm_default_value3, button_color="#b5b8b0"
                                            )
        self.algo_selection_dropdown3.set("None")
        self.algo_selection_dropdown3.grid(row=2,column=1,padx=(0,0),pady=8,sticky="w")

        # creating a run button
        self.run_button = ctk.CTkButton(master=self.norm_frame, text="Run Normalization", command=self.onlick_run_normalization, width=70)
        self.run_button.grid(row=3,column=0,padx=(60,0),pady=8,sticky="w")

        # creating a label to show the timer
        self.timer = TimerApp(self.norm_frame)
        self.timer.grid(row=4,column=0,padx=(60,0),pady=8,sticky="w")

        # creating a label to show the normalization is in processing
        self.norm_done_label = ctk.CTkLabel(self.norm_frame, text="", font = ("Arial", 14) , width= 300)
        self.norm_done_label.grid(row=5,column=0,padx=(0,0),pady=8,sticky="w")


        note = ctk.CTkTextbox(self.norm_frame, font = ("Arial", 14) , width= 700, height= 100)
        note.grid(row=6,column=0,padx=(0,0),pady=8,sticky="sw", rowspan= 2, columnspan= 2)

        note.insert("0.0", "Notes:\n1. Make sure to run the normalization on all of your files \n2. Make sure, to run the omics pooling once you are done with Normalization\nOtherwise, the Next steps, will not use the latest normalized data")
        note.configure(state="disabled") 

        logger.info("Normalization tab is created") 

    def update_normalize_with_dropdown(self, choice):
        values= self.file_handler.molecule_name[self.file_dropdown.get()]
        if self.algo_selection_dropdown.get() == 'CompNorm':
            self.algo_selection_dropdown3.configure(values=values)
            self.algo_selection_dropdown3.set(values[0])
        
        if self.algo_selection_dropdown.get() == 'SumNorm':
            self.algo_selection_dropdown3.set("None")
            self.algo_selection_dropdown3.configure(values=['None'])

        

    def run_normalization(self):

        # waiting till the input files are read
        wait(
            lambda: self.file_handler.is_files_read,
            timeout_seconds=600,
            waiting_for="File reading",
        )
        try:
            ref_compound = None
            if self.algo_selection_dropdown.get() == "CompNorm":
                if self.algo_selection_dropdown3.get() == "None":
                    CTkMessagebox(title="Info", message="Please select a compound to normalize with")
                    return
                ref_compound = self.algo_selection_dropdown3.get()

            # waiting till the input files 
            record = [pd.Timestamp.now(), self.file_dropdown.get(), 
                    self.algo_selection_dropdown.get(), 
                    self.algo_selection_dropdown2.get(), 
                    self.algo_selection_dropdown3.get()]
            self.tracker_df.loc[len(self.tracker_df)] = record
            self.tracker_df.to_csv(self.tracker_file, index=False)

            # running normalization
            self.normalized_data[self.file_dropdown.get()] = create_norm_dataset_gui(self.file_handler.input_data_raw[self.file_dropdown.get()],
                                                                self.file_handler.working_folder,
                                                                self.file_dropdown.get(),
                                                                    rowNorm = self.algo_selection_dropdown.get(),
                                                                    transNorm = self.algo_selection_dropdown2.get(),
                                                                    first_compound= self.file_handler.molecule_name[self.file_dropdown.get()][0],
                                                                    ref_compound = ref_compound
                                                                )
            del self.compound_matrix_high_res
            self.compound_matrix, self.compound_matrix_high_res, self.dict_id_to_tissue_name = create_compound_matrix(
                self.file_handler.input_data_raw[self.file_dropdown.get()],
                self.normalized_data[self.file_dropdown.get()].columns[3],
                roi=False,
                reverse=True,
            )

            # updating the molecule dropdown with the normalized data columns. if the compnorm is selected, in that case, the dropdown will be updated with the molecules,
            #because in the compnorm, we drop the reference compound
            self.molecule_dropdown.configure(values= self.normalized_data[self.file_dropdown.get()].columns[3:])
            self.molecule_dropdown.set(self.normalized_data[self.file_dropdown.get()].columns[3])

            if hasattr(self, 'normalised_compound_matrix_high_res' ):
                del self.normalised_compound_matrix_high_res
            
            # logger.info(f"Normalization matrix shape : {self.normalised_compound_matrix_high_res.shape}")
            self.norm_compound_matrix, self.normalised_compound_matrix_high_res, _ = create_compound_matrix( 
                                                                self.normalized_data[self.file_dropdown.get()],
                                                                self.normalized_data[self.file_dropdown.get()].columns[3],
                                                                roi=False,
                                                                reverse=True,
                                                                )
        
            self.queue.put("Normalization_done")
        except Exception as e:
            logger.error("Error in the normalization : {}".format(e))
            self.queue.put("Normalization_done")
        finally:
            self.queue.put("Normalization_done")


        
        # writing a ctk label to show the normalization is done

    def onlick_run_normalization(self):

        if self.file_dropdown.get() == "Select Dataset":
            CTkMessagebox(title="Info", message="Please select a dataset on the left panel")
        else:
            self.run_button.configure(state="disabled")
            self.norm_done_label.configure(text="Normalization is running", text_color="yellow")
            self.timer.reset_timer()
            self.timer.start_timer()
            #creating a thread to run the normalization 
            logger.info("Normalization is triggered")
            threading.Thread(target=self.run_normalization, args=(), daemon=True).start()
            self.check_for_normalization_thread_signal()
    
    def check_for_normalization_thread_signal(self):
        """
        This function checks for the signal from the normalization thread,
        On trigger, it updates the norm_plot tab 
        Also, spins a separate process to save the normalized data in csv

        """

        if not self.queue.empty():
            try:
                message = self.queue.get()
                if message == 'Normalization_done':
                    logger.info("Normaliztion done, message received")
                    
                    self.display_norm_plot(self.compound_matrix_high_res, self.normalised_compound_matrix_high_res )
                    # Spinning a process to convert the normalized to csv
                    file_name = self.file_dropdown.get() + '_normalized.csv'
                    file_name = os.path.join(*[self.file_handler.working_folder, 'normalised_data', file_name])
                    logger.info(f"file name : {file_name}")
                    logger.info("separate python process is spinned to write the normalized data in csv")
                    # csv_saving_process = Process(target=self.save_normalized_files_in_csv,
                    #                             args=(file_name,self.normalized_data[self.file_dropdown.get()], self.log_queue ), daemon=True)
                    # csv_saving_process.start()
                    self.norm_done_label.configure(text="Normalization is completed", font = ("Arial", 14), text_color = "green")

                    self.timer.stop_timer() 
                    self.run_button.configure(state="normal")
                    self.norm_done_label.update()
                    self.after(300, self.update())
                    self.after(300, self.norm_done_label.update())
            except:
                pass
                logger.error("Error in the normalization thread signal")
            finally:
                self.after(1000, self.check_for_normalization_thread_signal)
                self.run_button.configure(state="normal")
                self.timer.stop_timer() 
                # self.timer.reset_timer()
        else:
            # Schedule the next queue check
            self.after(1000, self.check_for_normalization_thread_signal)

    @staticmethod
    def save_normalized_files_in_csv(file_name, df, log_queue):
        # worker_configurer(log_queue)
        df.to_csv(file_name, index=False)
        logger.info(f"file saved in csv : {file_name}")
        return

    def update_frame_with_file(self, choice):

        """
        This function is called when the user selects a file from the dropdown
        It updates the molecule dropdown with the molecules in the selected file
        """
        self.norm_done_label.configure(text="")
        logger.info("update_frame_with_file function triggered")

        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()
        self.algo_selection_dropdown3.set("None")
        self.algo_selection_dropdown3.configure(values=['None'])
    

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

        logger.info("update_frame_with_selected_color_map function triggered")

        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()
        self.create_frames_in_slides_display_frame(self.compound_matrix_high_res)
        self.loading_label.configure(text="")
        

    def update_frame_with_molecule(self, choice):

        logger.info("update_frame_with_molecule Triggered")
        
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
        # self.vmax = np.percentile(data[data != 0], 99)
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
            # im = ax.imshow(image_array, cmap=new_cmap1, vmin=0, vmax=self.vmax)
            im = ax.imshow(image_array, cmap=new_cmap1)
        elif self.color_map_dropdown.get() == "viridis":
            # im = ax.imshow(image_array, cmap=new_cmap2, vmin=0, vmax=self.vmax)
            im = ax.imshow(image_array, cmap=new_cmap2)
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

        """
        This function is triggered when the user clicks on the image grid
        """

        logger.info("on_label_click Triggered")

        matrix = self.normalised_compound_matrix_high_res[id]
        # print(matrix.shape)
        scale_factor = 0.42  # Adjust this factor to scale the image size up
        dpi = 300  # Increasing the DPI for better resolution and larger image

        # Calculate the figure size based on the image dimensions and scaling factor
        height, width = matrix.shape
        figsize = (width / float(dpi) * scale_factor, height / float(dpi) * scale_factor)

        # Create the figure with the adjusted size and dpi
        fig = Figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(111)
        # ax = fig.add_subplot(111)
        # ax.set_facecolor('white')

        # Clear existing widgets in the container

        for widget in self.norm_slides.winfo_children():
            widget.destroy()

        logger.info("num childer in tissues tab : %s", len(self.norm_slides.winfo_children()))

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
                # im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
                im, ax=ax
            )
            # cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            # cbar.ax.set_yticklabels(["low", "high"])

        # Turn off axis labeling to maximize space for the image
        ax.axis("off")
        fig.tight_layout(pad=0)  # This reduces the padding around the image

        # Draw the canvas
        canvas.draw()

        image_label = ctk.CTkLabel(self.norm_slides, text= "Tissue : " +str(self.dict_id_to_tissue_name[id]), font=("Arial", 16))
        image_label.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
    

    def on_label_click_pre_post_norm_comparison(self,  event, id):
        # print("comparison", id)

        logger.debug("onlabel click triggered")
        logger.debug("id : {}".format(id))

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
        scale_factor = 0.18  # Adjust this factor to scale the image size up
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
                # im, ax=ax, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
                im, ax=ax
            )
            # cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            # cbar.ax.set_yticklabels(["low", "high"])

        # Turn off axis labeling to maximize space for the image
        ax.axis("off")
        fig.tight_layout(pad=0)  # This reduces the padding around the image
        canvas.draw()


        # POST Normalization frame
        matrix = self.normalised_compound_matrix_high_res[id]
        # print(matrix.shape)
        scale_factor = 0.18  # Adjust this factor to scale the image size up
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
                # im, ax=ax2, ticks=[0, np.percentile(matrix[matrix != 0], 99)], shrink=0.5
                im, ax=ax2
            )
            # cbar.mappable.set_clim(vmin=0, vmax=np.percentile(matrix[matrix != 0], 99))
            # cbar.ax.set_yticklabels(["low", "high"])

        # Turn off axis labeling to maximize space for the image
        ax2.axis("off")
        fig2.tight_layout(pad=0)  # This reduces the padding around the image
        canvas2.draw()
    #     return fig
    
    def generate_boxplot_directly(self, matrix, ax, title):
        import numpy as np
        matrix_reshape = matrix.reshape(matrix.shape[0], -1)

        ARE_THERE_INFIS = False
        non_zero_list = []
        for row in matrix_reshape:
            non_zero_row = row[np.logical_and(row != 0, np.isfinite(row))] # remove zeros and inf
            if len(row[np.isinf(row)]) > 0:
                ARE_THERE_INFIS = True
            non_zero_list.append(non_zero_row)

        ax.boxplot(non_zero_list, vert=False, showfliers=False)
        ax.invert_yaxis()
        ax.set_title(title, fontweight='bold', fontsize=12)
        ax.set_xlabel('Intensity', fontweight='bold', fontsize=12)
        ax.set_ylabel('Slice', fontweight='bold', fontsize=12)
        ax.tick_params(axis='both', which='both', labelsize=10)
        labels = ax.get_xticklabels() + ax.get_yticklabels()
        labels = [label.set_fontweight('bold') for label in labels]
        return ARE_THERE_INFIS
                
    def display_norm_plot(self, matrix, norm_matrix):
        
        logger.info("display_norm_plot function triggered")
        for widget in self.norm_plot.winfo_children():
            widget.destroy()

        self.norm_plot_frame = ctk.CTkScrollableFrame(self.norm_plot, height = 900)
        self.norm_plot_frame.columnconfigure(0,weight=1)
        self.norm_plot_frame.rowconfigure(0,weight=1)
        self.norm_plot_frame.grid(row=0,column=0,sticky="nsew")
        # data_fig = self.generate_boxplot(matrix)
        # normalised_data_fig = self.generate_boxplot(norm_matrix)


        combined_fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(int(matrix.shape[0] / 2), 8)))

        # Generate plots directly on the axes
        _ = self.generate_boxplot_directly(matrix, ax1, "Original Data")
        are_there_infis = self.generate_boxplot_directly(norm_matrix, ax2, "Normalized Data")
        if are_there_infis:
            CTkMessagebox(title="Warning Message!",message="Comp Norm resulted in infinites, It can potentially break next steps",
                  icon="warning", option_1="Ok")
        canvas = FigureCanvasTkAgg(combined_fig, master=self.norm_plot_frame)  # A tk.DrawingArea
        canvas.draw()
        canvas.get_tk_widget().grid(row=0,column=0)


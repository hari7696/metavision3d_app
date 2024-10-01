import tkinter as tk
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import pandas as pd
import os
import logging
from multiprocessing import Process, Queue
import numpy as np
from .timer import TimerApp
from SAMI.pathway import Pathway
from PIL import Image
import sys
from log_listener import worker_configurer
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
class PathwaysStep(ctk.CTkFrame):

    def __init__(self, master, file_handler, log_queue):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.makers_folder = os.path.join(*[file_handler.working_folder, 'results', 'markers'])
        self.pathways_folder = os.path.join(*[file_handler.working_folder, 'results', 'pathways'])
        self.queue = Queue()
        self.plot_dot_image_label = None
        self.network_image_label = None
        self.pathway_direction_image_label = None
        # self.sami_type = file_handler.file_type
        if not os.path.exists(self.pathways_folder):
            os.makedirs(self.pathways_folder)
            print("DIRECTORY CREATED")

        self.prepare_visualization_dock_type2()
        self.trigger_visz_functions_on_thread_run()
        # self.prep_cluster_int_options_tab()

    def prepare_visualization_dock_type2(self):
        """This visualization is used for the tabs 1. Pooling, 2. Clustering, 3. Clusters Integration, 4. Markers, 5. Pathways
        A separate tabview is created for this type of visualization, as it doesnt need left and right frames
        """

        for child in self.winfo_children():
            child.destroy()

        self.root_visualization_frame = ctk.CTkFrame(
            self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
        self.root_visualization_frame.rowconfigure(0, weight=1)
        # self.root_visualization_frame.rowconfigure(2, weight=5)
        # self.root_visualization_frame.rowconfigure(0, weight=5)
        self.root_visualization_frame.grid(row=0, column=0, sticky="nsew")

        self.vis_tabs = ctk.CTkTabview(self.root_visualization_frame)
        self.vis_tabs.columnconfigure(0, weight=1)
        self.vis_tabs.rowconfigure(0, weight=1)
        self.vis_tabs.grid(row=0, column=0, sticky="new", padx=5)

        self.markers_root_tab = self.vis_tabs.add("Pathways")
        self.markers_root_tab.columnconfigure(0, weight=1)
        self.markers_root_tab.rowconfigure(0, weight = 1)
        self.markers_root_tab.rowconfigure(1, weight = 20)
        self.markers_root_tab.rowconfigure(1, weight = 5)

        # adding new tablayout for pathway directions
        self.pathway_directions_tab = self.vis_tabs.add("Pathway Directions")
        self.pathway_directions_tab.columnconfigure(0, weight=1)
        self.pathway_directions_tab.rowconfigure(0, weight = 1)

        # adding a frame in the pathway directions tab
        self.pathway_directions_frame = ctk.CTkFrame(self.pathway_directions_tab, bg_color="transparent")
        self.pathway_directions_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        #options panel
        self.options_panel = ctk.CTkFrame(self.markers_root_tab, bg_color="transparent")
        self.options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        self.prepare_options_panel()

        # viz_frame
        self.viz_frame = ctk.CTkFrame(self.markers_root_tab, bg_color="transparent")
        self.viz_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.viz_frame.columnconfigure(0, weight=2)
        self.viz_frame.columnconfigure(1, weight=1)

        # scrollable frame for R output
        self.scrollable_frame = ctk.CTkFrame(self.markers_root_tab,bg_color="transparent", height=150)
        self.scrollable_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(0, weight=1)

        # breaking down the viz_frame into 2 frames
        self.plot_dot_frame = ctk.CTkFrame(self.viz_frame, bg_color="transparent")
        self.plot_dot_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)

        self.network_frame = ctk.CTkFrame(self.viz_frame, bg_color="transparent")
        self.network_frame.grid(row=0, column=1, sticky="new", padx=5, pady=5)
        logger.info("Pathways visualization dock prepared")

        self.prepare_options_panel()

    def refresh(self):
    
        files = os.listdir(self.makers_folder)
        files = [file for file in files if ('_marker.csv') in file]
        self.file_selection.configure(values=files)
        logger.info("refreshed the markers dropdowns")

    def prepare_options_panel(self):

        self.options_panel.columnconfigure(0, weight=1)
        self.options_panel.columnconfigure(1, weight=1)
        self.options_panel.columnconfigure(2, weight=1)
        self.options_panel.columnconfigure(3, weight=1)
        self.options_panel.columnconfigure(4, weight=1)
        self.options_panel.columnconfigure(5, weight=1)
        self.options_panel.columnconfigure(6, weight=7)
        # self.options_panel.rowconfigure(0, weight=1)
        self.options_panel.columnconfigure(7, weight=1)
        self.options_panel.columnconfigure(8, weight=1)
        self.options_panel.columnconfigure(9, weight=1)
        # self.options_panel.columnconfigure(10, weight=1)
        # self.options_panel.columnconfigure(11, weight=1)
        # self.options_panel.columnconfigure(12, weight=1)
        # self.options_panel.columnconfigure(13, weight=1)
        # self.options_panel.columnconfigure(14, weight=1)
        # self.options_panel.columnconfigure(15, weight=1)
        # self.options_panel.columnconfigure(16, weight=1)

        files = os.listdir(self.makers_folder)
        files = [file for file in files if ('_marker.csv') in file]
        logger.info(f"files: {files}")
        logger.info(f"markers folder: {self.makers_folder}")

        # file selection 1
        file_label = ctk.CTkLabel(self.options_panel, text="Select file:" )
        file_label.grid(row=0,column=0,padx=(2,0),pady=2,sticky="ew")    
        _ = tk.StringVar(value='choose file')
        self.file_selection = ctk.CTkComboBox(master= self.options_panel,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 150
                                            )
        self.file_selection.grid(row=0,column=1,padx=(2,0),pady=2,sticky="ew")


        # Omics selection
        region2_label = ctk.CTkLabel(self.options_panel, text="Select Omics :" )
        region2_label.grid(row=0,column=2,padx=(2,0),pady=2,sticky="ew")
        _ = tk.StringVar(value='choose omic')
        self.omics_selection = ctk.CTkComboBox(master= self.options_panel,
                                            values= ['metabolomics', 'glycomics', 'lipidomics'],
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 150
                                            )
        self.omics_selection.grid(row=0,column=3,padx=(2,5),pady=2,sticky="ew")

        self.omics_selection.set('metabolomics')

        # adding a Run button to run the markers generation
        self.run_button = ctk.CTkButton(self.options_panel, text="Generate Pathways", command=self.generate_pathways, width=80)
        self.run_button.grid(row=0,column=4,padx=(15,5),pady=2,sticky="ew")
        
        # timer button
        self.timer = TimerApp(self.options_panel)
        self.timer.grid(row=0,column=5,padx=(5,5),pady=2,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.options_panel, text="", text_color="yellow", width = 300)
        self.time_constraint_label.grid(row=0,column=6,padx=(5,5),pady=2,sticky="w")

        logger.info("options panel prepared")

    def generate_pathways(self):
        # self.run_button.configure(state="disabled")
        logger.info("Generating Pathways button hit")
        # this function run the command of generating markers button
        self.selected_file = self.file_selection.get()
        logger.info(f"selected file: {self.selected_file}")
        print("selected file: ", self.selected_file)
        self.omics = self.omics_selection.get()

        self.timer.start_timer()
        self.time_constraint_label.configure(text="Note : Pathways generation takes roughly 3 minutes", text_color="yellow")
        # creating a process to run the markers generation
        logger.info("creating a process to run the markers generation")
        region = self.selected_file.replace('_marker.csv', '')
        self.region_specific_pathways_folder = os.path.join(self.pathways_folder, region)
        print("region: ", region)
        # checking the number of clusters in the selected file, need this number for the visualization prep
        temp_df = os.path.join(self.makers_folder, self.selected_file)
        self.num_clusters = list(np.sort(pd.read_csv(temp_df)['cluster'].unique()))
        self.num_clusters = [str(value) for value in self.num_clusters]

        # for class referece
        self.pathway = Pathway(region, self.omics, self.region_specific_pathways_folder, self.makers_folder)

        # creating the pathway object inside the proces as well to avoid the pickling error/bottlenecks
        logger.info("creating a separate process to run the pathways generation")
        maker_process = Process(target=self.pathways_actual_run, args=(region, self.omics, self.region_specific_pathways_folder, self.makers_folder,self.queue, self.log_queue),  name = "SAMI:Pathways_step")
        maker_process.start()
        
        #self.pathways_actual_run(region, self.omics, region_specific_pathways_folder, self.makers_folder,self.queue)
    @staticmethod
    def pathways_actual_run(selected_file,omics, pathways_folder, makers_folder, queue, log_queue):
        # worker_configurer(log_queue)
        try:
            pathway = Pathway(selected_file, omics, pathways_folder, makers_folder, log_queue)
            pathway.findpathway()
        except Exception as e:
            logger.error("Error in pathway generation:{}".format(e))
        finally:
            queue.put("pathways_done")
            logger.info("pathways done")


    
    def trigger_visz_functions_on_thread_run(self):
        
        logger.info("checking the queue")
       
        try:
            if self.queue.qsize() > 0:
                signal = self.queue.get()
                if signal == "pathways_done":
                    logger.info("pathways compelete message received")
                    # self.prepare_cluster_visualization()
                    # self.dsplay_umpa_overlay()
                    self.timer.stop_timer()
                    self.timer.reset_timer()
                    self.time_constraint_label.configure(text="Note : Pathway generation completed", text_color="green")
                    self.after(500, self.display_r_output())
                    self.update()
                    self.prepare_plot_dot()
                    self.prepare_network_plot()
                    self.prepare_bar_plot()
                    self.after(500, self.display_plot_dot())
                    self.after(500, self.display_network_plot())
                    self.after(500, self.display_pathways_direction_plot())
                    self.after(1000, CTkMessagebox(title="Info", message="Pathways are generated, Please check the R output tab at the bottom for more details"))
                    logger.info("pathways visualizations done")
        except Exception as e:
            logger.error(f"Error: {e}")
        # Schedule the next queue check
        finally:
            self.after(10000, self.trigger_visz_functions_on_thread_run)

    def prepare_plot_dot(self):

        logger.info("preparing plot dot")

        for child in self.plot_dot_frame.winfo_children():
            child.destroy() 

        self.plot_dot_frame.columnconfigure(0, weight=1)
        self.plot_dot_frame.rowconfigure(0, weight=1)
        self.plot_dot_frame.rowconfigure(1, weight=9)

        # plot dot options panel
        self.plot_dot_options_panel = ctk.CTkFrame(self.plot_dot_frame, bg_color="transparent")
        self.plot_dot_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.circular_options_panel.columnconfigure(0, weight=1)
        # self.circular_options_panel.columnconfigure(1, weight=1)
        # self.circular_options_panel.columnconfigure(2, weight=1)
        # self.circular_options_panel.rowconfigure(0, weight=1)

        # plot_frame
        self.pot_image_frame = ctk.CTkFrame(self.plot_dot_frame, bg_color="transparent")
        self.pot_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.pot_image_frame.columnconfigure(0, weight=1)
        self.pot_image_frame.rowconfigure(0, weight=1)

        # creating a label to select cluster
        choose_cluster_label = ctk.CTkLabel(self.plot_dot_options_panel, text="choose cluster")
        choose_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        # self.cluster_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        # self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.cluster_entry.insert(0, "1")
 
        # values = [str(value) for value in values]
        _ = ctk.StringVar(value='choose cluster')
        self.cluster_entry = ctk.CTkComboBox(master= self.plot_dot_options_panel,
                                            values=self.num_clusters,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 140
                                            )
        self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.cluster_entry.set(self.num_clusters[0])

        # creating a label to select top N clusters
        choose_top_n = ctk.CTkLabel(self.plot_dot_options_panel, text="select top N")
        choose_top_n.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.top_n_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        self.top_n_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.top_n_entry.insert(0, "20")

        # entry box to take size
        self.size_label = ctk.CTkLabel(self.plot_dot_options_panel, text="Dot size ")
        self.size_label.grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.size_entry_dot = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        self.size_entry_dot.grid(row=0, column=5, sticky="w", padx=5, pady=5)
        self.size_entry_dot.insert(0, "30")

        # button to run the function
        self.run_button = ctk.CTkButton(self.plot_dot_options_panel, text="Run", command=self.display_plot_dot)
        self.run_button.grid(row=0, column=6, sticky="w", padx=(20,0), pady=5)

        self.status_label_plot_dot = ctk.CTkLabel(self.plot_dot_options_panel, text="", text_color="yellow", width = 150)
        self.status_label_plot_dot.grid(row=0,column=7,padx=(5,5),pady=2,sticky="w")

        
    def display_plot_dot(self):

        logger.info("displaying plot dot image")
        
        if self.plot_dot_image_label is not None:
            self.plot_dot_image_label.destroy()

        self.status_label_plot_dot.configure(text="Loading...", text_color="yellow")
        self.update()

        logger.info("displaying plot plot")
        # get the value from top N entry
        cluster = int(self.cluster_entry.get())
        top_n = int(self.top_n_entry.get())
        scale = int(self.size_entry_dot.get())
        try:
            image_location = self.pathway.plot_dot(cluster,scale=scale,height=10,top=top_n,show=False)
            
            logger.info(f"plot dot image location: {image_location}")   
        except Exception as e:
            logger.error(f"Error in plot_dot: {e}")
            CTkMessagebox(title="Error", message="Something went wrong in pathway calculation, Please check the R output tab at the bottom for more details", icon="cancel")
            self.status_label_plot_dot.configure(text="", text_color="yellow")
            self.update()
    

        # creating a label to display the image
        self.plot_dot_image_label = ctk.CTkLabel(self.pot_image_frame , text = "", width=1200, height=600)
        self.plot_dot_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image1 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (1200,600))
        self.plot_dot_image_label.configure(image=ctk_image1)
        self.plot_dot_image_label.image = ctk_image1

        self.status_label_plot_dot.configure(text="", text_color="yellow")
        self.update()
    
    def prepare_network_plot(self):

        logger.info("preparing network plot")

        for child in self.network_frame.winfo_children():
            child.destroy() 

        self.network_frame.columnconfigure(0, weight=1)
        self.network_frame.rowconfigure(0, weight=1)
        self.network_frame.rowconfigure(1, weight=9)

        # plot dot options panel
        self.network_options_panel = ctk.CTkFrame(self.network_frame, bg_color="transparent")
        self.network_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.circular_options_panel.columnconfigure(0, weight=1)
        # self.circular_options_panel.columnconfigure(1, weight=1)
        # self.circular_options_panel.columnconfigure(2, weight=1)
        # self.circular_options_panel.rowconfigure(0, weight=1)

        # plot_frame
        self.network_image_frame = ctk.CTkFrame(self.network_frame, bg_color="transparent")
        self.network_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.network_image_frame.columnconfigure(0, weight=1)
        self.network_image_frame.rowconfigure(0, weight=1)

        # creating a label to select cluster
        choose_cluster_label = ctk.CTkLabel(self.network_options_panel, text="choose cluster")
        choose_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        # self.cluster_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        # self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.cluster_entry.insert(0, "1")
        # values = np.arange(0, self.num_clusters+1)
        # values = [str(value) for value in values]
        _ = ctk.StringVar(value='choose cluster')
        self.network_cluster_entry = ctk.CTkComboBox(master= self.network_options_panel,
                                            values=self.num_clusters,
                                            variable=_,
                                            button_color="#b5b8b0", width= 140
                                            )
        self.network_cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.network_cluster_entry.set(self.num_clusters[0])

        # creating a label to select top N clusters
        choose_top_n = ctk.CTkLabel(self.network_options_panel, text="select top N")
        choose_top_n.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.network_top_n_entry = ctk.CTkEntry(self.network_options_panel, width=50, placeholder_text= "5",)
        self.network_top_n_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.network_top_n_entry.insert(0, "10")

        # entry box to take size
        self.size_label = ctk.CTkLabel(self.network_options_panel, text="Dot size ")
        self.size_label.grid(row=0, column=4, sticky="w", padx=5, pady=5)

        self.size_entry = ctk.CTkEntry(self.network_options_panel, width=50, placeholder_text= "5",)
        self.size_entry.grid(row=0, column=5, sticky="w", padx=5, pady=5)
        self.size_entry.insert(0, "8")


        # button to run the function
        self.run_button_network = ctk.CTkButton(self.network_options_panel, text="Run", command=self.display_network_plot)
        self.run_button_network.grid(row=0, column=6, sticky="w", padx=(20,0), pady=5)

        # adding a status label
        self.status_label_network_plot = ctk.CTkLabel(self.network_options_panel, text="", text_color="yellow", width = 150)
        self.status_label_network_plot.grid(row=0,column=7,padx=(5,5),pady=2,sticky="w")

        
    def display_network_plot(self):

        logger.info("displaying network plot image")

        self.status_label_network_plot.configure(text="Loading...", text_color="yellow")
        self.update()
        if self.network_image_label is not None:
            self.network_image_label.destroy()

        # get the value from top N entry
        cluster = int(self.network_cluster_entry.get())
        top_n = int(self.network_top_n_entry.get())
        size = int(self.size_entry.get())*100

        try:
            image_location = self.pathway.pathway_network(cluster=cluster,top=top_n,size = size, show=False)
        except Exception as e:
            logger.error(f"Error in plot_dot: {e}")
            CTkMessagebox(title="Error", message="Something went wrong in pathway calculation", icon="cancel")

        logger.info(f"network plot image location: {image_location}")
        # creating a label to display the image
        self.network_image_label = ctk.CTkLabel(self.network_image_frame , text = "", width=600, height=600)
        self.network_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image2 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (800,600))
        self.network_image_label.configure(image=ctk_image2)
        self.network_image_label.image = ctk_image2
        self.status_label_network_plot.configure(text="", text_color="yellow")
        self.update()

    def prepare_bar_plot(self):

        logger.info("preparing bar plot")

        for child in self.pathway_directions_frame.winfo_children():
            child.destroy() 

        self.pathway_directions_frame.columnconfigure(0, weight=1)
        self.pathway_directions_frame.rowconfigure(0, weight=1)
        self.pathway_directions_frame.rowconfigure(1, weight=9)

        # plot dot options panel
        self.path_dir_options_panel = ctk.CTkFrame(self.pathway_directions_frame, bg_color="transparent")
        self.path_dir_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.circular_options_panel.columnconfigure(0, weight=1)
        # self.circular_options_panel.columnconfigure(1, weight=1)
        # self.circular_options_panel.columnconfigure(2, weight=1)
        # self.circular_options_panel.rowconfigure(0, weight=1)

        # plot_frame
        self.path_dir_image_frame = ctk.CTkFrame(self.pathway_directions_frame, bg_color="transparent")
        self.path_dir_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.path_dir_image_frame.columnconfigure(0, weight=1)
        self.path_dir_image_frame.rowconfigure(0, weight=1)

        # creating a label to select cluster
        choose_cluster_label = ctk.CTkLabel(self.path_dir_options_panel, text="choose cluster")
        choose_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        # self.cluster_entry = ctk.CTkEntry(self.plot_dot_options_panel, width=50, placeholder_text= "5",)
        # self.cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.cluster_entry.insert(0, "1")
        # values = np.arange(0, self.num_clusters+1)
        # values = [str(value) for value in values]
        _ = ctk.StringVar(value='choose cluster')
        self.path_dir_cluster_entry = ctk.CTkComboBox(master= self.path_dir_options_panel,
                                            values=self.num_clusters,
                                            variable=_,
                                            button_color="#b5b8b0", width= 140
                                            )
        self.path_dir_cluster_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.path_dir_cluster_entry.set(self.num_clusters[0])

        # creating a label to select top N clusters
        choose_top_n = ctk.CTkLabel(self.path_dir_options_panel, text="select top N")
        choose_top_n.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.path_dir_n_entry = ctk.CTkEntry(self.path_dir_options_panel, width=50, placeholder_text= "5",)
        self.path_dir_n_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.path_dir_n_entry.insert(0, "5")

        # entry box to take size
        # self.size_label = ctk.CTkLabel(self.network_options_panel, text="Dot size ")
        # self.size_label.grid(row=0, column=4, sticky="w", padx=5, pady=5)

        # self.size_entry = ctk.CTkEntry(self.network_options_panel, width=50, placeholder_text= "5",)
        # self.size_entry.grid(row=0, column=5, sticky="w", padx=5, pady=5)
        # self.size_entry.insert(0, "8")


        # button to run the function
        self.run_button_path_dir= ctk.CTkButton(self.path_dir_options_panel, text="Run", command=self.display_pathways_direction_plot)
        self.run_button_path_dir.grid(row=0, column=6, sticky="w", padx=(20,0), pady=5)

        # adding a status label
        self.status_label_path_dir = ctk.CTkLabel(self.path_dir_options_panel, text="", text_color="yellow", width = 150)
        self.status_label_path_dir.grid(row=0,column=7,padx=(5,5),pady=2,sticky="w")

        
    def display_pathways_direction_plot(self):

        logger.info("displaying network plot image")

        self.status_label_path_dir.configure(text="Loading...", text_color="yellow")
        self.update()
        if self.pathway_direction_image_label is not None:
            self.pathway_direction_image_label.destroy()

        # get the value from top N entry
        cluster = int(self.path_dir_cluster_entry.get())
        top_n = int(self.path_dir_n_entry.get())
        # size = int(self.size_entry.get())*100

        try:
            image_location = self.pathway.plot_bar(cluster=cluster,top=top_n,show=False)
        except Exception as e:
            logger.error(f"Error in directions plot: {e}")
            CTkMessagebox(title="Error", message="Something went wrong in pathway calculation", icon="cancel")

        logger.info(f"bar plot image location: {image_location}")
        # creating a label to display the image
        self.pathway_direction_image_label = ctk.CTkLabel(self.path_dir_image_frame , text = "", width=600, height=600)
        self.pathway_direction_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image3 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (800,600))
        self.pathway_direction_image_label.configure(image=ctk_image3)
        self.pathway_direction_image_label.image = ctk_image3
        self.status_label_path_dir.configure(text="", text_color="yellow")
        self.update()


    def display_r_output(self):

        logger.info("displaying R output")

        for child in self.scrollable_frame.winfo_children():
            child.destroy()
        """This function displays the R output in the scrollable frame"""
        path = os.path.join(self.region_specific_pathways_folder, 'R_output.txt')
        # reading the text file and holding the whole text in a variable with line breakers
        try:
            with open(path) as f:
                lines = f.readlines()
            text = '\n'.join(lines)
        except Exception as e:
            logger.error(f"Error in reading R output file: {e}")
            text = "No R output found"

        # adding a text box in the scrollable frame
        self.r_output_box = ctk.CTkTextbox(self.scrollable_frame, font = ("Arial", 14) , height = 150)
        self.r_output_box.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.r_output_box.rowconfigure(0, weight=1)
        self.r_output_box.columnconfigure(0, weight=1)
        self.r_output_box.insert("0.0", text)
        self.r_output_box.configure(state="disabled") 

        logger.info("R output displayed")
    

        
        


    
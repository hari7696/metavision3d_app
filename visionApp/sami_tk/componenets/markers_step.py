import tkinter as tk
import customtkinter as ctk
import os
import logging
from multiprocessing import Process, Queue
from CTkMessagebox import CTkMessagebox
from .colormap import *
from .timer import TimerApp
from SAMI.markers import Markers
import scanpy as sc
from PIL import Image
from ..utils import adata_filter
logger = logging.getLogger(__name__)

class MarkerStep(ctk.CTkFrame):

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler
        self.working_folder = os.path.join(*[file_handler.working_folder, 'results', 'clustering'])
        self.makers_working_folder = os.path.join(*[file_handler.working_folder, 'results', 'markers'])
        self.umap_overlay_label = None
        self.circular_image_label = None
        self.volcano_image_label = None
        self.queue = Queue()
        self.image_label = None
        self.sami_type = self.file_handler.file_type

        self.prepare_visualization_dock_type2()
        self.trigger_visz_functions_on_thread_run()


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

        self.markers_root_tab = self.vis_tabs.add("Markers")
        self.markers_root_tab.columnconfigure(0, weight=1)
        self.markers_root_tab.rowconfigure(0, weight = 1)
        self.markers_root_tab.rowconfigure(1, weight = 20)

        #options panel

        self.options_panel = ctk.CTkFrame(self.markers_root_tab, bg_color="transparent")
        self.options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        self.prepare_options_panel()

        # viz_frame

        self.viz_frame = ctk.CTkFrame(self.markers_root_tab, bg_color="transparent")
        self.viz_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.viz_frame.columnconfigure(0, weight=2)
        self.viz_frame.columnconfigure(1, weight=1)

        # breaking down the viz_frame into 2 frames
        self.circular_tree_frame = ctk.CTkFrame(self.viz_frame, bg_color="transparent")
        self.circular_tree_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)

        self.volcano_frame = ctk.CTkFrame(self.viz_frame, bg_color="transparent")
        self.volcano_frame.grid(row=0, column=1, sticky="new", padx=5, pady=5)
        logger.info("Markers tab prepared") 

        self.prepare_options_panel()
    
    def refresh(self):
        "whenever the tab swtich happens this function updates the files available in dropdowns"
        files = os.listdir(self.working_folder)
        files = [file for file in files if ('.h5ad') in file]

        self.region1_selection.configure(values=files)

        if self.sami_type == "multi":
            self.region2_selection.configure(values=files)

        logger.info("Refreshing markers tab")

    def prepare_options_panel(self):
        

        for i in range(0,15):
            self.options_panel.columnconfigure(i, weight=1)


        files = os.listdir(self.working_folder)
        files = [file for file in files if ('.h5ad') in file]
        # region selection 1
        region1_label = ctk.CTkLabel(self.options_panel, text="Select Region 1 :" )
        region1_label.grid(row=0,column=0,padx=(2,0),pady=2,sticky="ew")    
        _ = tk.StringVar(value='choose file')
        self.region1_selection = ctk.CTkComboBox(master= self.options_panel,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 150
                                            )
        self.region1_selection.grid(row=0,column=1,padx=(2,0),pady=2,sticky="ew")

        if self.sami_type == "multi":
            # region selection 2
            region2_label = ctk.CTkLabel(self.options_panel, text="Select Region 2 :" )
            region2_label.grid(row=0,column=2,padx=(2,0),pady=2,sticky="ew")
            _ = tk.StringVar(value='choose file')
            self.region2_selection = ctk.CTkComboBox(master= self.options_panel,
                                                values=files,
                                                variable=_,
                                                button_color="#b5b8b0",
                                                width = 150
                                                )
            self.region2_selection.grid(row=0,column=3,padx=(2,0),pady=2,sticky="ew")

        # Taking the value abundance from user using CTkEntry
        abundance_label = ctk.CTkLabel(self.options_panel, text="Abundance:")
        abundance_label.grid(row=0,column=4,padx=(2,0),pady=2,sticky="ew")

        self.abundance_entry = ctk.CTkEntry(self.options_panel, width=20, placeholder_text= "0.1")
        self.abundance_entry.insert(0, "0.1")
        self.abundance_entry.grid(row=0,column=5,padx=(2,0),pady=2,sticky="ew")

        #taking the prevalence value from user using CTkEntry
        prevalence_label = ctk.CTkLabel(self.options_panel, text="Prevalence:")
        prevalence_label.grid(row=0,column=6,padx=(2,0),pady=2,sticky="ew")

        self.prevalance_entry = ctk.CTkEntry(self.options_panel, width=20, placeholder_text= "0.1")
        self.prevalance_entry.insert(0, "0.1")
        self.prevalance_entry.grid(row=0,column=7,padx=(2,0),pady=2,sticky="ew")

        #taking adj_pval_cutoff value from user using CTkEntry
        adj_pval_cutoff_label = ctk.CTkLabel(self.options_panel, text="Adj Pval Cutoff:")
        adj_pval_cutoff_label.grid(row=0,column=8,padx=(2,0),pady=2,sticky="ew")

        self.adj_pval_cutoff_entry = ctk.CTkEntry(self.options_panel, width=20, placeholder_text= "0.05")
        self.adj_pval_cutoff_entry.insert(0, "0.05")
        self.adj_pval_cutoff_entry.grid(row=0,column=9,padx=(2,0),pady=2,sticky="ew")

        # taking the value of top_n_molecules from user using CTkEntry
        top_n_molecules_label = ctk.CTkLabel(self.options_panel, text="Top N Molecules:")
        top_n_molecules_label.grid(row=0,column=10,padx=(2,0),pady=2,sticky="ew")

        self.top_n_molecules_entry = ctk.CTkEntry(self.options_panel, width=20, placeholder_text= "50")
        self.top_n_molecules_entry.insert(0, "50")  
        self.top_n_molecules_entry.grid(row=0,column=11,padx=(2,0),pady=2,sticky="ew")

        # adding a Run button to run the markers generation
        self.run_button = ctk.CTkButton(self.options_panel, text="Generate Markers", command=self.generate_markers)
        self.run_button.grid(row=0,column=12,padx=(5,5),pady=2,sticky="ew")
        
        # timer button
        self.timer = TimerApp(self.options_panel)
        self.timer.grid(row=0,column=13,padx=(5,5),pady=2,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.options_panel, text="", text_color="yellow")
        self.time_constraint_label.grid(row=0,column=14,padx=(2,0),pady=2,sticky="w")

        logger.info("Options panel prepared")   

    def generate_markers(self):
        
        logger.info("Generating markers button hit")
        # this function run the command of generating markers button
        region1 = self.region1_selection.get()

        if self.sami_type == "multi":
            region2 = self.region2_selection.get()
        abundance = float(self.abundance_entry.get())
        prevalence = float(self.prevalance_entry.get())
        adj_pval_cutoff = float(self.adj_pval_cutoff_entry.get())
        top_n_molecules = int(self.top_n_molecules_entry.get())
        logger.info(f"Num molecules: {top_n_molecules}")
        self.timer.start_timer()
        self.time_constraint_label.configure(text="Note : Markers generation takes roughly 3 minutes", text_color="yellow")
        

        adata1_path = os.path.join(self.working_folder, region1) 
        if self.sami_type == "multi":
            adata2_path = os.path.join(self.working_folder, region2)
            reference_name = '_'.join(region1.replace('.h5ad' , "").split('_')[:-1]) + '_with_' + '_'.join(region2.replace('.h5ad', "").split('_')[:-1])
        else:
            adata2_path = None
            reference_name = '_'.join(region1.replace('.h5ad', "").split('_')[:-1]) + '_single'
        logger.info(f"adata1_path: {adata1_path}")
        logger.info(f"adata2_path: {adata2_path}")
        logger.info(f"top_n_molecules: {top_n_molecules}")
        # creating a process to run the markers generation

        logger.info("Starting markers process")
        maker_process = Process(target=self.markers_actual_run, args=(adata1_path, adata2_path, abundance,
                                                                       prevalence, adj_pval_cutoff, top_n_molecules, self.queue, reference_name,
                                                                       self.makers_working_folder))
        maker_process.start()
        self.markers = Markers(reference_name)

    @staticmethod
    def markers_actual_run(adata1_path, adata2_path, abundance, prevalence, adj_pval_cutoff, top_n_molecules, queue, reference_name, makers_working_folder):

           
        adata1 = sc.read(adata1_path) # case 
        adata_filtered1 = adata_filter(adata1, abundance,prevalence)
        logger.info(f"adata1 shape: {adata_filtered1.shape}")
        if adata2_path is not None:
            adata2 = sc.read(adata2_path) # control
            adata_filtered2 = adata_filter(adata2,0.1,0.1)
        else:
            adata_filtered2 = None
            logger.info(f"adata2 shape: None")

        markers = Markers(reference_name)  # reference name is the name of the file where it will save with markers
        markers.findmarkers(adata_filtered1,adj_pval_cutoff,top_n_molecules, adata_filtered2,makers_working_folder )

        queue.put("markers_done")
        logger.info("markers done")


    
    def trigger_visz_functions_on_thread_run(self):

        if self.queue.qsize() > 0:

            signal = self.queue.get_nowait()
            if signal == "markers_done":
                logger.info("Markers generation complete message received from process")
                # self.prepare_cluster_visualization()
                # self.dsplay_umpa_overlay()
                self.timer.stop_timer()
                self.timer.reset_timer()
                self.time_constraint_label.configure(text="Note : Markers generation completed", text_color="green")
                self.prepare_circular_tree_plot()
                self.prepare_volcano_plot()
                self.after(500, self.display_circular_plot())
                self.after(500, self.display_volcano_plot())

                logger.info("Markers generation complete and visualizations prepared")
            # Schedule the next queue check
            
        logger.info("checking the queue")
        self.after(10000, self.trigger_visz_functions_on_thread_run)

    def prepare_circular_tree_plot(self):

        logger.info("Preparing circular tree plot")

        for child in self.circular_tree_frame.winfo_children():
            child.destroy() 

        self.circular_tree_frame.columnconfigure(0, weight=1)
        self.circular_tree_frame.rowconfigure(0, weight=1)
        self.circular_tree_frame.rowconfigure(1, weight=9)

        # circular options panel
        self.circular_options_panel = ctk.CTkFrame(self.circular_tree_frame, bg_color="transparent")
        self.circular_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.circular_options_panel.columnconfigure(0, weight=1)
        # self.circular_options_panel.columnconfigure(1, weight=1)
        # self.circular_options_panel.columnconfigure(2, weight=1)
        # self.circular_options_panel.rowconfigure(0, weight=1)

        # image frame
        self.circular_image_frame = ctk.CTkFrame(self.circular_tree_frame, bg_color="transparent")
        self.circular_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.circular_image_frame.columnconfigure(0, weight=1)
        self.circular_image_frame.rowconfigure(0, weight=1)


        # creating a label to select top N clusters
        top_clusters_label = ctk.CTkLabel(self.circular_options_panel, text="Select top N: ")
        top_clusters_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.top_n_entry = ctk.CTkEntry(self.circular_options_panel, width=50, placeholder_text= "5",)
        self.top_n_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.top_n_entry.insert(0, "5")

        # button to run the function
        self.run_button = ctk.CTkButton(self.circular_options_panel, text="Run", command=self.display_circular_plot)
        self.run_button.grid(row=0, column=2, sticky="w", padx=(20,0), pady=5)

        # adding a status label
        # self.status_label_circular_plot = ctk.CTkLabel(self.circular_options_panel, text="", text_color="yellow", width= 150)
        # self.status_label_circular_plot.grid(row=0, column=3, sticky="w", padx=(20,0), pady=5)

        

    def display_circular_plot(self):

        logger.info("Displaying circular plot")
        # self.status_label_circular_plot.configure(text="Loading...", text_color="yellow")
        # self.update()
        if self.circular_image_label is not None:
            self.circular_image_label.destroy()

        logger.info("displaying circular plot")

        # get the value from top N entry
        top = int(self.top_n_entry.get())
        

        try:
            image_location = self.markers.circular_tree(clusters=None,top=top, show=False, workdir= self.makers_working_folder)
            logger.info(f"Circular plot Image location: {image_location}")
        except Exception as e:
            logger.error(f"Error in plot_dot: {e}")
            CTkMessagebox(title="Error", message="Something went wrong in Markers calculation", icon="cancel")


        # creating a label to display the image
        self.circular_image_label = ctk.CTkLabel(self.circular_image_frame , width=800, height=800)
        self.circular_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image1 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (800,800))
        self.circular_image_label.configure(image=ctk_image1)
        self.circular_image_label.image = ctk_image1

        # self.status_label_circular_plot.configure(text="", text_color="yellow")
        # self.update()
    
    def prepare_volcano_plot(self):

        logger.info("Preparing volcano plot frame")

        for child in self.volcano_frame.winfo_children():
            child.destroy()

        self.volcano_frame.columnconfigure(0, weight=1)
        self.volcano_frame.rowconfigure(0, weight=1)
        self.volcano_frame.rowconfigure(1, weight=9)

        # options panel 
        self.volocano_options_panel = ctk.CTkFrame(self.volcano_frame, bg_color="transparent")
        self.volocano_options_panel.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        # self.volocano_options_panel.columnconfigure(0, weight=1)
        # self.volocano_options_panel.columnconfigure(1, weight=1)
        # self.volocano_options_panel.columnconfigure(2, weight=1)
        # self.volocano_options_panel.rowconfigure(0, weight=1)

        # image fram
        self.volcano_image_frame = ctk.CTkFrame(self.volcano_frame, bg_color="transparent")
        self.volcano_image_frame.grid(row=1, column=0, sticky="new", padx=5, pady=5)
        self.volcano_image_frame.columnconfigure(0, weight=1)
        self.volcano_image_frame.rowconfigure(0, weight=1)


        # creating a label to select top N clusters
        select_cluster_label = ctk.CTkLabel(self.volocano_options_panel, text="Select cluster: ")
        select_cluster_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        #entry box to take value
        self.cluster_selection = ctk.CTkEntry(self.volocano_options_panel, width=50, placeholder_text= "5",)
        self.cluster_selection.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.cluster_selection.insert(0, "1")

        # button to run the function
        self.run_button = ctk.CTkButton(self.volocano_options_panel, text="Run", command=self.display_volcano_plot)
        self.run_button.grid(row=0, column=2, sticky="w", padx=(20,0), pady=5)

        # adding a status label
        # self.status_label_volcano_plot = ctk.CTkLabel(self.volocano_options_panel, text="", text_color="yellow", width= 150)
        # self.status_label_volcano_plot.grid(row=0, column=3, sticky="w", padx=(20,0), pady=5)

    def display_volcano_plot(self):

        # self.status_label_circular_plot.configure(text="Loading...", text_color="yellow")
        # self.update()

        logger.info("Displaying volcano plot")

        if self.volcano_image_label is not None:
            self.volcano_image_label.destroy()

        # get the value from top N entry
        cluster = int(self.cluster_selection.get())
        try:
            image_location = self.markers.volcano_plot(cluster, show=False, work_dir= self.makers_working_folder)
            logger.info(f"Volcano Image location: {image_location}")    
        except Exception as e:
            logger.error(f"Error in plot_dot: {e}")
            CTkMessagebox(title="Error", message="Something went wrong in Markers calculation", icon="cancel")


        # creating a label to display the image
        self.volcano_image_label = ctk.CTkLabel(self.volcano_image_frame , width=400, height=400)
        self.volcano_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image2 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (400,400))
        self.volcano_image_label.configure(image=ctk_image2)
        self.volcano_image_label.image = ctk_image2

        # self.status_label_volcano_plot.configure(text="", text_color="yellow")
        # self.update()


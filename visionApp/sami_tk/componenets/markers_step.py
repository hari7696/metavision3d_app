import tkinter as tk
import customtkinter as ctk
import os
import logging
from multiprocessing import Process, Queue
from CTkMessagebox import CTkMessagebox
from sami_tk.colormap import *
from .timer import TimerApp
from SAMI.markers import Markers
import scanpy as sc
from PIL import Image
from ..utils import adata_filter
from .display_image import ImageDisaplay
from log_listener import worker_configurer
from .markers_utilities import DisplayFileInformation
from pandas.core.common import flatten
from CTkMessagebox import CTkMessagebox
import ast 
logger = logging.getLogger(__name__)
# logger = logging.getLogger(__name__)

class MarkerStep(ctk.CTkFrame):

    def __init__(self, master, file_handler, queue):
        super().__init__(
            master,
        )
        self.log_queue = queue
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

    def get_files(self): 
        self.files_to_path_dict = {}
        self.files = []
        for dirpath, dirs, lst_files in os.walk(self.working_folder):
            for file in lst_files:
                if file.endswith(".h5ad"):
                    # print(file, dirpath)
                    # if os.path.dirname(dirpath) != "clustering":
                    new_dir_ref = os.path.basename(dirpath)
                    if new_dir_ref != "clustering":
                        new_dir_ref = "Integrated"
                    file_ = new_dir_ref + "||" + file
                    self.files_to_path_dict[file_] = os.path.join(dirpath, file)
                    self.files.append(file_)
    
    def refresh(self):
        "whenever the tab swtich happens this function updates the files available in dropdowns"
        self.get_files()
        # self.region1_selection.configure(values=self.files)

        # if self.sami_type == "multi":
        #     self.region2_selection.configure(values=self.files)

        logger.info("Refreshing markers tab")

    def prepare_options_panel(self):
        

        # for i in range(0,15):
        #     self.options_panel.columnconfigure(i, weight=1)

        self.get_files()

        #options panel layout 2 colums, 3 rows
        self.options_panel.columnconfigure(0, weight=1)
        self.options_panel.columnconfigure(1, weight=9)
        self.options_panel.rowconfigure(0, weight=1)


        # creating a frame
        sami_type_frame = ctk.CTkFrame(self.options_panel)
        sami_type_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        # select type of markers, (single vs dual)
        markers_type_label = ctk.CTkLabel(sami_type_frame, text="Type: ")
        markers_type_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5, rowspan=3)
        # dropdown to select the type of markers
        self.markers_type_selection = ctk.CTkComboBox(master= sami_type_frame,
                                            values=["single", "dual"],
                                            button_color="#b5b8b0",
                                            width = 150, command=self.create_file_option_widgets
                                            )
        self.markers_type_selection.set("")
        self.markers_type_selection.grid(row=0, column=1, sticky="ew", padx=5, pady=5, rowspan=3)
    
    def create_file_option_widgets(self, choice):

        self.get_files()

        if hasattr(self, "file_option_frame"):
            for child in self.file_option_frame.winfo_children():
                child.destroy()
        else:
            # creating another frame for option
            self.file_option_frame = ctk.CTkFrame(self.options_panel)    
            self.file_option_frame.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
            self.file_option_frame.rowconfigure(0, weight=1)
            self.file_option_frame.columnconfigure(0, weight=1)

            

        if choice == "single":

            # initiaing custom tkinter object
            file_number =1
            self.region1_obj = DisplayFileInformation(self.file_option_frame, self.files_to_path_dict, file_number, choice, self.log_queue) 
            self.region1_obj.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        elif choice == "dual":

            file_number =1
            self.region1_obj = DisplayFileInformation(self.file_option_frame, self.files_to_path_dict, file_number, choice, self.log_queue) 
            self.region1_obj.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

            file_number =2
            self.region2_obj = DisplayFileInformation(self.file_option_frame, self.files_to_path_dict, file_number, choice, self.log_queue) 
            self.region2_obj.grid(row=1, column=0, sticky="ew", padx=2, pady=2)

        ###### Row2 ########

        # a separate frame for row 2
        self.row_2frame = ctk.CTkFrame(self.file_option_frame)    
        self.row_2frame.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        self.row_2frame.rowconfigure(0, weight=1)
        for i in range(0, 10):
            self.row_2frame.columnconfigure(i, weight=1)

        # # Taking the value abundance from user using CTkEntry
        abundance_label = ctk.CTkLabel(self.row_2frame, text="Abundance:")
        abundance_label.grid(row=0,column=0,padx=(2,0),pady=2,sticky="ew")

        self.abundance_entry = ctk.CTkEntry(self.row_2frame, width=20, placeholder_text= "0.1")
        self.abundance_entry.insert(0, "0.1")
        self.abundance_entry.grid(row=0,column=1,padx=(2,0),pady=2,sticky="ew")

        #taking the prevalence value from user using CTkEntry
        prevalence_label = ctk.CTkLabel(self.row_2frame, text="Prevalence:")
        prevalence_label.grid(row=0,column=2,padx=(2,0),pady=2,sticky="ew")

        self.prevalance_entry = ctk.CTkEntry(self.row_2frame, width=20, placeholder_text= "0.1")
        self.prevalance_entry.insert(0, "0.1")
        self.prevalance_entry.grid(row=0,column=3,padx=(2,0),pady=2,sticky="ew")

        #taking adj_pval_cutoff value from user using CTkEntry
        adj_pval_cutoff_label = ctk.CTkLabel(self.row_2frame, text="Adj Pval Cutoff:")
        adj_pval_cutoff_label.grid(row=0,column=4,padx=(2,0),pady=2,sticky="ew")

        self.adj_pval_cutoff_entry = ctk.CTkEntry(self.row_2frame, width=20, placeholder_text= "0.05")
        self.adj_pval_cutoff_entry.insert(0, "0.05")
        self.adj_pval_cutoff_entry.grid(row=0,column=5,padx=(2,0),pady=2,sticky="ew")

        # taking the value of top_n_molecules from user using CTkEntry
        top_n_molecules_label = ctk.CTkLabel(self.row_2frame, text="Top N Molecules:")
        top_n_molecules_label.grid(row=0,column=6,padx=(2,0),pady=2,sticky="ew")

        self.top_n_molecules_entry = ctk.CTkEntry(self.row_2frame, width=20, placeholder_text= "50")
        self.top_n_molecules_entry.insert(0, "50")  
        self.top_n_molecules_entry.grid(row=0,column=7,padx=(2,0),pady=2,sticky="ew")

        ######### ROW 3 #########

        # a separate frame for row 3
        self.row_3frame = ctk.CTkFrame(self.file_option_frame)
        self.row_3frame.grid(row=3, column=0, sticky="ew", padx=2, pady=2)
        self.row_3frame.rowconfigure(0, weight=1)
        for i in range(0, 10):
            self.row_3frame.columnconfigure(i, weight=1)

        # a label to ask for the output filename
        self.output_filename_label = ctk.CTkLabel(self.row_3frame, text="Output Filename:")
        self.output_filename_label.grid(row=0,column=0,padx=(5,5),pady=2,sticky="ew")

        # entry box to take the output filename
        self.output_filename_entry = ctk.CTkEntry(self.row_3frame, width=50, placeholder_text= "name_of_file")
        self.output_filename_entry.grid(row=0,column=1,padx=(5,5),pady=2,sticky="ew", columnspan=2)

        # adding a Run button to run the markers generation
        self.run_button = ctk.CTkButton(self.row_3frame, text="Generate Markers", command=self.generate_markers)
        self.run_button.grid(row=0,column=3,padx=(5,5),pady=2,sticky="ew")
        
        # timer button
        self.timer = TimerApp(self.row_3frame)
        self.timer.grid(row=0,column=4,padx=(5,5),pady=2,sticky="ew")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.row_3frame, text="", text_color="yellow")
        self.time_constraint_label.grid(row=0,column=5,padx=(5,5),pady=2,sticky="ew")

        logger.info("Options panel prepared")

    @staticmethod
    def validate_entry(entry, highest):
        try:
           if entry != "":
                entry = int(entry)
                if entry <= highest:
                     return True
                else:
                     return False
               
        except:
            return False

    def prep_parameter_data(self):
        
        if self.markers_type_selection.get() == "single":
            self.selected_file1, self.lst1_regions, self.clustermap, self.highest_cluster  = self.region1_obj.get_values()
        else:
            self.selected_file1, self.lst1_regions, self.clustermap, self.highest_cluster  = self.region1_obj.get_values()
            self.selected_file2, self.lst2_regions, _, self.highest_cluster  = self.region2_obj.get_values()

        # processing the clustermap
        # clustermap, its a list of lists . sample :- [['0', '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28'], 
        # ['1', '1,2,3'], ['2', ''], ['3', '1,2,3,'], ['4', '0,1,2,3,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28']]
        self.dict_clustermap = {}
        left_list = []
        right_list = []
        for item in self.clustermap:
            
            logger.info(f"item: {item}")
            left = item[0].split(",")
            right = item[1].split(",")

            left = [item for item in left if self.validate_entry(item, self.highest_cluster)]
            right = [item for item in right if self.validate_entry(item, self.highest_cluster)]
            
            left = list(flatten(left))
            right = list(flatten(right))

            # if either left or right is empty we are skipping that row
            if min(len(left),len(right))  == 0:
                continue
            left_list.append(left)
            right_list.append(right)

        self.dict_clustermap['left'] = left_list
        self.dict_clustermap['right'] = right_list
        

        logger.info(f"lst1_regions: {self.lst1_regions}")
        # logger.info(f"lst2_regions: {self.lst2_regions}")
        logger.info(f"clustermap : {self.clustermap}")
        logger.info(f"highest_cluster: {self.highest_cluster}") 
        logger.info(f"processed clustermap: {self.dict_clustermap}")
        logger.info(f" len of left lst  : {len(left_list)}")
        logger.info(f" len of right lst  : {len(right_list)}")


    def generate_markers(self):
        self.prep_parameter_data()
        # self.run_button.configure(state="disabled")
        logger.info("Generating markers button hit")
        # this function run the command of generating markers button
        # region1 = self.selected_file1.split("||")[-1]
        # if self.markers_type_selection.get() == "dual":
        #     region2 = self.selected_file2.split("||")[-1]

        abundance = float(self.abundance_entry.get())
        prevalence = float(self.prevalance_entry.get())
        adj_pval_cutoff = float(self.adj_pval_cutoff_entry.get())
        top_n_molecules = int(self.top_n_molecules_entry.get())
        reference_name = self.output_filename_entry.get()
        if reference_name == "":
            CTkMessagebox(title="info", message="Please provide a name for the output file")
            return


        logger.info(f"Num molecules: {top_n_molecules}")
        self.timer.start_timer()
        self.time_constraint_label.configure(text="Note : Markers generation takes 10+ minutes", text_color="yellow")
        

        adata1_path = os.path.join(self.working_folder, self.files_to_path_dict[self.selected_file1]) 
        if self.markers_type_selection.get() == "dual":
            adata2_path = os.path.join(self.working_folder, self.files_to_path_dict[self.selected_file2])
        else:
            adata2_path = None
        logger.info(f"adata1_path: {adata1_path}")
        logger.info(f"adata2_path: {adata2_path}")
        logger.info(f"top_n_molecules: {top_n_molecules}")
        # creating a process to run the markers generation

        logger.info("Starting markers process")

        if self.markers_type_selection.get() == "single":
            maker_process = Process(target=self.markers_actual_run, args=(adata1_path, adata2_path, abundance,
                                                                        prevalence, adj_pval_cutoff, top_n_molecules, self.queue, reference_name,
                                                                        self.makers_working_folder, self.log_queue, self.lst1_regions, None, self.dict_clustermap
                                                                        ),  name = "SAMI:Markers_step")
            
        else:
            maker_process = Process(target=self.markers_actual_run, args=(adata1_path, adata2_path, abundance,
                                                            prevalence, adj_pval_cutoff, top_n_molecules, self.queue, reference_name,
                                                            self.makers_working_folder, self.log_queue, self.lst1_regions, self.lst2_regions,  self.dict_clustermap
                                                            ),  name = "SAMI:Markers_step")
        maker_process.start()
        self.markers = Markers(reference_name, None)
        logger.info("Markers process started")

    @staticmethod
    def markers_actual_run(adata1_path, adata2_path, abundance, prevalence, adj_pval_cutoff, top_n_molecules, queue, reference_name, 
                           makers_working_folder, log_queue, lst1_regions, lst2_regions, dict_clustermap):


        try:
            # worker_configurer(log_queue)
            adata1 = sc.read(adata1_path) # case 
            # filtering out selected regions
            adata1 = adata1[adata1.obs['region'].isin(lst1_regions)]
            logger.info(f"adata regions: {adata1.obs['region'].unique()}")
            adata_filtered1 = adata_filter(adata1, abundance,prevalence)

            logger.info(f"adata1 shape: {adata_filtered1.shape}")
            mode = "single"
            if adata2_path is not None:
                adata2 = sc.read(adata2_path) # control
                # filtering out selected regions
                adata2 = adata2[adata2.obs['region'].isin(lst2_regions)]
                logger.info(f"adata2 regions: {adata2.obs['region'].unique()}")

                adata_filtered2 = adata_filter(adata2,abundance,prevalence)
                mode = "dual"
            else:
                adata_filtered2 = None
                logger.info(f"adata2 shape: None")

            markers = Markers(reference_name, log_queue)  # reference name is the name of the file where it will save with markers
            markers.findmarkers(dict_clustermap, adata_filtered1,adj_pval_cutoff,top_n_molecules, adata_filtered2,makers_working_folder )

            queue.put("markers_done")
            logger.info("markers done")
        except Exception as e:
            logger.error(f"Error in markers_actual_run: {e}")
            queue.put("markers_error")
            # logger.info("markers done")


    
    def trigger_visz_functions_on_thread_run(self):
                    
        logger.info("checking the queue")
        try:
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
                elif signal == "markers_error":
                    CTkMessagebox(title="Error", message="Something went wrong in Markers calculation", icon="cancel")
            # Schedule the next queue check
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
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
        self.status_label_circular_plot = ctk.CTkLabel(self.circular_options_panel, text="", text_color="yellow", width= 150)
        self.status_label_circular_plot.grid(row=0, column=3, sticky="w", padx=(20,0), pady=5)

        

    def display_circular_plot(self):

        logger.info("Displaying circular plot")
        self.status_label_circular_plot.configure(text="Loading...", text_color="yellow")
        self.update()


        logger.info("displaying circular plot")

        # get the value from top N entry
        
        try:
            image_location = self.markers.circular_tree(clusters=None,top_n=int(self.top_n_entry.get()), show=False, workdir= self.makers_working_folder)
            logger.info(f"Circular plot Image location: {image_location}")
        except Exception as e:
            logger.error(f"Error in circular plot: {e}")
            CTkMessagebox(title="Error", message="Something went wrong in Markers calculation", icon="cancel")


        # creating a label to display the image

        self.circular_image_label = ImageDisaplay(self.circular_image_frame, image_location, 700, 700, 1.0)
        self.circular_image_label.grid(row=0, column=0, sticky="nsew", padx=(5,0) , pady = (2,2))
        self.circular_image_label.columnconfigure(0, weight=1)
        self.circular_image_label.rowconfigure(0, weight=1)


        # self.circular_image_label = ctk.CTkLabel(self.circular_image_frame , text = "", width=800, height=800)
        # self.circular_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        # ctk_image1 = ctk.CTkImage(light_image=Image.open(image_location),
        #                              dark_image=None, size = (800,800))
        # self.circular_image_label.configure(image=ctk_image1)
        # self.circular_image_label.image = ctk_image1

        self.status_label_circular_plot.configure(text="", text_color="yellow")
        self.update()
    
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
        clusters = self.markers.get_clusters(self.makers_working_folder)
        clusters = [str(item) for item in clusters]
        self.cluster_selection = ctk.CTkComboBox(self.volocano_options_panel, values=clusters )
        self.cluster_selection.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.cluster_selection.set(clusters[0])
        # self.cluster_selection = ctk.CTkEntry(self.volocano_options_panel, width=50, placeholder_text= "5",)
        # self.cluster_selection.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.cluster_selection.insert(0, "1")

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
        self.volcano_image_label = ctk.CTkLabel(self.volcano_image_frame , text = "", width=600, height=600)
        self.volcano_image_label.grid(row=1, column=0, sticky="new", padx=5, pady=5)

        ctk_image2 = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (600,600))
        self.volcano_image_label.configure(image=ctk_image2)
        self.volcano_image_label.image = ctk_image2

        # self.status_label_volcano_plot.configure(text="", text_color="yellow")
        # self.update()


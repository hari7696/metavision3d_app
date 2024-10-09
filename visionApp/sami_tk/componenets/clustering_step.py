import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import os
import logging
from multiprocessing import Process, Queue
from PIL import Image
from sami_tk.colormap import *
from CTkTable import CTkTable
import io
import logging
from .timer import TimerApp
from SAMI.clustering import Clusters
from PRISM.ColumnTable import ColumnTable
from PRISM.NestedTable import NestedTable
from .display_image import ImageDisaplay
from .ClusterPrismExport import ClusterPrismExport
from log_listener import worker_configurer
import scanpy as sc
import pandas as pd 
from CTkMessagebox import CTkMessagebox
from .scrollable_multi_select import ScrollableWindowMulitSelect
from tkinter import Listbox, END
logger = logging.getLogger(__name__)
# logger = logging.getLogger(__name__)

class ClusteringStep(ctk.CTkFrame):

    """"
    This class is used to perform the clustering on the pooled data
    """

    def __init__(self, master, file_handler, log_queue):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler
        self.prepare_visualization_dock_type2()
        self.prep_cluster_options_tab()
        self.cluster_image_label = None
        self.image_label = None
        self.queue = Queue()
        self.is_clustering_ran = False
        self.prism_table_value = []
        self.prism_table_value.append(["Table Name", "Clusters", "Compounds"])
        self.dict_df = {}
        # self.trigger_visz_functions_on_thread_run()

        # clustering tracker 
        self.df_tracker_path = os.path.join(self.file_handler.working_folder, 'results', 'clustering_tracker.csv')

        if os.path.exists(self.df_tracker_path):
            self.df_tracker = pd.read_csv(self.df_tracker_path)
        else:
            self.df_tracker = pd.DataFrame(columns=['timestamp', 'resolution', 'harmony', 'input_file', 'clustered_file' ])


    def prepare_visualization_dock_type2(self):
        """This visualization is used for the tabs 1. Pooling, 2. Clustering, 3. Clusters Integration, 4. Markers, 5. Pathways
        A separate tabview is created for this type of visualization, as it doesnt need left and right frames
        """

        for child in self.winfo_children():
            child.destroy()

        self.root_visualization_frame = ctk.CTkFrame(
            self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
        # self.root_visualization_frame.columnconfigure(1,weight=2)
        self.root_visualization_frame.rowconfigure(0, weight=1)
        self.root_visualization_frame.grid(row=0, column=0, sticky="nsew")

        self.vis_tabs = ctk.CTkTabview(self.root_visualization_frame)
        self.vis_tabs.columnconfigure(0, weight=1)
        self.vis_tabs.rowconfigure(0, weight=1)
        self.vis_tabs.grid(row=0, column=0, sticky="nsew", padx=5)
        
        self.cluster_tab = self.vis_tabs.add("Clustering")
        self.cluster_tab.columnconfigure(0, weight=1)
        self.cluster_tab.rowconfigure((0), weight = 1)
        self.cluster_tab.rowconfigure((1), weight = 20)
        self.cluster_tab.rowconfigure((2), weight = 7)

        #prism export tab  
        self.prism_export_tab = self.vis_tabs.add("Prism Export")
        

        # self.prism_export_tab.columnconfigure(0, weight=1)
        # self.prism_export_tab.rowconfigure((0), weight = 1)


        # cluster options tab
        self.cluster_options = ctk.CTkFrame(self.cluster_tab, bg_color="transparent")
        self.cluster_options.grid(row=0, column=0, sticky="nsew")
        # self.cluster_options.columnconfigure(0, weight=1)
        # self.cluster_options.rowconfigure(0, weight=1)

        # cluster visualization tab
        self.cluster_visualization = ctk.CTkFrame(self.cluster_tab, bg_color="transparent")
        self.cluster_visualization.grid(row=1, column=0, sticky="nsew")
        self.cluster_visualization.columnconfigure(0, weight=1)

        # specific cluster tab
        self.specific_cluster = ctk.CTkFrame(self.cluster_tab, bg_color="transparent")
        self.specific_cluster.grid(row=2, column=0, sticky="nsew")

        logger.info("Clustering tab prepared")

        # self.specific_cluster.rowconfigure(1, weight=1)
        # self.specific_cluster.columnconfigure(1, weight=1)
        # self.specific_cluster.columnconfigure(2, weight=1)

    def refresh(self):
        "whenever the tab swtich happens this function updates the files available in dropdowns"
        logger.info("Refreshing the files in the dropdown")
        path = os.path.join(self.file_handler.working_folder, 'pooled_data')
        files = os.listdir(path)
        self.file_selection.configure(values=files)


    def prep_cluster_options_tab(self):
        
        self.cluster_options.columnconfigure(0, weight=1)
        self.cluster_options.columnconfigure(1, weight=5)
        self.cluster_options.columnconfigure(2, weight=5)
        self.cluster_options.columnconfigure(3, weight=5)
        self.cluster_options.columnconfigure(4, weight=5)
        self.cluster_options.columnconfigure(5, weight=5)
        self.cluster_options.columnconfigure(5, weight=100)
        self.cluster_options.rowconfigure(0, weight=1)


        file_name_label = ctk.CTkLabel(self.cluster_options, text="Select File :" )
        file_name_label.grid(row=0,column=0,padx=(5,0),pady=8,sticky="w")
        
        _ = tk.StringVar(value='choose file')

        path = os.path.join(self.file_handler.working_folder, 'pooled_data')
        files = os.listdir(path)
        # print(files)
        #files = [file for file in files if '_pool' in file]

        self.file_selection = ctk.CTkComboBox(master= self.cluster_options,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 200
                                            )
        self.file_selection.grid(row=0,column=1,padx=(10,0),pady=8,sticky="w")

        # write a label for resolution
        resolution_label = ctk.CTkLabel(self.cluster_options, text="Resolution :")
        resolution_label.grid(row=0,column=2,padx=(10,0),pady=8,sticky="w")
        self.resolution = ctk.CTkEntry(self.cluster_options,placeholder_text="1",width=100)
        self.resolution.grid(row=0,column=3,padx=(5,0),pady=8,sticky="w")
        self.resolution.insert(0, "1")

        #adding a check box for the Harmony optons
        self.harmony_checkbox = ctk.CTkCheckBox(self.cluster_options, text="Harmony")
        self.harmony_checkbox.grid(row=0,column=4,padx=(10,0),pady=8,sticky="w")
        self.harmony_checkbox.select()

        self.cluster_button = ctk.CTkButton(self.cluster_options,text="Run Clustering",command=self.perform_clustering)
        self.cluster_button.grid(row=0,column=5,padx=(10,0),pady=8,sticky="w")

        # timer button
        self.timer = TimerApp(self.cluster_options)
        self.timer.grid(row=0,column=6,padx=(50,0),pady=8,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.cluster_options, text="Note : clustering usally takes 15+ minutes",
                                                   text_color="yellow", width=300)
        self.time_constraint_label.grid(row=0,column=7,padx=(10,0),pady=8,sticky="e")

        logger.info("Cluster options tab prepared")

    def prepare_cluster_module(self, ):

        """
        This function prepares the cluster module by getting the selected file, region, modality and resolution
        """

        selected_file = self.file_selection.get()

        if len(selected_file.split('_')) ==1:
            region = selected_file.split('.')[0]
            modality = ""
        else:
            region = '_'.join(selected_file.split('_')[:-1])
            modality = selected_file.split('_')[-1].split('.')[0] 

        logger.info(f"region : {region} and modality : {modality}")
        logger.info("CLuster module is created")
        logger.info(f"Selected file is {selected_file}")
        logger.info(f"{region} and {modality} are the region and modality selected")
        # print(region, modality)   
        res = float(self.resolution.get())
        
        # print(res)
        file_location = os.path.join(*[self.file_handler.working_folder, 'results', 'clustering'])

        hmodality = modality + '_harmony' if self.harmony_checkbox.get() == 1 else modality
        clustered_file = os.path.join(file_location,f'{region}_{hmodality}_{res}.h5ad')
        logger.info(f"File location is {file_location}")
        logger.info(f"Clustered file location is {clustered_file}")
        self.post_norm_adata_filepath =os.path.join(*[self.file_handler.working_folder,'pooled_data', f'{region}_{modality}.h5ad'])
        logger.info(f"Post norm adata file path is {self.post_norm_adata_filepath}")

        # adding info in tracker
        self.record = [pd.Timestamp.now(), res, self.harmony_checkbox.get(),self.post_norm_adata_filepath, clustered_file]


        cluster = Clusters(region, 
                               hmodality,
                               res,
                               os.path.join(self.file_handler.working_folder, 'pooled_data'),
                               os.path.join(self.file_handler.working_folder), self.log_queue, harmony_flag = self.harmony_checkbox.get())
        
        return cluster, clustered_file
    
    @staticmethod
    def clustering(queue, cluster, clustered_file, log_queue):
        "This function is used to perform the clustering"
        # worker_configurer(log_queue)
        response_dict = {}
        clustering_result = None
        # checking whether the clustering is already performed or not
        try:
            if not os.path.exists(clustered_file):
                logger.info("didnt any existing file, Performing clustering ")
                clustering_result = cluster.clustering()
            else:
                logger.info("Clustering already done")

            image_location, n_clusters = cluster.plot_umap_cluster(size=50,show=False)
            response_dict['image_location'] = image_location
            response_dict['n_clusters'] = n_clusters
            queue.put(response_dict)

        except Exception as e:
            queue.put({'error': str(clustering_result) + str(e)})

        # sending a message to the queue that thread is completed


    def perform_clustering(self):
        """This function gets triggered when the Run clustering button is clicked
        It starts the clustering process in a separate process
        Once the clustering is done, it triggers the visualization functions"""
        logger.info("perform_clustering Triggered" )
        self.cluster_button.configure(state="disabled")
        self.timer.reset_timer()
        self.timer.start_timer()
        cluster, self.clustered_file = self.prepare_cluster_module()
        self.time_constraint_label.configure(text="Note : clustering usally takes 15+ minutes", text_color="yellow")
        self.clustering_process = Process(target=self.clustering, args=(self.queue, cluster,self.clustered_file, self.log_queue), name= "SAMI:Clustering")
        self.clustering_process.start()
        self.trigger_visz_functions_on_thread_run()

    def trigger_visz_functions_on_thread_run(self):

        """
        This function checks the queue for the message from the clustering process
        If the message is received, it triggers the visualization functions

        """
        logger.info("checking clustering queue")
        if not self.queue.empty():
            try:
                logger.info("clustering complete message received")
                message = self.queue.get()

                if 'error' in message.keys():
                    CTkMessagebox(title="error", message=f"Error in SAMI core: {message['error']}", icon="cancel")
                    self.time_constraint_label.configure(text="Clustering Failed", text_color="red")
                    self.cluster_button.configure(state="normal")
                    return

                self.image_location = message['image_location']
                logger.info(f"saved cluster Image location is {self.image_location}")
                
                self.n_clusters = message['n_clusters']
                self.cluster, _ = self.prepare_cluster_module()
                self.prepare_cluster_visualization()
                self.prepare_specific_cluster_vis()
                logger.info("visualization prepared")
                self.df_tracker.loc[len(self.df_tracker)] = self.record
                self.df_tracker.to_csv(self.df_tracker_path, index=False)
                self.prepare_prism_export_tab()
                logger.info("prism export tab prepared")
                self.timer.stop_timer()
                self.time_constraint_label.configure(text="Clustering Done", text_color="green")
                self.cluster_button.configure(state="normal")
            except Exception as e:
                logger.error(f"Error in getting the message from the queue {e}")
                CTkMessagebox(title="error", message=f"Error in creating the plots: {e}", icon="cancel")
            finally:
                self.after(10000, self.trigger_visz_functions_on_thread_run)
        if self.clustering_process.is_alive():
            self.after(10000, self.trigger_visz_functions_on_thread_run)
        else:
            self.clustering_process.join()

    def prepare_cluster_visualization(self):

        """
        This function prepares the cluster visualization by getting the image location and displaying it using the ImageDisplay class
        """
        logger.info("Preparing cluster visualization")
        for children in self.cluster_visualization.winfo_children():
            children.destroy()

        self.image_display = ImageDisaplay(self.cluster_visualization, self.image_location)
        self.image_display.grid(row=0, column=0, sticky="nsew", )
        self.image_display.columnconfigure(0, weight=1)
        self.image_display.rowconfigure(0, weight=1)

    def prepare_specific_cluster_vis(self):
        

        """
        This function prepares the specific cluster visualization by getting the cluster object and the number of clusters
        """
        logger.info("Preparing specific cluster visualization")
        self.specific_cluster.columnconfigure(0, weight=1)
        self.specific_cluster.columnconfigure(1, weight=1)
        self.specific_cluster.columnconfigure(2, weight=1)
        self.specific_cluster.rowconfigure(0, weight=1)

        for child in self.specific_cluster.winfo_children():
            child.destroy()

        self.frame1 = ctk.CTkFrame(self.specific_cluster)
        self.frame1.grid(row=0, column=0, sticky="nsew", padx=(3,3), pady=(3,3))
        # self.frame1.columnconfigure(0, weight=1)
        # self.frame1.rowconfigure(0, weight=1)

        self.frame2 = ctk.CTkFrame(self.specific_cluster)
        self.frame2.grid(row=0, column=1, sticky="nsew", padx=(3,3), pady=(3,3))
        # self.frame2.columnconfigure(0, weight=1)
        # self.frame2.rowconfigure(0, weight=1)

        self.frame3 = ctk.CTkFrame(self.specific_cluster)
        self.frame3.grid(row=0, column=2, sticky="nsew", padx=(3,3), pady=(3,3))
        # self.frame3.columnconfigure(0, weight=1)
        # self.frame3.rowconfigure(0, weight=1)

        specific_cluster1 = SpecificCluster(self.frame1, self.cluster, self.n_clusters, 0)
        specific_cluster1.grid(row=0, column=0, sticky="nsew")

        specific_cluster2 = SpecificCluster(self.frame2, self.cluster, self.n_clusters, 1)
        specific_cluster2.grid(row=0, column=1, sticky="nsew")

        specific_cluster3 = SpecificCluster(self.frame3, self.cluster, self.n_clusters, 2)
        specific_cluster3.grid(row=0, column=2, sticky="nsew")

    def prepare_prism_export_tab(self):
        
        logger.info("preparing prism export tab")
        for child in self.prism_export_tab.winfo_children():
            child.destroy()
        
        prism_pane = ClusterPrismExport(self.prism_export_tab, self.log_queue, self.clustered_file, self.post_norm_adata_filepath)
        prism_pane.grid(row=0, column=0, sticky="nsew")
        prism_pane.columnconfigure(0, weight=1)
        prism_pane.rowconfigure(0, weight=1)

class DropDownMulitSelect(ctk.CTkToplevel):
    def __init__(self, master, options):
        super().__init__(master)
        # self.title("Select Isobaric Compounds")
        self.geometry("350x300")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=5)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        self.selected_values = []
        self.options = options
        # self.selected_values_label = selected_values_label
        # self.selected_values_label = []

        self.button = ctk.CTkLabel(self, text="Select clusters")
        self.button.grid(
            row=0, column=0, sticky="ew"
        )  # Ensure button expands to fill grid cell
        self.create_drop_down()

    def create_drop_down(self):

        # creating a frame for the listbox

        self.drop_down_frame = ctk.CTkFrame(self, corner_radius=10)
        self.drop_down_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(5, 5),
            pady=(5, 5),
        )
        self.drop_down_frame.grid_rowconfigure(0, weight=1)
        self.drop_down_frame.grid_columnconfigure(0, weight=1)

        # yscrollbar = Scrollbar(self.drop_down_frame)
        # yscrollbar.grid(row=0, column=1, sticky="nsew")
        self.drop_down = Listbox(
            self.drop_down_frame, selectmode="multiple"
        )

        self.drop_down.grid(row=0, column=0, sticky="nsew")
        for each_item in range(len(self.options)):

            self.drop_down.insert(END, self.options[each_item])
            self.drop_down.itemconfig(each_item)

        # # Attach listbox to vertical scrollbar
        # yscrollbar.config(command=self.drop_down.yview)

        # creating a frame for the buttoms

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=2, column=0, sticky="nsew", pady=(5, 5))

        # adding a apply button
        self.apply_button = ctk.CTkButton(
            self.button_frame, text="Apply", command=self.get
        )
        self.apply_button.grid(row=0, column=1, sticky="w", padx=(5, 5))

        # adding a clear button
        self.clear_button = ctk.CTkButton(
            self.button_frame, text="Clear", command=self.clear
        )
        self.clear_button.grid(row=0, column=0, sticky="e", padx=(5, 5))

        # getting the selected items

    def get(self):
        self.selected_values = [
            int(self.drop_down.get(idx)) for idx in self.drop_down.curselection()
        ]

        # self.selected_values_label.configure(text = "Selected Compounds: {}".format( ))
        # self.selected_values_label.delete(0.0, "end")
        # text = "Selected Values\n" + "\n".join(self.selected_values)
        # self.selected_values_label.insert("0.0", text)

        self.destroy()

    def clear(self):
        # clearing the selected items
        self.selected_values = []
        self.drop_down.destroy()
        self.create_drop_down()
 

class SpecificCluster(ctk.CTkFrame):

    """
    This class is used to display the specific cluster visualization

    It spins a seperate process to get the image data and displays it 
    To make the process faster, the image data is sent as bytes and displayed
    """
    def __init__(self, master, cluster, n_clusters, initial_choice=0):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=10)
        self.cluster_selection = None
        self.cluster = cluster
        self.initial_choice = initial_choice
        self.n_clusters = n_clusters
        self.queue = Queue()    
        
        self.cluster_image_label = None

        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")

        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.grid(row=1, column=0, sticky="nsew")


        self.cluster_image_label = ctk.CTkLabel(self.image_frame, text = '', width=630, height=350)
        self.cluster_image_label.grid(row=1, column=0, sticky="ew", )
        self.cluster_image_label.columnconfigure(0, weight=1)
        self.cluster_image_label.rowconfigure(0, weight=1)

        self.loading_label = ctk.CTkLabel(self.nav_frame, text="", text_color="yellow", width = 80)
        self.loading_label.grid(row=0, column=3, padx=(5,0), pady=8, sticky="w")
        self.after(500, self.prepare_specific_cluster_vis())

    def create_popup_drop_down(self):

        if self.cluster_selection is None or not self.cluster_selection.winfo_exists():
            self.cluster_selection = DropDownMulitSelect(
                self, self.clusters
            )
            self.update()
            self.after(100, self.cluster_selection.focus())
            
        else:
            self.cluster_selection.focus()

    
    def prepare_specific_cluster_vis(self):

        # a row to select the cluster
        # label = ctk.CTkLabel(self.nav_frame, text="Select Cluster :")
        # label.grid(row=0, column=0, padx=(5,0), pady=8, sticky="w")

        # _ = tk.StringVar(value='choose cluster to display')
        # a combo box to select the cluster
        self.clusters = [str(i) for i in range(self.n_clusters)]
        # self.cluster_selection = ctk.CTkComboBox(self.nav_frame,
        #                     values=clusters,
        #                     variable=_,
        #                     button_color="#b5b8b0",
        #                     command=self.display_specific_cluster
        #                     )
        # button to select clusters
        self.select_button = ctk.CTkButton(self.nav_frame, text="Select Clusters", command=self.create_popup_drop_down, fg_color='transparent', border_width=1)
        self.select_button.grid(row=0, column=1, padx=(5,0), pady=8, sticky="w")

        # adding a button to run the viz 
        self.run_button = ctk.CTkButton(self.nav_frame, text="run", command=self.display_specific_cluster, fg_color='transparent', border_width=1, width = 70)
        self.run_button.grid(row=0, column=2, padx=(5,0), pady=8, sticky="w")

        # adding loading label


        # self.cluster_selection.set(str(self.initial_choice))
        self.display_specific_cluster()

    def display_specific_cluster(self):

        if self.cluster_selection is not None:
            choice = self.cluster_selection.selected_values
        else:
            choice = list(np.random.choice(self.n_clusters, 3, replace=False))

        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()
        
        self.image_getter = Process(target=self.trigger_process_for_specific_cluster, args=(self.cluster, choice, 50, False, self.queue))
        self.image_getter.start()
        self.check_queue()

    def check_queue(self):
        if not self.queue.empty():
            image_data = self.queue.get()
            image_temp = Image.open(io.BytesIO(image_data))
            self.display_image(image_temp)
        if self.image_getter.is_alive():
            self.after(100, self.check_queue)
        else:
            self.image_getter.join()

    @staticmethod
    def trigger_process_for_specific_cluster(cluster, choice, size, show=False, queue=None):
        image_path = cluster.plot_select_cluster(choice,size=50,show=False)
        image = Image.open(image_path)
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            image_data = output.getvalue()
        queue.put(image_data)

    def display_image(self, image_data):

        ctk_image = ctk.CTkImage(light_image=image_data,
                                     dark_image=None, size = (400,300))
        self.cluster_image_label.configure(image=ctk_image)
        self.cluster_image_label.image = ctk_image

        self.loading_label.configure(text="")
        

        

        





        







import tkinter as tk
import customtkinter as ctk
import os
import logging
from multiprocessing import Process, Queue
import logging
from .timer import TimerApp
from SAMI.clustering import Cluster_Integration
from .display_image import ImageDisaplay
from .cluster_int_selective_clusters import ClusterIntSelectiveClusters
from PIL import Image
import scanpy as sc
import anndata
logger = logging.getLogger(__name__)

class ClusterIntergrationStep(ctk.CTkFrame):

    def __init__(self, master, file_handler, log_queue):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.isrendering = False
        self.file_handler = file_handler
        self.working_folder = os.path.join(*[file_handler.working_folder, 'results', 'clustering'])
        self.umap_overlay_label = None
        self.image_label = None
        self.queue = Queue()
        # self.trigger_visz_functions_on_thread_run()
        self.prepare_visualization_dock_type2()
        self.prep_cluster_int_options_tab()

    def prepare_visualization_dock_type2(self):
        """
        This function prepares the visualization dock for the cluster integration tab
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
        
        self.cluster_int_tab = self.vis_tabs.add("cluster Intergration")
        self.cluster_int_tab.columnconfigure(0, weight=1)
        self.cluster_int_tab.rowconfigure(0, weight = 1)
        self.cluster_int_tab.rowconfigure(1, weight = 20)
        self.cluster_int_tab.rowconfigure(2, weight = 20)


        # cluster options tab
        self.cluster_int_options = ctk.CTkFrame(self.cluster_int_tab, bg_color="transparent")
        self.cluster_int_options.grid(row=0, column=0, sticky="nsew")
        # self.cluster_int_options.columnconfigure(0, weight=1)
        # self.cluster_int_options.rowconfigure(0, weight=1)

        # region1
        self.type1 = ctk.CTkFrame(self.cluster_int_tab, bg_color="transparent")
        self.type1.grid(row=1, column=0, sticky="nsew")

        # region2
        self.type2 = ctk.CTkFrame(self.cluster_int_tab, bg_color="transparent")
        self.type2.grid(row=2, column=0, sticky="nsew")

        #adding a frame for the specific cluster selection
        self.specific_cluster_tab = self.vis_tabs.add("Selective Clusters")

        # Intergrated cluster overlay umap
        self.cluster_overlay_umap = self.vis_tabs.add("Umap Overlay")
        self.cluster_overlay_umap.columnconfigure(0, weight=1)
        self.cluster_overlay_umap.rowconfigure(0, weight = 1)

        self.umap_overlay_frame = ctk.CTkFrame(self.cluster_overlay_umap, bg_color="transparent")
        self.umap_overlay_frame.grid(row=0, column=0, sticky="nsew")
        self.umap_overlay_frame.columnconfigure(0, weight=1)
        self.umap_overlay_frame.rowconfigure(0, weight=1)

        logger.info("Prepared Visualization Dock")

    def refresh(self):
        "whenever the tab swtich happens this function updates the files available in dropdowns"


        files = os.listdir(self.working_folder)
        #files = [file for file in files if ('_pool') in file and ('h5ad' in file)]
        files = [file for file in files if (('h5ad' in file) and ('integrated' not in file))]

        self.region1_selection.configure(values=files)
        self.region2_selection.configure(values=files)
        logger.info("refreshed the dropdowns")  


    def prep_cluster_int_options_tab(self):
        
        self.cluster_int_options.columnconfigure(0, weight=5)
        self.cluster_int_options.columnconfigure(1, weight=5)
        self.cluster_int_options.columnconfigure(2, weight=5)
        self.cluster_int_options.columnconfigure(3, weight=5)
        self.cluster_int_options.columnconfigure(4, weight=5)
        self.cluster_int_options.columnconfigure(5, weight=5)
        self.cluster_int_options.columnconfigure(6, weight=100)
        self.cluster_int_options.rowconfigure(0, weight=1)

        # getting the clustered files
        files = os.listdir(self.working_folder)
        #files = [file for file in files if ('_pool') in file and ('h5ad' in file)]
        files = [file for file in files if (('h5ad' in file) and ('integrated' not in file))]

        # region selection 1
        region1_label = ctk.CTkLabel(self.cluster_int_options, text="Select Region1 :" )
        region1_label.grid(row=0,column=0,padx=(5,0),pady=8,sticky="w")
        
        _ = tk.StringVar(value='choose file')
        self.region1_selection = ctk.CTkComboBox(master= self.cluster_int_options,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.region1_selection.grid(row=0,column=1,padx=(10,0),pady=8,sticky="w")

        # region selection 2
        region1_labe2 = ctk.CTkLabel(self.cluster_int_options, text="Select Region2 :" )
        region1_labe2.grid(row=0,column=2,padx=(20,0),pady=8,sticky="w")
        
        _ = tk.StringVar(value='choose file')
        self.region2_selection = ctk.CTkComboBox(master= self.cluster_int_options,
                                            values=files,
                                            variable=_,
                                            button_color="#b5b8b0",
                                            width = 250
                                            )
        self.region2_selection.grid(row=0,column=3,padx=(10,0),pady=8,sticky="w")

        self.cluster_button = ctk.CTkButton(self.cluster_int_options,text="Run Intergration",command=self.perform_clustering)
        self.cluster_button.grid(row=0,column=4,padx=(20,0),pady=8,sticky="w")

        # timer button
        self.timer = TimerApp(self.cluster_int_options)
        self.timer.grid(row=0,column=5,padx=(50,0),pady=8,sticky="w")

        # time constraint
        self.time_constraint_label = ctk.CTkLabel(self.cluster_int_options, text="Note : cluster Integration takes roughly 10 minutes", text_color="yellow", width=300)
        self.time_constraint_label.grid(row=0,column=6,padx=(10,0),pady=8,sticky="e")

        logger.info("Prepared Cluster Integration Options Tab")

    def prep_specific_cluster_tab(self):
        # For the selective cluster tab
        for child in self.specific_cluster_tab.winfo_children():
            child.destroy()
        self.specific_cluster = ClusterIntSelectiveClusters(self.specific_cluster_tab, 
                                                            self.cluster_int, self.n_clusters,
                                                              (self.region1, self.modality1, self.res1),
                                                              (self.region2, self.modality2, self.res2),
                                                              self.log_queue)
        
        self.specific_cluster.grid(row=0, column=0, sticky="nsew", padx=(3,3), pady=(3,3))

        logger.info("Prepared Specific Cluster Tab")    

        

    @staticmethod
    def splitname(adata):
        # name,_ = os.path.splitext(adata)
        # region, modality, resolution = name.split('_')
        # return region, modality, resolution
        # changed for GUI braoder handling
        # cerebellum_2_WT_lip_1.0.h5ad
        name = adata.replace('.h5ad', '')
        #region, modality, resolution = name.split('_')
        resolution = name.split('_')[-1]
        modality = name.split('_')[-2]
        region = '_'.join(name.split('_')[:-2])
        logger.info(f"region : {region}, modality : {modality}, resolution : {resolution}")

        return region, modality, resolution
    
    def prepare_cluster_module(self, ):

        """This function prepares the cluster integration module"""

        self.region1, self.modality1, self.res1 = self.splitname(self.region1_selection.get())
        self.region2, self.modality2, self.res2 = self.splitname(self.region2_selection.get())
        self.clusterInt_specific_working_folder = os.path.join(*[self.working_folder, f"{self.region1}-{self.modality1}-{self.res1}__{self.region2}-{self.modality2}-{self.res2}__integrated"])
        if not os.path.exists(self.clusterInt_specific_working_folder):
            os.makedirs(self.clusterInt_specific_working_folder)

        self.integrated_file1 = os.path.join(self.clusterInt_specific_working_folder, f"{self.region1}-{self.modality1}-{self.res1}_integrated.h5ad")
        self.integrated_file2 = os.path.join(self.clusterInt_specific_working_folder, f"{self.region2}-{self.modality2}-{self.res2}_integrated.h5ad")

        logger.info(f"path Integrated file 1 : {self.integrated_file1}")
        logger.info(f"path Integrated file 2 : {self.integrated_file2}")

        
        cluster_int = Cluster_Integration(self.region1_selection.get(), self.region2_selection.get(), self.working_folder, 
                                          self.clusterInt_specific_working_folder, self.log_queue)

        # try:    
        #     adata1 = sc.read(r"C:\Users\ghari\Documents\OPS\Test_folders\original_data_test\AD_WT\results\clustering\brain1wt_pool_1.0.h5ad")
        #     adata2 = sc.read(r"C:\Users\ghari\Documents\OPS\Test_folders\original_data_test\AD_WT\results\clustering\brain1ad_pool_1.0.h5ad")
        #     var_names = adata1.var_names.intersection(adata2.var_names)
        #     adata1.obs['sample'] = "brain1wt"
        #     adata2.obs['sample'] = "brain1ad"
        #     logger.info("adata1 {}".format(str(adata1)))
        #     logger.info("adata2 {}".format(str(adata2)))

        #     logger.info("integrating outside process started")
        #     sc.tl.ingest(adata1,adata2,obs='leiden')
        #     logger.info("integration outside process ended")

        #     logger.info("adata1 {}".format(str(adata1)))
        #     logger.info("adata2 {}".format(str(adata2)))
        # except Exception as e:
        #     logger.error(f"error in reading the files : {e}")
        
        return cluster_int
    
    @staticmethod
    def clusterintegration(queue, cluster_int, integrated_file1, integrated_file2, region1, modality1, res1, region2, modality2, res2):
        
        response_dict = {}
        # checking whether the clustering is already performed or not
        if not (os.path.exists(integrated_file1) and os.path.exists(integrated_file2)):
            logger.info("didnt find any existing file, Performing Integration")
            cluster_int.integrate()
        else:
            logger.info("Clustering already done")

        image_location1, n_clusters = cluster_int.plot_umap_cluster(region1, modality1, res1 ,size=50,show=False)
        image_location2, n_clusters = cluster_int.plot_umap_cluster(region2 ,modality2, res2 , size=50,show=False)

        response_dict['image_location1'] = image_location1
        response_dict['image_location2'] = image_location2
        response_dict['n_clusters'] = n_clusters
        # sending a message to the queue that thread is completed
        logger.info("sending signal to the queue")
        queue.put(response_dict)
        logger.info("signal sent to the queue")
        logger.info("messages in queue : {}".format(queue.qsize()))

    def perform_clustering(self):
        self.timer.reset_timer()
        self.timer.start_timer()
        self.cluster_int = self.prepare_cluster_module()
        self.time_constraint_label.configure(text="Note : cluster Integration usally takes roughly 10 minutes")

        # image_location1, self.n_clusters = self.cluster_int.plot_umap_cluster(region ,size=50,show=False)
        # image_location2, self.n_clusters = self.cluster_int.plot_umap_cluster(region ,size=50,show=False)
        logger.info("started the clustering process")
        self.clustering_process = Process(target=self.clusterintegration, args=(self.queue, self.cluster_int, 
                                                                   self.integrated_file1, self.integrated_file2,
                                                                   self.region1,self.modality1,self.res1,
                                                                    self.region2, self.modality2, self.res2), name = "SAMI:cluster_integration")
        self.clustering_process.start()
        self.trigger_visz_functions_on_thread_run()


    def trigger_visz_functions_on_thread_run(self):
        
        logger.info("checking the queue")
        if not self.queue.empty():
            try:
                logger.info("clustering interation compelete message received from process")
                message = self.queue.get()
                self.image_location1 = message['image_location1']
                self.image_location2 = message['image_location2']
                self.n_clusters = message['n_clusters']
                self.prepare_cluster_visualization()
                self.dsplay_umpa_overlay()
                self.prep_specific_cluster_tab()
                self.timer.stop_timer()
                self.time_constraint_label.configure(text="Clustering Intergration Completed", text_color="green")
                logger.info("clustering interation compelete")
            except Exception as e:
                logger.error(f"error in getting the message from the queue : {e}")
            finally:
                self.after(10000, self.trigger_visz_functions_on_thread_run)

        if self.clustering_process.is_alive():
            self.after(10000, self.trigger_visz_functions_on_thread_run)
        else:
            self.clustering_process.join()

    def prepare_cluster_visualization(self):

        logging.info("Preparing cluster visualization")

        for child in self.type1.winfo_children():
            child.destroy() 

        for child in self.type2.winfo_children():
            child.destroy() 

        self.type1.columnconfigure(0, weight=1)
        self.type1.columnconfigure(1, weight=9)
        # region1 display
        region_label_frame = ctk.CTkFrame(self.type1, bg_color="transparent")
        region_label_frame.grid(row=0, column=0, sticky="nsew", padx=(5,5) , pady = 0)
        region_label_frame.columnconfigure(0, weight=1)
        region_label_frame.rowconfigure(0, weight=1)
        
        type1_display_frame = ctk.CTkFrame(self.type1, bg_color="transparent")
        type1_display_frame.grid(row=0, column=1, sticky="sew", padx=(5,0) , pady = (2,2))
        type1_display_frame.columnconfigure(0, weight=1)
        type1_display_frame.rowconfigure(0, weight=1)

        #values
        region1_label = ctk.CTkLabel(region_label_frame, text="Region 1 :")
        region1_label.grid(row=0, column=0, padx=(5,0), pady=2, sticky="w")

        image_display = ImageDisaplay(type1_display_frame, self.image_location1)
        image_display.grid(row=0, column=0, sticky="nsew", padx=(5,0) , pady = (2,2))
        image_display.columnconfigure(0, weight=1)
        image_display.rowconfigure(0, weight=1)

        self.type2.columnconfigure(0, weight=1)
        self.type2.columnconfigure(1, weight=9)

        # region2 display

        #frames
        region_label_frame2 = ctk.CTkFrame(self.type2, bg_color="transparent")
        region_label_frame2.grid(row=0, column=0, sticky="nsew", padx=(5,5) , pady = (2,2)) 
        region_label_frame2.columnconfigure(0, weight=1)
        region_label_frame2.rowconfigure(0, weight=1)

        type2_display_frame = ctk.CTkFrame(self.type2, bg_color="transparent")
        type2_display_frame.grid(row=0, column=1, sticky="sew", padx=(5,0) , pady = (2,2))
        type2_display_frame.columnconfigure(0, weight=1)
        type2_display_frame.rowconfigure(0, weight=1)

        #values
        region2_label = ctk.CTkLabel(region_label_frame2, text="Region 2 :")
        region2_label.grid(row=0, column=0, padx=(5,0), pady=2, sticky="w")

        image_display2 = ImageDisaplay(type2_display_frame, self.image_location2)
        image_display2.grid(row=0, column=0, sticky="nsew", padx=(5,0) , pady = 0)
        image_display2.columnconfigure(0, weight=1)
        image_display2.rowconfigure(0, weight=1)

    def dsplay_umpa_overlay(self):

        logging.info("Displaying Umap Overlay")
        
        for child in self.umap_overlay_frame.winfo_children(): 
            child.destroy()

        # a label for the image
        self.umap_overlay_label = ctk.CTkLabel(self.umap_overlay_frame, width=1000, height=700)
        self.umap_overlay_label.grid(row=0, column=0, sticky="ew", )
        self.umap_overlay_label.columnconfigure(0, weight=1)
        self.umap_overlay_label.rowconfigure(0, weight=1)

        # attaching image to the label
        image_location = self.cluster_int.plot_overlap_umap(show=False)
        ctk_image = ctk.CTkImage(light_image=Image.open(image_location),
                                     dark_image=None, size = (1000,700))
        self.umap_overlay_label.configure(image=ctk_image)
        self.umap_overlay_label.image = ctk_image

       


        

        





        







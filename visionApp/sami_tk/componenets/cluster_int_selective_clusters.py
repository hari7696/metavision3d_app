import customtkinter as ctk
import tkinter as tk
from PIL import Image
from multiprocessing import Queue, Process
import io
import logging
import numpy as np
from tkinter import Listbox, END
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class ClusterIntSelectiveClusters(ctk.CTkFrame):

    """
    This class is used to display the selective clusters for a given region

    Its a part of of the cluster Intergration tab (selective clusters) in the SAMI app
    """

    def __init__(self, master, cluster_int, n_clusters, region1, region2, log_queue=None):
        super().__init__(
            master,
        )
        self.cluster_int = cluster_int
        self.cluster_int = cluster_int
        self.n_clusters = n_clusters
        self.region1, self.modality1, self.res1 = region1
        self.region2, self.modality2, self.res2 = region2
        self.log_queue = log_queue
        self.create_layout()
        self.after(500, self.prepare_specific_cluster_vis(self.region1_frame, self.region1, self.modality1, self.res1))
        self.after(500, self.prepare_specific_cluster_vis(self.region2_frame, self.region2, self.modality2, self.res2))

    def create_layout(self):

        self.parent_frame = ctk.CTkFrame(self)
        self.parent_frame.grid(row=0, column=0, sticky="nsew")
        self.parent_frame.columnconfigure(0, weight=1)
        self.parent_frame.rowconfigure(0, weight=1)
        self.parent_frame.rowconfigure(1, weight=1)

        # row 1 
        self.region1_frame = ctk.CTkFrame(self.parent_frame, bg_color="transparent")
        self.region1_frame.grid(row=0, column=0, sticky="nsew", padx=(5,5) , pady = 0)
        self.region1_frame.columnconfigure(0, weight=1)
        self.region1_frame.rowconfigure(1, weight=9)
        self.region1_frame.rowconfigure(0, weight=1)
        # region_label_frame.columnconfigure(0, weight=1)
        # region_label_frame.rowconfigure(0, weight=1)

        # row 2
        self.region2_frame = ctk.CTkFrame(self.parent_frame, bg_color="transparent")
        self.region2_frame.grid(row=1, column=0, sticky="nsew", padx=(5,5) , pady = (2,2)) 
        self.region2_frame.columnconfigure(0, weight=1)
        self.region2_frame.rowconfigure(1, weight=9)
        self.region2_frame.rowconfigure(0, weight=1)


    def prepare_specific_cluster_vis(self, frame, region, modality, res):

        for child in frame.winfo_children():
            child.destroy()


        left_frame = ctk.CTkFrame(frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(3,3), pady=(3,3))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        right_frame = ctk.CTkFrame(frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(3,3), pady=(3,3))

        # adding a region label to the left frame   
        region_label = ctk.CTkLabel(left_frame, text = region)
        region_label.grid(row=0, column=0, sticky="nsew")
        region_label.columnconfigure(0, weight=1)
        region_label.rowconfigure(0, weight=1)

        # adding a specific cluster frame to the right frame
        right_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(1, weight=1)
        right_frame.columnconfigure(2, weight=1)
        right_frame.rowconfigure(0, weight=1)

        specific_cluster1 = SpecificCluster(right_frame, self.cluster_int, self.n_clusters, region, modality, res, 0, self.log_queue)
        specific_cluster1.grid(row=0, column=0, sticky="nsew", padx=(3,3), pady=(3,3))

        specific_cluster2 = SpecificCluster(right_frame, self.cluster_int, self.n_clusters, region, modality, res, 1, self.log_queue)
        specific_cluster2.grid(row=0, column=1, sticky="nsew", padx=(3,3), pady=(3,3))

        specific_cluster3 = SpecificCluster(right_frame, self.cluster_int, self.n_clusters, region, modality, res, 2, self.log_queue)
        specific_cluster3.grid(row=0, column=2, sticky="nsew", padx=(3,3), pady=(3,3))

        logger.info(f"Prepared specific cluster vis for {region}")

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
    def __init__(self, master, cluster, n_clusters, region,modality, res, initial_choice=0 , log_queue=None):
        super().__init__(
            master,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=10)
        self.cluster = cluster
        self.cluster_selection = None
        self.n_clusters = n_clusters
        self.initial_choice = initial_choice    
        self.region = region
        self.modality = modality
        self.res = res
        self.queue = Queue()
        self.log_queue = log_queue
        
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
        # # a combo box to select the cluster
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

        self.display_specific_cluster()

        # label = ctk.CTkLabel(self.nav_frame, text="Select Cluster :")
        # label.grid(row=0, column=2, padx=(5,0), pady=8, sticky="w")

    def display_specific_cluster(self):

        self.loading_label.configure(text="Loading...", text_color="yellow")
        self.update()

        if self.cluster_selection is not None:
            choice = self.cluster_selection.selected_values
        else:
            choice = list(np.random.choice(self.n_clusters, int(np.random.randint(1,5)), replace=False))
        # attaching image to the label
        #integration.plot_select_cluster('cerebellumNPC1',cluster=i, size=60, show=False)
        # image_location = self.cluster.plot_select_cluster(self.region,int(choice),size=60,show=False)

        self.image_getter = Process(target=self.trigger_process_for_specific_cluster, args=(self.cluster, self.region, self.modality, self.res, choice, 60, False, self.queue))
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
    def trigger_process_for_specific_cluster(cluster, region,modality, res, choice, size=60, show=False, queue=None):
        image_path = cluster.plot_select_cluster(region,modality, res ,choice,size=size,show=False)
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

        


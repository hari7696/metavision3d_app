import customtkinter as ctk
import logging
from .file_handler import FileOpenbutton
from .visualization_step import VisualizationStep
from .normalization_step import NormalizationStep
from .pooling_step import PoolingStep
from .clustering_step import ClusteringStep
from .cluster_intergration_step import ClusterIntergrationStep
from .markers_step import MarkerStep
from .pathways_step import PathwaysStep
import sys
import queue
sys.path.append('../SAMI')
logger = logging.getLogger(__name__)


class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.nav_frame = nav_frame
        self.process_step = None
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.queue = queue.Queue()
        logger.debug("SAMI class initialized")
        # this functions check for messages from file handler, whenever the use opens files, it will refreshes the visualization tab
        self.check_for_file_load()

        # for the SAMI UI, we need to choose whether the processing needs to be done on single file or multiple files

        file_type_variable = ctk.StringVar(value="Single/Multi file?")
        self.dropdown_file_type_single_multi = ctk.CTkOptionMenu(
            self.nav_frame,
            values=["Single file", "Multi file"],
            command=self.file_open,
            variable=file_type_variable,
        )
        self.dropdown_file_type_single_multi.grid(
            row=0, column=1, padx=(5, 0), pady=(2, 2), sticky="w"
        )

        self.create_process_bar()
        logger.debug(
            f"Number of children in nav_frame: { len(self.nav_frame.winfo_children())}"
        )
        logger.debug(
            "Number of children in parent: {}".format(len(list(self.winfo_children())))
        )
        self.create_parent_tab_switch()
        # self.create_visualization_dock()
        # self.create_left_visualization_dock()

    def file_open(self, choice):
        self.file_handler = FileOpenbutton(self.nav_frame, self.queue)
        self.file_handler.file_opening_button(choice)
        self.file_handler.grid(row=0, column=2, padx=(5, 5), pady=(2, 2), sticky="w", columnspan=2)
        self.file_handler.columnconfigure(0, weight=1)
        self.file_handler.columnconfigure(1, weight=1)
        # updating the process bar based on the file type selected
        self.create_process_bar()

    def check_for_file_load(self):

        # check the queue for messages  
        try:
            logger.info("messages in queue : {}".format(self.queue.qsize()))
            signal = self.queue.get_nowait()
            if signal == "loaded_files":
                logger.info("file load thread trigger received")
                # print("HIT")
                self.process_step.set("Visualization")
                # self.after(100, self.process_step.invoke())
                self.execute_selected_step("Visualization")
                
        except Exception as e:
            logger.error(e)
        finally:
            # Schedule the next queue check
            self.after(1000, self.check_for_file_load)
            # logger.info("checking the queue")


    def create_process_bar(self):
        """Bar in the NavFrame to show the process steps
        This bar is gonna trigger the process steps
        """
        # destroying the existing process bar, before creating a new one. The initial value of of process_step is None
        for widget in self.nav_frame.winfo_children():
            if widget == self.process_step:
                widget.destroy()

        logger.debug(
            "value in dropdown:{}".format(self.dropdown_file_type_single_multi.get())
        )
        # multi file process steps
        values = [
            "Visualization",
            "Normalization",
            "Pooling",
            "Clustering",
            "Clusters Integration",
            "Markers",
            "Pathways",
        ]

        if self.dropdown_file_type_single_multi.get() == "Single file":
            values = [
            "Visualization",
            "Normalization",
            "Pooling",
            "Clustering",
            "Markers",
            "Pathways",
            ]

        self.process_step = ctk.CTkSegmentedButton(
            master=self.nav_frame, values=values, command=self.execute_selected_step
        )
        self.process_step.grid(
            row=0, column=4, padx=(5, 5), pady=(2, 2), sticky="w"
        )

    def create_parent_tab_switch(self):
        """Parent Tab consists of Visualization and Export tabs"""

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.parent_tab_switch = ctk.CTkTabview(self, bg_color="transparent")
        self.parent_tab_switch.columnconfigure(0, weight=1)
        self.parent_tab_switch.rowconfigure(0, weight=1)

        self.visualization_tab = self.parent_tab_switch.add("Visualization")
        self.export_tab = self.parent_tab_switch.add("Export")

        self.visualization_tab.columnconfigure(0, weight=1)
        self.visualization_tab.rowconfigure(0, weight=1)

        # it goes to parent frame row 1
        self.parent_tab_switch.grid(row=0, column=0, sticky="new", padx=5)


    def execute_selected_step(self, choice):
        """
        This functions acts as a key trigger for the process steps
        It controls the right framme of the visualization tab

        """

        logger.info(f"Processing step: {choice}")
        # tabview visualization on the right frame

        if choice == "Visualization":

            self.vis_step = VisualizationStep(self.visualization_tab, self.file_handler)
            self.vis_step.columnconfigure(0, weight=1)
            self.vis_step.rowconfigure(0, weight=1)
            self.vis_step.grid(row=0, column=0, sticky="nsew")

        elif choice == "Normalization":

            self.norm_step = NormalizationStep(self.visualization_tab, self.file_handler)
            self.norm_step.columnconfigure(0, weight=1)
            self.norm_step.rowconfigure(0, weight=1)
            self.norm_step.grid(row=0, column=0, sticky="nsew")
            # self.norm_plot.columnconfigure(0,weight=1)
            # self.norma_regions.columnconfigure(0,weight=1)

        elif choice == "Pooling":
            self.pooling_step = PoolingStep(self.visualization_tab, self.file_handler)
            self.pooling_step.columnconfigure(0, weight=1)  
            self.pooling_step.rowconfigure(0, weight=1)
            self.pooling_step.grid(row=0, column=0, sticky="nsew")

            # self.pooling.columnconfigure(0,weight=1)

        elif choice == "Clustering":

            self.clustering_step = ClusteringStep(self.visualization_tab, self.file_handler)
            self.clustering_step.columnconfigure(0, weight=1)  
            self.clustering_step.rowconfigure(0, weight=1)
            self.clustering_step.grid(row=0, column=0, sticky="nsew")

            # self.clustering.columnconfigure(0,weight=1)
        elif choice == "Clusters Integration":

            self.clustering_step = ClusterIntergrationStep(self.visualization_tab, self.file_handler)
            self.clustering_step.columnconfigure(0, weight=1)  
            self.clustering_step.rowconfigure(0, weight=1)
            self.clustering_step.grid(row=0, column=0, sticky="nsew")

        elif choice == "Markers":
            self.clustering_step = MarkerStep(self.visualization_tab, self.file_handler)
            self.clustering_step.columnconfigure(0, weight=1)  
            self.clustering_step.rowconfigure(0, weight=1)
            self.clustering_step.grid(row=0, column=0, sticky="nsew")

        elif choice == "Pathways":
            
            self.clustering_step = PathwaysStep(self.visualization_tab, self.file_handler)
            self.clustering_step.columnconfigure(0, weight=1)  
            self.clustering_step.rowconfigure(0, weight=1)
            self.clustering_step.grid(row=0, column=0, sticky="nsew")

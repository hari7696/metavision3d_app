import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import logging
from .componenets.file_handler import FileOpenbutton
from .componenets.visualization_step import VisualizationStep
from .componenets.normalization_step import NormalizationStep
from .componenets.pooling_step import PoolingStep
from .componenets.clustering_step import ClusteringStep
from .componenets.cluster_intergration_step import ClusterIntergrationStep
from .componenets.markers_step import MarkerStep
from .componenets.pathways_step import PathwaysStep
from .componenets.grouping_step import GroupingStep
from .componenets.ScilsExport import ScilsExportStep
from .componenets.tissue_picker_step import TissuePicker
import sys
import queue
sys.path.append('../SAMI')
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
class SAMIApp(ctk.CTkFrame):
    def __init__(self, master, nav_frame, algo_drop_down, log_queue):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.columnconfigure(0, weight=1)
        self.nav_frame = nav_frame
        self.process_step = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.queue = queue.Queue()
        self.file_loading_status = False
        self.algo_drop_down = algo_drop_down    
        logger.debug("SAMI class initialized")

        file_type_variable = ctk.StringVar(value="File Type")
        self.dropdown_file_type_single_multi = ctk.CTkOptionMenu(
            self.nav_frame,
            values=[ "CSV", "Scils"],
            command=self.file_open,
            variable=file_type_variable,
        )
        self.dropdown_file_type_single_multi.grid(
            row=0, column=1, padx=(5, 0), pady=(2, 2), sticky="w"
        )
        self.steps = {} 
        self.loaded_steps = {}
        self.file_handler = None
        self.create_process_bar()
        logger.debug(
            f"Number of children in nav_frame: { len(self.nav_frame.winfo_children())}")
        logger.debug(
            "Number of children in parent frame: {}".format(len(list(self.winfo_children()))))
        self.create_parent_tab_switch()
        # self.create_visualization_dock()
        # self.create_left_visualization_dock()
        self.check_for_file_load()
        self.initialize_step_constructor()
 

    def file_open(self, choice):

        for child in self.nav_frame.winfo_children():
            if (child != self.dropdown_file_type_single_multi) and (child != self.algo_drop_down):
                child.destroy()

        if self.dropdown_file_type_single_multi.get() == "Scils":
            self.create_process_bar()
            self.process_step.set("ScilsExport")
            self.execute_selected_step("ScilsExport")
            return
        
            

        self.file_handler = FileOpenbutton(self.nav_frame, self.queue)
        self.file_handler.file_opening_button(choice)
        self.file_handler.grid(row=0, column=2, padx=(5, 5), pady=(2, 2), sticky="w", columnspan=2)
        self.file_handler.columnconfigure(0, weight=1)
        self.file_handler.columnconfigure(1, weight=1)
        logger.info(f"File handler created")
        # updating the process bar based on the file type selected
        self.create_process_bar()

    def check_for_file_load(self):

        """
        whenever the file handler sends a message, this function will be triggered
        When the file load happens, the process steps need to be deleted and reinitialized,
        other the count of frames will increase and the memory will be wasted by retaining the old frames

        This functions kinds of acts like a messaging service, the moment it recievies messages from
        the file handler, it destroys the old process steps and calls the visualization step
        """
        try:
            if not self.queue.empty():
                message = self.queue.get()
                logger.info("file load thread trigger received")
                # print("HIT")
                # when the file switch happens we need to reinitialize the process steps, the old views are not automatically destroyed,
                # so we need to destroy them manually
                for step in self.loaded_steps.values():
                    step.destroy()
                self.file_loading_status = False
                self.loaded_steps = {}
                self.file_loading_status = True
                self.process_step.set("Visualization")
                self.initialize_step_constructor()
                # self.after(100, self.process_step.invoke())
                self.execute_selected_step("Visualization")
            # Schedule the next queue check
        except Exception as e:
            logger.error(f"Error in check_for_file_load: {e}")
            logger.info(f" File reading status {self.file_handler.is_files_read}" )
        finally:
            self.after(100, self.check_for_file_load)

        
    def create_process_bar(self):
        """
        Bar in the NavFrame to show the process steps
        This bar is gonna trigger the process steps
        """
        # destroying the existing process bar, before creating a new one. The initial value of of process_step is None
        for widget in self.nav_frame.winfo_children():
            if widget == self.process_step:
                widget.destroy()

        logger.debug(
            "value in dropdown:{}".format(self.dropdown_file_type_single_multi.get())
        )
        # Multiple CSV process steps
        values = [
            "Visualization",
            "Normalization",
            "Pooling",
            "Grouping",
            "Clustering",
            "Clusters Integration",
            # "Tissue Pick",
            "Markers",
            "Pathways",
        ]

        if self.dropdown_file_type_single_multi.get() == "Single CSV":
            values = [
            "Visualization",
            "Normalization",
            "Pooling",
            "Grouping",
            "Clustering",
            # "Tissue Pick",
            "Markers",
            "Pathways",
            ]

        if self.dropdown_file_type_single_multi.get() == "Scils":

            values = ["ScilsExport"]


        self.process_step = ctk.CTkSegmentedButton(
            master=self.nav_frame, values=values, command=self.execute_selected_step, font = ("Arial", 14)
        )
        self.process_step.grid(
            row=0, column=4, padx=(5, 5), pady=(2, 2), sticky="w"
        )

    def initialize_step_constructor(self):
        """
        This function initializes the steps constructor
        """

        self.steps = {
            "Visualization": (VisualizationStep, self.file_handler, self.log_queue),
            "Normalization": (NormalizationStep, self.file_handler,  self.log_queue),
            "Pooling": (PoolingStep, self.file_handler, self.log_queue),
            "Grouping": (GroupingStep, self.file_handler, self.log_queue),
            "Clustering": (ClusteringStep, self.file_handler, self.log_queue),
            "Clusters Integration": (ClusterIntergrationStep, self.file_handler, self.log_queue),
            # "Tissue Pick" : (TissuePicker, self.file_handler, self.log_queue),
            "Markers": (MarkerStep, self.file_handler, self.log_queue),
            "Pathways": (PathwaysStep, self.file_handler, self.log_queue),
            "ScilsExport": (ScilsExportStep, self.file_handler, self.log_queue)
        }

    def initialize_step(self, step_name):

        """Initialize a step only if it has not been created yet."""
        if step_name not in self.loaded_steps:
            # Create the step using the constructor and parameters stored in `steps`
            step = self.steps[step_name][0](self.visualization_tab, *self.steps[step_name][1:])
            step.columnconfigure(0, weight=1)
            step.rowconfigure(0, weight=1)
            step.grid(row=0, column=0, sticky="nsew")
            step.columnconfigure(0, weight=1)
            step.rowconfigure(0, weight=1)
            self.loaded_steps[step_name] = step
        return self.loaded_steps[step_name]

    def create_parent_tab_switch(self):
        """Parent Tab consists of Visualization and Export tabs
            Visualization tab is the main tab where all the processing steps are done
            Export tab is the tab where the user can export the results

            But the requirement is changed now, so I deleted the Export tab and the made the original frame as the parent tab
        """

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.visualization_tab = ctk.CTkFrame(self, bg_color="transparent")
        self.visualization_tab.columnconfigure(0, weight=1)
        self.visualization_tab.rowconfigure(0, weight=1)
        # it goes to parent frame row 1
        self.visualization_tab.grid(row=0, column=0, sticky="new", padx=(5,5), pady=(5,5))

    def execute_selected_step(self, choice):
        """This finctions is the key trigger for the process steps
            It forgets the previous steps and shows the selected step
            It also initailizes the step if it has not been created yet"""

        if self.file_loading_status == False and self.dropdown_file_type_single_multi.get() != "Scils":
            logger.info("Please load the files first")
            CTkMessagebox(title="Info", message="Select files and wait till the file loading is complete")
            return

        step = self.initialize_step(choice)
        # Hide all steps
        for s in self.loaded_steps.values():
            s.grid_remove()
        # Show the selected step
        step.refresh()
        step.grid(row=0, column=0, sticky="nsew")
        step.columnconfigure(0, weight=1)
        step.rowconfigure(0, weight=1)


    # def execute_selected_step(self, choice):
    #     """
    #     This functions acts as a key trigger for the process steps
    #     It controls the right framme of the visualization tab

    #     """
    #     for step in self.steps.values():
    #         step.grid_remove()

    #     logger.info(f"Processing step: {choice}")
    #     # tabview visualization on the right frame

    #     if choice == "Visualization":

    #         # self.vis_step = VisualizationStep(self.visualization_tab, self.file_handler)
    #         # self.vis_step.columnconfigure(0, weight=1)
    #         # self.vis_step.rowconfigure(0, weight=1)
    #         self.steps["Visualization"].grid(row=0, column=0, sticky="nsew")

    #     elif choice == "Normalization":

    #         # self.norm_step = NormalizationStep(self.visualization_tab, self.file_handler)
    #         # self.norm_step.columnconfigure(0, weight=1)
    #         # self.norm_step.rowconfigure(0, weight=1)
    #         self.steps["Normalization"].grid(row=0, column=0, sticky="nsew")
    #         # self.norm_plot.columnconfigure(0,weight=1)
    #         # self.norma_regions.columnconfigure(0,weight=1)

    #     elif choice == "Pooling":
    #         # self.pooling_step = PoolingStep(self.visualization_tab, self.file_handler)
    #         # self.pooling_step.columnconfigure(0, weight=1)  
    #         # self.pooling_step.rowconfigure(0, weight=1)
    #         self.steps["Pooling"].grid(row=0, column=0, sticky="nsew")

    #         # self.pooling.columnconfigure(0,weight=1)

    #     elif choice == "Clustering":

    #         # self.clustering_step = ClusteringStep(self.visualization_tab, self.file_handler)
    #         # self.clustering_step.columnconfigure(0, weight=1)  
    #         # self.clustering_step.rowconfigure(0, weight=1)
    #         self.steps["Clustering"].grid(row=0, column=0, sticky="nsew")

    #         # self.clustering.columnconfigure(0,weight=1)
    #     elif choice == "Clusters Integration":

    #         # self.clustering_step = ClusterIntergrationStep(self.visualization_tab, self.file_handler)
    #         # self.clustering_step.columnconfigure(0, weight=1)  
    #         # self.clustering_step.rowconfigure(0, weight=1)
    #         self.steps["Clusters Integration"].grid(row=0, column=0, sticky="nsew")

    #     elif choice == "Markers":
    #         # self.clustering_step = MarkerStep(self.visualization_tab, self.file_handler)
    #         # self.clustering_step.columnconfigure(0, weight=1)  
    #         # self.clustering_step.rowconfigure(0, weight=1)
    #         self.steps["Markers"].grid(row=0, column=0, sticky="nsew")

    #     elif choice == "Pathways":
            
    #         # self.clustering_step = PathwaysStep(self.visualization_tab, self.file_handler)
    #         # self.clustering_step.columnconfigure(0, weight=1)  
    #         # self.clustering_step.rowconfigure(0, weight=1)
    #         self.steps["Pathways"].grid(row=0, column=0, sticky="nsew")

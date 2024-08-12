import logging
import time
import customtkinter as ctk
import os
import pandas as pd 
from multiprocessing import Process, Queue
from SAMI.utils import adata_concat
from .timer import TimerApp
from log_listener import worker_configurer
from multiprocessing import Queue, Process
from CTkMessagebox import CTkMessagebox
import scanpy as sc
from log_listener import worker_configurer
logger = logging.getLogger(__name__)
# logger = logging.getLogger(__name__)

class GroupingStep(ctk.CTkFrame):

    """
    This class is used for the Grouping step of the SAMI app
    """

    def __init__(self, master, file_handler, log_queue):
        super().__init__(
            master,
        )
        self.log_queue = log_queue
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.file_handler = file_handler    
        self.queue = Queue()
        self.log_queue = log_queue
        self.prepare_visualization_dock_type2()
        self.creating_grouping_tab()
        # self.check_queue()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

    def refresh(self):
        "whenever the tab swtich happens this function updates the files available in dropdowns"
        for child in self.grouping_frame.winfo_children():
            child.destroy()
        self.create_grouping_widget()


    def prepare_visualization_dock_type2(self):
        """
        This function is used to prepare the visualization dock for the app
        This dock is different from the one used in earlier steps like visualization and normalization
        There is no left and right frame, only one frame is used
        """

        for child in self.winfo_children():
            child.destroy()

        self.root_visualization_frame = ctk.CTkFrame(self, bg_color="transparent")
        self.root_visualization_frame.columnconfigure(0, weight=1)
        self.root_visualization_frame.rowconfigure(0, weight=1)
        self.root_visualization_frame.grid(row=0, column=0, sticky="nsew")

        self.vis_tabs = ctk.CTkTabview(self.root_visualization_frame)
        self.vis_tabs.grid(row=0, column=0, sticky="new", padx=5)
        self.vis_tabs.columnconfigure(0, weight=1)
        self.vis_tabs.rowconfigure(0, weight=1)

    def creating_grouping_tab(self):

        "This function is used to create the grouping tab in the app"

        self.grouping_tab = self.vis_tabs.add("Grouping")
        self.grouping_tab.columnconfigure(0, weight=1)
        self.grouping_tab.rowconfigure(0, weight=1)

        self.grouping_frame = ctk.CTkFrame(self.grouping_tab)
        self.grouping_frame.grid(row=0, column=0, sticky="new")
        self.create_grouping_widget()

    def create_grouping_widget(self):

        "This function is used to create the widgets in the grouping tab"

        self.grouping_frame.columnconfigure(0, weight=1)
        self.grouping_frame.columnconfigure(1, weight=1)
        self.grouping_frame.columnconfigure(2, weight=1)
    
        # add a intro label

        intro_label = ctk.CTkLabel(self.grouping_frame, text="This step is optional, You can use this to group multiple samples", font=("Arial", 15))
        intro_label.grid(row=0, column=0, columnspan=2, padx=(0, 0), pady=(2, 10), sticky="w")

        # add a label for file selection
        file_selection_label = ctk.CTkLabel(self.grouping_frame, text="Select file")
        file_selection_label.grid(row=1, column=0, padx=(0, 0), pady=(2, 2), sticky="w")

        # add a dropdown for file selection
        path = os.path.join(self.file_handler.working_folder, 'pooled_data')
        self.files = os.listdir(path)
        # adding a scrollable frame and adding checkboxes in it for selection

        self.file_selection_frame  = ctk.CTkScrollableFrame(self.grouping_frame, width= 400)
        self.file_selection_frame.grid(row=2, column=0, padx=(0, 0), pady=(2, 2), sticky="w")

        self.lst_file_checkboxes = []
        self.selected_files = []

        for i, file_name in enumerate(self.files):
            file_checkbox = ctk.CTkCheckBox(self.file_selection_frame, text=file_name, command= self.one_file_selection)
            file_checkbox.grid(row=i, column=0, padx=(0, 0), pady=(2, 2), sticky="w")
            self.lst_file_checkboxes.append(file_checkbox)

        # creating a frame for all buttons
        self.button_frame = ctk.CTkFrame(self.grouping_frame)
        self.button_frame.grid(row=3, column=0, columnspan = 3,  padx=(0, 0), pady=(10, 2), sticky="w")
        self.button_frame.rowconfigure(0, weight=1)

        for i in range(5):
            self.button_frame.columnconfigure(i, weight=1)

        # adding a button to clear the selection
        self.clear_button = ctk.CTkButton(self.button_frame, text="Clear", command=self.clear_selection)
        self.clear_button.grid(row=0, column=0, padx=(0, 0), pady=(10, 2), sticky="w")

        #adding a labe for group name
        group_name_label = ctk.CTkLabel(self.button_frame, text="Group name")
        group_name_label.grid(row=0, column=1, padx=(20, 0), pady=(10, 2), sticky="w")
        # adding a text box to read the group name
        self.group_name = ctk.CTkEntry(self.button_frame, width=500, placeholder_text= "filename.h5ad")
        self.group_name.grid(row=0, column=2, padx=(10, 0), pady=(10, 2), sticky="w")

        # adding a Group button
        self.group_button = ctk.CTkButton(self.button_frame, text="Group", command=self.group_files)
        self.group_button.grid(row=0, column=3, padx=(20, 0), pady=(10, 2), sticky="e")

        # adding a label to display the processing status
        self.processing_status_label = ctk.CTkLabel(self.button_frame, text="", font = ("Arial", 15), width = 80)
        self.processing_status_label.grid(row=0, column=4, padx=(20, 0), pady=(2, 2), sticky="w")

        # Displaying selected files
        self.selected_files_textbox = ctk.CTkTextbox(self.grouping_frame, font = ("Arial", 15), width = 400)
        self.selected_files_textbox.grid(row=2, column=1,  padx=(0, 0), pady=(10, 10), sticky="w")



    def one_file_selection(self):
        "This function is used to check if atleast one file is selected"

        for cbox, file_name in zip(self.lst_file_checkboxes, self.files):
            if cbox.get() ==1:
                if file_name not in self.selected_files:
                    self.selected_files.append(file_name)
            if cbox.get() ==0:
                if file_name in self.selected_files:
                    self.selected_files.remove(file_name)

        self.display_selected_files()

    def clear_selection(self):
        "This function is used to clear the selection"
        logging.info("Clearing the selection")
        for cbox in self.lst_file_checkboxes:
            cbox.deselect()
        self.selected_files = []
        self.display_selected_files()
    
    def display_selected_files(self):

        "This function is used to display the selected files"
        logger.info("updating file names{}".format(len(self.selected_files)))
        str_files = "\n".join(self.selected_files)
        str_files = "Selected files are: \n" + str_files
        self.selected_files_textbox.delete("0.0", "end")
        self.selected_files_textbox.insert("0.0", str_files)

    def write_group_information_tocsv(self):

        file_path = os.path.join(self.file_handler.working_folder, "group_info.csv" )
        if not os.path.exists(file_path):
            temp_df = pd.DataFrame(columns = ["group_name", "files"])
            temp_df.to_csv(file_path, index = False)
        group_df = pd.read_csv(file_path)
        if self.group_name.get() in group_df["group_name"].values:
            logger.info("Group name already exists")
            CTkMessagebox(title="Warning Message!", message="Group Name already exists, choose a different name ", icon="warning", option_1="Ok")
            return 
        group_df.loc[len(group_df)] = [self.group_name.get(), ", ".join(self.selected_files)]
        group_df.to_csv(file_path, index = False)

    def group_files(self):
        self.processing_status_label.configure(text="Processing...")
        self.master.update()
        # writing group information to csv for historical reference
        self.write_group_information_tocsv()

        files_to_group = [os.path.join(self.file_handler.working_folder, "pooled_data", file) for file in self.selected_files]
        
        group_name = self.group_name.get()
        if '_' not in group_name:
            group_name = group_name + "_"

        if not group_name.endswith(".h5ad"):
            group_name = group_name + ".h5ad"
        group_name = os.path.join(self.file_handler.working_folder, "pooled_data", group_name)

        self.group_process = Process(target=self.run_grouping, args=(files_to_group, group_name, self.queue, self.log_queue))
        self.group_process.start()
        self.check_queue()

    def check_queue(self):
        logger.info("checking queue for messages")
        if not self.queue.empty():
            messgae = self.queue.get()
            self.processing_status_label.configure(text="Group {} created".format(self.group_name.get()), text_color="green")
        if self.group_process.is_alive():
            self.after(2000, self.check_queue)
        else:
            self.group_process.join()

    @staticmethod
    def run_grouping(lst_files, group_name, queue, log_queue):

        worker_configurer(log_queue)
        logger.info("Grouping started")
        h5ad_files = []
        for file in lst_files:
            h5ad_files.append(sc.read(file))
        logger.info("Files read")
        # combining the files
        try:
            concatenated_file = adata_concat(h5ad_files)
            concatenated_file.write(group_name)
        except Exception as e:
            logger.error("Concatenation Error {}".format(e))

        finally:
            queue.put("Grouping completed")
            logger.info("Grouping completed")


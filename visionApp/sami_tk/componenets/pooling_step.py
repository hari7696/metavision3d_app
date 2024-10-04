import logging
import customtkinter as ctk
import os
from multiprocessing import Process, Queue
from SAMI.preprocessing import pooldata, csv2h5ad
from .timer import TimerApp
from log_listener import worker_configurer
from CTkMessagebox import CTkMessagebox
logger = logging.getLogger(__name__)
# logger = logging.getLogger(__name__)

class PoolingStep(ctk.CTkFrame):

    """
    This class is used for the Pooling step of the SAMI app
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
        self.queue = Queue()
        self.prepare_visualization_dock_type2()
        self.creating_pooling_tab()
        # self.check_queue()

        # threading.Thread(target=self.displaying_loading_on_main_thread, args= (),daemon=True).start()

    def refresh(self):
        self.get_files()
        for child in self.pooling_frame.winfo_children():
            child.destroy()
        self.creating_pooling_tab()

    def get_files(self):
        
        self.normalized_files = []
        for file in os.listdir(os.path.join(*[self.file_handler.working_folder, 'normalised_data'])):
            if '_norm.pq' in file:
                self.normalized_files.append(file)

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

        self.pooling_tab = self.vis_tabs.add("Pooling")
        self.pooling_tab.columnconfigure(0, weight=1)
        self.pooling_tab.rowconfigure(0, weight=1)
        self.pooling_frame = ctk.CTkFrame(self.pooling_tab)
        self.pooling_frame.grid(row=0, column=0, sticky="new")
        self.pooling_frame.columnconfigure(0, weight=7)
        self.pooling_frame.columnconfigure(1, weight=3)


    def creating_pooling_tab(self):

        "This function is used to create the pooling tab in the app"

        # splitting the frame into 2 columns
        # this is intended for file options
        self.left_frame = ctk.CTkFrame(self.pooling_frame)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        for i in range(2):
            self.left_frame.columnconfigure(0, weight=1)

        # this is intended for notes and other information
        self.right_frame = ctk.CTkFrame(self.pooling_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.right_frame.columnconfigure(0, weight=1)

        # writing a ahead label about functionalty
        self.head_label = ctk.CTkLabel(self.left_frame, text="Omics Pooling" , font=("Arial", 20))
        self.head_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # getting the files
        self.get_files()

        # a frame to display the files and comboboxes
        self.file_options_frame = ctk.CTkFrame(self.left_frame)
        self.file_options_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.file_options_frame.columnconfigure(0, weight=1)
        self.file_options_frame.columnconfigure(1, weight=1)
        self.file_options_frame.columnconfigure(2, weight=1)

        # basing on the number of files we have, we will display the combobox dropdowns
        if len(self.normalized_files) == 0:
            self.no_files_label = ctk.CTkLabel(self.file_options_frame, text="No files found for pooling", font=("Arial", 15))
            self.no_files_label.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
            return
        
        self.dict_compound_type = {}
        for i, file in enumerate(self.normalized_files):
            self.file_label = ctk.CTkLabel(self.file_options_frame, text=f"{file}", font=("Arial", 15))
            self.file_label.grid(row=i+1, column=0, sticky="ew", padx=5, pady=5)

            combobox = ctk.CTkComboBox(self.file_options_frame, values=["lipidomics", "metabolomics","glycomics", "other"])
            combobox.grid(row=i+1, column=1, sticky="ew", padx=5, pady=5)
            combobox.configure(state="readonly")
            self.dict_compound_type[file] = combobox

        # a frame to display the buttons and other information
        self.button_frame = ctk.CTkFrame(self.left_frame)
        self.button_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        for i in range(5):
            self.button_frame.columnconfigure(i, weight=1)

        # making a button to start the pooling  
        self.pooling_button = ctk.CTkButton(self.button_frame, text="Start Pooling", command=self.spin_seperate_process_for_pooling, width=40)
        self.pooling_button.grid(row=2, column=2, sticky="ew", padx=5, pady=5)

        # adding a timer
        self.timer = TimerApp(self.button_frame)
        self.timer.grid(row=3, column=2, sticky="ew", padx=5, pady=(5, 5))

        # adding a status label
        self.status_label = ctk.CTkLabel(self.button_frame, text="", font = ("Arial", 15), width = 80)
        self.status_label.grid(row=4, column=2, sticky="ew", padx=0, pady=10)

        # adding a label to display the files generated
        self.files_label = ctk.CTkLabel(self.button_frame, text="", font = ("Arial", 15), width = 300, height = 300)
        self.files_label.grid(row=5, column=2, sticky="ew", padx=0, pady=10, )

        # adding a ctk text box
        self.ctk_text = ctk.CTkTextbox(self.right_frame, width=120, height=200)
        self.ctk_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.ctk_text.insert("0.0", """Notes: \n1. You need to select appropritate omics present in corresponding file\n 2. If you select Other, you will face issues in Pathways step but till markers, you should be able to run\n 3. If the pixels doesnt align during pooling, it will throw a wraning and wont generate any pooled files\n4. you CAN still continue the rest of the steps with available data""")
        
        self.ctk_text.configure(state="disabled", font = ("Arial", 16))



    def spin_seperate_process_for_pooling(self):

        # getting the files and the compound type
        self.file_compound_types = {}
        
        # getting the dropdown selections
        for file in self.dict_compound_type:

            if self.dict_compound_type[file].get() == "sm":
                self.file_compound_types[file] = "metabolomics"
            else:
                self.file_compound_types[file] = self.dict_compound_type[file].get()

        logger.info(f"Files and compound types are {self.file_compound_types}")

        self.pooling_button.configure(state="disabled")
        self.timer.reset_timer()
        self.timer.start_timer()
        self.status_label.configure(text= "Omics Pooling started")    
        logger.info("Pooling started in separate process")
        self.process = Process(target=self.startpooling, args=(self.file_handler.working_folder, self.file_compound_types, self.queue, self.log_queue))
        self.process.start()
        self.check_queue()

    @staticmethod
    def temp():
        pass

    def check_queue(self):
        if not self.queue.empty():
            messgae = self.queue.get()
            files = messgae[0]
            merge_error_flag = messgae[1]
            # print(messgae)
            self.status_label.configure(text= "Omics pooling completed", text_color="green")
            self.files_label.configure(text= files)
            self.timer.stop_timer()
            self.pooling_button.configure(state="normal")
            logger.info(f"error flag {merge_error_flag}")
            if len(merge_error_flag) > 0:
                logger.error("Pixel mismatch error")
                CTkMessagebox(title="Warning", message="Potential Pixel mismatch issue occured, a custom data handling is required for this data.\
                              you CAN continue to next steps with available files",
                    icon="warning", option_1="OK")
        if self.process.is_alive():
            self.master.after(5000, self.check_queue)
        else:
            self.process.join()

        # print("checking")
        
    @staticmethod   
    def startpooling(working_dir, dict_compound_type, queue, log_queue):

        worker_configurer(log_queue)
        
        logger.info("Pooling started")  
        data_reading_path = os.path.join(working_dir, 'normalised_data')
        data_saving_path = os.path.join(working_dir, 'pooled_data')
        
        if not os.path.exists(data_saving_path):
            os.makedirs(data_saving_path)
        logger.info("csv2h5ad started")
        csv2h5ad(dict_compound_type, data_reading_path, data_saving_path, split=True, log_queue = log_queue)

        logger.info("OMICS started")
        # pooling omics data
        try:
            merge_error_flag = pooldata(dict_compound_type, data_reading_path, data_saving_path, split=True, log_queue = log_queue)
        except:
            merge_error_flag = ["pixel count is different in both the datasets"]



        files = os.listdir(data_saving_path)
        str = ""
        for file in files:
            file_name = os.path.basename(file)
            if '_pool' in file_name:
                str = str + file_name + "\n"
        queue.put([str, merge_error_flag])
        logger.info("Pooling completed")









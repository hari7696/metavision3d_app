import logging
import customtkinter as ctk
import os
from multiprocessing import Process, Queue
from SAMI.preprocessing import pooldata, csv2h5ad
from .timer import TimerApp
logger = logging.getLogger(__name__)

class PoolingStep(ctk.CTkFrame):

    """
    This class is used for the Pooling step of the SAMI app
    """

    def __init__(self, master, file_handler):
        super().__init__(
            master,
        )
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
        pass

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
        # self.pooling_tab = self.vis_tabs.add("Pooling")

        # self.pooling_tab.columnconfigure(0, weight=1)
        # self.pooling_tab.rowconfigure(0, weight=1)
        # self.pooling_tab.grid(row=0, column=0, sticky="nsew")

    def creating_pooling_tab(self):

        "This function is used to create the pooling tab in the app"

        self.pooling_tab = self.vis_tabs.add("Pooling")
        self.pooling_tab.columnconfigure(0, weight=1)
        self.pooling_tab.rowconfigure(0, weight=1)
        self.pooling_frame = ctk.CTkFrame(self.pooling_tab)
        self.pooling_frame.grid(row=0, column=0, sticky="new")
        self.pooling_frame.columnconfigure(0, weight=10)
        self.pooling_frame.columnconfigure(1, weight=3)
        self.pooling_frame.columnconfigure(2, weight=10)

        # writing a ahead label about functionalty
        self.head_label = ctk.CTkLabel(self.pooling_frame, text="Omics Pooling" , font=("Arial", 20))
        self.head_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        # self.head_label.columnconfigure(0, weight=1)
        # self.head_label.rowconfigure(0, weight=1)

        # making a button to start the pooling  
        self.pooling_button = ctk.CTkButton(self.pooling_frame, text="Start Pooling", command=self.spin_seperate_process_for_pooling, width=40)
        self.pooling_button.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # adding a timer
        self.timer = TimerApp(self.pooling_frame)
        self.timer.grid(row=2, column=1, sticky="ew", padx=5, pady=(5, 5))

        # adding a status label
        self.status_label = ctk.CTkLabel(self.pooling_frame, text="", font = ("Arial", 15), width = 80)
        self.status_label.grid(row=3, column=1, sticky="ew", padx=0, pady=10)

        # adding a label to display the files generated
        self.files_label = ctk.CTkLabel(self.pooling_frame, text="", font = ("Arial", 15), width = 300, height = 300)
        self.files_label.grid(row=4, column=1, sticky="ew", padx=0, pady=10, )



    def spin_seperate_process_for_pooling(self):
        self.timer.reset_timer()
        self.timer.start_timer()
        self.status_label.configure(text= "Omics Pooling started")    
        self.process = Process(target=self.start_pooling, args=(self.file_handler.working_folder, self.queue))
        self.process.start()
        self.check_queue()

    def check_queue(self):
        if not self.queue.empty():
            messgae = self.queue.get()
            # print(messgae)
            self.status_label.configure(text= "Omics pooling completed", text_color="green")
            self.files_label.configure(text= messgae)
            self.timer.stop_timer()
        if self.process.is_alive():
            self.master.after(500, self.check_queue)
        else:
            self.process.join()

        # print("checking")
        
    @staticmethod   
    def start_pooling(working_dir, queue):
        
        logger.info("Pooling started")  
        data_reading_path = os.path.join(working_dir, 'normalised_data')
        data_saving_path = os.path.join(working_dir, 'pooled_data')
        
        if not os.path.exists(data_saving_path):
            os.makedirs(data_saving_path)
        logger.info("csv2h5ad started")
        # pooldata()
        csv2h5ad(data_reading_path, r'^\w+norm\.pq', data_saving_path, split=True)

        logger.info("OMICS started")
        # pooling omics data
        pooldata(data_reading_path, r'^\w+norm\.pq', data_saving_path, split=True)

        files = os.listdir(data_saving_path)
        str = ""
        for file in files:
            file_name = os.path.basename(file)
            if '_pool' in file_name:
                str = str + file_name + "\n"
        queue.put(str)
        logger.info("Pooling completed")









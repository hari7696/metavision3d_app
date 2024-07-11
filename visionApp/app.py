import customtkinter as ctk
import os
from Metavision_tk.MetavisionApp import MetaVision3DApp
from sami_tk.SamiApp import SAMIApp
import logging
from logging import handlers
import sys
import logging
import multiprocessing
from log_listener import listener_process
sys.path.append('SAMI')
logger = logging.getLogger(__name__) 
def root_configurer(queue):
    h = handlers.QueueHandler(queue)
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.INFO)
    
class VisionApp(ctk.CTk):

    """DO NOT CHNAGE THIS TEMPLATE, you may update change_to_algo_ui() if new algorithm is added"""

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.title("Vision")
        self.geometry("1350x710")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        # self.rowconfigure(1,weight=9)
        
        # the Parent, we need to pass to all the algorithm UI classes
        self.parent_frame = ctk.CTkFrame(self)
        self.parent_frame.grid(row=0,column=0,columnspan=2,sticky="nsew")
        self.parent_frame.columnconfigure(0,weight=1)
        self.parent_frame.rowconfigure(0,weight=1)
        self.parent_frame.rowconfigure(1,weight=10)

        self.nav_frame = ctk.CTkFrame(self.parent_frame)
        self.nav_frame.grid(row=0,column=0,sticky="new")
        self.nav_frame.columnconfigure(0,weight=1)
        self.nav_frame.columnconfigure(1,weight=1)
        self.nav_frame.columnconfigure(2,weight=1)
        self.nav_frame.columnconfigure(3,weight=1)
        self.nav_frame.columnconfigure(4,weight=15)
        self.nav_frame.rowconfigure(0,weight=1)

        # self.nav_frame.columnconfigure(5,weight=1)
        
        # self.nav_frame.rowconfigure(0,weight=1)
        logger.info("application started")
        algo_default_value = ctk.StringVar(value="Select the ALgorithm")
        self.algo_selection_dropdown = ctk.CTkOptionMenu(master= self.nav_frame,
                                            values=["MetaVision3D","SAMI"],
                                            command=self.change_to_algo_ui,
                                            variable=algo_default_value,
                                            )
        self.algo_selection_dropdown.grid(row=0,column=0,padx=(5,5),pady=10, sticky="w")

        self.write_num_children_to_logs()

    def write_num_children_to_logs(self):

        def count_all_children(widget):
            """
            Recursively counts all descendants of a given widget.
            """
            count = len(widget.winfo_children())
            for child in widget.winfo_children():
                count += count_all_children(child)
            return count

        # Assuming self.parent_frame is your root widget from which you want to start counting
        total_children = count_all_children(self.parent_frame)

        logger.info("Frequent_checker :: Total children {}".format(str(total_children)))
        self.after(1000, self.write_num_children_to_logs)
        

    def destroy_children(self):
        """
        Only frames that are gonna stay between switching the algorithms is the NavFrame and the algo_selection_dropdown widget in it
        """
        for child in self.parent_frame.winfo_children():
            if child != self.nav_frame:
                child.destroy()
            
        for child in self.nav_frame.winfo_children():
            if child != self.algo_selection_dropdown:
                child.destroy()


    def change_to_algo_ui(self, choice):
        """
        Switching to respective UI based on the choice
        """

        if choice == "MetaVision3D":
            # Destroy all widgets in the parent frame except nav_frame

            self.destroy_children()
            logging.info("num children {}".format(str(len(self.parent_frame.winfo_children()))))
            self.meta_frame = MetaVision3DApp(self.parent_frame, self.nav_frame)
            self.meta_frame.grid(row=1, column=0, sticky="nsew",pady=(5,0), padx=(0,0))

        elif choice == "SAMI":
            # Destroy all widgets in the parent frame except nav_frame and dropdown bar in it
            self.destroy_children()
            logger.info("num children in parent_frame {}".format(str(len(self.parent_frame.winfo_children()))))
            self.sami_ap = SAMIApp(self.parent_frame, self.nav_frame, self.algo_selection_dropdown, self.log_queue)
            self.sami_ap.grid(row=1, column=0, sticky="nsew", pady=(5,0), padx=(0,0),)
            self.rowconfigure(1,weight=10)


if __name__ == "__main__":

    ENVIRONMENT = "NONE"
    try :
        base_path = sys._MEIPASS
        log_directory= os.path.join(base_path, "logs")
        ENVIRONMENT = "EXE"
    except Exception as e:
        log_directory = os.path.abspath(r"C:\Users\ghari\Documents\OPS\UI\metavision3d_app\logs")
        ENVIRONMENT = "DEV"

    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
        

    multiprocessing.set_start_method('spawn')
    multiprocessing.freeze_support()
    log_queue = multiprocessing.Queue(-1)
    listener = multiprocessing.Process(target=listener_process, args=(log_queue, log_directory))
    listener.start()
    root_configurer(log_queue)

    logger.info("Starting the application")
    try:
        import pyi_splash # type: ignore
        pyi_splash.close()
    except Exception as e:
        logger.error("error in closing splash screen {}".format(str(e)))
    app = VisionApp(log_queue)
    app.mainloop()
    logger.info("teminating log listener process")
    listener.terminate()
    


    # (r'c:\Users\ghari\Pictures\R', 'R')


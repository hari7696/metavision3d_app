import customtkinter as ctk
import logging
from tkinter import filedialog, messagebox
import threading
import os

logger = logging.getLogger(__name__)
def open_file(self):
    """
    Open file dialog,

    The moment the folder is opened, its starts reading the files via threading
    """
    self.filepath = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )
    if self.filepath:
        logging.debug(f"Filepath is {self.filepath}")
        self.folder = os.path.dirname(self.filepath)
        self.display_file_loading()
        # threading.Thread(target=self.load_file, args=(self.filepath,),
        #                   daemon=True).start()

def open_multiple_files(self):

    """ Open folder dialog to select the folder containing the files"""

    self.files_path = filedialog.askopenfilenames(title="Select  multiple files")
    logging.debug(f"Folder path is {self.folder_path}")
    # self.display_file_loading()
    # folder_path = os.path.join(self.folder_path,'*.csv')
    # folder_files = glob.glob(folder_path)
    # logging.debug(f"Folder files are {folder_files}")   


    # threading.Thread(target=self.load_file, args=(os.path.join(self.sami_folder,self.sami_multi_file_names[0]),), daemon=True).start()



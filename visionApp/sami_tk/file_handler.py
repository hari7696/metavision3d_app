import customtkinter as ctk
import logging
from tkinter import filedialog, messagebox
import threading
import os
import pandas as pd

logger = logging.getLogger(__name__)


class FileOpenbutton(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
        )
        self.columnconfigure(0, weight=1)
        self.files_path = None
        self.input_data_raw = {}
        self.is_files_read = False
        self.working_folder = None
        self.tissue_ids = {}
        self.molecule_name = {}
        self.file_type = None
        self.base_files = []

    def file_opening_button(self, choice):
        """
        Button to open the file dialog to select the file

        if its single file type, It should display open file dialog
        if its multi file type, It should display open directory dialog
        """
        logger.debug(f"Choice is {choice}")
        logger.debug(
            "'file_opening_button' : children count {}".format(
                len(list(self.winfo_children()))
            )
        )

        if choice == "Multi file":
            self.f_open_btn = ctk.CTkButton(
                self, text="Open Folder", command=self.open_multiple_files
            )
            logger.debug("multi file type selected")
            self.file_type = "multi"

        elif choice == "Single file":

            self.f_open_btn = ctk.CTkButton(
                self, text="Open File", command=self.open_file
            )
            logger.debug("Single file type selected")
            self.file_type = "single"

        self.f_open_btn.grid(row=0, column=0, padx=(0, 0), pady=(2, 2), sticky="w")

    def open_file(self):
        """
        Open file dialog,

        The moment the file is selected, its starts reading the files via threading
        """
        self.filepath = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if self.filepath:
            logger.info(f"selected file: {self.filepath}")
            self.working_folder = os.path.dirname(self.filepath)
            logger.info(f"working folder: {self.working_folder}")
            self.base_files = [os.path.basename(file) for file in [self.filepath]]
            self.base_files = [file.strip(".csv") for file in self.base_files]
            self.display_file_loading()
            threading.Thread(
                target=self.async_read_files, args=([self.filepath],), daemon=True
            ).start()

    def open_multiple_files(self):
        """
        Open folder dialog to select multuple files.
        Once the files are selected, they will be read via threading
        """

        self.files_path = filedialog.askopenfilenames(title="Select  multiple files")
        logger.info(f"selected files:  {self.files_path}")
        self.working_folder = os.path.dirname(self.files_path[0])
        logger.info(f"working folder: {self.working_folder}")
        self.base_files = [os.path.basename(file) for file in self.files_path]
        self.base_files = [file.strip(".csv") for file in self.base_files]

        self.display_file_loading()
        threading.Thread(
            target=self.async_read_files, args=(self.files_path,), daemon=True
        ).start()

        # threading.Thread(target=self.load_file, args=(os.path.join(self.sami_folder,self.sami_multi_file_names[0]),), daemon=True).start()

    def async_read_files(self, file_path):
        """
        Read the files in the folder
        """
        self.input_data_raw = {}
        for file in file_path:

            base_filename = os.path.basename(file)

            temp_df = pd.read_csv(os.path.join(self.working_folder, base_filename))
            logger.info(f"file read: {base_filename}")
            base_filename = base_filename.strip(".csv")
            self.input_data_raw[base_filename] = self.preprocess(temp_df, base_filename)
        self.is_files_read = True
        self.loading_label.destroy()

    def preprocess(self, df, base_filename):
        """
        Preprocess the data

        The expetection columns are:

        x, y, region and molecules

        The field 'region' is adhoc, need to discuss with the team to get the correct field name

        """
        for col in ['Unnamed: 0', 'spotId','raster', 'z', 'Date', ]:
            if col in df.columns:
                df = df.drop(col, axis=1)
        if 'tissue_id' in df.columns:
            df = df.rename(columns={'tissue_id': 'region'})
        self.tissue_ids[base_filename] = list(df["region"].unique())
        self.molecule_name[base_filename] = list(df.columns[3:])
        return df

    def display_file_loading(self):
        # Displying the loading label
        logger.debug("displaying the loading label")
        self.loading_label = ctk.CTkLabel(self, text="Loading...")
        self.loading_label.grid(row=0, column=1, padx=(0, 0), pady=(2, 2), sticky="w")

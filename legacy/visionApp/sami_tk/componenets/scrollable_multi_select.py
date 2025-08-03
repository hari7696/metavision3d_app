import customtkinter as ctk

class ScrollableWindowMulitSelect(ctk.CTkFrame):
    def __init__(self, master, files):
        super().__init__(
            master,
        )
        # self.grid_columnconfigure(0, weight=1)
        # self.grid_rowconfigure(0, weight=1)
        # self.log_queue = log_queue
        # self.columnconfigure(0, weight=1)
        # self.rowconfigure(0, weight=1)
        
        self.files = files
        self.grid(row=0, column=0, padx=(0, 0), pady=(2, 2), sticky="w")
        self.create_widgets()

    def create_widgets(self):

        self.file_selection_frame  = ctk.CTkScrollableFrame(self,height=350,width=400)
        self.file_selection_frame.grid(row=0, column=0, padx=(5, 5), pady=(5, 1), sticky="w")
        self.file_selection_frame.columnconfigure(0, weight=1)
        self.file_selection_frame.rowconfigure(0, weight=1)
        self.lst_file_checkboxes = []
        self.selected_files = []

        for i, file_name in enumerate(self.files):
            file_checkbox = ctk.CTkCheckBox(self.file_selection_frame, text=file_name, command= self.one_file_selection)
            file_checkbox.grid(row=i, column=0, padx=(0, 0), pady=(2, 2), sticky="w")
            self.lst_file_checkboxes.append(file_checkbox)
            
            
        # a frame for button
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=1, column=0, padx=(0, 0), pady=(2, 2), sticky="w")
            
        # adding a clear selection button
        self.clear_selection_button = ctk.CTkButton(self.button_frame, text="Clear Selection", command=self.clear_selection, fg_color='transparent', border_width=0.5, width = 100)
        self.clear_selection_button.grid(row=0, column=1, padx=(10, 0), pady=(1, 5), sticky="w", columnspan=2)
        
        # adding a select all button
        self.btn_select_all = ctk.CTkButton(self.button_frame, text="Select All", command=self.select_all, fg_color='transparent', border_width=0.5, width = 100)
        self.btn_select_all.grid(row=0, column=3, padx=(20, 0), pady=(1, 5), sticky="w", columnspan=2)
        

    def clear_selection(self):
        "This function is used to clear the selection"
        # logging.info("Clearing the selection")
        for cbox in self.lst_file_checkboxes:
            cbox.deselect()
        self.selected_files = []
        # self.display_selected_files()

    def one_file_selection(self):
        "This function is used to check if atleast one file is selected"

        for cbox, file_name in zip(self.lst_file_checkboxes, self.files):
            if cbox.get() ==1:
                if file_name not in self.selected_files:
                    self.selected_files.append(file_name)
            if cbox.get() ==0:
                if file_name in self.selected_files:
                    self.selected_files.remove(file_name)

        # self.display_selected_files()

    def get_selected_files(self):
        "This function is used to get the selected files"
        return self.selected_files
    
    def select_all(self):
        "This function is used to select all the files"
        for cbox in self.lst_file_checkboxes:
            cbox.select()
        self.selected_files = self.files
        # self.display_selected_files()
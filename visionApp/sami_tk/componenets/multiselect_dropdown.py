import logging
import customtkinter as ctk
from tkinter import *

logger = logging.getLogger(__name__)


class DropDownMulitSelect(ctk.CTkToplevel):
    def __init__(self, master, options, selected_values_label):
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
        self.selected_values_label = selected_values_label
        # self.selected_values_label = []

        self.button = ctk.CTkLabel(self, text="Select Regions")
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
            self.drop_down.get(idx) for idx in self.drop_down.curselection()
        ]

        # self.selected_values_label.configure(text = "Selected Compounds: {}".format( ))
        self.selected_values_label.delete(0.0, "end")
        text = "Selected Values\n" + "\n".join(self.selected_values)
        self.selected_values_label.insert("0.0", text)

        self.destroy()

    def clear(self):
        # clearing the selected items
        self.selected_values = []
        self.drop_down.destroy()
        self.create_drop_down()


if __name__ == "__main__":
    app = DropDownMulitSelect(
        [
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
        ]
    )
    app.mainloop()

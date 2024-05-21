import customtkinter as ctk
import tkinter as tk
from threading import Thread
import time

class TimerApp(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master )

        # Label to display the timer
        self.timer_label = ctk.CTkLabel(self, text="00:00:00", font=('Helvetica', 12),bg_color = "transparent", width=100)
        self.timer_label.pack(pady=3)

        # Timer variable
        self.timer_active = False
        self.seconds = 0

    def start_timer(self):
        # Activate the timer if it is not already running
        if not self.timer_active:
            self.timer_active = True
            self.update_timer()

    def update_timer(self):
        if self.timer_active:
            # Increment the timer
            self.seconds += 1
            # Calculate hours, minutes, and seconds
            hours, remainder = divmod(self.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Update the label in HH:MM:SS format
            self.timer_label.configure(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            # Schedule the next call within 1 second
            self.after(1000, self.update_timer)

    def reset_timer(self):
        # Reset the seconds counter
        self.seconds = 0
        # Update the timer label to 00:00:00
        self.timer_label.configure(text="00:00:00")

    def stop_timer(self):
        self.timer_active = False

if __name__ == "__main__":
    app = TimerApp()
    app.mainloop()

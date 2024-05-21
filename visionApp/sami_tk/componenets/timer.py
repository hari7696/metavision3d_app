import customtkinter as ctk

class TimerApp(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master )

        self.timer_label = ctk.CTkLabel(self, text="00:00:00", font=('Helvetica', 12),bg_color = "transparent", width=100)
        self.timer_label.pack(pady=3)

        self.timer_active = False
        self.seconds = 0

    def start_timer(self):
        if not self.timer_active:
            self.timer_active = True
            self.update_timer()

    def update_timer(self):
        if self.timer_active:
            # Increment the timer
            self.seconds += 1
            hours, remainder = divmod(self.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.configure(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            self.after(1000, self.update_timer)

    def reset_timer(self):
        self.seconds = 0
        self.timer_label.configure(text="00:00:00")

    def stop_timer(self):
        self.timer_active = False

if __name__ == "__main__":
    app = TimerApp()
    app.mainloop()

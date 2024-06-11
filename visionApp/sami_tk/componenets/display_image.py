import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import Canvas
from multiprocessing import Process, Queue
import io
import time
class ImageDisaplay(ctk.CTkFrame):

    def __init__(self, master, image_location="cerebellumWT_umap_integrated.png", width = 1400, height = 400, zoom_factor = 0.2):
        super().__init__( master)

        self.frame_width = width
        self.frame_height = height
        self.last_event_time = 0




        self.cluster_visualization = ctk.CTkFrame(master, width=self.frame_width, height=self.frame_height, bg_color = "red")
        self.cluster_visualization.grid(row=0, column=0, sticky="nsew")
        self.cluster_visualization.columnconfigure(0, weight=1)
        self.cluster_visualization.rowconfigure(0, weight=1)

        self.canvas = Canvas(self.cluster_visualization, width=self.frame_width, height=self.frame_height, bg='#404040')
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.zoom_factor = zoom_factor
        self.image_id = None
        self.image_location = image_location
        self.queue = Queue()
        # self.prepare_visualization()
        # self.load_image_thread = threading.Thread(target=self.load_image)
        # self.load_image_thread.start()
        self.process = Process(target=self.load_image_process, args=(self.image_location, self.queue))
        self.process.start()
        self.check_queue()

    @staticmethod
    def load_image_process(image_path, queue):
        image = Image.open(image_path)
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            image_data = output.getvalue()
        queue.put(image_data)


    def check_queue(self):
        if not self.queue.empty():
            image_data = self.queue.get()
            self.original_image = Image.open(io.BytesIO(image_data))
            self.prepare_visualization()
        if self.process.is_alive():
            self.master.after(1000, self.check_queue)
        else:
            self.process.join()

    def prepare_visualization(self):

        self.tk_image = ImageTk.PhotoImage(self.original_image.resize((self.frame_width, self.frame_height), Image.LANCZOS))
        self.image_id = self.canvas.create_image(self.frame_width // 2, self.frame_height // 2, image=self.tk_image, anchor="center")

        self.canvas.bind("<MouseWheel>", self.zoom_image)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<Double-Button-1>", self.reset_zoom)

    def zoom_image(self, event):

        current_time = time.time()
        # print(current_time - self.last_event_time)
        if current_time - self.last_event_time < 0.5:  # Adjust this value as needed
            # print("Hit")
            return  # Skip this update
        self.last_event_time = current_time


        zoom_factor_change = 1.1 if event.delta > 0 else 0.9
        new_zoom_factor = self.zoom_factor * zoom_factor_change
        # print(new_zoom_factor)
        if new_zoom_factor < 0.1:
            return
            # new_zoom_factor = 1.0
        new_width = int(self.original_image.width * new_zoom_factor)
        new_height = int(self.original_image.height * new_zoom_factor)
        new_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(new_image)

        self.canvas.itemconfig(self.image_id, image=self.tk_image)
        self.zoom_factor = new_zoom_factor

    def start_drag(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def do_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def reset_zoom(self, event):
        original_size_image = self.original_image.resize((self.frame_width, self.frame_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(original_size_image)
        self.canvas.itemconfig(self.image_id, image=self.tk_image)
        self.canvas.coords(self.image_id, self.frame_width // 2, self.frame_height // 2)


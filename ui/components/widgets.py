"""Contenedores reutilizables; actualizaciones solo en hilo Tkinter."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from ui.theme import BG, PANEL, TEXT


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas, padding=12)
        item = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(item, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-int(e.delta / 120), 'units'))


class Video(ttk.Frame):
    def __init__(self, parent, title='Cámara real'):
        super().__init__(parent)
        ttk.Label(self, text=title, style='Heading.TLabel').pack(anchor='w', pady=(0, 8))
        self.label = tk.Label(self, bg=PANEL, fg=TEXT, text='Cámara desconectada', anchor='center')
        self.label.pack(fill='both', expand=True)
        self.photo = None
        self.last = None

    def update_frame(self, snap):
        if not snap['fresh']:
            self.label.configure(image='', text=snap['status'])
            self.photo = None
            self.last = None
            return
        f = snap['frame']
        size = (max(160, self.label.winfo_width()), max(100, self.label.winfo_height()))
        key = (f.id, size)
        if key == self.last:
            return
        image = Image.fromarray(f.image[:, :, ::-1])
        image.thumbnail(size)
        self.photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self.photo, text='')
        self.last = key

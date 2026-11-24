import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from dataset.capture import SHAPES, COLORS
from ui.components.widgets import Video


class DatasetTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='Dataset · originales de la cámara real', style='Heading.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        self.video = Video(self)
        self.video.grid(row=1, column=0, sticky='nsew', padx=(0, 14))
        panel = ttk.Frame(self)
        panel.grid(row=1, column=1, sticky='nsew')
        self.shape, self.color, self.session = tk.StringVar(value=SHAPES[0]), tk.StringVar(value=COLORS[0]), tk.StringVar(value='sesion_01')
        for name, variable, choices in [('Forma', self.shape, SHAPES), ('Color', self.color, COLORS), ('Sesión de captura', self.session, None)]:
            ttk.Label(panel, text=name).pack(anchor='w', pady=(12, 4))
            (ttk.Combobox(panel, textvariable=variable, values=choices, state='readonly') if choices else ttk.Entry(panel, textvariable=variable)).pack(fill='x')
        ttk.Button(panel, text='Capturar original', style='Primary.TButton', command=lambda: app.capture(self.shape.get(), self.color.get(), self.session.get())).pack(fill='x', pady=(18, 6))
        ttk.Button(panel, text='Ráfaga · fase siguiente', state='disabled').pack(fill='x')
        self.counts = tk.StringVar(value='Contadores: cargando…')
        ttk.Label(panel, textvariable=self.counts, wraplength=280).pack(anchor='w', pady=12)
        self.preview = ttk.Label(panel, text='Vista previa: sin capturas', anchor='center')
        self.preview.pack(fill='both', expand=True)
        self.storage = tk.StringVar(value='Destino: ' + str(app.dataset.root))
        ttk.Label(self, textvariable=self.storage, wraplength=1100, style='Muted.TLabel').grid(row=2, column=0, columnspan=2, sticky='w', pady=10)
        app.job(lambda: app.event('counts', app.dataset.counts()))

    def show_saved(self, path, counts):
        with Image.open(path) as original:
            image = original.copy()
        image.thumbnail((250, 160))
        self.photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.photo, text='')
        self.counts.set('Originales reales por forma:\n' + '\n'.join(f'{k}: {v}' for k, v in counts.items()))
        self.storage.set('Guardado: ' + str(path))

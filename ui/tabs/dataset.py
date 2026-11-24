"""Estudio de captura: contadores derivados únicamente de originales reales."""

import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from dataset.capture import SHAPES, COLORS
from ui.dataset_view import dataset_summary
from ui.preferences import load_goal, save_goal
from ui.components.widgets import Card, Metric, Video, label, button, set_value

NAMES = {
    "cubo": "Cubos",
    "cilindro": "Cilindros",
    "prisma_triangular": "Prismas triangulares",
}


class DatasetTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.summary = None
        self.photo = None
        self.goal = 150
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        metrics = ttk.Frame(self)
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.total = Metric(metrics, "Originales reales", "camera", "—")
        classes = Metric(metrics, "Clases de forma", "dataset", "3")
        self.target = Metric(metrics, "Objetivo de captura", "target", "450")
        for i, card in enumerate((self.total, classes, self.target)):
            metrics.columnconfigure(i, weight=1, uniform="metrics")
            card.grid(row=0, column=i, sticky="ew", padx=(0, 8) if i < 2 else 0)
        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=6, uniform="dataset")
        body.columnconfigure(1, weight=5, uniform="dataset")
        body.rowconfigure(0, weight=1)
        camera = Card(body, padding=12)
        camera.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.video = Video(
            camera.body,
            "Previsualización de cámara",
            lambda: self.winfo_toplevel().navigate_config("Conectividad"),
        )
        self.video.pack(fill="both", expand=True)
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        capture = Card(right, "Configuración de captura", "settings", padding=10)
        capture.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        fields = ttk.Frame(capture.body, style="Surface.TFrame")
        fields.pack(fill="x")
        fields.columnconfigure(1, weight=1)
        fields.columnconfigure(3, weight=1)
        self.shape = tk.StringVar(value=SHAPES[0])
        self.color = tk.StringVar(value=COLORS[0])
        self.session = tk.StringVar(value="sesion_01")
        for i, (name, var, choices) in enumerate(
            (
                ("Forma", self.shape, SHAPES),
                ("Color", self.color, COLORS),
                ("Sesión", self.session, None),
            )
        ):
            field_row = 0 if i < 2 else 1
            field_column = 0 if i != 1 else 2
            label(fields, name).grid(
                row=field_row, column=field_column, sticky="w", padx=(0, 8), pady=1
            )
            widget = (
                ttk.Combobox(
                    fields,
                    textvariable=var,
                    values=choices,
                    state="readonly",
                    width=17 if i == 0 else 9,
                )
                if choices
                else ttk.Entry(fields, textvariable=var)
            )
            widget.grid(
                row=field_row,
                column=field_column + 1,
                columnspan=3 if i == 2 else 1,
                sticky="ew",
                pady=1,
                padx=(0, 8) if i == 0 else 0,
            )
        row = ttk.Frame(capture.body, style="Surface.TFrame")
        row.pack(fill="x", pady=(8, 0))
        self.capture_button = button(
            row,
            "Capturar original",
            lambda: app.capture(self.shape.get(), self.color.get(), self.session.get()),
            style="Primary.TButton",
        )
        self.capture_button.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.burst = button(row, "Ráfaga · pendiente", state="disabled")
        self.burst.pack(side="left")
        distribution = Card(right, "Distribución del dataset", "dataset", padding=10)
        distribution.grid(row=1, column=0, sticky="nsew")
        self.progress = {}
        self.class_labels = {}
        for shape in SHAPES:
            row = ttk.Frame(distribution.body, style="Surface.TFrame")
            row.pack(fill="x", pady=1)
            label(row, NAMES[shape], width=20, style="Muted.TLabel").pack(side="left")
            bar = ttk.Progressbar(row, maximum=150)
            bar.pack(side="left", fill="x", expand=True, padx=8)
            self.progress[shape] = bar
            value = tk.StringVar(value="— / 150")
            self.class_labels[shape] = value
            label(
                row, textvariable=value, width=10, anchor="e", style="Muted.TLabel"
            ).pack(side="right")
        self.counts = tk.StringVar(value="Colores: leyendo manifiesto…")
        label(distribution.body, textvariable=self.counts, style="Muted.TLabel").pack(
            anchor="w", pady=(4, 4)
        )
        last = ttk.Frame(distribution.body, style="Surface.TFrame")
        last.pack(fill="both", expand=True)
        self.preview = ttk.Label(
            last, text="Sin imágenes guardadas", style="Muted.TLabel", anchor="center"
        )
        self.preview.pack(side="left", fill="both", expand=True)
        goal = ttk.Frame(last, style="Surface.TFrame")
        goal.pack(side="right", padx=(8, 0))
        label(goal, "Meta/clase", style="Muted.TLabel").pack(side="left")
        self.goal_var = tk.StringVar(value="150")
        ttk.Spinbox(goal, from_=1, to=100000, width=5, textvariable=self.goal_var).pack(
            side="left", padx=8
        )
        button(
            goal,
            "Guardar",
            lambda: self.winfo_toplevel().run(self.set_goal),
            style="Compact.TButton",
        ).pack(side="right")
        self.storage = tk.StringVar(value="Destino: " + str(app.dataset.root))
        label(
            self, textvariable=self.storage, style="Caption.TLabel", wraplength=1000
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.request_summary()
        app.job(lambda: app.event("ui_goal", load_goal()))

    def request_summary(self):
        root = self.app.dataset.root
        self.app.job(lambda: self.app.event("dataset_summary", dataset_summary(root)))

    def set_goal(self):
        value = int(self.goal_var.get())
        from app.config import integer

        integer(value, 1, 100000, "Meta por clase")
        self.app.job(lambda: (save_goal(value), self.app.event("ui_goal", value)))

    def apply_goal(self, value):
        self.goal = value
        self.goal_var.set(str(value))
        set_value(self.target.value, str(value * 3))
        if self.summary:
            self.apply_summary(self.summary)

    def apply_summary(self, summary):
        if summary["root"] != self.app.dataset.root.resolve():
            return
        self.summary = summary
        set_value(self.total.value, str(summary["total"]))
        for shape in SHAPES:
            n = summary["shapes"][shape]
            self.progress[shape].configure(maximum=self.goal, value=n)
            set_value(self.class_labels[shape], f"{n} / {self.goal}")
        set_value(
            self.counts,
            "Colores: "
            + "  ·  ".join(f"{c} {n}" for c, n in summary["colors"].items()),
        )
        if summary["preview"] is not None:
            self.photo = ImageTk.PhotoImage(summary["preview"])
            self.preview.configure(image=self.photo, text="")
        else:
            self.photo = None
            self.preview.configure(image="", text="Sin imágenes guardadas")
        set_value(self.storage, "Destino: " + str(summary["root"]))

    def show_saved(self, path, counts):
        self.request_summary()

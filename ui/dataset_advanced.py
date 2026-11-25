"""Guía de cobertura y derivados por archivo; nunca reescribe originales."""

import copy
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from dataset.storage import safe_path
from dataset.tools import review
from dataset.normalize import derive, records, set_derivative_review
from ui.dataset_view import dataset_summary


class DatasetAdvanced:
    def __init__(self, tab):
        self.tab = tab
        self.app = tab.app
        self.root = self.app.dataset.root
        self.results = queue.Queue(maxsize=4)
        self.photos = []
        self.window, body = tab.dialog(
            "Cobertura, contexto y normalización por archivo"
        )
        self.window.geometry("920x690")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.closed = False
        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True)
        guide = ttk.Frame(notebook, padding=10)
        normal = ttk.Frame(notebook, padding=10)
        notebook.add(guide, text="Plan y contexto")
        notebook.add(normal, text="Revisar orientación / recorte")
        self.coverage = tk.Text(guide, height=12, wrap="word", font=("Consolas", 10))
        self.coverage.pack(fill="both", expand=True)
        ttk.Label(
            guide,
            text="Guía por combinación (50): 10 cerca · 15 media · 10 lejos · 10 ángulos · 5 iluminación.\nPositivos: 9 combinaciones × 50 = 450. Negativos no_objetivo: 100–150 adicionales.\nLas cuotas orientan la toma; no bloquean capturas ni certifican diversidad.",
            wraplength=830,
        ).pack(fill="x", pady=6)
        self.context = {}
        for key, title in [
            ("distance", "Distancia"),
            ("perspective", "Perspectiva"),
            ("lighting", "Iluminación"),
            ("shade", "Tono"),
        ]:
            row = ttk.Frame(guide)
            row.pack(fill="x")
            ttk.Label(row, text=title, width=16).pack(side="left")
            var = tk.StringVar(value=tab.capture_context.get(key, ""))
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
            self.context[key] = var
        ttk.Button(
            guide,
            text="Usar contexto en siguientes capturas / ráfaga",
            command=self.set_context,
        ).pack(pady=5)
        self.selected = tk.StringVar()
        self.choice = ttk.Combobox(normal, textvariable=self.selected, state="readonly")
        self.choice.pack(fill="x")
        self.choice.bind("<<ComboboxSelected>>", lambda e: self.preview())
        self.orientation = tk.StringVar(value="Usar metadatos del archivo")
        self.rotations = {
            "Usar metadatos del archivo": None,
            "Original (0°)": 0,
            "90° izquierda": 270,
            "90° derecha": 90,
            "180°": 180,
        }
        ttk.Combobox(
            normal,
            textvariable=self.orientation,
            values=list(self.rotations),
            state="readonly",
        ).pack(fill="x", pady=4)
        ttk.Label(
            normal,
            text="La opción de metadatos usa la transformación registrada de ese archivo.\nPara orientación desconocida seleccione explícitamente una rotación tras revisar el original.\nEl ajuste actual de la cámara no se impone a capturas antiguas.",
            wraplength=820,
        ).pack(fill="x")
        actions = ttk.Frame(normal)
        actions.pack(fill="x", pady=5)
        ttk.Button(
            actions, text="Ver original y recorte registrado", command=self.preview
        ).pack(side="left")
        ttk.Button(
            actions, text="Crear derivado normalizado nuevo…", command=self.normalize
        ).pack(side="left", padx=8)
        review_bar = ttk.Frame(normal)
        review_bar.pack(fill="x")
        self.derivative = tk.StringVar()
        self.derivative_choice = ttk.Combobox(
            review_bar, textvariable=self.derivative, state="readonly", width=40
        )
        self.derivative_choice.pack(side="left", fill="x", expand=True)
        self.derivative_choice.bind("<<ComboboxSelected>>", self.preview_derivative)
        for state, title in (
            ("aceptada", "Aceptar"),
            ("rechazada", "Rechazar"),
            ("sin_revisar", "Pendiente"),
        ):
            ttk.Button(
                review_bar,
                text=title,
                command=lambda s=state: self.review_derivative(s),
            ).pack(side="left")
        self.preview_label = ttk.Label(normal, anchor="center")
        self.preview_label.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Lectura local en curso…")
        ttk.Label(body, textvariable=self.status, wraplength=830).pack(fill="x")
        self.submit(lambda: (review(self.root), dataset_summary(self.root)), "loaded")
        self.poll()

    def submit(self, fn, kind):
        def task():
            try:
                value = fn()
            except Exception as exc:
                kind_result, value = "error", str(exc)
            else:
                kind_result = kind
            try:
                self.results.put_nowait((kind_result, value))
            except queue.Full:
                pass

        self.app.job(task)

    def set_context(self):
        from dataset.capture import validate_context

        try:
            context = {k: v.get() for k, v in self.context.items() if v.get()}
            validate_context(context)
            self.tab.capture_context = context
            self.status.set(
                "Contexto guardado para siguientes capturas; una ráfaga en curso conserva el suyo"
            )
        except Exception as exc:
            messagebox.showerror("Contexto", str(exc), parent=self.window)

    def make_preview(self, paths):
        canvas = Image.new("RGB", (800, 300), "#e8edf4")
        x = 0
        for path in paths:
            if not path:
                continue
            with Image.open(safe_path(self.root, path)) as image:
                image = image.convert("RGB")
                image.thumbnail((390, 290))
                canvas.paste(
                    image, (x + (390 - image.width) // 2, (300 - image.height) // 2)
                )
                x += 400
        return canvas

    def preview(self):
        record = next(
            (
                r
                for r in getattr(self, "rows", [])
                if r["original"] == self.selected.get()
            ),
            None,
        )
        if record:

            def task():
                return self.make_preview([record["original"], record.get("crop")]), [
                    r["normalized"]
                    for r in records(self.root)
                    if r["original"] == record["original"]
                ]

            self.submit(task, "original_preview")

    def review_derivative(self, state):
        name = self.derivative.get()
        if not name:
            return

        def task():
            set_derivative_review(self.root, name, state)
            return "Revisión del derivado: " + state + "; regenerar división"

        self.submit(task, "reviewed")

    def preview_derivative(self, event=None):
        paths = [self.selected.get(), self.derivative.get()]
        self.submit(lambda: self.make_preview(paths), "preview")

    def normalize(self):
        original = self.selected.get()
        if not original:
            return
        rotation = self.rotations[self.orientation.get()]
        config = copy.deepcopy(self.app.config)
        if not messagebox.askyesno(
            "Crear derivado",
            "¿Crear un archivo nuevo para este original?\nLa operación conserva el original y deja el derivado sin revisar; invalida la división anterior.",
            parent=self.window,
        ):
            return

        def task():
            self.app.vision_guard()
            item = derive(self.root, original, config, rotation)
            return item, self.make_preview([original, item["normalized"]])

        self.submit(task, "derived")

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, value = self.results.get_nowait()
                if kind == "loaded":
                    self.rows, summary = value
                    names = [r["original"] for r in self.rows]
                    self.choice.configure(values=names)
                    self.selected.set(names[0] if names else "")
                    text = "Forma                    rojo    verde    azul   total\n"
                    for shape, colors in summary["combinations"].items():
                        text += (
                            f"{shape:24}"
                            + "".join(f"{n:8}" for n in colors.values())
                            + f"{sum(colors.values()):8}\n"
                        )
                    text += f'\nPositivos: {summary["total"]}/450\nNegativos: {summary["negatives"]}/100–150 (aparte)'
                    self.coverage.insert("1.0", text)
                    self.coverage.configure(state="disabled")
                    self.status.set(
                        "Original y recorte se muestran por separado. Sin CNN ni entrenamiento."
                    )
                    self.preview()
                elif kind == "error":
                    self.status.set(value)
                elif kind == "reviewed":
                    self.status.set(value)
                else:
                    if kind == "original_preview":
                        value, names = value
                        self.derivative_choice.configure(values=names)
                        self.derivative.set(names[-1] if names else "")
                    if kind == "derived":
                        item, value = value
                        self.status.set(
                            "Nuevo derivado: "
                            + item["normalized"]
                            + " · pendiente de revisión"
                        )
                        names = list(self.derivative_choice.cget("values")) + [
                            item["normalized"]
                        ]
                        self.derivative_choice.configure(values=names)
                        self.derivative.set(item["normalized"])
                    photo = ImageTk.PhotoImage(value)
                    self.photos = [photo]
                    self.preview_label.configure(image=photo)
        except queue.Empty:
            pass
        self.timer = self.window.after(150, self.poll)

    def close(self):
        self.closed = True
        if hasattr(self, "timer"):
            self.window.after_cancel(self.timer)
        self.window.destroy()

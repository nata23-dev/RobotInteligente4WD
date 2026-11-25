"""Estudio de captura: contadores derivados únicamente de originales reales."""

import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from dataset.capture import SHAPES, COLORS, CAPTURE_SHAPES, CAPTURE_COLORS
from ui.dataset_view import dataset_summary
from ui.preferences import load_goal, save_goal
from ui.components.widgets import Card, Metric, Video, label, button, set_value
from app.models import Frame

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
        self.capture_context = {}
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
        for variable in (self.shape, self.color, self.session):
            variable.trace_add("write", lambda *_: self.check_burst_labels())
        for i, (name, var, choices) in enumerate(
            (
                ("Forma", self.shape, CAPTURE_SHAPES),
                ("Color", self.color, CAPTURE_COLORS),
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
            lambda: app.capture(
                self.shape.get(),
                self.color.get(),
                self.session.get(),
                metadata=self.capture_context,
            ),
            style="Primary.TButton",
        )
        self.capture_button.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.burst = button(row, "Ráfaga", self.burst_dialog, state="disabled")
        self.burst.pack(side="left")
        button(row, "Herramientas", self.tools_dialog, style="Compact.TButton").pack(
            side="left", padx=(4, 0)
        )
        self.burst_labels = None
        self.burst_message = tk.StringVar(value="Ráfaga inactiva")
        self.quality_message = tk.StringVar(value="Sin evaluación de calidad")
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

    def update_video(self, snap):
        from ui.video_source import original_snapshot

        view = original_snapshot(self.app, snap)
        self.video.update_frame(view)
        if view["fresh"]:
            frame = view["frame"]
            h, w = snap["frame"].image.shape[:2]
            set_value(
                self.video.metrics,
                f"Recibida {w} × {h} · Vista {frame.image.shape[1]} × {frame.image.shape[0]} · {frame.fps:.1f} FPS · {frame.source}",
            )

    def dialog(self, title):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("720x560")
        dialog.minsize(640, 450)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        bar = ttk.Frame(dialog, padding=10)
        bar.grid(row=0, column=0, sticky="ew")
        label(bar, title, style="PageTitle.TLabel").pack(side="left")
        button(
            bar,
            "STOP GLOBAL",
            lambda: self.app.dispatcher.stop(),
            style="Danger.TButton",
        ).pack(side="right")
        dialog.bind("<Escape>", lambda e: self.app.dispatcher.stop())
        body = ttk.Frame(dialog, padding=12)
        body.grid(row=1, column=0, sticky="nsew")
        return dialog, body

    def burst_dialog(self):
        dialog, body = self.dialog("Captura por ráfagas")
        options = self.app.config["dataset_options"]
        self.burst_count = tk.StringVar(value=str(options["burst_count"]))
        self.burst_interval = tk.StringVar(value=str(options["burst_interval_s"]))
        label(
            body,
            "Usará las etiquetas actuales. Cada muestra requiere un frame nuevo y fresco.\nEl armado, movimiento, cambio de etiquetas, pérdida de cámara o cierre cancelan la ráfaga.",
            wraplength=650,
        ).pack(anchor="w", pady=8)
        label(body, "Cantidad (1–100)").pack(anchor="w")
        ttk.Entry(body, textvariable=self.burst_count, width=12).pack(anchor="w")
        label(body, "Intervalo en segundos (0.2–60)").pack(anchor="w", pady=(8, 0))
        ttk.Entry(body, textvariable=self.burst_interval, width=12).pack(anchor="w")

        def start():
            labels = (self.shape.get(), self.color.get(), self.session.get())
            self.app.start_burst(
                *labels,
                int(self.burst_count.get()),
                float(self.burst_interval.get()),
                metadata=self.capture_context,
            )
            self.burst_labels = labels

        button(
            body,
            "Iniciar ráfaga",
            lambda: self.winfo_toplevel().run(start),
            style="Primary.TButton",
        ).pack(anchor="w", pady=12)
        button(body, "Cancelar ráfaga", lambda: self.app.job(self.app.burst.stop)).pack(
            anchor="w"
        )
        label(body, textvariable=self.burst_message, wraplength=650).pack(
            anchor="w", pady=8
        )
        label(body, textvariable=self.quality_message, wraplength=650).pack(anchor="w")

        def close():
            self.app.burst.cancel.set()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close)

    def check_burst_labels(self):
        if (
            self.app.burst.running
            and self.burst_labels
            and self.burst_labels
            != (self.shape.get(), self.color.get(), self.session.get())
        ):
            self.app.burst.cancel.set()

    def burst_status(self, payload):
        set_value(
            self.burst_message,
            f'{payload["saved"]}/{payload["total"]} · {payload["reason"]}',
        )
        if payload["done"]:
            self.burst_labels = None

    def quality_status(self, payload):
        set_value(
            self.quality_message,
            f'Brillo {payload["brightness_mean"]:.1f} · Nitidez {payload["sharpness_laplacian"]:.1f}\n'
            + (
                "; ".join(payload["warnings"])
                or "Sin advertencias del perfil provisional"
            ),
        )

    def tools_dialog(self):
        dialog, body = self.dialog("Revisión y sesiones")
        label(
            body,
            "Las advertencias no eliminan originales. Los umbrales se ajustan en Configuración.\nLa división requiere al menos tres sesiones balanceadas e independientes.",
            wraplength=650,
        ).pack(anchor="w", pady=6)
        row = ttk.Frame(body)
        row.pack(fill="x")

        def review():
            from dataset.tools import review

            root = self.app.dataset.root
            self.app.job(lambda: self.app.event("dataset_review", review(root)))

        def split():
            from dataset.tools import split_sessions

            root = self.app.dataset.root

            def task():
                result = split_sessions(root)
                self.app.event("dataset_split", result)
                self.app.event(
                    "info",
                    f'División guardada por {len(result["sessions"])} sesiones en metadata/split_sessions.json',
                )

            self.app.job(task)

        button(row, "Revisar calidad y recortes", review).pack(side="left", padx=(0, 8))
        button(row, "Preparar división 70/15/15", split).pack(side="left")

        def advanced():
            from ui.dataset_advanced import DatasetAdvanced

            DatasetAdvanced(self)

        button(body, "Cobertura, contexto y orientación por archivo…", advanced).pack(
            fill="x", pady=6
        )
        self.review_selection = tk.StringVar()
        self.review_choice = ttk.Combobox(
            body, textvariable=self.review_selection, state="readonly"
        )
        self.review_choice.pack(fill="x", pady=(8, 4))
        decisions = ttk.Frame(body)
        decisions.pack(fill="x")

        def decide(state):
            from dataset.tools import set_review

            root = self.app.dataset.root
            name = self.review_selection.get()

            def task():
                set_review(root, name, state)
                from dataset.tools import review as read_review

                self.app.event("dataset_review", read_review(root))
                self.app.event(
                    "info",
                    "Revisión guardada: " + state + "; regenerar división si existía",
                )

            self.app.job(task)

        for state, title in [
            ("aceptada", "Aceptar"),
            ("rechazada", "Rechazar"),
            ("sin_revisar", "Sin revisar"),
        ]:
            button(
                decisions,
                title,
                lambda state=state: decide(state),
                style="Compact.TButton",
            ).pack(side="left", padx=(0, 8))
        self.review_text = tk.Text(body, wrap="word", font=("Consolas", 9), height=16)
        self.review_text.pack(fill="both", expand=True, pady=8)
        review()

    def show_review(self, rows):
        widget = getattr(self, "review_text", None)
        if widget is None or not widget.winfo_exists():
            return
        names = [r["original"] for r in rows]
        self.review_choice.configure(values=names)
        if self.review_selection.get() not in names:
            self.review_selection.set(names[0] if names else "")
        widget.delete("1.0", "end")
        for r in rows:
            widget.insert(
                "end",
                f'{r["original"]}\n{r["shape"]}/{r["color"]} · {r["session"]} · {r["source"]} · revisión {r["review"]}\nRecorte: {r.get("crop")} / ROI {r.get("roi")}\n'
                + ("; ".join(r["quality"]["warnings"]) or "Sin advertencias")
                + "\n\n",
            )
        if not rows:
            widget.insert(
                "end",
                "No hay registros de calidad. Los originales anteriores siguen en el manifiesto CSV.",
            )

    def show_split(self, result):
        widget = getattr(self, "review_text", None)
        if widget is None or not widget.winfo_exists():
            return
        widget.delete("1.0", "end")
        widget.insert(
            "end",
            f'División por sesiones · semilla {result["seed"]}\nHabilitada para entrenamiento: {result["training_ready"]}\n\n',
        )
        for subset, summary in result["summary"].items():
            widget.insert(
                "end",
                f'{subset}: {summary["total"]} originales\nFormas: {summary["shapes"]}\nColores: {summary["colors"]}\n\n',
            )
        widget.insert("end", "\n".join(result["warnings"]))

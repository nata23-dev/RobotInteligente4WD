"""Calibración integrada: reutiliza la cámara; análisis fuera del hilo Tk."""

import copy
import tkinter as tk
from tkinter import ttk
import cv2
from app.config import defaults
from app.models import Frame
from ai.perception import Perception
from ui.components.widgets import Video, label, button, set_value


class VisionPanel:
    def __init__(self, tab):
        self.tab = tab
        self.app = tab.app
        self.pending = False
        self.result = None
        self.last = None
        p = tab.section("Visión artificial", "Orientación y captura real", "camera")
        label(
            p,
            "Captura remota: pendiente de verificar con cámara real.\nVGA 640 × 480 y QVGA 320 × 240: propuestas para evaluación.\nJPEG, brillo, contraste, saturación, exposición, balance, nitidez y enfoque: sin controles remotos verificados.",
            style="Muted.TLabel",
            wraplength=650,
        ).pack(anchor="w")
        tab.form(
            p,
            [
                ("vision.rotation", "Rotación horaria (0,90,180,270)", int),
                ("vision.flip_horizontal", "Inversión horizontal", bool),
                ("vision.flip_vertical", "Inversión vertical", bool),
            ],
        )
        self.orientation_labels = {
            "Original (0°)": 0,
            "90° izquierda": 270,
            "90° derecha": 90,
            "180°": 180,
        }
        self.orientation = tk.StringVar()
        old = tab.form_widgets["vision.rotation"]
        old.grid_remove()
        combo = ttk.Combobox(
            old.master,
            textvariable=self.orientation,
            values=list(self.orientation_labels),
            state="readonly",
        )
        combo.grid(row=0, column=1, sticky="ew", pady=5)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda e: tab.fields["vision.rotation"].set(
                str(self.orientation_labels[self.orientation.get()])
            ),
        )
        button(
            p, "Calibrador de colores…", self.open_calibrator, style="Primary.TButton"
        ).pack(anchor="w", pady=8)
        p = tab.section(
            "Visión artificial",
            "Ajustes digitales locales · no aumentan resolución",
            "settings",
        )
        tab.form(
            p,
            [
                (f"vision.digital.{k}", title, float)
                for k, title in [
                    ("brightness", "Brillo (−40 a 40)"),
                    ("contrast", "Contraste (0.7 a 1.3)"),
                    ("saturation", "Saturación (0.7 a 1.3)"),
                    ("gamma", "Gamma (0.7 a 1.4)"),
                    ("sharpness", "Nitidez (0 a 1)"),
                ]
            ],
        )
        button(p, "Restablecer digitales", lambda: self.reset("digital")).pack(
            anchor="w", pady=5
        )
        p = tab.section(
            "Visión artificial",
            "Calibración HSV · perfiles iniciales provisionales",
            "settings",
        )
        self.color = tk.StringVar(value="rojo")
        choice = ttk.Combobox(
            p,
            textvariable=self.color,
            values=["rojo", "verde", "azul", "combinada"],
            state="readonly",
            width=20,
        )
        choice.pack(anchor="w")
        self.color_forms = {}
        for color, n in [("rojo", 2), ("verde", 1), ("azul", 1)]:
            form = ttk.Frame(p, style="Surface.TFrame")
            self.color_forms[color] = form
            for index in range(n):
                label(
                    form,
                    f"{color.capitalize()} · intervalo {index+1}",
                    font=("Segoe UI", 10, "bold"),
                ).grid(row=index * 3, column=0, columnspan=6, sticky="w", pady=(12, 2))
                for j, name in enumerate(
                    [
                        "H mínimo",
                        "S mínimo",
                        "V mínimo",
                        "H máximo",
                        "S máximo",
                        "V máximo",
                    ]
                ):
                    path = f"vision.hsv.{color}.{index}.{j}"
                    var = tk.StringVar()
                    tab.fields[path] = var
                    tab.types[path] = int
                    row = index * 3 + 1 + j // 3
                    col = (j % 3) * 2
                    label(form, name).grid(row=row, column=col, padx=(0, 6), pady=3)
                    widget = ttk.Entry(form, textvariable=var, width=6)
                    widget.grid(row=row, column=col + 1, padx=(0, 12), pady=3)
                    tab.form_widgets[path] = widget

        def show_color(_=None):
            for color, form in self.color_forms.items():
                if color == self.color.get() or (
                    self.color.get() == "combinada" and color == "rojo"
                ):
                    form.pack(fill="x", after=choice)
                else:
                    form.pack_forget()

        choice.bind("<<ComboboxSelected>>", show_color)
        show_color()
        tab.form(
            p,
            [
                ("vision.open_kernel", "Apertura (impar,1–15)", int),
                ("vision.close_kernel", "Cierre (impar,1–15)", int),
                ("vision.min_area", "Área mínima (px²)", int),
                ("vision.max_area_ratio", "Área máxima relativa", float),
            ],
        )
        row = ttk.Frame(p, style="Surface.TFrame")
        row.pack(fill="x", pady=8)
        button(
            row, "Previsualizar perfil del formulario", lambda: tab.run(self.preview)
        ).pack(side="left")
        button(row, "Restablecer HSV", lambda: self.reset("hsv")).pack(
            side="left", padx=5
        )
        label(
            p,
            "Guardar y aplicar conserva el perfil en la configuración privada.\nLa máscara usa el mismo stream. H: 0–179; S y V: 0–255.",
            style="Muted.TLabel",
        ).pack(anchor="w")
        self.video = Video(p, "Máscara de calibración")
        self.video.configure(height=300)
        self.video.pack(fill="x", pady=8)
        self.video.grid_propagate(False)
        self.sample = tk.StringVar(
            value="Pulse sobre la máscara para consultar BGR / HSV de ese píxel."
        )
        label(p, textvariable=self.sample, style="Muted.TLabel", wraplength=650).pack(
            anchor="w"
        )
        self.video.label.bind("<Button-1>", self.pixel)
        p = tab.section(
            "Visión artificial", "Región de agarre y seguimiento visual", "target"
        )
        tab.form(
            p,
            [
                (f"vision.grip_roi.{i}", title, float)
                for i, title in enumerate(
                    [
                        "X normalizada",
                        "Y normalizada",
                        "Ancho normalizado",
                        "Alto normalizado",
                    ]
                )
            ]
            + [
                ("vision.crop_margin", "Margen del recorte (0–0.5)", float),
                ("vision.tracking_radius", "Radio de continuidad (0.01–1)", float),
                ("vision.lost_frames", "Frames antes de cambiar objetivo", int),
            ],
        )
        label(
            p,
            "ROI en coordenadas normalizadas, después de orientar. Presencia en ROI no confirma agarre.",
            style="Muted.TLabel",
            wraplength=650,
        ).pack(anchor="w")
        tab.form(
            p,
            [
                (f"vision.overlays.{k}", title, bool)
                for k, title in [
                    ("objects", "Cajas, colores y centroides"),
                    ("target", "Objetivo seleccionado"),
                    ("axis", "Eje de alineación"),
                    ("roi", "Región de agarre"),
                    ("markers", "ArUco y estaciones"),
                ]
            ],
        )

    def reset(self, section):
        if section == "hsv":
            config = self.tab.read()
            config["vision"]["hsv"] = defaults()["vision"]["hsv"]
            config["vision"]["interval_meta"] = defaults()["vision"]["interval_meta"]
            self.tab.populate(config)
            return
        profile = defaults()["vision"][section]
        for path, var in self.tab.fields.items():
            prefix = "vision." + section + "."
            if path.startswith(prefix):
                value = profile
                for k in path[len(prefix) :].split("."):
                    value = value[int(k) if isinstance(value, list) else k]
                var.set(value)

    def preview(self):
        if self.pending:
            return
        config = self.tab.read()
        camera = self.app.camera
        color = self.color.get()
        self.pending = True

        def task():
            try:
                snap = camera.snapshot()
                if not snap["fresh"]:
                    raise ValueError("Inicie cámara antes de previsualizar")
                result = Perception(config["vision"]).process(snap["frame"])
                self.app.event("vision_preview", (camera, result, color))
            finally:
                self.pending = False

        if not self.app.job(task):
            self.pending = False

    def apply_preview(self, payload):
        camera, result, color = payload
        if camera is not self.app.camera:
            return
        self.result = result
        self.last = color
        self.refresh()

    def refresh(self):
        import time

        snap = self.app.camera.snapshot()
        now = time.monotonic()
        if (
            self.tab.category == "Visión artificial"
            and snap["fresh"]
            and not self.pending
            and now - getattr(self, "requested_at", 0) > 0.3
        ):
            self.requested_at = now
            self.tab.run(self.preview)
        r = self.result
        if r is None:
            return
        snap = self.app.camera.snapshot()
        fresh = (
            snap["fresh"]
            and snap["frame"].generation == r.frame.generation
            and time.monotonic() - r.frame.received_at
            <= self.app.config["frame_max_age_s"]
        )
        f = Frame(
            r.frame.id,
            r.frame.received_at,
            cv2.cvtColor(r.masks[self.last], cv2.COLOR_GRAY2BGR),
            r.frame.fps,
            r.frame.generation,
            r.frame.source,
        )
        self.video.update_frame(dict(snap, frame=f, fresh=fresh))

    def pixel(self, event):
        if not self.result or not self.video.photo:
            return
        r = self.result
        import time

        if time.monotonic() - r.frame.received_at > self.app.config["frame_max_age_s"]:
            return
        h, w = r.processing.shape[:2]
        x = min(w - 1, max(0, int(event.x * w / self.video.photo.width())))
        y = min(h - 1, max(0, int(event.y * h / self.video.photo.height())))
        hsv = cv2.cvtColor(r.processing, cv2.COLOR_BGR2HSV)[y, x]
        set_value(
            self.sample,
            f"({x},{y}) BGR={r.processing[y,x].tolist()} HSV={hsv.tolist()} · Frame {r.frame.id}",
        )

    def sync_orientation(self):
        value = int(self.tab.fields["vision.rotation"].get())
        self.orientation.set(
            next(
                (
                    label
                    for label, degree in self.orientation_labels.items()
                    if degree == value
                ),
                "Original (0°)",
            )
        )

    def open_calibrator(self):
        if (
            getattr(self, "calibrator", None) is not None
            and self.calibrator.window.winfo_exists()
        ):
            self.calibrator.window.lift()
            return
        from ui.color_calibrator import Calibrator

        self.calibrator = Calibrator(self.tab, self.app)

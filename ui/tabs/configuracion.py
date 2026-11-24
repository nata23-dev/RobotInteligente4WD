"""Formularios de presentación sobre el schema y validaciones originales."""

import copy
import tkinter as tk
from tkinter import ttk
from app.config import defaults, validate
from ui.components.widgets import (
    Card,
    ScrollFrame,
    Badge,
    label,
    button,
    confirm,
    set_value,
)

CATEGORIES = (
    "Conectividad",
    "Hardware",
    "Calibración",
    "Visión artificial",
    "Inteligencia artificial",
    "Estaciones",
    "Mantenimiento",
)


class ConfigTab(ttk.Frame):
    def __init__(self, parent, app, run):
        super().__init__(parent)
        self.app, self.run = app, run
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        menu = Card(self, padding=8)
        menu.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.nav = {}
        self.pages = {}
        self.fields = {}
        self.form_widgets = {}
        self.types = {}
        for name in CATEGORIES:
            b = button(
                menu.body,
                name,
                lambda name=name: self.select_category(name),
                style="Nav.TButton",
                width=21,
            )
            b.pack(fill="x", pady=2)
            self.nav[name] = b
        self.container = ttk.Frame(self)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)
        for name in CATEGORIES:
            page = ScrollFrame(self.container)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page
        self.diagnostics = tk.StringVar(value="Firmware y API sin verificar")
        self.build_connectivity()
        self.build_hardware()
        self.build_calibration()
        self.build_vision()
        self.build_ai()
        self.build_stations()
        self.build_maintenance()
        actions = ttk.Frame(self)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.save_button = button(
            actions,
            "Guardar y aplicar",
            lambda: run(self.save),
            style="Primary.TButton",
        )
        self.save_button.pack(side="right")
        self.feedback = tk.StringVar(
            value="Cambios locales sin aplicar. Guardar requiere robot desarmado."
        )
        label(
            actions, textvariable=self.feedback, style="Caption.TLabel", wraplength=700
        ).pack(side="left")
        self.populate(app.config)
        self.select_category(CATEGORIES[0])

    def section(self, name, title, symbol):
        card = Card(self.pages[name].body, title, symbol, padding=12)
        card.pack(fill="x", pady=(0, 8))
        return card.body

    def form(self, parent, specs):
        form = ttk.Frame(parent, style="Surface.TFrame")
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        for row, (path, title, kind) in enumerate(specs):
            label(form, title).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=5)
            var = tk.BooleanVar() if kind is bool else tk.StringVar()
            self.fields[path] = var
            self.types[path] = kind
            entry = (
                ttk.Checkbutton(
                    form, variable=var, text="Simulación (desmarcar para hardware real)"
                )
                if kind is bool
                else ttk.Entry(
                    form,
                    textvariable=var,
                    show="●" if path == "api_key" else "",
                    width=30,
                )
            )
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            self.form_widgets[path] = entry
        return form

    def build_connectivity(self):
        p = self.section("Conectividad", "Conexión del robot", "wifi")
        self.form(
            p,
            [
                ("robot_url", "Dirección HTTP del ESP32", str),
                ("camera_url", "URL del video", str),
                ("api_key", "Clave API local", str),
                ("simulation", "Equipo de destino", bool),
                ("timeout_s", "Timeout HTTP (s)", float),
                ("heartbeat_s", "Heartbeat (s)", float),
            ],
        )
        self.key = self.fields["api_key"]
        row = ttk.Frame(p, style="Surface.TFrame")
        row.pack(fill="x", pady=(8, 0))
        button(
            row, "Verificar conexión / API", lambda: app_command(self.app, "verify")
        ).pack(side="left", padx=(0, 8))
        button(row, "Iniciar video", lambda: self.app.job(self.app.camera.start)).pack(
            side="left", padx=(0, 8)
        )
        button(row, "Detener video", lambda: self.app.job(self.app.camera.stop)).pack(
            side="left"
        )
        label(
            p, textvariable=self.diagnostics, style="Muted.TLabel", wraplength=600
        ).pack(anchor="w", pady=(8, 0))
        label(
            p,
            "La verificación usa la configuración aplicada. Guardar nunca conecta ni arma.",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=(4, 0))

    def build_hardware(self):
        p = self.section("Hardware", "Patrones de movimiento · referencia V7", "wheel")
        label(
            p,
            "Orden: FL, FR, RL, RR. Signos −1, 0, +1. Pendientes de validación física.",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w")
        self.pattern_name = tk.StringVar(value="adelante")
        select = ttk.Combobox(
            p,
            textvariable=self.pattern_name,
            values=list(defaults()["patterns"]),
            state="readonly",
            width=36,
        )
        select.pack(fill="x", pady=12)
        select.bind("<<ComboboxSelected>>", lambda e: self.show_pattern())
        row = ttk.Frame(p, style="Surface.TFrame")
        row.pack(fill="x")
        self.pattern_values = []
        for i, wheel in enumerate(
            ("FL · del. izq.", "FR · del. der.", "RL · tras. izq.", "RR · tras. der.")
        ):
            row.columnconfigure(i, weight=1)
            label(row, wheel, style="Muted.TLabel").grid(row=0, column=i, padx=4)
            var = tk.StringVar()
            self.pattern_values.append(var)
            widget = ttk.Combobox(
                row,
                textvariable=var,
                values=["-1", "0", "1"],
                state="readonly",
                width=5,
            )
            widget.grid(row=1, column=i, padx=4, pady=8)
            var.trace_add("write", lambda *_: self.pattern_changed())
        button(p, "Intercambiar izquierda ↔ derecha", lambda: self.run(self.swap)).pack(
            anchor="w", pady=8
        )
        label(
            p,
            "FL GPIO26/25 · FR 33/32 · RL 13/12 · RR 14/27\nENA/ENB con jumpers: dirección y pulso, sin PWM de velocidad.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=8)

    def build_calibration(self):
        p = self.section("Calibración", "Pulsos y límites seguros", "settings")
        self.form(
            p,
            [
                ("pulse_ms", "Pulso inicial (ms)", int),
                ("pulse_min_ms", "Pulso mínimo (ms)", int),
                ("pulse_max_ms", "Pulso máximo (ms)", int),
                ("servos.garra.min", "Garra · mínimo (°)", int),
                ("servos.garra.max", "Garra · máximo (°)", int),
                ("servos.garra.closed", "Cierre provisional (°)", int),
                ("servos.base.min", "Base · mínimo (°)", int),
                ("servos.base.max", "Base · máximo (°)", int),
            ],
        )
        label(
            p,
            "HOME del firmware: garra 60° / base 75°. Ángulos ordenados, sin sensor físico.",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=8)
        p = self.section("Calibración", "Registrar medición humana", "clock")
        self.movement = tk.StringVar(value="adelante")
        self.ms = tk.StringVar(value="150")
        self.measurement = tk.StringVar()
        self.unit = tk.StringVar(value="cm")
        ttk.Combobox(
            p,
            textvariable=self.movement,
            values=list(defaults()["patterns"]),
            state="readonly",
        ).pack(fill="x", pady=4)
        row = ttk.Frame(p, style="Surface.TFrame")
        row.pack(fill="x")
        for title, var in [("Pulso ms", self.ms), ("Medición", self.measurement)]:
            label(row, title).pack(side="left", padx=4)
            ttk.Entry(row, textvariable=var, width=7).pack(side="left", padx=4)
        ttk.Combobox(
            row,
            textvariable=self.unit,
            values=["cm", "grados"],
            state="readonly",
            width=8,
        ).pack(side="left", padx=4)
        button(
            p,
            "Registrar prueba ya realizada",
            lambda: self.run(
                lambda: self.app.record_calibration(
                    self.movement.get(),
                    int(self.ms.get()),
                    float(self.measurement.get()),
                    self.unit.get(),
                )
            ),
        ).pack(anchor="w", pady=8)

    def build_vision(self):
        p = self.section("Visión artificial", "Recepción de cámara", "camera")
        self.form(
            p,
            [
                ("camera_retry_s", "Espera de reconexión (s)", float),
                ("camera_timeout_ms", "Timeout de captura (ms)", int),
                ("frame_max_age_s", "Antigüedad máxima (s)", float),
                ("dataset_dir", "Directorio del dataset", str),
            ],
        )
        label(p, "HSV y regiones de interés", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(16, 4)
        )
        label(
            p,
            "Pendientes de implementación y calibración con cámara real.",
            style="Muted.TLabel",
        ).pack(anchor="w")
        button(p, "Editar HSV / ROI · pendiente", state="disabled").pack(
            anchor="w", pady=8
        )

    def build_ai(self):
        p = self.section("Inteligencia artificial", "Módulos de decisión", "brain")
        for title, status in [
            ("CNN de formas", "Sin modelo entrenado"),
            ("Lógica difusa", "Sin reglas implementadas"),
            ("Heurística autónoma", "Pendiente de integración"),
        ]:
            row = ttk.Frame(p, style="Surface.TFrame")
            row.pack(fill="x", pady=8)
            label(row, title, font=("Segoe UI", 11, "bold")).pack(side="left")
            Badge(row, status, "neural").pack(side="right")
        button(p, "Seleccionar modelo · pendiente", state="disabled").pack(
            anchor="w", pady=8
        )
        button(p, "Editar reglas difusas · pendiente", state="disabled").pack(
            anchor="w", pady=4
        )

    def build_stations(self):
        p = self.section("Estaciones", "Estaciones de clasificación", "target")
        label(p, "Diccionario DICT_4X4_50", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=8
        )
        for text, value in [
            ("Cubos", 0),
            ("Cilindros", 1),
            ("Prismas triangulares", 2),
        ]:
            row = ttk.Frame(p, style="Surface.TFrame")
            row.pack(fill="x", pady=8)
            label(row, text).pack(side="left")
            Badge(row, f"ID {value}", "primary").pack(side="right")
        label(
            p,
            "Contrato fijado para esta fase. Detección y navegación pendientes.",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=12)
        button(p, "Configurar navegación · pendiente", state="disabled").pack(
            anchor="w"
        )

    def build_maintenance(self):
        p = self.section(
            "Mantenimiento", "Seguridad, registros y diagnóstico", "shield"
        )
        self.form(p, [("controller_lease_s", "Salud del controlador (s)", float)])
        self.performance = tk.StringVar(value="Métricas sin muestras")
        label(
            p, textvariable=self.performance, style="Muted.TLabel", wraplength=600
        ).pack(anchor="w", pady=8)
        label(
            p,
            "Robot4WD 1.0.0 / API 1 · Aplicación Fase 01.1\nSTOP conserva PWM y no corta alimentación física. Rearme siempre explícito.",
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=12)
        button(p, "Exportar registros", self.app.export_logs).pack(anchor="w", pady=8)
        button(p, "Restaurar valores iniciales…", self.restore).pack(anchor="w", pady=8)
        button(
            p, "Releer configuración aplicada", lambda: self.populate(self.app.config)
        ).pack(anchor="w", pady=8)

    def select_category(self, name):
        self.pages[name].tkraise()
        self.category = name
        for key, b in self.nav.items():
            b.configure(style="Selected.Nav.TButton" if key == name else "Nav.TButton")

    def populate(self, config):
        self.draft = copy.deepcopy(config)
        self.loading = True
        for path, var in self.fields.items():
            value = config
            for key in path.split("."):
                value = value[key]
            var.set(value)
        self.show_pattern()
        self.loading = False

    def show_pattern(self):
        self.loading = True
        for var, value in zip(
            self.pattern_values, self.draft["patterns"][self.pattern_name.get()]
        ):
            var.set(str(value))
        self.loading = False

    def pattern_changed(self):
        if getattr(self, "loading", True):
            return
        try:
            self.draft["patterns"][self.pattern_name.get()] = [
                int(v.get()) for v in self.pattern_values
            ]
        except ValueError:
            pass

    def read(self):
        config = copy.deepcopy(self.draft)
        for path, var in self.fields.items():
            try:
                value = self.types[path](var.get())
            except (ValueError, tk.TclError) as exc:
                raise ValueError("Valor inválido en " + path) from exc
            obj = config
            keys = path.split(".")
            for key in keys[:-1]:
                obj = obj[key]
            obj[keys[-1]] = value
        return validate(config)

    def save(self):
        config = self.read()
        if config["simulation"] != self.app.config["simulation"]:
            if not confirm(
                "Cambiar equipo de destino",
                "¿Confirma cambiar explícitamente entre simulación y hardware real? Se requiere nueva verificación y armado.",
                self,
            ):
                return
        self.app.update_config(config)
        set_value(self.feedback, "Validación correcta. Aplicando con robot desarmado…")

    def swap(self):
        p = self.draft["patterns"]
        p["izquierda"], p["derecha"] = p["derecha"], p["izquierda"]
        self.show_pattern()
        set_value(
            self.feedback,
            "Laterales intercambiados en formulario. Guarde para aplicar.",
        )

    def restore(self):
        if confirm(
            "Restaurar formularios",
            "¿Cargar valores iniciales en los formularios? Debe guardar para aplicarlos.",
            self,
        ):
            self.populate(defaults())
            set_value(self.feedback, "Valores iniciales cargados, todavía sin aplicar.")


def app_command(app, action):
    app.command(action)

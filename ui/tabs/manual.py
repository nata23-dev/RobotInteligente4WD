"""Controles manuales compactos; se conservan las rutas autorizadas de Fase 01."""

import tkinter as tk
from tkinter import ttk
from ui import theme
from ui.components.widgets import Card, Badge, label, button, confirm, set_value


class ManualTab(ttk.Frame):
    def __init__(self, parent, app, run):
        super().__init__(parent)
        self.app, self.run = app, run
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        connection = Card(self, padding=8)
        connection.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for text, callback, style in [
            ("Verificar conexión", lambda: app.command("verify"), "TButton"),
            ("Armar explícitamente", lambda: app.command("arm"), "Primary.TButton"),
            ("STOP / desarmar", lambda: app.dispatcher.stop(), "Danger.TButton"),
        ]:
            button(connection.body, text, callback, style=style).pack(
                side="left", padx=(0, 8)
            )
        self.session = Badge(connection.body, "Sin sesión")
        self.session.pack(side="right")
        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=5, uniform="panels")
        body.columnconfigure(1, weight=6, uniform="panels")
        body.rowconfigure(0, weight=1)
        chassis = Card(body, "Locomoción", "auto")
        chassis.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        controls = ttk.Frame(chassis.body, style="Surface.TFrame")
        controls.pack(fill="both", expand=True)
        controls.columnconfigure(0, weight=3)
        controls.columnconfigure(1, weight=2)
        controls.rowconfigure(0, weight=1)
        pad = ttk.Frame(controls, style="Surface.TFrame")
        pad.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        directions = [
            ("↖", "diagonal_frente_izquierda"),
            ("↑", "adelante"),
            ("↗", "diagonal_frente_derecha"),
            ("←", "izquierda"),
            ("■", None),
            ("→", "derecha"),
            ("↙", "diagonal_atras_izquierda"),
            ("↓", "atras"),
            ("↘", "diagonal_atras_derecha"),
        ]
        self.drive_buttons = []
        for i, (text, key) in enumerate(directions):
            pad.columnconfigure(i % 3, weight=1, uniform="pad")
            pad.rowconfigure(i // 3, weight=1, uniform="pad")
            callback = (
                (lambda: app.dispatcher.stop())
                if key is None
                else lambda key=key: run(lambda: self.move(key))
            )
            b = button(
                pad,
                text,
                callback,
                style=(
                    "Direction.Danger.TButton"
                    if key is None
                    else (
                        "Direction.Primary.TButton"
                        if i in (1, 3, 5, 7)
                        else "Direction.TButton"
                    )
                ),
                width=2,
            )
            b.grid(row=i // 3, column=i % 3, sticky="nsew", padx=3, pady=3)
            self.drive_buttons.append(b)
        settings = ttk.Frame(controls, style="Surface.TFrame")
        settings.grid(row=0, column=1, sticky="nsew")
        button(
            settings,
            "↶  Giro izquierdo",
            lambda: run(lambda: self.move("girar_izquierda")),
        ).pack(fill="x", pady=3)
        button(
            settings, "↷  Giro derecho", lambda: run(lambda: self.move("girar_derecha"))
        ).pack(fill="x", pady=3)
        label(settings, "Duración del pulso", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(12, 4)
        )
        self.ms = tk.StringVar(value=str(app.config["pulse_ms"]))
        self.pulse = ttk.Spinbox(
            settings, from_=50, to=700, increment=25, textvariable=self.ms, width=7
        )
        self.pulse.pack(fill="x")
        label(settings, "50–700 ms · sin PWM", style="Muted.TLabel").pack(
            anchor="w", pady=5
        )
        self.requested = tk.StringVar(value="Sin movimiento solicitado")
        label(
            chassis.body,
            textvariable=self.requested,
            style="Muted.TLabel",
            wraplength=370,
        ).pack(anchor="w", pady=(8, 0))
        arm = Card(body, "Brazo de altura fija", "arm")
        arm.grid(row=0, column=1, sticky="nsew")
        self.angles = {}
        self.servo_status = {}
        self.servo_limits = {}
        self.angle_inputs = {}
        for name, title in [
            ("garra", "Garra · GPIO21"),
            ("base", "Base horizontal · GPIO18"),
        ]:
            servo = ttk.Frame(arm.body, style="Surface.TFrame")
            servo.pack(fill="x", pady=(0, 8))
            heading = ttk.Frame(servo, style="Surface.TFrame")
            heading.pack(fill="x")
            label(heading, title, font=("Segoe UI", 11, "bold")).pack(side="left")
            status = Badge(heading, "Sin verificar")
            status.pack(side="right")
            self.servo_status[name] = status
            info = tk.StringVar(
                value="Orden: —   ·   Límites "
                + ("35–60°" if name == "garra" else "35–115°")
            )
            self.servo_limits[name] = info
            label(servo, textvariable=info, style="Muted.TLabel").pack(
                anchor="w", pady=(2, 4)
            )
            row = ttk.Frame(servo, style="Surface.TFrame")
            row.pack(fill="x")
            self.angles[name] = tk.StringVar(
                value=str(app.config["servos"][name]["home"])
            )
            limits = app.config["servos"][name]
            button(
                row,
                "−1°",
                lambda name=name: run(lambda: self.fine(name, -1)),
                style="Compact.TButton",
                width=4,
            ).pack(side="left")
            entry = ttk.Spinbox(
                row,
                from_=limits["min"],
                to=limits["max"],
                width=4,
                textvariable=self.angles[name],
            )
            entry.pack(side="left", padx=4)
            self.angle_inputs[name] = entry
            button(
                row,
                "+1°",
                lambda name=name: run(lambda: self.fine(name, 1)),
                style="Compact.TButton",
                width=4,
            ).pack(side="left")
            button(
                row,
                "Enviar",
                lambda name=name: run(
                    lambda: self.servo(name, int(self.angles[name].get()))
                ),
                style="Compact.TButton",
            ).pack(side="left", padx=4)
            button(
                row,
                "Activar",
                lambda name=name: self.enable(name),
                style="Compact.TButton",
            ).pack(side="left")
            button(
                row,
                "Liberar…",
                lambda name=name: self.release(name),
                style="Compact.TButton",
            ).pack(side="left", padx=4)
            quick = ttk.Frame(servo if name == "garra" else row, style="Surface.TFrame")
            if name == "garra":
                quick.pack(fill="x", pady=(6, 0))
            else:
                quick.pack(side="left", padx=4)
            button(
                quick,
                "Abrir 60°" if name == "garra" else "Centro 75°",
                lambda name=name: run(
                    lambda: self.servo(name, app.config["servos"][name]["home"])
                ),
                style="Compact.TButton",
            ).pack(side="left", padx=(0, 6))
            if name == "garra":
                button(
                    quick,
                    "Cerrar provisional",
                    lambda: run(
                        lambda: self.servo(
                            "garra", app.config["servos"]["garra"]["closed"]
                        )
                    ),
                    style="Compact.TButton",
                ).pack(side="left")
        label(
            arm.body,
            "Ángulos ordenados por software. Sin medición de posición ni agarre.",
            style="Muted.TLabel",
            wraplength=440,
        ).pack(anchor="w")
        motors = Card(self, padding=8)
        motors.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        label(
            motors.body,
            "DIAGNÓSTICO DE RUEDAS   ·   Estado lógico; patrones V7 pendientes de validación física",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 4))
        layout = ttk.Frame(motors.body, style="Surface.TFrame")
        layout.pack(fill="x")
        schema = tk.Canvas(
            layout, width=112, height=60, bg=theme.PANEL, highlightthickness=0
        )
        schema.pack(side="left", padx=(0, 12))
        schema.create_rectangle(
            39,
            10,
            73,
            50,
            outline=theme.COLORS["border"],
            fill=theme.COLORS["surface_secondary"],
        )
        schema.create_line(56, 22, 56, 9, arrow="last", fill=theme.BLUE, width=2)
        for x, y, text, tx in (
            (30, 15, "FL", 12),
            (82, 15, "FR", 100),
            (30, 45, "RL", 12),
            (82, 45, "RR", 100),
        ):
            schema.create_rectangle(
                x - 4,
                y - 7,
                x + 4,
                y + 7,
                fill=theme.COLORS["primary_soft"],
                outline=theme.BLUE,
            )
            schema.create_text(
                tx, y, text=text, fill=theme.TEXT, font=("Segoe UI", 9, "bold")
            )
        row = ttk.Frame(layout, style="Surface.TFrame")
        row.pack(side="left", fill="x", expand=True)
        self.motor_status = []
        for i, (wheel, position) in enumerate(
            (
                ("FL", "Del. izq."),
                ("FR", "Del. der."),
                ("RL", "Tras. izq."),
                ("RR", "Tras. der."),
            )
        ):
            row.columnconfigure(i, weight=1, uniform="wheels")
            cell = ttk.Frame(row, style="Surface.TFrame")
            cell.grid(row=0, column=i, sticky="ew", padx=4)
            text = tk.StringVar(value=f"{wheel} · {position}   —")
            self.motor_status.append(text)
            label(cell, textvariable=text, font=("Segoe UI", 9, "bold")).pack(
                anchor="w"
            )
            buttons = ttk.Frame(cell, style="Surface.TFrame")
            buttons.pack(fill="x", pady=(4, 0))
            for direction in (-1, 1):
                button(
                    buttons,
                    f"{direction:+d}",
                    lambda i=i, d=direction: run(
                        lambda: self.drive([d if n == i else 0 for n in range(4)])
                    ),
                    style="Compact.TButton",
                    width=4,
                ).pack(side="left", padx=(0, 4))
        self.state = tk.StringVar(value="Estado de actuadores sin verificar")

    def move(self, key):
        self.drive(self.app.config["patterns"][key])
        set_value(self.requested, "Solicitado: " + key.replace("_", " "))

    def drive(self, directions):
        self.app.controller.drive(directions, int(self.ms.get())).add_done_callback(
            self.app_command_done
        )

    def app_command_done(self, future):
        if future.cancelled():
            self.app.event("info", "Movimiento cancelado")
        elif future.exception():
            self.app.event("error", str(future.exception()))
        else:
            self.app.event("info", "Pulso aceptado; no confirma desplazamiento físico")

    def servo(self, name, degree):
        self.app.command("servo", {"nombre": name, "grado": degree})

    def fine(self, name, delta):
        state = self.app.dispatcher.state
        if name not in state:
            raise ValueError("Verifique el estado del servo primero")
        self.servo(name, state[name] + delta)

    def enable(self, name):
        if confirm(
            "Activar servo",
            f"Activar {name} puede moverlo a HOME. ¿Brazo apoyado y zona despejada?",
            self,
        ):
            self.app.command("enable", {"nombre": name})

    def release(self, name):
        if confirm(
            "Liberación individual",
            f"Sujete el brazo y la carga. ¿Confirma liberar {name} con el robot desarmado?",
            self,
        ):
            self.app.command("release", {"nombre": name, "confirm": 1})

    def refresh(self):
        d = self.app.dispatcher
        s = d.state if d.safety.connected else {}
        status = "Sesión autorizada" if d.safety.session else "Sin sesión"
        if s.get("motor_activo") or s.get("brazo_ocupado"):
            status += " · Actuadores ocupados"
        self.session.set(status, "warning" if d.safety.session else "neutral")
        for name in self.angles:
            limits = self.app.config["servos"][name]
            text = f'Orden: {s[name]}° → {s[name+"_objetivo"]}°' if s else "Orden: —"
            set_value(
                self.servo_limits[name],
                text + f'   ·   Límites {limits["min"]}–{limits["max"]}°',
            )
            self.servo_status[name].set(
                (
                    "PWM activo"
                    if s.get("servo_" + name + "_activo")
                    else "PWM inactivo" if s else "Sin verificar"
                ),
                "primary" if s.get("servo_" + name + "_activo") else "neutral",
            )
        for i, wheel in enumerate(
            ("FL · Del. izq.", "FR · Del. der.", "RL · Tras. izq.", "RR · Tras. der.")
        ):
            direction = s.get("directions", [None] * 4)[i]
            set_value(
                self.motor_status[i],
                wheel
                + "   "
                + (
                    "—"
                    if direction is None
                    else "Reposo" if direction == 0 else f"{direction:+d}"
                ),
            )

    def configured(self):
        self.ms.set(str(self.app.config["pulse_ms"]))
        self.pulse.configure(
            from_=self.app.config["pulse_min_ms"], to=self.app.config["pulse_max_ms"]
        )
        for name, entry in self.angle_inputs.items():
            limits = self.app.config["servos"][name]
            entry.configure(from_=limits["min"], to=limits["max"])
            self.angles[name].set(str(limits["home"]))

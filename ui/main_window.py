"""Shell de escritorio: navegación lateral, seguridad persistente y actualización incremental."""

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
from ui import theme
from ui.components.icons import icon
from ui.components.widgets import PageStack, Badge, label, button, set_value
from ui.tabs.automatico import AutomaticTab
from ui.tabs.manual import ManualTab
from ui.tabs.dataset import DatasetTab
from ui.tabs.configuracion import ConfigTab

TITLES = (
    "Supervisión autónoma",
    "Control manual",
    "Dataset Studio",
    "Configuración del sistema",
)
SUBTITLES = (
    "Percepción, decisiones y ejecución del robot",
    "Locomoción y manipulación · pulsos discretos",
    "Captura de originales para entrenamiento",
    "Administración, calibración y mantenimiento",
)


class MainWindow(tk.Tk):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.closing = False
        self.last_telemetry = 0.0
        self.title("Robot Inteligente 4WD | Fase 03")
        self.geometry(
            f"{min(1366,self.winfo_screenwidth()-24)}x{min(820,self.winfo_screenheight()-90)}"
        )
        self.minsize(1200, 650)
        # Tk limita por defecto el máximo al monitor actual. Permitir monitores
        # mayores y comprobaciones geométricas sin cambiar la resolución de Windows.
        self.maxsize(7680, 4320)
        theme.apply(self)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.sidebar = tk.Frame(self, bg=theme.PANEL, width=184)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(3, weight=1)
        identity = ttk.Frame(self.sidebar, style="Surface.TFrame", padding=(16, 24))
        identity.grid(row=0, column=0, sticky="ew")
        self.brand = icon(self, "robot", 44)
        label(identity, image=self.brand).pack(anchor="w", pady=(0, 12))
        label(identity, "Robot Inteligente", font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        label(identity, "4WD / Control System", style="Muted.TLabel").pack(
            anchor="w", pady=(4, 0)
        )
        ttk.Separator(self.sidebar).grid(row=1, column=0, sticky="ew", padx=16)
        nav = ttk.Frame(self.sidebar, style="Surface.TFrame", padding=(8, 20))
        nav.grid(row=2, column=0, sticky="ew")
        self.nav_buttons = []
        self.nav_icons = []
        for i, (name, symbol) in enumerate(
            (
                ("Automático", "auto"),
                ("Manual", "manual"),
                ("Dataset", "dataset"),
                ("Configuración", "settings"),
            )
        ):
            photo = icon(self, symbol, 22)
            self.nav_icons.append(photo)
            b = button(
                nav,
                "  " + name,
                lambda i=i: self.navigate(i),
                style="Nav.TButton",
                image=photo,
                compound="left",
            )
            b.pack(fill="x", pady=4)
            self.nav_buttons.append(b)
        lower = ttk.Frame(self.sidebar, style="Surface.TFrame", padding=16)
        lower.grid(row=4, column=0, sticky="ew")
        self.connection = Badge(lower, "●  Sin verificar")
        self.connection.pack(anchor="w", pady=(0, 12))
        label(
            lower, "FASE 03", font=("Segoe UI", 9, "bold"), foreground=theme.BLUE
        ).pack(anchor="w")
        label(
            lower,
            "Percepción visual\nValidación física pendiente",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        label(lower, "Alt 1–4 · Esc: STOP", style="Muted.TLabel").pack(
            anchor="w", pady=(8, 0)
        )
        main = ttk.Frame(self, padding=(20, 16, 20, 8))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        top = ttk.Frame(main)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top.columnconfigure(0, weight=1)
        heading = ttk.Frame(top)
        heading.grid(row=0, column=0, sticky="w")
        self.heading = tk.StringVar(value=TITLES[0])
        self.subtitle = tk.StringVar(value=SUBTITLES[0])
        label(heading, textvariable=self.heading, style="PageTitle.TLabel").pack(
            anchor="w"
        )
        label(heading, textvariable=self.subtitle, style="Caption.TLabel").pack(
            anchor="w", pady=(2, 0)
        )
        self.badge = Badge(top, "Modo simulación", "warning")
        self.badge.grid(row=0, column=1, padx=12)
        self.stop_button = button(
            top, "■  STOP GLOBAL", lambda: app.dispatcher.stop(), style="Danger.TButton"
        )
        self.stop_button.grid(row=0, column=2, sticky="e")
        self.tabs = PageStack(main)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        self.auto = AutomaticTab(self.tabs, app)
        self.manual = ManualTab(self.tabs, app, self.run)
        self.dataset = DatasetTab(self.tabs, app)
        self.config_tab = ConfigTab(self.tabs, app, self.run)
        for page, name in zip(
            (self.auto, self.manual, self.dataset, self.config_tab), TITLES
        ):
            self.tabs.add(page, text=name)
        self.tabs.bind("<<NotebookTabChanged>>", self.tab_changed)
        self.journal = self.auto.log.text
        footer = ttk.Frame(main, padding=(0, 8, 0, 0))
        footer.grid(row=2, column=0, sticky="ew")
        self.security = Badge(footer, "Desarmado local", "warning")
        self.security.pack(side="left", padx=(0, 12))
        self.status = tk.StringVar(
            value="ESP32 sin verificar  ·  Cámara desconectada  ·  API —"
        )
        self.status_label = label(
            footer, textvariable=self.status, style="Caption.TLabel", wraplength=800
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.message = tk.StringVar(
            value="Inicio desarmado. No se envían órdenes al conectar ni navegar sin conexión."
        )
        self.message_label = label(
            main, textvariable=self.message, style="Caption.TLabel", wraplength=1000
        )
        self.message_label.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        for i in range(4):
            self.bind(f"<Alt-Key-{i+1}>", lambda e, i=i: self.navigate(i))
        self.bind("<Escape>", lambda e: app.dispatcher.stop())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._update_navigation()
        # Resolver geometría inicial antes de aceptar los primeros frames;
        # el primer tick no debe consumir su presupuesto de frescura en layout.
        self.update_idletasks()
        self._tick_id = self.after(80, self.tick)

    def navigate(self, index):
        self.tabs.select(index)

    def navigate_config(self, category="Conectividad"):
        self.navigate(3)
        self.config_tab.select_category(category)

    def _update_navigation(self):
        index = self.tabs.index("current")
        set_value(self.heading, TITLES[index])
        set_value(self.subtitle, SUBTITLES[index])
        for i, b in enumerate(self.nav_buttons):
            b.configure(style="Selected.Nav.TButton" if i == index else "Nav.TButton")

    def run(self, callback):
        try:
            callback()
        except Exception as exc:
            self.app.event("error", str(exc))

    def tab_changed(self, _=None):
        self._update_navigation()
        self.last_telemetry = 0.0
        if self.closing or self.app.reconfiguring:
            return
        selected = self.tabs.index("current")
        if selected < 3:
            self.app.controller.change_mode(
                ("automatico", "manual", "dataset")[selected]
            )

    def tick(self):
        if self.closing:
            if self.app.closed:
                self.destroy()
            else:
                self._tick_id = self.after(80, self.tick)
            return
        if not self.app.reconfiguring:
            self.app.controller.tick()
        now = time.monotonic()
        cam = self.app.camera.snapshot()
        selected = self.tabs.index("current")
        if selected == 0:
            self.auto.update_video(cam)
        elif selected == 2:
            self.dataset.update_video(cam)
        elif selected == 3:
            self.config_tab.vision_panel.refresh()
        if now - self.last_telemetry >= 0.24:
            self._telemetry(cam)
            self.last_telemetry = now
        for _ in range(30):
            try:
                kind, payload = self.app.events.get_nowait()
            except queue.Empty:
                break
            if kind == "dataset_summary":
                self.dataset.apply_summary(payload)
                continue
            if kind == "vision_preview":
                self.config_tab.vision_panel.apply_preview(payload)
                continue
            if kind == "burst":
                self.dataset.burst_status(payload)
                continue
            if kind == "quality":
                self.dataset.quality_status(payload)
                continue
            if kind == "dataset_review":
                self.dataset.show_review(payload)
                continue
            if kind == "vision_configured":
                self.config_tab.populate(self.app.config)
                self.dataset.request_summary()
            if kind == "dataset_split":
                self.dataset.show_split(payload)
                continue
            if kind == "ui_goal":
                self.dataset.apply_goal(payload)
                continue
            if kind == "counts":
                self.dataset.request_summary()
                continue
            if kind == "capture":
                self.dataset.show_saved(*payload)
                text = "Captura original guardada"
                category = "DATASET"
            elif kind == "configured":
                self.manual.configured()
                self.config_tab.populate(self.app.config)
                set_value(
                    self.config_tab.feedback,
                    "Ajustes guardados. Verifique conexión antes de armar.",
                )
                self.dataset.request_summary()
                self.tab_changed()
                text = str(payload)
                category = "SISTEMA"
            else:
                text = str(payload)
                category = "ERROR" if kind == "error" else "SISTEMA"
            set_value(self.message, text)
            self.message_label.configure(
                foreground=(
                    theme.COLORS["danger_text"] if kind == "error" else theme.MUTED
                )
            )
            self.auto.log.append(category, text)
        self._tick_id = self.after(80, self.tick)

    def destroy(self):
        if getattr(self, "_tick_id", None):
            self.after_cancel(self._tick_id)
            self._tick_id = None
        super().destroy()

    def _telemetry(self, cam):
        d = self.app.dispatcher
        s = d.safety.snapshot()
        comm = d.communication_snapshot()
        sim = self.app.config["simulation"]
        self.badge.set(
            "Modo simulación" if sim else "Hardware real",
            "warning" if sim else "primary",
        )
        compact = {
            "Sin verificar": "Sin verificar",
            "Conectando": "Conectando",
            "Conectado": "Conectado",
            "Conexión inestable": "Conexión inestable",
            "Comunicación perdida": "Sin comunicación",
            "Reconectando": "Reconectando",
            "Conexión recuperada / desarmado": "Recuperado/desarmado",
            "Estado remoto desconocido": "Estado desconocido",
        }
        self.connection.set(
            "Simulador listo" if sim and s["connected"] else compact[comm["state"]],
            (
                "primary"
                if sim and s["connected"]
                else (
                    "success"
                    if s["connected"]
                    else "warning" if d.recovery_enabled else "neutral"
                )
            ),
        )
        danger = (
            "no confirmada" in s["safety"]
            or "pérdida" in s["safety"]
            or "Error" in s["safety"]
        )
        self.security.set(
            (
                "Parada no confirmada"
                if danger
                else "Armado local" if s["session_authorized"] else "Desarmado local"
            ),
            "danger" if danger else "warning",
        )
        metrics = comm
        selected = self.tabs.index("current")
        if selected == 0:
            self.auto.refresh(metrics)
        if selected == 1:
            self.manual.refresh()
        can_capture = (
            cam["fresh"]
            and not s["session_authorized"]
            and not d.state.get("armed")
            and not d.state.get("motor_activo")
            and not d.state.get("brazo_ocupado")
        )
        try:
            self.app.capture_guard()
        except PermissionError:
            can_capture = False
        self.dataset.capture_button.state(
            ["!disabled"] if can_capture else ["disabled"]
        )
        self.dataset.burst.state(
            ["!disabled"]
            if can_capture and not self.app.burst.running
            else ["disabled"]
        )
        self.dataset.check_burst_labels()
        fps = f'{cam["frame"].fps:.1f}' if cam["fresh"] else "—"
        resolution = (
            f'{cam["frame"].image.shape[1]}×{cam["frame"].image.shape[0]}'
            if cam["fresh"]
            else "—"
        )
        p95 = "—" if metrics["p95"] is None else f'{metrics["p95"]:.1f}'
        firmware_state = {
            "Desconocido": "Remoto desconocido",
            "Desarmado / reposo lógico": "Remoto en reposo",
            "Armado aceptado (ACK); sin telemetría reciente": "Armado (ACK)",
        }.get(comm["remote_state"], comm["remote_state"])
        mode = {"manual": "Manual", "automatico": "Automático", "dataset": "Dataset"}[
            s["mode"]
        ]
        text = (
            f'{"Simulador" if sim else "ESP32"}: {compact[comm["state"]]}  ·  Cámara: {cam["status"]}  ·  Modo: {mode}\nFW {d.health.get("version","—")} / API {d.health.get("api_version","—")} · {firmware_state}  ·  {resolution} / {fps} FPS  ·  p95 {p95} ms'
            + (" (sim.)" if sim else "")
            + f'  ·  Errores {metrics["errors"]}'
        )
        set_value(self.status, text)
        set_value(
            self.config_tab.diagnostics,
            f'Firmware {d.health.get("version","—")} / API {d.health.get("api_version","—")} · {comm["state"]} · {s["safety"]}',
        )

        def number(value):
            return "—" if value is None else f"{value:.1f}"

        if selected != 3 or self.config_tab.category != "Mantenimiento":
            return
        set_value(
            self.config_tab.performance,
            f'API {"simulada" if sim else "HTTP"}, ventana 60 s: OK {comm["successes"]} / fallos {comm["errors"]} / consecutivos {comm["consecutive_errors"]}\n'
            f'p50 {number(metrics["p50"])} / p95 {p95} / máximo {number(comm["max"])} ms · última válida hace {number(comm["last_valid_age_s"])} s\n'
            f'Reconexiones {comm["reconnections"]} · corte actual {number(comm["current_outage_s"])} / último {number(comm["last_outage_s"])} s · motivo {comm["last_failure"] or "sin fallos"}\n'
            f'STOP: {comm["stop_state"]} · remoto: {comm["remote_state"]} · edad desde inicio de state {number(comm["state_age_s"])} s\n'
            f'Controlador {number(d.response_ms)} ms · errores cámara {cam["errors"]}. La latencia de cámara completa no se mide aquí.',
        )

    def close(self):
        if self.closing:
            return
        self.closing = True
        set_value(
            self.message,
            "Cerrando trabajadores y solicitando STOP si existía conexión…",
        )

        def task():
            try:
                self.app.close()
            except Exception as exc:
                import logging

                self.app.close_error = str(exc)
                logging.getLogger(__name__).error(
                    "Cierre incompleto: %s", type(exc).__name__
                )
                self.app.closed = True

        threading.Thread(target=task, name="cierre", daemon=True).start()

    def screenshot(self, path):
        self.update_idletasks()
        # Capturar solo esta ventana, incluso si otra aplicación tiene el foco.
        # Evita incluir contenido ajeno al proyecto desde el escritorio compartido.
        import ctypes

        hwnd = ctypes.windll.user32.GetAncestor(self.winfo_id(), 2)
        ImageGrab.grab(window=hwnd).save(path)

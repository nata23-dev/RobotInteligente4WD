"""Centro de supervisión; todos los datos pendientes permanecen explícitos."""

import tkinter as tk
from tkinter import ttk
from ui import theme
from ui.components.widgets import (
    Card,
    Metric,
    Badge,
    Video,
    EventLog,
    button,
    label,
    set_value,
)


class AutomaticTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        metrics = ttk.Frame(self)
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for i in range(3):
            metrics.columnconfigure(i, weight=1, uniform="metrics")
        self.pieces = Metric(metrics, "Piezas clasificadas", "dataset")
        self.precision = Metric(
            metrics,
            "Confianza CNN · sin modelo",
            "brain",
            accent=theme.COLORS["neural_accent"],
        )
        self.latency = Metric(metrics, "Latencia de comunicación p95", "clock")
        for i, card in enumerate((self.pieces, self.precision, self.latency)):
            card.grid(row=0, column=i, sticky="ew", padx=(0, 8) if i < 2 else 0)
        main = ttk.Frame(self)
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=8, uniform="columns")
        main.columnconfigure(1, weight=5, uniform="columns")
        main.rowconfigure(0, weight=1)
        camera = Card(main, padding=12)
        camera.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.video = Video(
            camera.body,
            configure_camera=lambda: self.winfo_toplevel().navigate_config(
                "Conectividad"
            ),
        )
        self.video.pack(fill="both", expand=True)
        selector = ttk.Frame(self.video, style="Surface.TFrame")
        selector.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self.view = tk.StringVar(value="Original")
        choice = ttk.Combobox(
            selector,
            textvariable=self.view,
            values=["Original", "Procesada · pendiente"],
            state="readonly",
            width=23,
        )
        choice.pack(side="left")
        choice.bind("<<ComboboxSelected>>", lambda e: self.select_view())
        label(selector, "Contornos / ArUco: pendientes", style="Muted.TLabel").pack(
            side="right"
        )
        intelligence = ttk.Frame(main)
        intelligence.grid(row=0, column=1, sticky="nsew")
        for column in range(2):
            intelligence.columnconfigure(column, weight=1, uniform="ai_columns")
        modules = [
            (
                "Procesamiento de imágenes",
                "camera",
                "Pendiente",
                [
                    ("Objeto", "—"),
                    ("Color", "—"),
                    ("Posición", "—"),
                    ("Área aparente", "—"),
                ],
            ),
            (
                "Red neuronal",
                "brain",
                "Sin modelo",
                [
                    ("Clase", "—"),
                    ("Confianza", "—"),
                    ("Modelo", "—"),
                    ("Probabilidades", "— / — / —"),
                ],
            ),
            (
                "Lógica difusa",
                "fuzzy",
                "Sin evaluar",
                [
                    ("Error X", "—"),
                    ("Proximidad", "—"),
                    ("Reglas", "—"),
                    ("Orden / pulso", "—"),
                ],
            ),
            (
                "Heurística",
                "dataset",
                "Inactiva",
                [
                    ("Estado", "—"),
                    ("Condición", "—"),
                    ("Acción", "—"),
                    ("Destino", "—"),
                ],
            ),
        ]
        self.module_cards = []
        for i, (title, symbol, status, values) in enumerate(modules):
            intelligence.rowconfigure(i // 2, weight=1, uniform="modules")
            card = Card(intelligence, padding=4)
            card.grid(
                row=i // 2,
                column=i % 2,
                sticky="nsew",
                padx=(0, 6) if i % 2 == 0 else 0,
                pady=(0, 6) if i < 2 else 0,
            )
            heading = ttk.Frame(card.body, style="Surface.TFrame")
            heading.pack(fill="x")
            label(
                heading, "Imágenes" if i == 0 else title, font=("Segoe UI", 10, "bold")
            ).pack(anchor="w")
            label(
                heading,
                status,
                style="Muted.TLabel",
                foreground=theme.COLORS["neural_text"] if i in (1, 2) else theme.MUTED,
            ).pack(anchor="w")
            fields = ttk.Frame(card.body, style="Surface.TFrame")
            fields.pack(fill="x")
            for j, (name, value) in enumerate(values):
                fields.columnconfigure(j % 2, weight=1)
                short_name = (
                    "Área"
                    if name == "Área aparente"
                    else "Mov./ms" if name == "Orden / pulso" else name
                )
                wide = name == "Probabilidades"
                label(fields, f"{short_name}: {value}", style="Muted.TLabel").grid(
                    row=2 if wide else j // 2,
                    column=0 if wide else j % 2,
                    columnspan=2 if wide else 1,
                    sticky="w",
                )
            self.module_cards.append(card)
        cycle = Card(self, padding=8)
        cycle.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        label(
            cycle.body,
            "CICLO AUTÓNOMO   ·   Pendiente de integración",
            style="Muted.TLabel",
        ).pack(anchor="w")
        steps = ttk.Frame(cycle.body, style="Surface.TFrame")
        steps.pack(fill="x", pady=(4, 0))
        for i, name in enumerate(
            (
                "Buscar",
                "Detectar",
                "Alinear",
                "Aproximar",
                "Recoger",
                "Transportar",
                "Depositar",
                "Verificar",
            )
        ):
            steps.columnconfigure(i, weight=1)
            label(steps, f"{i+1}  {name}", style="Muted.TLabel").grid(
                row=0, column=i, sticky="w"
            )
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(0, weight=1)
        journal = Card(bottom, padding=8)
        journal.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        header = ttk.Frame(journal.body, style="Surface.TFrame")
        header.pack(fill="x")
        label(header, "Registro de decisiones", font=("Segoe UI", 10, "bold")).pack(
            side="left"
        )
        button(
            header, "Limpiar vista", lambda: self.log.clear(), style="Compact.TButton"
        ).pack(side="right")
        self.log = EventLog(journal.body, height=1)
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        actions = ttk.Frame(bottom)
        actions.grid(row=0, column=1, sticky="s")
        self.start = button(
            actions, "▶  Iniciar", style="Primary.TButton", state="disabled"
        )
        self.start.pack(side="left", padx=(0, 6))
        self.pause = button(actions, "Ⅱ  Pausar", state="disabled")
        self.pause.pack(side="left", padx=(0, 6))
        button(
            actions, "■  Detener", lambda: app.dispatcher.stop(), style="Danger.TButton"
        ).pack(side="left")
        self.log.append(
            "SISTEMA", "Aplicación iniciada; autonomía pendiente de integración."
        )

    def select_view(self):
        self.video.processed = self.view.get() != "Original"
        self.video.empty_state = None

    def refresh(self, metrics):
        v = metrics["p95"]
        set_value(
            self.latency.value,
            (
                "—"
                if v is None
                else f"{v:.1f} ms"
                + (" · sim." if self.app.config["simulation"] else "")
            ),
        )

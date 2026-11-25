"""Un visor protagonista, percepción real y detalles bajo demanda."""

import time
import tkinter as tk
from tkinter import ttk
import cv2
from app.models import Frame
from ui.components.widgets import Card, Video, EventLog, button, label, set_value


class AutomaticTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.main = ttk.Frame(self)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.main.columnconfigure(0, weight=3, uniform="supervision")
        self.main.columnconfigure(1, weight=1, uniform="supervision")
        self.main.rowconfigure(0, weight=1)
        self.camera_card = Card(self.main, padding=8)
        self.camera_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.video = Video(
            self.camera_card.body,
            configure_camera=lambda: self.winfo_toplevel().navigate_config(
                "Conectividad"
            ),
        )
        self.video.pack(fill="both", expand=True)
        selector = ttk.Frame(self.video, style="Surface.TFrame")
        selector.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self.view = tk.StringVar(value="Original")
        select = ttk.Combobox(
            selector,
            textvariable=self.view,
            values=["Original", "Procesada", "Máscara"],
            state="readonly",
            width=11,
        )
        select.pack(side="left")
        select.bind("<<ComboboxSelected>>", lambda e: self.select_view())
        self.mask = tk.StringVar(value="combinada")
        ttk.Combobox(
            selector,
            textvariable=self.mask,
            values=["combinada", "rojo", "verde", "azul"],
            state="readonly",
            width=11,
        ).pack(side="left", padx=4)
        self.expand_button = button(
            selector, "Ampliar", self.expand, style="Compact.TButton"
        )
        self.expand_button.pack(side="right")
        self.side = Card(self.main, padding=10)
        self.side.grid(row=0, column=1, sticky="nsew")
        label(self.side.body, "Objetivo visual", font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        self.context = tk.StringVar(value="Sin observación vigente")
        self.context_label = label(
            self.side.body, textvariable=self.context, wraplength=210, justify="left"
        )
        self.context_label.pack(anchor="w", fill="x", pady=12)
        label(
            self.side.body,
            "CNN, difusa y heurística\nsin implementar.\nAutonomía bloqueada.",
            style="Muted.TLabel",
            wraplength=210,
        ).pack(anchor="w", pady=8)
        button(
            self.side.body,
            "Detalles técnicos",
            self.toggle_details,
            style="Compact.TButton",
        ).pack(fill="x", pady=4)
        button(
            self.side.body,
            "Registro de eventos",
            self.toggle_details,
            style="Compact.TButton",
        ).pack(fill="x", pady=4)
        self.details = Card(self, padding=6)
        self.details.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.details.grid_remove()
        self.detail_var = tk.StringVar()
        label(
            self.details.body,
            textvariable=self.detail_var,
            style="Muted.TLabel",
            wraplength=950,
        ).pack(anchor="w")
        self.log = EventLog(self.details.body, height=2)
        self.log.pack(fill="both", expand=True)
        self.log.append("SISTEMA", "Solo percepción visual. Autonomía bloqueada.")
        bottom = ttk.Frame(self)
        bottom.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        bottom.columnconfigure(0, weight=1)
        self.cycle = label(
            bottom,
            "1 Buscar · 2 Detectar · 3 Alinear · 4 Aproximar\n5 Recoger · 6 Transportar · 7 Depositar · 8 Verificar",
            style="Muted.TLabel",
        )
        self.cycle.grid(row=0, column=0, sticky="w")
        actions = ttk.Frame(bottom)
        actions.grid(row=0, column=1, sticky="e")
        self.start = button(actions, "Iniciar", state="disabled")
        self.start.pack(side="left", padx=3)
        self.pause = button(actions, "Pausar", state="disabled")
        self.pause.pack(side="left", padx=3)
        button(
            actions, "Detener", lambda: app.dispatcher.stop(), style="Danger.TButton"
        ).pack(side="left")
        self.expanded = False

    def select_view(self):
        self.video.processed = self.view.get() != "Original"
        self.video.empty_state = None

    def toggle_details(self):
        if self.details.winfo_manager():
            self.details.grid_remove()
        else:
            self.details.grid()

    def expand(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.side.grid_remove()
            self.main.columnconfigure(1, weight=0, minsize=0, uniform="")
            self.main.columnconfigure(0, weight=1, uniform="")
        else:
            self.side.grid()
            self.main.columnconfigure(0, weight=3, uniform="supervision")
            self.main.columnconfigure(1, weight=1, uniform="supervision")
        self.expand_button.configure(text="Restaurar" if self.expanded else "Ampliar")

    def update_video(self, snap):
        from ui.video_source import original_snapshot

        v = self.app.vision.snapshot()
        r = v["result"]
        mode = self.view.get()
        if mode == "Original":
            view = original_snapshot(self.app, snap)
            self.video.processed = False
            self.video.update_frame(view)
            if snap["fresh"]:
                f = snap["frame"]
                image = view["frame"].image
                set_value(
                    self.video.metrics,
                    f"Recibida {f.image.shape[1]} × {f.image.shape[0]} · Vista {image.shape[1]} × {image.shape[0]} · {f.fps:.1f} FPS · #{f.id} · {f.source}",
                )
        if r is None:
            if mode != "Original":
                self.video.update_frame(dict(snap, frame=None, fresh=False))
            set_value(
                self.context,
                "Sin observación vigente\n\nDestino sin determinar\nAcción: ninguna\nClasificadas: sin contador",
            )
            return
        o = r.observation
        mode = self.view.get()
        image = (
            r.normalized
            if mode == "Original"
            else (
                cv2.cvtColor(r.masks[self.mask.get()], cv2.COLOR_GRAY2BGR)
                if mode == "Máscara"
                else r.overlay
            )
        )
        f = Frame(
            r.frame.id,
            r.frame.received_at,
            image,
            r.frame.fps,
            r.frame.generation + mode + self.mask.get() + str(o.vision_revision),
            r.frame.source,
        )
        self.video.processed = False
        if mode != "Original":
            self.video.update_frame(
                dict(
                    snap,
                    frame=f,
                    fresh=True,
                    age_s=time.monotonic() - f.received_at,
                    status=f.source,
                )
            )
        h, w = r.frame.image.shape[:2]
        if mode != "Original":
            set_value(
                self.video.metrics,
                f"Recibida {w} × {h} · Vista {image.shape[1]} × {image.shape[0]} · {f.fps:.1f} FPS · #{f.id} · {f.source}",
            )
        target = o.target
        set_value(
            self.context,
            f'{o.tracking_state}\n\n{target.color.capitalize()+" — figura pendiente de clasificación CNN" if target else "Sin objetivo confirmado"}\nSeguimiento: {o.track_id or "sin ID"}\nDestino: sin determinar\nAcción: ninguna\nClasificadas: sin contador',
        )
        self.context_label.configure(wraplength=max(100, self.side.winfo_width() - 28))

    def refresh(self, metrics):
        comm = self.app.dispatcher.communication_snapshot()
        network = (
            f'Comunicación: {comm["state"]} · fallos/consecutivos {comm["errors"]}/{comm["consecutive_errors"]} · reconexiones {comm["reconnections"]}\n'
            f'STOP: {comm["stop_state"]} · remoto: {comm["remote_state"]} · último fallo: {comm["last_failure"] or "ninguno"}'
        )
        v = self.app.vision.snapshot()
        r = v["result"]
        if not r:
            set_value(
                self.detail_var,
                "Sin percepción vigente. CNN: sin modelo. Difusa y heurística: sin implementar.\n"
                + network,
            )
            return
        o = r.observation
        objects = (
            "; ".join(
                f"{x.color} caja={x.box} c=({x.centroid[0]:.0f},{x.centroid[1]:.0f}) área={x.area:.0f} errorX={x.error_x:+.2f}"
                for x in o.objects[:6]
            )
            or "ninguno"
        )
        set_value(
            self.detail_var,
            f"Objetos ({len(o.objects)}): {objects}\nMarcadores: "
            + ", ".join(f'{m.id}: {m.station or "desconocido"}' for m in o.markers)
            + f'\nRecepción {r.frame.fps:.1f} FPS · proceso {v["fps"]:.1f} FPS / {o.processing_ms:.1f} ms · edad {(time.monotonic()-r.frame.received_at)*1000:.0f} ms · HTTP p95 {metrics["p95"]} ms · errores visión {v["errors"]}\nCNN: sin modelo/clase/confianza/probabilidades. Difusa: sin entradas/pertenencias/reglas/salidas. Heurística: sin estado/condición/acción/destino.',
        )

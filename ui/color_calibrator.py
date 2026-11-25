"""Calibrador local sobre la única cámara; aplicar es una acción explícita."""

import copy
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from dataclasses import replace
import cv2
from ai.vision import VisionWorker
from ai.calibration import sample_region, append_sample, display_rect, overlaps
from ai.profiles import Profiles, TUNING
from app.vision_config import validate, dataset_defaults
from ui.components.widgets import Video


class Calibrator:
    def __init__(self, parent, app):
        self.app = app
        self.base = copy.deepcopy(app.config["vision"])
        self.draft = copy.deepcopy(self.base)
        self.profiles = Profiles(self.base)
        self.samples = []
        self.sample_counter = 0
        self.result = None
        self.drag = None
        self.closed = False
        self.window = tk.Toplevel(parent)
        self.window.title("Calibrador de colores · experimental")
        self.window.geometry("1100x680")
        self.window.minsize(900, 600)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Escape>", lambda e: app.dispatcher.stop())
        top = ttk.Frame(self.window, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Button(top, text="STOP GLOBAL", command=app.dispatcher.stop).pack(
            side="right"
        )
        self.color = tk.StringVar(value="rojo")
        self.mode = tk.StringVar(value="Procesada")
        self.action = tk.StringVar(value="Muestra")
        for var, values in (
            (self.color, ["rojo", "verde", "azul"]),
            (self.mode, ["Original", "Procesada", "Máscara"]),
            (self.action, ["Muestra", "ROI de búsqueda"]),
        ):
            ttk.Combobox(
                top, textvariable=var, values=values, state="readonly", width=18
            ).pack(side="left", padx=4)
        self.color.trace_add("write", lambda *_: self.refresh_intervals())
        body = ttk.Panedwindow(self.window, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", padx=8)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)
        self.video = Video(left, "Arrastre sobre la imagen normalizada")
        self.video.pack(fill="both", expand=True)
        self.video.label.bind("<ButtonPress-1>", self.start_drag)
        self.video.label.bind("<ButtonRelease-1>", self.end_drag)
        self.video.label.bind("<B1-Motion>", self.show_drag)
        self.info = tk.StringVar(
            value="Sin muestra. Los reflejos y píxeles poco saturados se excluyen."
        )
        ttk.Label(left, textvariable=self.info, wraplength=550).pack(fill="x")
        self.sample_list = tk.Listbox(left, height=4)
        self.sample_list.pack(fill="x")
        ttk.Button(
            left,
            text="Eliminar muestra seleccionada y sus intervalos",
            command=lambda: self.run(self.remove_sample),
        ).pack(fill="x")
        tabs = ttk.Notebook(right)
        tabs.pack(fill="both", expand=True)
        self.tabs = tabs
        intervals = ttk.Frame(tabs, padding=8)
        filter_page = ttk.Frame(tabs)
        profiles = ttk.Frame(tabs, padding=8)
        tabs.add(intervals, text="Intervalos")
        tabs.add(filter_page, text="Filtros / ROI")
        tabs.add(profiles, text="Perfiles")
        canvas = tk.Canvas(filter_page, highlightthickness=0)
        scroll = ttk.Scrollbar(filter_page, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        filters = ttk.Frame(canvas, padding=8)
        item = canvas.create_window(0, 0, window=filters, anchor="nw")
        filters.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))
        self.tree = ttk.Treeview(
            intervals, columns=("name", "enabled", "bounds"), show="headings", height=7
        )
        for key, title, width in [
            ("name", "Nombre", 100),
            ("enabled", "Activo", 45),
            ("bounds", "H/S/V mín · máx", 180),
        ]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=True)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.choose_interval)
        self.name = tk.StringVar(value="Intervalo")
        self.enabled = tk.BooleanVar(value=True)
        self.bounds = tk.StringVar(value="0 55 35 15 255 255")
        ttk.Entry(intervals, textvariable=self.name).pack(fill="x", pady=3)
        ttk.Checkbutton(intervals, text="Habilitado", variable=self.enabled).pack(
            anchor="w"
        )
        ttk.Label(intervals, text="H mín S mín V mín H máx S máx V máx").pack(
            anchor="w"
        )
        ttk.Entry(intervals, textvariable=self.bounds).pack(fill="x")
        for title, fn in [
            ("Añadir intervalo", lambda: self.edit_interval("add")),
            ("Actualizar seleccionado", lambda: self.edit_interval("update")),
            ("Eliminar seleccionado", lambda: self.edit_interval("delete")),
        ]:
            ttk.Button(intervals, text=title, command=lambda f=fn: self.run(f)).pack(
                fill="x", pady=2
            )
        self.filter_vars = {}
        settings = (
            [
                ("min_area", self.draft["min_area"]),
                ("max_area_ratio", self.draft["max_area_ratio"]),
            ]
            + [("filters." + k, v) for k, v in self.draft["filters"].items()]
            + [("tracking." + k, v) for k, v in self.draft["tracking"].items()]
        )
        titles = {
            "min_area": "Área mínima (px²)",
            "max_area_ratio": "Área máxima / imagen (0–1)",
            "filters.min_width": "Ancho mínimo (px)",
            "filters.min_height": "Alto mínimo (px)",
            "filters.min_area_ratio": "Área mínima / imagen (0–1)",
            "filters.aspect_min": "Ancho/alto mínimo",
            "filters.aspect_max": "Ancho/alto máximo",
            "filters.solidity_min": "Solidez mínima (0–1)",
            "filters.extent_min": "Área / caja mínima (0–1)",
            "filters.fill_min": "Proporción de color mínima (0–1)",
            "filters.reject_border": "Rechazar contacto con borde",
            "tracking.confirm_frames": "Frames distintos para confirmar",
            "tracking.size_ratio_max": "Cambio máximo de área (factor)",
            "tracking.smoothing": "Peso de posición nueva (0.05–1)",
            "tracking.max_gap_s": "Tiempo máximo de pérdida (s)",
        }
        for i, (key, value) in enumerate(settings):
            ttk.Label(filters, text=titles[key]).grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=str(value))
            self.filter_vars[key] = var
            widget = (
                ttk.Checkbutton(filters, variable=var, onvalue="True", offvalue="False")
                if type(value) is bool
                else ttk.Entry(filters, textvariable=var, width=10)
            )
            widget.grid(row=i, column=1, sticky="ew")
        r = len(settings)
        self.roi_enabled = tk.BooleanVar(value=self.draft["search_roi"]["enabled"])
        ttk.Checkbutton(
            filters,
            text="Limitar búsqueda a ROI arrastrada",
            variable=self.roi_enabled,
            command=lambda: self.run(self.set_filters),
        ).grid(row=r, column=0, columnspan=2)
        ttk.Button(
            filters, text="Búsqueda en imagen completa", command=self.full_frame
        ).grid(row=r + 1, column=0, columnspan=2)
        ttk.Button(
            filters,
            text="Previsualizar filtros",
            command=lambda: self.run(self.set_filters),
        ).grid(row=r + 2, column=0, columnspan=2)
        self.overlay_vars = {}
        for i, (key, title) in enumerate(
            (
                ("regions", "Regiones segmentadas"),
                ("discarded", "Candidatos descartados"),
                ("objects", "Candidatos válidos e IDs"),
            )
        ):
            var = tk.BooleanVar(value=self.draft["overlays"][key])
            self.overlay_vars[key] = var
            ttk.Checkbutton(
                filters,
                text=title,
                variable=var,
                command=lambda: self.run(self.set_filters),
            ).grid(row=r + 3 + i, column=0, columnspan=2, sticky="w")
        self.profile = tk.StringVar(value=self.draft["profile_name"])
        self.profile_choice = ttk.Combobox(
            profiles,
            textvariable=self.profile,
            values=list(self.profiles.data),
            state="readonly",
        )
        self.profile_choice.pack(fill="x")
        for title, fn in [
            ("Previsualizar perfil", self.select_profile),
            ("Crear / duplicar borrador", self.save_profile),
            ("Renombrar perfil propio", self.rename_profile),
            ("Eliminar perfil propio", self.delete_profile),
            ("Restablecer Original", self.reset_original),
        ]:
            ttk.Button(profiles, text=title, command=lambda f=fn: self.run(f)).pack(
                fill="x", pady=5
            )
        ttk.Label(
            profiles,
            text="Original y Ampliado experimental están protegidos. El perfil ampliado requiere verificación con piezas reales. Seleccionar solo cambia la vista previa.",
            wraplength=330,
        ).pack(fill="x", pady=8)
        self.status = tk.StringVar()
        ttk.Label(self.window, textvariable=self.status, wraplength=1050).grid(
            row=2, column=0, sticky="ew", padx=8, pady=5
        )
        bottom = ttk.Frame(self.window, padding=8)
        bottom.grid(row=3, column=0, sticky="ew")
        for title, fn in [
            ("Aplicar y guardar", self.apply),
            ("Restaurar ajustes activos", self.restore),
            ("Cancelar / cerrar", self.close),
        ]:
            ttk.Button(bottom, text=title, command=lambda f=fn: self.run(f)).pack(
                side="left", padx=5
            )
        self.worker = VisionWorker(app.camera, copy.deepcopy(app.config))
        app.calibration_workers.add(self.worker)
        self.worker.start()
        self.refresh_intervals()
        self.poll()

    def run(self, fn):
        try:
            fn()
        except Exception as exc:
            messagebox.showerror("Calibración", str(exc), parent=self.window)

    def preview(self):
        name = self.draft["profile_name"]
        if name in self.profiles.data and self.profiles.data[name]["protected"]:
            original = self.profiles.select(name, self.draft)
            if any(self.draft[key] != original[key] for key in TUNING):
                self.draft["profile_name"] = "Borrador de " + name
        validate(self.draft, dataset_defaults())
        self.worker.reconfigure(self.draft)
        self.status.set(
            "Vista previa local · "
            + self.draft["profile_name"]
            + " · "
            + (
                "ADVERTENCIA: intervalos de distintos colores se solapan; región incierta"
                if overlaps(self.draft)
                else "Sin solapamientos HSV entre colores"
            )
        )

    def refresh_intervals(self):
        self.tree.delete(*self.tree.get_children())
        c = self.color.get()
        for i, (bounds, meta) in enumerate(
            zip(self.draft["hsv"][c], self.draft["interval_meta"][c])
        ):
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    meta["name"],
                    "Sí" if meta["enabled"] else "No",
                    " ".join(map(str, bounds)),
                ),
            )

    def choose_interval(self, event=None):
        if not self.tree.selection():
            return
        i = int(self.tree.selection()[0])
        c = self.color.get()
        m = self.draft["interval_meta"][c][i]
        self.name.set(m["name"])
        self.enabled.set(m["enabled"])
        self.bounds.set(" ".join(map(str, self.draft["hsv"][c][i])))

    def edit_interval(self, action):
        new = copy.deepcopy(self.draft)
        c = self.color.get()
        if action == "add":
            new["hsv"][c].append(list(map(int, self.bounds.get().split())))
            new["interval_meta"][c].append(
                {"name": self.name.get(), "enabled": self.enabled.get()}
            )
        else:
            if not self.tree.selection():
                raise ValueError("Seleccione un intervalo")
            i = int(self.tree.selection()[0])
            if action == "delete":
                del new["hsv"][c][i]
                del new["interval_meta"][c][i]
            else:
                new["hsv"][c][i] = list(map(int, self.bounds.get().split()))
                new["interval_meta"][c][i] = {
                    "name": self.name.get(),
                    "enabled": self.enabled.get(),
                }
        validate(new, dataset_defaults())
        self.draft = new
        self.refresh_intervals()
        self.preview()

    def start_drag(self, e):
        if self.result is not None:
            self.drag = (e.x, e.y, self.result)

    def show_drag(self, e):
        if self.drag is None:
            return
        x, y, result = self.drag
        image = result.normalized.copy()
        h, w = image.shape[:2]
        dw, dh = max(1, self.video.label.winfo_width()), max(
            1, self.video.label.winfo_height()
        )
        cv2.rectangle(
            image,
            (int(x * w / dw), int(y * h / dh)),
            (int(max(0, min(dw, e.x)) * w / dw), int(max(0, min(dh, e.y)) * h / dh)),
            (0, 220, 255),
            2,
        )
        frame = replace(result.frame, image=image, generation=f"drag:{e.x}:{e.y}")
        self.video.update_frame(
            {
                "frame": frame,
                "fresh": True,
                "status": "Selección local",
                "age_s": max(0, time.monotonic() - frame.received_at),
            }
        )

    def end_drag(self, e):
        self.run(lambda: self.finish_drag(e))

    def finish_drag(self, e):
        if self.drag is None:
            return
        x, y, result = self.drag
        self.drag = None
        if (
            time.monotonic() - result.frame.received_at
            > self.app.config["frame_max_age_s"]
        ):
            raise ValueError("Frame atrasado: repita la selección con video fresco")
        rect = display_rect(
            (x, y),
            (e.x, e.y),
            result.normalized.shape,
            (self.video.label.winfo_width(), self.video.label.winfo_height()),
        )
        if self.action.get() == "ROI de búsqueda":
            self.draft["search_roi"] = {"enabled": True, "rect": rect}
            self.roi_enabled.set(True)
            self.preview()
            return
        sample = sample_region(result.processing, rect)
        self.sample_counter += 1
        name = f"Muestra {self.sample_counter}"
        self.draft = append_sample(self.draft, self.color.get(), sample, name)
        self.samples.append((name, self.color.get(), sample))
        self.sample_list.insert(
            "end",
            f'{name}: {self.color.get()} · H {sample["hue_center"]:.1f} · {sample["pixels_used"]} px',
        )
        self.info.set(
            f'Mediana S/V {sample["median_sv"]}; dispersión circular H {sample["hue_dispersion"]:.1f}; intervalos {sample["ranges"]}'
        )
        self.refresh_intervals()
        self.preview()

    def remove_sample(self):
        if not self.sample_list.curselection():
            raise ValueError("Seleccione una muestra")
        i = self.sample_list.curselection()[0]
        name, color, _ = self.samples.pop(i)
        self.sample_list.delete(i)
        keep = [
            j
            for j, m in enumerate(self.draft["interval_meta"][color])
            if not m["name"].startswith(name + " ")
        ]
        if not keep:
            raise ValueError("Debe quedar al menos un intervalo por color")
        self.draft["hsv"][color] = [self.draft["hsv"][color][j] for j in keep]
        self.draft["interval_meta"][color] = [
            self.draft["interval_meta"][color][j] for j in keep
        ]
        self.refresh_intervals()
        self.preview()

    def set_filters(self):
        new = copy.deepcopy(self.draft)
        for key, var in self.filter_vars.items():
            parts = key.split(".")
            target = new if len(parts) == 1 else new[parts[0]]
            k = parts[-1]
            old = target[k]
            value = var.get()
            target[k] = (
                (
                    value.lower() == "true"
                    if value.lower() in ("true", "false")
                    else (_ for _ in ()).throw(ValueError("Use True/False"))
                )
                if type(old) is bool
                else type(old)(value)
            )
        new["search_roi"]["enabled"] = self.roi_enabled.get()
        for key, var in self.overlay_vars.items():
            new["overlays"][key] = var.get()
        validate(new, dataset_defaults())
        self.draft = new
        self.preview()

    def full_frame(self):
        self.draft["search_roi"] = {"enabled": False, "rect": [0.0, 0.0, 1.0, 1.0]}
        self.roi_enabled.set(False)
        self.preview()

    def select_profile(self):
        self.draft = self.profiles.select(self.profile.get(), self.draft)
        self.sync()
        self.preview()

    def sync(self):
        self.refresh_intervals()
        self.roi_enabled.set(self.draft["search_roi"]["enabled"])
        for key, var in self.overlay_vars.items():
            var.set(self.draft["overlays"][key])
        for key, var in self.filter_vars.items():
            parts = key.split(".")
            var.set(
                str(
                    self.draft[parts[0]]
                    if len(parts) == 1
                    else self.draft[parts[0]][parts[1]]
                )
            )

    def save_profile(self):
        name = simpledialog.askstring(
            "Perfil", "Nombre nuevo del perfil:", parent=self.window
        )
        if name and messagebox.askyesno(
            "Guardar perfil",
            "¿Guardar este borrador como perfil local?",
            parent=self.window,
        ):
            self.app.vision_guard()
            self.profiles.put(name, self.draft)
            self.profile_choice.configure(values=list(self.profiles.data))
            self.profile.set(name)
            self.draft["profile_name"] = name

    def rename_profile(self):
        name = simpledialog.askstring("Renombrar", "Nuevo nombre:", parent=self.window)
        if name:
            self.app.vision_guard()
            self.profiles.rename(self.profile.get(), name)
            self.profile_choice.configure(values=list(self.profiles.data))
            self.profile.set(name)

    def delete_profile(self):
        if messagebox.askyesno(
            "Eliminar perfil", "¿Eliminar el perfil seleccionado?", parent=self.window
        ):
            self.app.vision_guard()
            self.profiles.delete(self.profile.get())
            self.profile_choice.configure(values=list(self.profiles.data))
            self.profile.set("Original")

    def reset_original(self):
        if messagebox.askyesno(
            "Restablecer",
            "¿Previsualizar el perfil Original protegido?",
            parent=self.window,
        ):
            self.draft = self.profiles.select("Original", self.draft)
            self.sync()
            self.preview()

    def restore(self):
        self.draft = copy.deepcopy(self.app.config["vision"])
        self.samples.clear()
        self.sample_list.delete(0, "end")
        self.sync()
        self.preview()

    def apply(self):
        if messagebox.askyesno(
            "Aplicar calibración",
            "¿Guardar y activar el borrador visual? Requiere robot desarmado y en reposo.",
            parent=self.window,
        ):
            self.app.update_vision(copy.deepcopy(self.draft))

    def poll(self):
        if self.closed:
            return
        if self.drag is None:
            result = self.worker.snapshot()["result"]
            self.result = result
            if result:
                mode = self.mode.get()
                image = (
                    result.normalized
                    if mode == "Original"
                    else (
                        result.overlay
                        if mode == "Procesada"
                        else cv2.cvtColor(
                            result.masks[self.color.get()], cv2.COLOR_GRAY2BGR
                        )
                    )
                )
                frame = replace(
                    result.frame,
                    image=image,
                    generation=f"{result.frame.generation}:{result.observation.vision_revision}:{mode}:{self.color.get()}",
                )
                self.video.update_frame(
                    {
                        "frame": frame,
                        "fresh": True,
                        "status": "Vista previa",
                        "age_s": max(0, time.monotonic() - frame.received_at),
                    }
                )
            else:
                self.video.update_frame(
                    {
                        "frame": None,
                        "fresh": False,
                        "status": "Sin frame fresco",
                        "age_s": 0,
                    }
                )
        self.timer = self.window.after(120, self.poll)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if hasattr(self, "timer"):
            self.window.after_cancel(self.timer)
        self.worker.stop()
        self.app.calibration_workers.discard(self.worker)
        self.window.destroy()

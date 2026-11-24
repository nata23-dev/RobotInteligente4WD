"""Componentes de presentación; solo el hilo principal toca Tkinter."""

from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from ui import theme
from ui.components.icons import icon

C = theme.COLORS


def set_value(variable, value):
    text = str(value)
    if variable.get() != text:
        variable.set(text)


def label(parent, text="", style="Surface.TLabel", **kwargs):
    return ttk.Label(parent, text=text, style=style, **kwargs)


def button(parent, text, command=None, style="TButton", **kwargs):
    return ttk.Button(parent, text=text, command=command, style=style, **kwargs)


def confirm(title, message, parent=None):
    return messagebox.askyesno(title, message, parent=parent)


class Card(tk.Frame):
    """Panel redondeado discreto; Canvas solo para el borde decorativo."""

    def __init__(self, parent, title=None, symbol=None, accent=None, padding=12):
        super().__init__(parent, bg=theme.BG, bd=0)
        self.back = tk.Canvas(self, bg=theme.BG, highlightthickness=0, bd=0)
        self.back.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = ttk.Frame(self, style="Surface.TFrame", padding=padding)
        self.body.pack(fill="both", expand=True, padx=2, pady=2)
        self.bind("<Configure>", self._draw)
        if title:
            self.heading = ttk.Frame(self.body, style="Surface.TFrame")
            self.heading.pack(fill="x", pady=(0, 8))
            if symbol:
                self.photo = icon(self, symbol, 22, accent)
                label(self.heading, image=self.photo).pack(side="left", padx=(0, 8))
            label(self.heading, title, font=theme.FONTS["section"]).pack(side="left")

    def _draw(self, event):
        if event.widget is not self:
            return
        w, h, r = event.width - 1, event.height - 1, 10
        self.back.delete("edge")
        points = [
            r,
            1,
            w - r,
            1,
            w,
            1,
            w,
            r,
            w,
            h - r,
            w,
            h,
            w - r,
            h,
            r,
            h,
            1,
            h,
            1,
            h - r,
            1,
            r,
            1,
            1,
        ]
        self.back.create_polygon(
            points,
            smooth=True,
            fill=theme.PANEL,
            outline=C["border"],
            width=1,
            tags="edge",
        )


class Badge(tk.Label):
    def __init__(self, parent, text="", tone="neutral"):
        super().__init__(parent, padx=9, pady=4, font=("Segoe UI", 9, "bold"), bd=0)
        self.set(text, tone)

    def set(self, text, tone="neutral"):
        tones = {
            "neutral": (C["surface_secondary"], C["muted_text"]),
            "primary": (C["primary_soft"], C["primary_text"]),
            "success": (C["success_soft"], C["success_text"]),
            "warning": (C["warning_soft"], C["warning_text"]),
            "danger": (C["danger_soft"], C["danger_text"]),
            "neural": (C["neural_soft"], C["neural_text"]),
        }
        bg, fg = tones[tone]
        if self.cget("text") != text or self.cget("background") != bg:
            self.configure(text=text, bg=bg, fg=fg)


class Metric(Card):
    def __init__(self, parent, title, symbol, value="—", accent=None):
        super().__init__(parent, padding=8)
        self.photo = icon(self, symbol, 24, accent)
        label(self.body, image=self.photo).pack(side="left", padx=(0, 8))
        label(self.body, title, style="Muted.TLabel").pack(
            side="left", fill="x", expand=True
        )
        self.value = tk.StringVar(value=value)
        label(
            self.body,
            textvariable=self.value,
            font=("Segoe UI", 16, "bold"),
            foreground=accent or C["primary"],
        ).pack(side="right", padx=(8, 0))


class EventLog(ttk.Frame):
    def __init__(self, parent, height=3):
        super().__init__(parent, style="Surface.TFrame")
        self.items = deque(maxlen=150)
        self.text = tk.Text(
            self,
            height=height,
            font=theme.FONTS["mono"],
            bg=C["surface_secondary"],
            fg=theme.TEXT,
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=4,
            state="disabled",
            wrap="word",
        )
        self.text.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(self, command=self.text.yview).pack(side="right", fill="y")
        self.text.configure(yscrollcommand=self.winfo_children()[-1].set)
        for category, color in [
            ("SISTEMA", C["primary"]),
            ("ERROR", C["danger_text"]),
            ("SEGURIDAD", C["success_text"]),
            ("DATASET", C["neural_text"]),
        ]:
            self.text.tag_configure(category, foreground=color)

    def append(self, category, message):
        self.items.append((category, message))
        self.text.configure(state="normal")
        self.text.insert("end", datetime.now().strftime("%H:%M:%S") + "  ")
        self.text.insert("end", category + "  ", category)
        self.text.insert("end", message + "\n")
        if len(self.text.get("1.0", "end-1c").splitlines()) > 150:
            self.text.delete("1.0", "2.0")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.items.clear()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class PageStack(ttk.Frame):
    """Navegación sin pestañas visibles; conserva select/index y su evento público."""

    def __init__(self, parent):
        super().__init__(parent)
        self.pages = []
        self.current = 0
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def add(self, page, text=""):
        self.pages.append(page)
        page.grid(row=0, column=0, sticky="nsew")
        if len(self.pages) - 1 != self.current:
            page.grid_remove()
        self.pages[self.current].tkraise()

    def index(self, value):
        return (
            self.current
            if value == "current"
            else len(self.pages) if value == "end" else int(value)
        )

    def select(self, value=None):
        if value is None:
            return str(self.current)
        index = self.index(value)
        if not 0 <= index < len(self.pages):
            raise ValueError("Sección inválida")
        changed = index != self.current
        if changed:
            self.pages[self.current].grid_remove()
        self.current = index
        self.pages[index].grid()
        self.pages[index].tkraise()
        if changed:
            self.event_generate("<<NotebookTabChanged>>")
        return str(index)


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.body = ttk.Frame(self.canvas)
        item = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfigure(item, width=e.width)
        )
        self.canvas.configure(yscrollcommand=self._scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", self._wheel, add="+")

    def _scroll(self, first, last):
        self.scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.scrollbar.pack_forget()
        elif not self.scrollbar.winfo_manager():
            self.scrollbar.pack(side="right", fill="y")

    def _wheel(self, event):
        if str(event.widget).startswith(str(self)) and self.scrollbar.winfo_manager():
            self.canvas.yview_scroll(-int(event.delta / 120), "units")


class Video(ttk.Frame):
    def __init__(self, parent, title="Visión del robot", configure_camera=None):
        super().__init__(parent, style="Surface.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        top = ttk.Frame(self, style="Surface.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.photo_icon = icon(self, "camera", 22)
        label(top, image=self.photo_icon).pack(side="left", padx=(0, 8))
        label(top, title, font=("Segoe UI", 12, "bold")).pack(side="left")
        self.badge = Badge(top, "Desconectada")
        self.badge.pack(side="right")
        self.viewport = tk.Frame(self, bg=C["surface_secondary"])
        self.viewport.grid(row=1, column=0, sticky="nsew")
        self.label = tk.Label(self.viewport, bg=C["surface_secondary"], bd=0)
        self.empty = tk.Frame(self.viewport, bg=C["surface_secondary"])
        self.empty.place(relx=0.5, rely=0.5, anchor="center")
        self.empty_photo = icon(self, "camera", 32, C["text_secondary"])
        tk.Label(self.empty, image=self.empty_photo, bg=C["surface_secondary"]).pack(
            pady=(0, 8)
        )
        self.empty_title = tk.Label(
            self.empty,
            text="Esperando cámara real",
            bg=C["surface_secondary"],
            fg=theme.TEXT,
            font=("Segoe UI", 12, "bold"),
        )
        self.empty_title.pack()
        if configure_camera:
            button(
                self.empty,
                "Configurar cámara",
                configure_camera,
                style="Compact.TButton",
            ).pack(pady=4)
        self.metrics = tk.StringVar(value="Resolución —    FPS —    Frame —    Edad —")
        label(self, textvariable=self.metrics, style="Muted.TLabel").grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        self.photo = None
        self.last = None
        self.processed = False
        self.empty_state = None

    def update_frame(self, snap):
        f = snap["frame"]
        if self.processed or not snap["fresh"]:
            title = (
                "Procesamiento pendiente"
                if self.processed
                else "Video atrasado" if f else "Esperando cámara real"
            )
            if title != self.empty_state:
                self.label.place_forget()
                self.empty.place(relx=0.5, rely=0.5, anchor="center")
                self.empty_title.configure(text=title)
                self.empty_state = title
                self.photo = None
                self.last = None
            self.badge.set(
                "Pendiente" if self.processed else snap["status"],
                "warning" if f else "neutral",
            )
        else:
            size = (
                max(1, self.viewport.winfo_width() - 8),
                max(1, self.viewport.winfo_height() - 8),
            )
            key = (f.id, size)
            if key != self.last:
                image = Image.fromarray(f.image[:, :, ::-1])
                image.thumbnail(size)
                self.photo = ImageTk.PhotoImage(image)
                self.empty.place_forget()
                self.label.configure(image=self.photo)
                self.label.place(relx=0.5, rely=0.5, anchor="center")
                self.last = key
                self.empty_state = None
            self.badge.set("Video recibido", "success")
        if f:
            text = f'{f.image.shape[1]} × {f.image.shape[0]}    {f.fps:.1f} FPS    Frame {f.id}    Edad {snap["age_s"]*1000:.0f} ms'
        else:
            text = "Resolución —    FPS —    Frame —    Edad —"
        set_value(self.metrics, text)

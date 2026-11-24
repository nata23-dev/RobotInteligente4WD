"""Sistema de diseño claro: tokens únicos de color, tipografía y espaciado."""

from tkinter import ttk

COLORS = {
    "background": "#F5F7FA",
    "surface": "#FFFFFF",
    "surface_secondary": "#EDF2F7",
    "border": "#DCE4ED",
    "primary": "#426FA8",
    "primary_soft": "#E7EFF9",
    "text_primary": "#243247",
    "text_secondary": "#64748B",
    "success": "#398575",
    "warning": "#B58A42",
    "danger": "#C34848",
    "neural_accent": "#7976B1",
    "danger_soft": "#FCEEEE",
    "warning_soft": "#FBF4E8",
    "success_soft": "#EAF5F1",
    "neural_soft": "#F0EFF8",
    "hover": "#DCE7F5",
    "pressed": "#345B8B",
    "disabled_text": "#718096",
    "warning_text": "#795B25",
    "success_text": "#286354",
    "muted_text": "#59697E",
    "neural_text": "#625C95",
    "danger_text": "#A83D3D",
    "primary_text": "#365F93",
}
BG, PANEL, TEXT = COLORS["background"], COLORS["surface"], COLORS["text_primary"]
MUTED, BLUE, RED = COLORS["muted_text"], COLORS["primary"], COLORS["danger"]
SPACE = (4, 8, 12, 16, 24, 32)
FONTS = {
    "title": ("Segoe UI", 23, "bold"),
    "section": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "metric": ("Segoe UI", 19, "bold"),
    "mono": ("Consolas", 9),
}


def apply(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=FONTS["body"])
    for prefix, color in [
        ("", BG),
        ("Surface.", PANEL),
        ("Secondary.", COLORS["surface_secondary"]),
    ]:
        style.configure(prefix + "TFrame", background=color)
        style.configure(prefix + "TLabel", background=color, foreground=TEXT)
    for name, font, fg in [
        ("Title", FONTS["title"], TEXT),
        ("Heading", FONTS["section"], TEXT),
        ("Muted", FONTS["small"], MUTED),
        ("Metric", FONTS["metric"], BLUE),
    ]:
        style.configure(name + ".TLabel", font=font, background=PANEL, foreground=fg)
    style.configure("PageTitle.TLabel", font=FONTS["title"], background=BG)
    style.configure(
        "Caption.TLabel", font=FONTS["small"], foreground=MUTED, background=BG
    )
    style.configure(
        "TButton",
        padding=(10, 6),
        background=PANEL,
        foreground=TEXT,
        bordercolor=COLORS["border"],
        lightcolor=PANEL,
        darkcolor=PANEL,
        borderwidth=1,
        focusthickness=2,
        focuscolor=BLUE,
    )
    style.map(
        "TButton",
        background=[
            ("disabled", COLORS["surface_secondary"]),
            ("pressed", COLORS["hover"]),
            ("active", COLORS["primary_soft"]),
        ],
        foreground=[("disabled", COLORS["disabled_text"])],
        bordercolor=[("focus", BLUE)],
    )
    for name, color, hover in [
        ("Primary", BLUE, "#375F92"),
        ("Danger", RED, "#AA3939"),
    ]:
        style.configure(
            name + ".TButton",
            background=color,
            foreground="white",
            bordercolor=color,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            name + ".TButton",
            background=[
                ("disabled", COLORS["surface_secondary"]),
                ("pressed", hover),
                ("active", hover),
            ],
            foreground=[("disabled", COLORS["disabled_text"]), ("!disabled", "white")],
        )
    style.configure("Compact.TButton", padding=(6, 4))
    for name in (
        "Direction.TButton",
        "Direction.Primary.TButton",
        "Direction.Danger.TButton",
    ):
        style.configure(name, font=("Segoe UI", 22, "bold"), padding=(4, 4))
    style.configure(
        "Nav.TButton",
        anchor="w",
        padding=(12, 12),
        borderwidth=0,
        background=PANEL,
        foreground=MUTED,
    )
    style.map(
        "Nav.TButton",
        background=[("active", COLORS["primary_soft"])],
        foreground=[("active", BLUE)],
    )
    style.configure(
        "Selected.Nav.TButton",
        background=COLORS["primary_soft"],
        foreground=COLORS["primary_text"],
        font=("Segoe UI", 10, "bold"),
    )
    style.map("Selected.Nav.TButton", background=[("active", COLORS["hover"])])
    for widget in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(
            widget,
            fieldbackground=PANEL,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=COLORS["border"],
            padding=5,
            arrowsize=12,
        )
        style.map(
            widget,
            fieldbackground=[
                ("readonly", PANEL),
                ("disabled", COLORS["surface_secondary"]),
            ],
            foreground=[("disabled", MUTED)],
            bordercolor=[("focus", BLUE)],
        )
    style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
    style.map("TCheckbutton", background=[("active", PANEL)])
    style.configure(
        "Horizontal.TProgressbar",
        background=BLUE,
        troughcolor=COLORS["surface_secondary"],
        borderwidth=0,
        thickness=6,
    )
    style.configure("TSeparator", background=COLORS["border"])
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)

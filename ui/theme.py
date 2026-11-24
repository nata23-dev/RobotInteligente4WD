"""Paleta uniforme para la aplicación local."""
from tkinter import ttk

BG = '#0b1220'
PANEL = '#152237'
TEXT = '#e6edf7'
MUTED = '#9daec5'
BLUE = '#2478e5'
RED = '#c93748'


def apply(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=BG, foreground=TEXT, font=('Segoe UI', 10))
    style.configure('TFrame', background=BG)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
    style.configure('Heading.TLabel', font=('Segoe UI', 12, 'bold'))
    style.configure('TLabelframe', background=BG, bordercolor='#2a405f')
    style.configure('TLabelframe.Label', foreground=MUTED)
    style.configure('TButton', background=PANEL, foreground=TEXT, padding=(12, 8))
    style.map('TButton', background=[('active', '#274565'), ('disabled', '#182333')],
              foreground=[('disabled', '#708097')])
    style.configure('Primary.TButton', background=BLUE)
    style.configure('Danger.TButton', background=RED, foreground='white')
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(22, 10), background=PANEL, foreground=MUTED)
    style.map('TNotebook.Tab', background=[('selected', '#233d5c')], foreground=[('selected', TEXT)])
    style.configure('TEntry', fieldbackground=PANEL, foreground=TEXT, insertcolor=TEXT)
    style.configure('TCombobox', fieldbackground=PANEL, foreground=TEXT, arrowcolor=TEXT)
    style.map('TCombobox', fieldbackground=[('readonly', PANEL)], foreground=[('readonly', TEXT)])
    style.configure('TSpinbox', fieldbackground=PANEL, foreground=TEXT, arrowcolor=TEXT)
    root.option_add('*TCombobox*Listbox.background', PANEL)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)

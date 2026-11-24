"""Ventana única; Tkinter solo recibe eventos desde el hilo principal."""
from collections import deque
import queue
import threading
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
from app.config import ROOT
from ui import theme
from ui.tabs.automatico import AutomaticTab
from ui.tabs.manual import ManualTab
from ui.tabs.dataset import DatasetTab
from ui.tabs.configuracion import ConfigTab


class MainWindow(tk.Tk):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.title('Robot Inteligente 4WD | Fase 01')
        self.geometry(f"{min(1280, self.winfo_screenwidth() - 40)}x{min(720, self.winfo_screenheight() - 110)}")
        self.minsize(1050, 640)
        theme.apply(self)
        self.history = deque(maxlen=150)
        self.closing = False
        top = ttk.Frame(self, padding=(16, 10))
        top.pack(fill='x')
        ttk.Label(top, text='ROBOT INTELIGENTE 4WD', style='Title.TLabel').pack(side='left')
        self.badge = tk.Label(top, bg='#73531b', fg='#ffe8a8', padx=14, pady=6, font=('Segoe UI', 11, 'bold'))
        self.badge.pack(side='right')
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True, padx=12)
        self.auto = AutomaticTab(self.tabs, app)
        self.manual = ManualTab(self.tabs, app, self.run)
        self.dataset = DatasetTab(self.tabs, app)
        self.config_tab = ConfigTab(self.tabs, app, self.run)
        for tab, name in [(self.auto, 'Automático'), (self.manual, 'Manual'),
                          (self.dataset, 'Dataset'), (self.config_tab, 'Configuración')]:
            self.tabs.add(tab, text=name)
        self.tabs.bind('<<NotebookTabChanged>>', self.tab_changed)
        status = ttk.Frame(self, padding=(14, 8))
        status.pack(fill='x')
        self.status = tk.StringVar()
        ttk.Label(status, textvariable=self.status, wraplength=1040).pack(side='left', fill='x', expand=True)
        ttk.Button(status, text='■ STOP GLOBAL', style='Danger.TButton', command=lambda: app.dispatcher.stop()).pack(side='right', padx=(12, 0))
        self.message = tk.StringVar(value='Inicio desarmado. No se ha enviado ninguna orden al hardware.')
        ttk.Label(self, textvariable=self.message, wraplength=1200, style='Muted.TLabel', padding=(14, 4)).pack(fill='x')
        self.journal = tk.Text(self, height=3, bg=theme.PANEL, fg=theme.TEXT, font=('Consolas', 9), state='disabled')
        self.journal.pack(fill='x', padx=14, pady=(0, 8))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(80, self.tick)

    def run(self, callback):
        try:
            callback()
        except Exception as exc:
            self.app.event('error', str(exc))

    def tab_changed(self, _=None):
        if self.closing or self.app.reconfiguring:
            return
        selected = self.tabs.index('current')
        # Configuración supervisa el modo actual; las demás pestañas cambian propietario.
        if selected < 3:
            self.app.controller.change_mode(('automatico', 'manual', 'dataset')[selected])

    def tick(self):
        if self.closing:
            if self.app.closed:
                self.destroy()
            else:
                self.after(80, self.tick)
            return
        if not self.app.reconfiguring:
            self.app.controller.tick()
        c = self.app.config
        self.badge.configure(text='SIMULACIÓN · SIN VALIDACIÓN FÍSICA' if c['simulation'] else 'HARDWARE REAL · OPERADOR')
        d = self.app.dispatcher
        s = d.safety.snapshot()
        cam = self.app.camera.snapshot()
        metrics = d.bridge.metrics()
        def number(v):
            return 'N/D' if v is None else f'{v:.1f}'
        frame = cam['frame']
        resolution = f'{frame.image.shape[1]}×{frame.image.shape[0]}' if frame else 'N/D'
        self.status.set(f"ESP32: {'verificado' if s['connected'] else 'sin conexión verificada'} | Cámara: {cam['status']} | "
                        f"FW {d.health.get('version', 'N/D')} / API {d.health.get('api_version', 'N/D')} | "
                        f"{'ARMADO local' if s['session_authorized'] else 'DESARMADO local'} / FW {'armado' if d.state.get('armed') else 'desarmado' if d.state else 'N/D'} | modo {s['mode']}\n"
                        f"{s['safety']} | FPS {number(frame.fps if frame and cam['fresh'] else None)} · {resolution} | "
                        f"edad desde recepción {number(cam['age_s'] * 1000 if cam['age_s'] is not None else None)} ms | "
                        f"{'API simulada' if c['simulation'] else 'HTTP'} p50/p95 {number(metrics['p50'])}/{number(metrics['p95'])} ms | "
                        f"errores {metrics['errors']} | controlador {number(d.response_ms)} ms")
        selected = self.tabs.index('current')
        if selected == 0:
            self.auto.video.update_frame(cam)
        elif selected == 2:
            self.dataset.video.update_frame(cam)
        self.manual.refresh()
        self.config_tab.diagnostics.set(f"Firmware: {d.health.get('firmware', 'No disponible')} {d.health.get('version', '')} / API {d.health.get('api_version', 'N/D')} · {s['safety']}")
        for _ in range(30):
            try:
                kind, payload = self.app.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'capture':
                self.dataset.show_saved(*payload)
                text = 'Captura original guardada'
            elif kind == 'counts':
                self.dataset.counts.set('Originales reales: ' + ', '.join(f'{k}: {v}' for k, v in payload.items()))
                continue
            else:
                text = str(payload)
            if kind == 'configured':
                self.manual.ms.set(str(c['pulse_ms']))
                self.dataset.storage.set('Destino: ' + str(self.app.dataset.root))
                self.tab_changed()
            self.message.set(text)
            self.history.append(f'{kind.upper()}: {text}')
            self.journal.configure(state='normal')
            self.journal.delete('1.0', 'end')
            self.journal.insert('1.0', '\n'.join(self.history))
            self.journal.see('end')
            self.journal.configure(state='disabled')
        self.after(80, self.tick)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.message.set('Cerrando trabajadores y solicitando STOP si existía conexión…')
        def task():
            try:
                self.app.close()
            except Exception as exc:
                import logging
                self.app.close_error = str(exc)
                logging.getLogger(__name__).error('Cierre incompleto: %s', type(exc).__name__)
                self.app.closed = True
        threading.Thread(target=task, name='cierre', daemon=True).start()

    def screenshot(self, path):
        self.update_idletasks()
        x, y = self.winfo_rootx(), self.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + self.winfo_width(), y + self.winfo_height())).save(path)

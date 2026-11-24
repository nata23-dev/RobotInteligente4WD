import json
import tkinter as tk
from tkinter import ttk, messagebox
from app.config import defaults
from ui.components.widgets import ScrollFrame
from ui.theme import PANEL, TEXT


class ConfigTab(ScrollFrame):
    def __init__(self, parent, app, run):
        super().__init__(parent)
        self.app, self.run = app, run
        p = self.body
        ttk.Label(p, text='Configuración persistente · solo con robot desarmado', style='Heading.TLabel').pack(anchor='w')
        ttk.Label(p, text='La simulación se cambia explícitamente aquí. Guardar exige volver a verificar y armar. No hay conexión automática.', style='Muted.TLabel').pack(anchor='w', pady=5)
        row = ttk.Frame(p)
        row.pack(fill='x', pady=6)
        ttk.Label(row, text='Clave API local').pack(side='left')
        self.key = tk.StringVar(value=app.config['api_key'])
        ttk.Entry(row, textvariable=self.key, show='●', width=36).pack(side='left', padx=10)
        ttk.Button(row, text='Verificar conexión / API', command=lambda: app.command('verify')).pack(side='left', padx=8)
        ttk.Button(row, text='Iniciar video', command=lambda: app.job(app.camera.start)).pack(side='left', padx=8)
        ttk.Button(row, text='Detener video', command=lambda: app.job(app.camera.stop)).pack(side='left', padx=8)
        self.diagnostics = tk.StringVar(value='Firmware y API: no verificados')
        ttk.Label(p, textvariable=self.diagnostics, wraplength=1100).pack(anchor='w', pady=5)
        ttk.Label(p, text='Ajustes JSON: red, tiempos, patrones FL/FR/RL/RR, servos, ArUco y destino del dataset. api_key se toma del campo protegido.', wraplength=1100).pack(anchor='w', pady=6)
        self.editor = tk.Text(p, height=17, bg=PANEL, fg=TEXT, insertbackground=TEXT, font=('Consolas', 10), undo=True)
        self.editor.pack(fill='x')
        self.populate(app.config)
        row = ttk.Frame(p)
        row.pack(fill='x', pady=9)
        ttk.Button(row, text='Validar y guardar ajustes', style='Primary.TButton', command=lambda: run(self.save)).pack(side='left', padx=(0, 8))
        ttk.Button(row, text='Intercambiar izquierda ↔ derecha', command=lambda: run(self.swap)).pack(side='left', padx=8)
        ttk.Button(row, text='Restaurar valores…', command=self.restore).pack(side='left', padx=8)
        ttk.Button(row, text='Exportar registros', command=app.export_logs).pack(side='left', padx=8)
        ttk.Label(p, text='Calibración humana · registrar medición de una prueba manual ya realizada', style='Heading.TLabel').pack(anchor='w', pady=(12, 5))
        row = ttk.Frame(p)
        row.pack(fill='x')
        self.movement = tk.StringVar(value='adelante')
        self.ms = tk.StringVar(value='150')
        self.measurement = tk.StringVar()
        self.unit = tk.StringVar(value='cm')
        ttk.Combobox(row, textvariable=self.movement, values=list(app.config['patterns']), state='readonly', width=30).pack(side='left', padx=4)
        for label, variable in [('Pulso ms', self.ms), ('Medición', self.measurement)]:
            ttk.Label(row, text=label).pack(side='left', padx=4)
            ttk.Entry(row, textvariable=variable, width=8).pack(side='left', padx=4)
        ttk.Combobox(row, textvariable=self.unit, values=['cm', 'grados'], state='readonly', width=8).pack(side='left', padx=4)
        ttk.Button(row, text='Registrar', command=lambda: run(lambda: app.record_calibration(self.movement.get(), int(self.ms.get()), float(self.measurement.get()), self.unit.get()))).pack(side='left', padx=8)
        ttk.Label(p, text='Red prevista: ESP32CAM-CARRO, cámara 192.168.4.1; ESP32 por DHCP. Diagnóstico: Robot4WD_Diagnostico / 192.168.10.1. Confirmar URL y puerto reales. No hay PWM de velocidad.', wraplength=1100, style='Muted.TLabel').pack(anchor='w', pady=12)

    def populate(self, config):
        clean = dict(config)
        clean['api_key'] = ''
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', json.dumps(clean, indent=2, ensure_ascii=False))

    def read(self):
        config = json.loads(self.editor.get('1.0', 'end'))
        config['api_key'] = self.key.get()
        return config

    def save(self):
        config = self.read()
        if config['simulation'] != self.app.config['simulation']:
            if not messagebox.askyesno('Cambiar modo de hardware', '¿Aplicar el cambio explícito entre simulación y hardware real? Se requiere nueva verificación y armado.'):
                return
        self.app.update_config(config)

    def swap(self):
        c = self.read()
        c['patterns']['izquierda'], c['patterns']['derecha'] = c['patterns']['derecha'], c['patterns']['izquierda']
        self.populate(c)
        self.app.event('info', 'Laterales intercambiados en editor; valide y guarde para aplicar')

    def restore(self):
        if messagebox.askyesno('Restaurar editor', '¿Cargar valores iniciales en el editor? Debe guardar para aplicarlos.'):
            self.populate(defaults())
            self.key.set('')

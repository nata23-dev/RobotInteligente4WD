from tkinter import ttk
from ui.components.widgets import Video, ScrollFrame


class AutomaticTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='Supervisión autónoma · infraestructura Fase 01', style='Heading.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        self.video = Video(self)
        self.video.grid(row=1, column=0, sticky='nsew', padx=(0, 14))
        details = ScrollFrame(self)
        details.grid(row=1, column=1, sticky='nsew')
        for title in ('Imagen procesada', 'Objeto detectado', 'Color', 'Clasificación neuronal',
                      'Confianza', 'Estado heurístico', 'Reglas difusas', 'Error de alineación',
                      'Proximidad estimada', 'Movimiento seleccionado', 'Destino',
                      'Etapa del ciclo', 'Piezas clasificadas', 'Historial de decisiones'):
            ttk.Label(details.body, text=title, style='Heading.TLabel').pack(anchor='w', pady=(8, 1))
            ttk.Label(details.body, text='No disponible · pendiente de implementación', style='Muted.TLabel').pack(anchor='w')
        row = ttk.Frame(self)
        row.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        ttk.Button(row, text='Iniciar · pendiente', state='disabled').pack(side='left', padx=(0, 8))
        ttk.Button(row, text='Pausar · pendiente', state='disabled').pack(side='left', padx=8)
        ttk.Button(row, text='Detener', style='Danger.TButton', command=lambda: app.dispatcher.stop()).pack(side='left', padx=8)
        ttk.Label(row, text='CNN, heurística, difusa y navegación: sin implementar', style='Muted.TLabel').pack(side='left', padx=12)

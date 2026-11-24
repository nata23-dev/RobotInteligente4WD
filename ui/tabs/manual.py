import tkinter as tk
from tkinter import ttk, messagebox
from ui.components.widgets import ScrollFrame


class ManualTab(ScrollFrame):
    def __init__(self, parent, app, run):
        super().__init__(parent)
        self.app, self.run = app, run
        p = self.body
        ttk.Label(p, text='Control manual · órdenes discretas y sin repetición', style='Heading.TLabel').pack(anchor='w')
        ttk.Label(p, text='Patrones V7 sin certificación física. ENA/ENB con jumper: sin control PWM de velocidad.', style='Muted.TLabel').pack(anchor='w', pady=5)
        top = ttk.Frame(p)
        top.pack(fill='x', pady=8)
        ttk.Button(top, text='Verificar conexión', command=lambda: app.command('verify')).pack(side='left', padx=(0, 8))
        ttk.Button(top, text='Armar explícitamente', style='Primary.TButton', command=lambda: app.command('arm')).pack(side='left', padx=8)
        ttk.Button(top, text='STOP / desarmar', style='Danger.TButton', command=lambda: app.dispatcher.stop()).pack(side='left', padx=8)
        ttk.Label(top, text='Pulso ms').pack(side='left', padx=(16, 5))
        self.ms = tk.StringVar(value=str(app.config['pulse_ms']))
        ttk.Spinbox(top, from_=50, to=700, increment=25, width=7, textvariable=self.ms).pack(side='left')
        columns = ttk.Frame(p)
        columns.pack(fill='x', pady=10)
        wheels = ttk.LabelFrame(columns, text='Chasis Mecanum · FL, FR, RL, RR', padding=12)
        wheels.pack(side='left', fill='both', expand=True, padx=(0, 12))
        directions = [('↖ Diagonal', 'diagonal_frente_izquierda'), ('↑ Avanzar', 'adelante'), ('Diagonal ↗', 'diagonal_frente_derecha'),
                      ('← Lateral', 'izquierda'), ('STOP', None), ('Lateral →', 'derecha'),
                      ('↙ Diagonal', 'diagonal_atras_izquierda'), ('↓ Retroceder', 'atras'), ('Diagonal ↘', 'diagonal_atras_derecha'),
                      ('↶ Giro izquierda', 'girar_izquierda'), ('↷ Giro derecha', 'girar_derecha')]
        for i, (label, key) in enumerate(directions):
            ttk.Button(wheels, text=label, style='Danger.TButton' if key is None else 'TButton',
                       command=(lambda: app.dispatcher.stop()) if key is None else
                       lambda key=key: run(lambda: self.drive(app.config['patterns'][key]))).grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky='ew')
        for i in range(3):
            wheels.columnconfigure(i, weight=1)
        individual = ttk.LabelFrame(columns, text='Ruedas individuales', padding=12)
        individual.pack(side='left', fill='both')
        for i, name in enumerate(('FL · delantera izquierda', 'FR · delantera derecha', 'RL · trasera izquierda', 'RR · trasera derecha')):
            ttk.Label(individual, text=name).grid(row=i, column=0, padx=5, pady=7, sticky='w')
            for j, direction in enumerate((-1, 1)):
                ttk.Button(individual, text=f'{direction:+d}', command=lambda i=i, d=direction: run(lambda: self.drive([d if n == i else 0 for n in range(4)]))).grid(row=i, column=j + 1, padx=3)
        self.angles = {}
        for name, title in [('garra', 'Garra · GPIO21'), ('base', 'Base horizontal · GPIO18')]:
            box = ttk.LabelFrame(p, text=title, padding=12)
            box.pack(fill='x', pady=6)
            ttk.Button(box, text='Activar individual', command=lambda name=name: self.enable(name)).pack(side='left', padx=4)
            self.angles[name] = tk.StringVar(value=str(app.config['servos'][name]['home']))
            limits = app.config['servos'][name]
            ttk.Spinbox(box, from_=limits['min'], to=limits['max'], width=6, textvariable=self.angles[name]).pack(side='left', padx=5)
            ttk.Button(box, text='Enviar ángulo', command=lambda name=name: run(lambda: self.servo(name, int(self.angles[name].get())))).pack(side='left', padx=4)
            for delta in (-1, 1):
                ttk.Button(box, text=f'{delta:+d}°', command=lambda name=name, delta=delta: run(lambda: self.fine(name, delta))).pack(side='left', padx=4)
            ttk.Button(box, text='Abrir 60°' if name == 'garra' else 'Centro 75°', command=lambda name=name: run(lambda: self.servo(name, app.config['servos'][name]['home']))).pack(side='left', padx=4)
            if name == 'garra':
                ttk.Button(box, text='Cerrar provisional', command=lambda: run(lambda: self.servo('garra', app.config['servos']['garra']['closed']))).pack(side='left', padx=4)
            ttk.Button(box, text='Liberar…', command=lambda name=name: self.release(name)).pack(side='left', padx=4)
        self.state = tk.StringVar(value='Estado de actuadores no disponible')
        ttk.Label(p, textvariable=self.state, wraplength=1100).pack(anchor='w', pady=12)
        ttk.Label(p, text='Los ángulos son órdenes de software; no son mediciones de posición ni de agarre.', style='Muted.TLabel').pack(anchor='w')

    def drive(self, directions):
        self.app.controller.drive(directions, int(self.ms.get())).add_done_callback(self.app_command_done)

    def app_command_done(self, future):
        if future.cancelled():
            self.app.event('info', 'Movimiento cancelado')
        elif future.exception():
            self.app.event('error', str(future.exception()))
        else:
            self.app.event('info', 'Pulso aceptado; no confirma desplazamiento físico')

    def servo(self, name, degree):
        self.app.command('servo', {'nombre': name, 'grado': degree})

    def fine(self, name, delta):
        state = self.app.dispatcher.state
        if name not in state:
            raise ValueError('Verifique el estado del servo primero')
        self.servo(name, state[name] + delta)

    def enable(self, name):
        if messagebox.askyesno('Activar servo', f'Activar {name} puede moverlo a HOME. ¿Brazo apoyado y zona despejada?'):
            self.app.command('enable', {'nombre': name})

    def release(self, name):
        if messagebox.askyesno('Liberación individual', f'Sujete el brazo y la carga. ¿Confirma liberar {name} con el robot desarmado?'):
            self.app.command('release', {'nombre': name, 'confirm': 1})

    def refresh(self):
        s = self.app.dispatcher.state
        if s:
            self.state.set(f"Ruedas activas: {s['motor_activo']} · brazo ocupado: {s['brazo_ocupado']}\n"
                           f"Garra ordenada: {s['garra']}° → {s['garra_objetivo']}° / PWM: {s['servo_garra_activo']} · "
                           f"Base ordenada: {s['base']}° → {s['base_objetivo']}° / PWM: {s['servo_base_activo']}")

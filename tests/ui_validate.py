"""Validación gráfica opcional, siempre simulada; sin órdenes al robot físico."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.application import Application
from app.models import Command
from ui.main_window import MainWindow


def main():
    app = Application(simulation=True)
    window = MainWindow(app)
    output = Path('evidencias')
    output.mkdir(exist_ok=True)
    results = {'simulation_only': True, 'layouts': [], 'screen': [window.winfo_screenwidth(), window.winfo_screenheight()]}
    def pump(seconds=.2):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            window.update()
            time.sleep(.01)
    try:
        pump()
        assert window.tabs.index('current') == 0
        assert not app.dispatcher.bridge.history, 'El arranque no debe emitir solicitudes'
        for width, height in ((1366, 768), (1920, 1080)):
            if width == 1366:
                window.state('zoomed')
            else:
                window.state('normal')
                window.geometry(f'{width}x{height}+0+0')
            pump()
            for index in range(4):
                window.tabs.select(index)
                pump()
                tab = (window.auto, window.manual, window.dataset, window.config_tab)[index]
                body = tab.body if hasattr(tab, 'body') else tab
                overflow = []
                def inspect(parent):
                    for child in parent.winfo_children():
                        if child.winfo_manager() in ('pack', 'grid'):
                            if child.winfo_x() + child.winfo_width() > parent.winfo_width() + 2:
                                overflow.append(str(child))
                        inspect(child)
                inspect(body)
                results['layouts'].append({'size': [width, height], 'tab': index, 'horizontal_overflow': overflow})
                if width == 1366 and window.winfo_screenwidth() >= 1366 and window.winfo_screenheight() >= 768:
                    window.screenshot(output / f'ui_{index}_1366.png')
        window.tabs.select(1)
        pump()
        app.command('verify')
        pump(.3)
        app.command('arm')
        pump(.15)
        assert app.dispatcher.safety.session
        window.manual.ms.set('150')
        window.manual.drive(app.config['patterns']['adelante'])
        pump(.3)
        assert any(a == 'drive' for a, _ in app.dispatcher.bridge.history)
        window.tabs.select(2)
        pump(.2)
        assert not app.dispatcher.safety.session
        assert not app.dispatcher.bridge.request('state')['armed']
        results['manual_simulated_pulse_and_mode_stop'] = 'OK'
        results['overflow_count'] = sum(len(r['horizontal_overflow']) for r in results['layouts'])
        (output / 'validacion_gui.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(json.dumps(results, indent=2))
        assert results['overflow_count'] == 0, 'Controles desbordados horizontalmente'
    finally:
        app.close()
        window.destroy()


if __name__ == '__main__':
    main()

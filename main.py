"""Punto único de entrada. Predeterminado seguro: simulación sin cámara ficticia."""
import argparse
import sys
import struct


def main():
    if sys.version_info[:2] != (3, 12) or struct.calcsize('P') != 8:
        raise SystemExit('Use Python 3.12 de 64 bits y el entorno .venv del proyecto')
    parser = argparse.ArgumentParser(description='Robot Inteligente 4WD · Fase 01')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--simulacion', action='store_true')
    group.add_argument('--real', action='store_true')
    parser.add_argument('--smoke-ui', action='store_true', help='Abrir GUI simulada, verificar cuatro pestañas y cerrar')
    args = parser.parse_args()
    from app.application import Application, setup_logging
    from ui.main_window import MainWindow
    listener = setup_logging()
    app = None
    try:
        app = Application(simulation=True if args.simulacion or args.smoke_ui else False if args.real else None)
        window = MainWindow(app)
        if args.smoke_ui:
            def inspect():
                assert window.tabs.index('end') == 4
                assert not app.dispatcher.safety.session
                print('GUI: cuatro pestañas, Automático principal, inicio desarmado; simulación')
                window.close()
            window.after(1800, inspect)
        window.mainloop()
        if app.close_error:
            raise RuntimeError('Cierre incompleto: ' + app.close_error)
    finally:
        if app and not app.closed:
            app.close()
        listener.stop()


if __name__ == '__main__':
    main()

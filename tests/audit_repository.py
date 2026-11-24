"""Auditoría previa al commit; no imprime los valores privados encontrados."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z'], cwd=ROOT).decode().split('\0')
    files = [name for name in files if name]
    if not files:
        raise SystemExit('No hay archivos preparados para auditar')
    forbidden = ('referencias_locales/', '.venv/', '.runtime/', '.tools/', 'logs/robot', 'dataset/images/', 'dataset/metadata/')
    secrets = set()
    references = list((ROOT / 'referencias_locales').rglob('*.ino'))
    for path in references:
        source = path.read_text(encoding='utf-8-sig')
        for name, value in re.findall(r'const char\*\s+(\w+)\s*=\s*"([^"]*)"', source):
            if ('PASSWORD' in name or name == 'API_KEY') and len(value) >= 8:
                secrets.add(value.encode())
    problems = []
    for name in files:
        if (name.startswith(forbidden) and not name.endswith('.gitkeep')) or name.endswith('.zip') or 'config.local' in name or '__pycache__' in name:
            problems.append('Ruta privada: ' + name)
        data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
        if any(value in data for value in secrets):
            problems.append('Valor de credencial histórica en: ' + name)
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    print(f'Auditoría OK: {len(files)} archivos; referencias privadas fuera del índice; sin valores de credenciales históricas detectados')


if __name__ == '__main__':
    main()

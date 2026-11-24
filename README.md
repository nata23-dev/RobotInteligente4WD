# Robot Inteligente 4WD — Fase 01.1

Aplicación local de escritorio para supervisar y operar manualmente el robot mediante **Robot4WD 1.0.0 / API 1**. La primera ejecución usa **simulación**, sin conectar ni armar hardware. La sección Automático abre por defecto; CNN, heurística, control difuso y navegación están pendientes y su inicio está deshabilitado. La Fase 01.1 incorpora identidad clara y navegación lateral sobre la base funcional de la Fase 01.

Esta entrega de software no certifica el robot físico. No se enviaron órdenes al hardware durante su desarrollo. Los patrones recuperados de V7, el agarre, la alimentación y el video real requieren validación del operador. La parada de software no corta electricidad.

## Instalar en Windows

Requisitos: Python **3.12 x64 con Tcl/Tk**, Git si se desea conservar historial y acceso a Internet durante la instalación inicial. La operación posterior es local. No instalar TensorFlow en esta fase.

1. Abra `C:\RobotInteligente4WD`.
2. Ejecute `INSTALAR.bat`.
3. Ejecute `INICIAR_APLICACION.bat`.

En el equipo de desarrollo quedó Python 3.12.10 bajo `.runtime/` y el entorno independiente `.venv/`. El instalador reconoce ese intérprete; en otra computadora usa `py -3.12`. `.runtime/` y `.venv/` no se distribuyen en Git. El intérprete se obtuvo del instalador oficial x64 con firma válida de Python Software Foundation; no se instalaron dependencias en los Python globales existentes.

Comandos equivalentes de PowerShell desde la raíz, para un equipo con Python 3.12 instalado:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py
```

En este equipo también puede crear el entorno con `.\.runtime\python.exe -m venv .venv`. No necesita activar el entorno ni modificar la política de ejecución de PowerShell.

Inicio explícito en simulación:

```powershell
.\INICIAR_APLICACION.bat --simulacion
```

`--real` elige hardware real explícitamente para esa ejecución; no verifica, arma ni mueve por sí mismo. Sin argumentos se utiliza la configuración local. No hay conmutación automática entre simulador y robot real.

## Primera operación en simulación

Abra Manual, pulse **Verificar conexión** y luego **Armar explícitamente**. Pruebe un pulso de 150 ms y STOP. Los servos requieren activación individual y el tiempo de asentamiento reportado por el firmware simulado. Liberar requiere detener primero y confirmar con el brazo apoyado. Cambiar a Dataset o Automático detiene y desarma. Configuración conserva el modo vigente para permitir diagnóstico sin cambios de propietario.

El simulador genera estado lógico de actuadores y errores de protocolo; no genera video ni datos de IA. Las métricas de API simulada son tiempos reales del código local y no representan latencia Wi-Fi.

## Primera conexión física

1. Lea [el plan físico](docs/PLAN_DE_PRUEBAS_FISICAS.md). Confirme firmware instalado, cableado y alimentación con los actuadores inicialmente sin energía, ruedas suspendidas, brazo apoyado e interruptor físico accesible.
2. Conecte la PC a `ESP32CAM-CARRO`, si la topología real lo permite. Obtenga la IP DHCP del principal desde monitor serie a 115200. No suponga `.200`. La red `Robot4WD_Diagnostico` en `192.168.10.1` permite diagnóstico, pero no garantiza acceso a cámara.
3. En Configuración → Conectividad introduzca la dirección HTTP del ESP32, la URL del video y la clave local en su campo oculto. Desmarque Simulación, guarde y confirme el cambio explícito a hardware real. El JSON interno y sus validaciones se conservan; no hace falta editarlo manualmente.
4. Pulse Verificar conexión/API. Debe identificar Robot4WD **1.0.0**, API **1**, y obtener estado autenticado. La aplicación rechaza PythonBridgeV6.
5. Pulse Iniciar video con la URL real comprobada, incluido su puerto y ruta. La dirección prevista de cámara es `192.168.4.1`; no hay URL ni puerto supuestos en la configuración inicial.
6. Sin armar, compruebe STOP y estado desarmado. Complete pruebas de red, caducidad y alimentación del plan. Solo el operador podrá autorizar después el armado y las pruebas individuales.

No cargar firmware, mover ruedas ni activar servos automáticamente. El firmware original del ZIP tiene credenciales vacías de forma intencional; debe configurarlo y compilarlo el operador en su copia privada. Su fuente sin cambios está en `firmware/`; no se compiló ni cargó desde esta sesión.

## Configuración y datos

`config.example.json` no contiene claves. `config.local.json` es privado y está excluido de Git; se crea con valores iniciales en este equipo y se guarda atómicamente desde la aplicación. No comparta ese archivo. El campo de clave se oculta visualmente, pero la configuración local está en texto legible bajo los permisos de su cuenta de Windows. HTTP del firmware tampoco cifra la clave; use la red local controlada.

Los formularios de Conectividad, Hardware, Calibración, Visión artificial y Mantenimiento permiten cambiar patrones, duración, límites conservadores, timeout, heartbeat, reconexión, directorio del dataset y salud del controlador. Las categorías Inteligencia artificial y Estaciones muestran contratos pendientes y destinos fijados para esta fase. Se rechazan límites fuera de firmware, patrones de ceros, tipos incorrectos y cambios de HOME incompatibles. ArUco queda fijado en DICT_4X4_50, 0=cubo, 1=cilindro, 2=prisma triangular.

El Dataset muestra totales por forma y color desde el manifiesto de originales reales existentes. Su meta inicial de 150 imágenes por clase se puede cambiar y guardar en `ui.local.json`, una preferencia visual privada separada del schema de control. Cambiar la meta no genera muestras ni cambia el comportamiento del robot.

Dataset guarda originales PNG sin anotaciones en `dataset/images/forma/sesion/`. El manifiesto CSV incluye etiqueta humana, color, sesión, UTC, ID, tiempo monotónico de recepción, antigüedad al guardar y dimensiones. No guarda URL ni credenciales. Solo acepta fotogramas frescos con el robot desarmado. Las ráfagas y división por sesiones están pendientes. El contador excluye fixtures sintéticos de pruebas.

Las mediciones de desplazamiento se introducen después de una prueba manual, con movimiento, pulso, valor y unidad; se registran en `calibration/mediciones.csv`. El antecedente 20.5 cm/350 ms de la bitácora no se importa como calibración vigente. Los registros rotan en `logs/` y se exportan desde Configuración a `evidencias/`.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py --smoke-ui
.\.venv\Scripts\python.exe tests\ui_validate.py
.\.venv\Scripts\python.exe tests\ui_redesign_validate.py
```

Las pruebas gráficas requieren escritorio: `ui_validate.py` conserva el chequeo original; `ui_redesign_validate.py` añade recortes verticales/horizontales, 1280×720, 1366×768, 1600×900 y 1920×1080 con comprobación de tamaño efectivamente aplicado, categorías de formularios, escalados tipográficos virtuales y STOP simulado. Guarda evidencia en `evidencias/ui_fase01_1/`. Los frames sintéticos se usan solo en pruebas y nunca como datos del robot real.

## Interfaz Fase 01.1

Tema claro, paleta centralizada, iconos lineales locales y navegación lateral. Automático reúne visor original/procesado, contratos de los cuatro módulos de IA, ocho etapas y registro. Manual conserva todos los controles y añade un esquema físico FL/FR/RL/RR. Dataset reúne captura y distribución real; Configuración utiliza siete categorías de formularios. STOP GLOBAL permanece en la cabecera, fuera del contenido desplazable. `Alt+1` a `Alt+4` cambian de sección y `Esc` solicita STOP; no hay atajos de movimiento continuo.

La navegación usa los mismos cambios de propietario que antes: Manual/Dataset/Automático detienen y desarman al cambiar cuando existía conexión; Configuración conserva el modo para diagnóstico. Ninguna navegación arma. El visor procesado está señalado como pendiente y no inventa imágenes. Captura queda deshabilitada si falta un frame fresco o hay actuadores autorizados/ocupados.

Consulte [el sistema de diseño](docs/DESIGN_SYSTEM.md) y [el informe UX/UI](docs/VALIDACION_UI_FASE01_1.md). No se agregaron dependencias de ejecución ni se modificaron firmware, HTTP, sesiones, heartbeat o seguridad.

## Mapa del proyecto

```text
main.py                         entrada única
app/                            configuración, modelos y composición
ui/components/, ui/tabs/         interfaz Tkinter y cuatro pestañas
hardware/                       cliente API 1, cámara y simulador
control/                        despachador, seguridad y arbitraje
ai/                             contratos pendientes de percepción/IA
dataset/                        captura, originales y manifiesto
training/, models/              reservados; sin entrenamiento ni pesos
calibration/, logs/, evidencias/ mediciones y evidencia local
firmware/                       distribución original sin modificar
docs/                           arquitectura, API, pruebas y validación
tests/                          pruebas sin robot y validación gráfica
referencias_locales/            originales privados, fuera de Git
```

Dependencias directas verificadas: OpenCV contrib 4.12.0.88, NumPy 2.2.6, Pillow 12.0.0 y Requests 2.32.5. `requirements-lock.txt` fija también dependencias transitivas. Se eligió una rama OpenCV 4.x con ruedas disponibles para Python 3.12 y se verificó ArUco por generación/detección de IDs 0, 1 y 2. No se instalan otros paquetes que compartan `cv2`. Versiones consultadas en el índice real y resueltas en `.venv`; no se exige usar la última versión publicada.

Referencias: [Python 3.12.10 oficial](https://www.python.org/downloads/release/python-31210/), [distribución OpenCV contrib](https://pypi.org/project/opencv-contrib-python/4.12.0.88/). El contrato se deriva del sketch y LEEME originales, no de documentación web genérica.

Consulte [arquitectura](docs/ARQUITECTURA.md), [contrato API](docs/CONTRATO_API.md), [validación de software](docs/VALIDACION_FASE01.md) y la bitácora histórica. La siguiente puerta es la validación física controlada de esta infraestructura. La Fase 02 requiere autorización nueva.

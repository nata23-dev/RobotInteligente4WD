# Robot Inteligente 4WD

**Corrección 03.3-C — 25/11/2026:** recuperación automática de supervisión desarmada tras errores transitorios, sin rearme ni repetición de movimientos. Conexión, estado reciente, autorización y STOP se muestran por separado. Heartbeat y STOP conservan prioridad; las lecturas lentas de recuperación no habilitan captura. Configuración privada efectiva preservada: timeout 0.30 s y heartbeat 0.25 s. [Política, diagnóstico y pruebas físicas pendientes](docs/COMUNICACIONES_Y_RECUPERACION.md). No se reprodujeron las mediciones físicas del operador durante el desarrollo.

**Fase 03 implementada en software, 24/11/2026.** Rama de revisión `feat/fase-03-vision`; `main` conserva la base estable `4bd6ba6`. Incluye orientación y ajustes digitales, Automático con visor Original/Procesada/Máscara, HSV, seguimiento visual, ArUco, ROI, ráfagas cancelables, calidad, recortes trazables y división por sesiones. No se contactó hardware; autonomía, CNN, lógica difusa y heurística siguen bloqueadas o pendientes. Véanse [la guía de uso](docs/VISION_Y_DATASET_FASE03.md) y [la validación](docs/VALIDACION_FASE03.md). Los informes anteriores conservan su contexto histórico.

Aplicación local de escritorio para supervisar y operar manualmente el robot mediante **Robot4WD 1.0.0 / API 1**. La primera ejecución usa **simulación**, sin conectar ni armar hardware. La sección Automático abre por defecto; CNN, heurística, control difuso y navegación están pendientes y su inicio está deshabilitado. La Fase 01.1 incorpora identidad clara y navegación lateral sobre la base funcional de la Fase 01.

Durante la construcción y esta consolidación automatizada no se enviaron órdenes al hardware. El operador reportó posteriormente conexión real, video simultáneo y pruebas lógicas de sesión/STOP; esos avances parciales están registrados en la bitácora. No certifican la seguridad física completa. **El robot está fuera de servicio temporalmente por una incidencia de alimentación y un giro inesperado de una rueda al encender. La autonomía permanece bloqueada.** La parada de software no corta electricidad.

## Propósito y estado actual — 24/11/2026

Proyecto académico de Inteligencia Artificial, con entrega el **30 de noviembre de 2026**. El objetivo final es detectar, reconocer, recoger, transportar y clasificar cubos, cilindros y prismas triangulares de colores rojo/verde/azul, clasificando principalmente por forma. Se prevé integrar heurística, procesamiento de imágenes, CNN y lógica difusa en las decisiones y movimientos reales; **esa autonomía todavía no está implementada ni validada**.

- **Fase 01:** infraestructura modular, API 1, control manual, seguridad, cámara, dataset y simulador.
- **Fase 01.1:** interfaz clara con navegación lateral y formularios; se conserva sin un nuevo rediseño de Automático.
- **Fase 02:** comprobaciones físicas iniciales comunicadas por el operador, con cierre formal pendiente; no existe un commit independiente que implemente otra arquitectura.
- **Fase 02.1:** consolidación, auditoría y publicación del estado completo; consultar [el informe de consolidación](docs/CONSOLIDACION_FASE02_1.md).
- **Fase 03:** software de las subfases 03.1–03.4 implementado en rama de revisión; [estado y pendientes físicos](docs/PLAN_FASE03.md). No se han confirmado controles remotos de la cámara ni validado físicamente la visión.

Fuente central de continuidad: [ESTADO_PROYECTO_ROBOT_INTELIGENTE.md](ESTADO_PROYECTO_ROBOT_INTELIGENTE.md). Los informes históricos conservan los resultados de cada fase y no sustituyen la ejecución actual de pruebas.

## Arquitectura y componentes

Una sola aplicación Python en Windows realiza interfaz, comunicaciones, captura, registros y futura IA. El ESP32 principal ejecuta actuadores y vigilancia local mediante HTTP Robot4WD 1.0.0/API 1; la ESP32-CAM transmite MJPEG y proporciona la red compartida según el montaje observado. La operación es local, sin servicios externos durante el control.

Hardware declarado: ESP32 principal, ESP32-CAM con OV5640, cuatro motores DC y ruedas Mecanum, dos L298N con jumpers ENA/ENB, brazo de altura fija con giro horizontal y dos servos funcionales (garra/base), baterías y alimentación del montaje. No hay control PWM independiente de velocidad ni sensores de agarre, corriente o posición física reportados. Pines conservados: FL 26/25, FR 33/32, RL 13/12, RR 14/27; garra 21 y base 18.

La PC recibe video en un trabajador, despacha comandos/heartbeat en otro, supervisa seguridad y actualiza Tkinter en su hilo principal. Python no comparte la autoridad de actuadores con fuentes paralelas. Tecnologías: Python 3.12 x64, Tkinter/ttk, OpenCV contrib, NumPy, Pillow, Requests, threading/queue, dataclasses, JSON, CSV, logging, unittest y Git. TensorFlow/Keras se reserva para una fase posterior.

### Observaciones comunicadas por el operador

SSID corregido: `ESP32-CAM-CARRO`. Cámara `192.168.4.1`, principal observado por DHCP en `192.168.4.2` y diagnóstico `Robot4WD_Diagnostico` en `192.168.10.1`. Stream reportado: `http://192.168.4.1:81/stream`, 320×240 y aproximadamente 10–12 FPS, con orientación incorrecta cercana a 90° y calidad pendiente de optimizar. Se reportaron p95 de 32–47 ms en algunas pruebas estables; no son mediciones nuevas de esta consolidación. Varias desconexiones fueron deliberadas al cambiar de Wi-Fi.

En Fase 02.1 el archivo privado guardaba heartbeat 0.25 s y timeout **0.18 s**, aunque se había comunicado ajustar 0.30 s. En la revisión del **25/11/2026** ya guardaba **0.30 s**, avance del operador que se preservó sin reescribir configuración. Las direcciones DHCP observadas no son garantías permanentes.

La pérdida de ambas redes y de potencia apunta provisionalmente a baterías descargadas/caída de tensión, sin medición eléctrica que confirme la causa. El giro de una rueda desde la energización es una incidencia prioritaria: debe resolverse y verificarse físicamente antes de autorizar autonomía. Brazo, desplazamientos, agarre, transporte y depósito siguen pendientes. Detalle y procedencia: [bitácora](ESTADO_PROYECTO_ROBOT_INTELIGENTE.md).

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
2. Conecte la PC a `ESP32-CAM-CARRO`, según el nombre corregido comunicado por el operador. Obtenga la IP DHCP del principal desde monitor serie a 115200. No suponga `.200` ni que `.2` sea permanente. La red `Robot4WD_Diagnostico` en `192.168.10.1` permite diagnóstico, pero no garantiza acceso a cámara.
3. En Configuración → Conectividad introduzca la dirección HTTP del ESP32, la URL del video y la clave local en su campo oculto. Desmarque Simulación, guarde y confirme el cambio explícito a hardware real. El JSON interno y sus validaciones se conservan; no hace falta editarlo manualmente.
4. Pulse Verificar conexión/API. Debe identificar Robot4WD **1.0.0**, API **1**, y obtener estado autenticado. La aplicación rechaza PythonBridgeV6.
5. Pulse Iniciar video con la URL real comprobada, incluido su puerto y ruta. La dirección prevista de cámara es `192.168.4.1`; no hay URL ni puerto supuestos en la configuración inicial.
6. Sin armar, compruebe STOP y estado desarmado. Complete pruebas de red, caducidad y alimentación del plan. Solo el operador podrá autorizar después el armado y las pruebas individuales.

Este procedimiento queda condicionado a resolver primero las incidencias de alimentación/arranque y seguir el plan físico actualizado. No cargar firmware, mover ruedas ni activar servos automáticamente. El firmware original del ZIP tiene credenciales vacías intencionalmente y conserva el SSID histórico sin guion; su fuente sin cambios está en `firmware/`. Para una preparación futura, trabaje sobre una copia privada ignorada, no introduzca claves en el sketch rastreado. La fuente exacta del binario instalado no se recuperó en esta consolidación; no se compiló ni cargó firmware.

## Configuración y datos

`config.example.json` no contiene claves. `config.local.json` es privado y está excluido de Git; se crea con valores iniciales en este equipo y se guarda atómicamente desde la aplicación. No comparta ese archivo. El campo de clave se oculta visualmente, pero la configuración local está en texto legible bajo los permisos de su cuenta de Windows. HTTP del firmware tampoco cifra la clave; use la red local controlada.

Los formularios de Conectividad, Hardware, Calibración, Visión artificial y Mantenimiento permiten cambiar patrones, duración, límites conservadores, timeout, heartbeat, reconexión, directorio del dataset y salud del controlador. Las categorías Inteligencia artificial y Estaciones muestran contratos pendientes y destinos fijados para esta fase. Se rechazan límites fuera de firmware, patrones de ceros, tipos incorrectos y cambios de HOME incompatibles. ArUco queda fijado en DICT_4X4_50, 0=cubo, 1=cilindro, 2=prisma triangular.

El Dataset muestra totales por forma y color desde el manifiesto de originales reales existentes. Su meta inicial de 150 imágenes por clase se puede cambiar y guardar en `ui.local.json`, una preferencia visual privada separada del schema de control. Cambiar la meta no genera muestras ni cambia el comportamiento del robot.

Dataset guarda originales PNG sin anotaciones en `dataset/images/forma/sesion/`. El manifiesto CSV incluye etiqueta humana, color, sesión, UTC, ID, tiempo monotónico de recepción, antigüedad al guardar y dimensiones. No guarda URL ni credenciales. Solo acepta fotogramas frescos con el robot desarmado y actuadores en reposo. Fase 03 agrega ráfagas, calidad, recortes orientados sin filtros/overlays en `derived/`, sidecar versionado y división por sesiones completas. El contador y la división excluyen fixtures sintéticos de pruebas.

Las mediciones de desplazamiento se introducen después de una prueba manual, con movimiento, pulso, valor y unidad; se registran en `calibration/mediciones.csv`. El antecedente 20.5 cm/350 ms de la bitácora no se importa como calibración vigente. Los registros rotan en `logs/` y se exportan desde Configuración a `evidencias/`.

## Verificación

```powershell
.\.venv\Scripts\python.exe scripts\check_software.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py --smoke-ui
.\.venv\Scripts\python.exe tests\ui_validate.py
.\.venv\Scripts\python.exe tests\ui_redesign_validate.py
```

`scripts/check_software.py` ejecuta la suite existente con un cerco adicional: solo permite loopback para las pruebas de HTTP y bloquea abrir la cámara física. No modifica `config.local.json`. Los resultados quedan en `evidencias/software_checks/`. Para ejecutarlo en este proyecto necesita el entorno gráfico requerido por las pruebas Tk. La referencia histórica fue de 50 pruebas; los resultados actuales y cualquier fallo corregido se detallan en [el informe](docs/CONSOLIDACION_FASE02_1.md).

Validación Fase 03: `python scripts/check_software.py --output evidencias/fase03/final` y `python scripts/validate_phase03.py` usando `.venv/Scripts/python.exe`. El segundo abre la aplicación real con `fixture_prueba`, bloquea toda red, usa destino temporal, captura evidencias locales y mide QVGA/VGA; no incorpora imágenes al dataset real. El mínimo admitido sigue siendo 1200×650; 1024×768 requiere mayor ancho de escritorio. 1600/1920 se verificaron geométricamente en el monitor de desarrollo 1366×768, sin afirmar inspección física en un monitor mayor.

Marcadores: [PDF A4 de estaciones](docs/recursos/estaciones_aruco.pdf), patrón propuesto de 10 cm, imprimir al 100 % y medir. Para regenerarlo: `python scripts/generate_markers.py`, con ReportLab opcional como herramienta de documentación. Las dependencias de ejecución de la aplicación permanecen sin cambios.

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

Consulte [arquitectura](docs/ARQUITECTURA.md), [contrato API](docs/CONTRATO_API.md), [validación histórica de software](docs/VALIDACION_FASE01.md), [plan de pruebas físicas](docs/PLAN_DE_PRUEBAS_FISICAS.md) y [bitácora](ESTADO_PROYECTO_ROBOT_INTELIGENTE.md). La siguiente puerta física exige resolver alimentación y giro al encender; la siguiente implementación, Fase 03, requiere nuevas instrucciones.

## Repositorio y revisión externa

Repositorio existente: [nata23-dev/RobotInteligente4WD](https://github.com/nata23-dev/RobotInteligente4WD), rama estable `main`. El propietario autorizó expresamente conservarlo **público** durante esta consolidación, sustituyendo el requisito inicial de privado. No se conceden permisos de aplicaciones externas ni se publican las ramas locales indiscriminadamente.

Se versionan código, plantillas, pruebas y documentación. `.venv/`, `.runtime/`, `.tools/`, referencias originales, configuraciones privadas, `.env`, claves locales, logs, datasets/modelos pesados y evidencias privadas quedan locales. La configuración de ejemplo usa simulación y una clave vacía. No publique `config.local.json`, `ui.local.json` ni copias del firmware con contraseñas. El informe de auditoría explica las limitaciones; no se afirma ausencia universal de secretos desconocidos.

Auditoría reproducible de contenido, índice e historial, sin mostrar valores sensibles:

```powershell
.\.venv\Scripts\python.exe scripts\audit_publication.py
```

Se complementa con Gitleaks y revisión de rutas/plantillas. Las capturas enlazadas en informes históricos permanecen locales y por eso no están disponibles desde un clon remoto; sus resultados y condiciones sí están documentados. La siguiente implementación es la Fase 03 únicamente cuando el propietario la autorice; la autonomía física sigue bloqueada por las incidencias abiertas.

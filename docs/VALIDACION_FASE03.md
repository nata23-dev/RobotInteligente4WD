# Validación de software — Fase 03

## Corrección de comunicaciones 03.3-C — 25/11/2026

Base `a69eb0334620dae3f18cf0e9fbee0610b2de2960`; rama `feat/fase-03-vision`, inicialmente limpia y sincronizada 0/0. Se confirmó el enclavamiento: el error ponía connected=False y la condición del polling impedía cualquier lectura posterior. Se corrige la recuperación de supervisión, **no se atribuye causa física** al corte inicial. [Política de comunicación, estados, timeouts y procedimiento físico](COMUNICACIONES_Y_RECUPERACION.md).

Estado, autorización, reposo remoto, frescura y STOP separados. Recuperación en el mismo trabajador, lecturas health/state con versión/autenticación, backoff 0.5/1/2/3 s, sin cola ni reenvío de órdenes. Las generaciones canceladas no pueden restaurar conexión. Tras recuperar exige reposo lógico reciente y nueva acción de armado. Un estado inseguro solicita STOP prioritario; si no se confirma, no se concede autoridad. Cierre/configuración suspenden intentos antes de sustituir transportes. Un fallo interno inesperado enclava el trabajador cerrado y estado desconocido, sin imprimir el texto arbitrario de la excepción ni crear otro trabajador.

Timeout privado efectivo encontrado **0.30 s**, heartbeat **0.25 s**, archivo privado idéntico al respaldo. Control/STOP usan connect/read configurados; heartbeat limita ambas fases a 0.15 s; recuperación desarmada usa connect <=0.30/read 1.0 s. No son límites absolutos totales. No se amplía TTL firmware 1200 ms ni límites de actuadores. Telemetría periódica suspendida mientras armado; supervisor independiente invalida y solicita STOP sin confirmación de heartbeat en 0.75 s. Ángulos/ruedas antiguos no se presentan como actuales y un incremento sobre ángulo no reciente se rechaza; objetivos explícitos mantienen el protocolo previo.

State se fecha **desde el inicio del GET**, conservando frescura de 0.75 s. La captura real queda bloqueada también si el despachador está cerrado o su trabajador no está vivo. Cámara/video y percepción siguen independientes del control; se verificó video fresco durante pérdida y recuperación sin sesión. No se armaron actuadores reales, cambió firmware, arquitectura inalámbrica ni credenciales. No hubo nuevas dependencias, cambios de app/config.py, patrones, pines, pulsos, servos o caducidad del firmware.

Regresión de partida: **115/115, 51.078 s**. Primera integración conservó **115/115, 50.750 s**. Primera ampliación 135: 130 aprobadas, cuatro fallos y un error en 98.546 s. Los montajes nuevos corregidos fueron: nombre de helper que ocultaba unittest.fail; comparación con espera nominal en lugar de frontera observada de inicio; URL de fixture vacía rechazada correctamente por el cerco de red; aserción de STOP remoto antes de terminar su hilo. Las dos regresiones anteriores afectadas fueron caducidad del frame durante layout inicial y recorte de botones al agrandar diagnóstico. Se resolvieron preparando layout antes del primer frame, evitando actualizar paneles ocultos y manteniendo detalles completos en Mantenimiento. **No se modificó ni debilitó ninguna de las 115 pruebas anteriores ni los límites de frescura.**

Después: **135/135, 72.969 s** y **137/137, 59.015 s**. Ampliación posterior con CLI JSON y sanitización de errores: **139/139, 63.719 s**; con fallo interno seguro: **140/140, 58.921 s**. Regresión definitiva, incluida exportación local de métricas: **141 ejecutadas, 141 aprobadas, 0 fallos, 0 errores, 0 omitidas, 69.016 s**. Se conservaron intactas las 115 anteriores y se agregaron 26. Resumen: `evidencias/fase03_3C/final_publicacion/unittest_summary.json`.

Cobertura nueva: error aislado y recuperación automática sin operador; backoff/fallos consecutivos y corte prolongado; remoto aún armado; STOP no confirmado; fallo armado, cola cancelada, sin rearme ni repetición de movimiento; tiempo de solicitud, respuesta lenta y generación obsoleta; reconfiguración/cierre durante reconexión; ausencia de trabajadores duplicados; captura bloqueada con estado desconocido; cámara independiente; STOP mientras una lectura espera; heartbeat sin telemetría competidora y watchdog con UI sana; roles/timeouts de transporte; métricas recientes y categorías de error; respuestas arbitrarias sin fuga de valores; herramienta GET limitada, CLI JSON y exportación sanitizada.

El servidor HTTP **loopback** reprodujo 200 consultas state con cortes de conexión en 1,44,73: **197 respuestas válidas, tres errores, tres interrupciones**, consultas siguientes satisfactorias. Es una prueba sintética equivalente en patrón; no reproduce radio, alimentación ni latencias físicas. Evidencia JSON completa: `evidencias/fase03_3C/diagnostico_fixture_200.json`. La CLI se probó también contra health loopback, generando JSON y comprobando que no publica la clave ni envía cabecera privada en health. El script no se ejecutó contra robot/cámara.

`validate_phase03.py --output evidencias/fase03_3C/validacion`: **20 layouts sin problemas**, diez capturas temporales `fixture_prueba` y cero imágenes reales. Se inspeccionaron capturas de conexión inestable/reconectando/recuperada con video activo y diagnóstico en `evidencias/fase03_3C/interfaz/`. Se mantienen los límites de resolución documentados de las fases anteriores. compileall, pip check y BAT --smoke-ui satisfactorios; no se reinstalaron dependencias.

Archivos nuevos: `control/communication.py`, `hardware/telemetry.py`, `scripts/diagnose_communications.py`, `tests/test_communications_recovery.py`, `docs/COMUNICACIONES_Y_RECUPERACION.md`. Modificados: `control/command_dispatcher.py`, `hardware/bridge.py`, `hardware/protocol.py`, `app/application.py`, `ui/main_window.py`, `ui/tabs/automatico.py`, `ui/tabs/manual.py`, README, este informe y bitácora. Safety/Controller se revisaron y mantienen su autoridad/contratos. Privados, evidencias y scripts auxiliares locales no se publican.

Los datos físicos comunicados por el operador (197/200, 98.5 %, p50 94/p95 312/máximo 422 ms, cortes en 1/44/73 y ambas redes con/sin video/baterías cargadas) se preservan con procedencia en la guía de comunicaciones y bitácora. No son mediciones nuevas del agente. Pendientes: causa inalámbrica, validación física de recuperación/STOP y prioridades, rueda al energizar y puertas físicas anteriores. No se avanzó de fase ni se habilitó autonomía. Publicación en un commit `fix: implementar recuperacion segura de comunicaciones`, solo en feat/fase-03-vision, después de Gitleaks/auditor y sin merge/force. Resultado remoto en `evidencias/fase03_3C/remote_verification.json`.

## Revisión externa 03.1-R — 24/11/2026

Commit revisado `bd91084c3e07cbbf6827c0ac1e66e0b11e25b2f4`, rama `feat/fase-03-vision`. Se confirmaron dependencia de Original respecto a percepción, admisión de captura sin estado remoto conocido, carrera entre encolado/ejecución y captura, almacenamiento parcial, ausencia de decisiones persistentes de revisión y riesgo de fuga por duplicados entre sesiones. También se confirmó que una cola llena podía dejar `reconfiguring=True` y que el rollback del ciclo de vida podía reconstruir módulos aunque otro trabajador siguiera vivo.

Correcciones puntuales sobre la arquitectura existente:

- `ui/video_source.py` obtiene el Frame fresco directamente de Camera, orienta sin overlays ni digitales y mantiene una caché de una imagen compartida por Automático/Dataset. Reutiliza la normalizada de percepción solo si coinciden ID, generación y orientación. Una excepción de percepción no oculta el original. Procesada/Máscara siguen necesitando observación vigente y el contexto declara su ausencia. La caducidad sigue vaciando el visor.
- `capture_guard()` distingue simulación de hardware real integrado. En real exige conexión verificada, confirmación remota de antigüedad **0…0.75 s** y booleanos explícitos `armed=False`, `motor_activo=False`, `brazo_ocupado=False`, `maintenance=False`. Ausencia, desconexión, campos faltantes y estado antiguo bloquean captura; no se implementó un modo implícito «solo cámara». Esta antigüedad limita la validez lógica, no certifica seguridad física ni modifica timeout/heartbeat.
- Dispatcher comparte el mutex de captura para admitir y ejecutar órdenes, incluyendo la ventana entre sacar una orden de la cola y ejecutarla. Usa adquisición sin espera: una orden incompatible se rechaza en vez de coincidir con la escritura. El armado durante ráfaga la cancela. STOP, su transporte independiente y el heartbeat no adquieren ese mutex. La guarda se repite antes de cada archivo y antes del commit, comprobando cámara, generación, estado, cierre y cancelación.
- `dataset/storage.py` incorpora transacción con journal, respaldo de metadatos, archivos nuevos con UUID, reemplazos atómicos y marcador de commit. Las excepciones revierten el CSV/JSONL y los artefactos de esa operación. Constructor, contadores, resumen, revisión y división recuperan journals pendientes antes de leer. Una interrupción de proceso real se probó con `os._exit(73)` después del JSONL; al reabrir se recuperó exactamente el estado anterior, sin duplicados ni recortes huérfanos. Solo se eliminan artefactos nuevos de una transacción sin commit; no se borran originales anteriores.
- Se omite el recorte cuando hay cero o varios candidatos del color humano indicado. En varios candidatos se registra advertencia para revisión; ya no se elige automáticamente el de mayor área como si fuera inequívoco.
- Dataset → Herramientas permite seleccionar una muestra y persistir **Sin revisar / Aceptar / Rechazar** en `metadata/reviews.json`. Se conserva la decisión aunque el archivo falte. Las rechazadas se excluyen de la división. Las no revisadas pueden figurar en una propuesta de planificación, pero quedan `eligible_for_training=False` y la división completa `training_ready=False`. Ninguna CNN se entrena.
- La división enlaza sesiones por hashes exactos de píxeles/dimensiones de originales **y recortes** antes de asignar conjuntos. Comprueba etiquetas incompatibles, existencia, derivados, tres clases por conjunto y al menos tres grupos independientes; busca una asignación reproducible con semilla fija. Informa cantidades por conjunto, clase y color en JSON y en la interfaz. Cambiar una revisión o agregar capturas invalida la división anterior. Un archivo legado sin revisar no decodificable se conserva visible con advertencia para compatibilidad, pero no habilita entrenamiento. Una imagen aceptada no decodificable bloquea la división.
- Si no se puede encolar la configuración, se restablece `reconfiguring` y se informa. Tras fallo de detención solo se reconstruyen módulos si todos los trabajadores anteriores terminaron; si alguno sigue vivo se bloquean órdenes/capturas y se exige reiniciar, sin crear duplicados.

**Pruebas reales de esta revisión:** base 96/96 en 26.219 s; integración conservando las 96: 96/96 en 34.734 s. Primera ampliación: 112/112 en 37.188 s. Una ejecución posterior de 115 tuvo dos problemas nuevos: se perdió una decisión de rechazo al faltar el archivo (corregido leyendo también las filas legadas del CSV), y el montaje de una prueba de carrera instalaba el hook después de que Queue.get hubiera comenzado (se sincronizó explícitamente la instalación, sin relajar la aserción). Después: 115/115 en 41.797 s. Regresión de cierre, incluyendo estado nulo y rechazo de reconfiguración tras fallo de ciclo de vida: **115 ejecutadas, 115 aprobadas, 0 fallos, 0 errores, 0 omitidas, 41.172 s**. Las 96 pruebas anteriores permanecen byte por byte intactas; se agregaron 19 en `tests/test_external_review.py`. Resumen final en `evidencias/fase03_1R/cierre/unittest_summary.json`.

Cobertura nueva: cámara fresca con percepción fallida/orientación/caducidad; estado remoto vacío/desconectado/antiguo/conocido; simulación explícita; armado durante reserva, en ejecución y entre dequeue/ejecución; STOP sin esperar captura; cancelación de ráfaga al perder confirmación; fallo PNG/CSV/recorte/JSONL incluso tras reemplazar el archivo; cierre durante almacenamiento; caída de proceso y recuperación idempotente; ambigüedad del recorte; persistencia de revisión/rechazo/ausencia del archivo; duplicados entre sesiones; imposibilidad de split sin fuga; archivos faltantes; resumen/reproducibilidad; cola llena y trabajador que no logra detenerse.

`scripts/validate_phase03.py --output evidencias/fase03_1R/validacion` ejecutado: **20 layouts, cero problemas**, diez fixtures temporales de ráfaga y cero originales reales. Preserva evidencias anteriores mediante el nuevo argumento opcional. También pasaron compileall, pip check y `INICIAR_APLICACION.bat --smoke-ui`. Se inspeccionaron capturas nuevas de Original/Dataset con percepción fallida y del diálogo de revisión con los tres estados. Todas son de la aplicación real ejecutándose con `fixture_prueba` y red/cámara físicas bloqueadas. Resultados locales en `evidencias/fase03_1R/`; no se publican capturas ni fixtures.

Archivos modificados: `app/application.py`, `control/command_dispatcher.py` (admisión y fecha de estado), `dataset/capture.py`, `dataset/tools.py`, `ui/dataset_view.py`, `ui/main_window.py`, `ui/tabs/automatico.py`, `ui/tabs/dataset.py`, `scripts/validate_phase03.py`, esta documentación, la guía y la bitácora. Nuevos: `dataset/storage.py`, `ui/video_source.py`, `tests/test_external_review.py`. Sin dependencias nuevas, cambios de firmware, pines, patrones, pulsos, servos, timeout o heartbeat. Configuración privada idéntica al respaldo inicial de revisión.

Límites: el journal y los locks están diseñados para **una instancia escritora de la aplicación** por destino; no abrir dos procesos sobre el mismo dataset. Se probó interrupción de proceso, no corrupción de disco, apagón físico ni todos los sistemas de archivos. Si el disco continúa fallando y no se puede completar recuperación, las lecturas fallan explícitamente; no se anuncia una captura completa ni se entrena con archivos parciales. Un bloqueo de E/S del sistema no se puede cancelar instantáneamente; STOP mantiene su canal independiente. El estado remoto reciente sigue siendo lógico, no medición de reposo físico. Los porcentajes de split son aproximados por grupos y pueden resultar inviables por duplicados o diversidad insuficiente. No hay clasificador ni entrenamiento implementado.

Publicación prevista en un solo commit `fix: corregir regresiones y robustecer vision y dataset`, después de auditor del proyecto y Gitleaks. El SHA remoto y los resultados exactos de auditoría se verifican al cerrar; `main` no se integra ni reescribe. Pendientes físicos sin cambios: alimentación, rueda al energizar, FL/ruedas, STOP/caducidad físicos, brazo, cámara/HSV/ROI reales, marcadores impresos y dataset real. Sin Fase 04 ni autonomía.

Reproducción de revisión, desde la raíz: `.\.venv\Scripts\python.exe scripts\check_software.py --output evidencias\fase03_1R\cierre` y `.\.venv\Scripts\python.exe scripts\validate_phase03.py --output evidencias\fase03_1R\validacion`. La configuración privada y el prefijo completo de la bitácora anterior se compararon byte por byte, sin cambios. Auditorías y verificación remota se guardan bajo `evidencias/fase03_1R/`.

## Registro original de Fase 03 — conservado como histórico

Fecha: 24/11/2026. Base `4bd6ba6d0953637f84c83e6d47c7f50bb6a5fc43`. Trabajo en `feat/fase-03-vision`; main permanece estable, sin merge ni force push. Rama prevista para revisión: https://github.com/nata23-dev/RobotInteligente4WD/tree/feat/fase-03-vision . Último SHA y sincronización se comprueban al publicar y se entregan en el informe final, sin insertar un hash autorreferente en este archivo.

## Alcance y preservación

03.1: orientación/inversiones, digitales neutros, ampliación/reducción proporcional, generación de cámara, migración y adaptación remota bloqueada. 03.2: visor 3:1, vistas reales, ampliación, contexto, diagnóstico/eventos bajo demanda, ocho etapas neutrales, STOP/Escape y autonomía deshabilitada. 03.3: HSV, morfología, candidatos/centroides/cajas/error, selección/seguimiento con pérdida explícita, proximidad visual, ROI, ArUco y PDF. 03.4: captura original, ráfagas, calidad/duplicados, recortes sin overlays, sidecar v2, revisión y split por sesiones. [Uso, convenciones y limitaciones](VISION_Y_DATASET_FASE03.md).

No se reconstruyó la aplicación; Python/Tkinter y dependencias de ejecución se conservan. Sin cambios en control/, HTTPBridge, protocolo, simulador, firmware, pines, patrones ni límites. Configuración privada comparada byte por byte con respaldo local inicial: idéntica. Timeout efectivo 0.18 s y heartbeat 0.25 s preservados; 0.30 s no aplicado. Git inicial limpio y main/origin/main sincronizados 0/0. La bitácora conserva su contenido anterior y añade un registro.

El SVG adjunto se inspeccionó como referencia de distribución. Sus porcentajes, estados autónomos y clase de ejemplo no se incorporaron como resultados reales. No contiene autoridad para ejecutar operaciones. No se abrió cámara ni se contactó al robot, ni se cargó firmware. Las pruebas HTTP existentes solo usan loopback.

## Regresiones y correcciones

Línea base: **65 ejecutadas, 65 aprobadas, 0 fallos/errores/omisiones, 24.812 s**. Primer incremento de cámara: **71/71, 22.000 s**. Percepción integrada: **80/80, 35.656 s**. Dataset: **89/89, 31.531 s**.

La primera integración gráfica encontró un viewport de calibración con altura 1 por usar propagación de pack en un widget con hijos grid. Se corrigió usando grid_propagate(False). La nueva prueba de diagnóstico encontró imagen grande durante el cambio de altura: se agregó redibujado inmediato ante Configure. Otra ejecución de la prueba nueva de Escape no tenía foco de teclado; se corrigió el montaje de esa prueba solicitando foco antes de generar el evento. Ninguna de las 65 pruebas anteriores se eliminó, modificó ni debilitó.

Tras esas correcciones: **94/94, 59.890 s**, sin fallos/errores/omisiones. Se añadieron pruebas del bloqueo de armado durante captura y de pérdida/caducidad/generación durante ráfaga. **Resultado final: 96 ejecutadas, 96 aprobadas, 0 fallos, 0 errores, 0 omitidas, 34.906 s**. Son las 65 anteriores intactas y 31 nuevas. Informe local: `evidencias/fase03/final/unittest_summary.json`.

Cobertura agregada: rotaciones/inversiones, originales intactos y digitales neutros, escalado de ambos tamaños, migración/persistencia, rangos inválidos, HSV circular rojo/verde/azul, ruido y vacío, objetos múltiples, cajas/centroides/error, continuidad/pérdida/cambio de generación, trabajador sin reprocesar un ID, último resultado y descarte de trabajo atrasado, ArUco 0/1/2/desconocido/rotado/múltiple, originales/CSV previos, hashes/duplicados, calidad, recortes trazables, ráfagas/progreso/cancelación/frames nuevos/interlocks, división agrupada, vistas gráficas, ampliación, diagnóstico, Escape y cierre.

Compilación Python, pip check e inicio por BAT --smoke-ui correctos. Se conservan NumPy 2.2.6, Pillow 12.0.0, OpenCV contrib 4.12.0 y Requests del lock. ReportLab/PyMuPDF y herramientas de medición se usaron únicamente bajo `.tools/` ignorado para documentación/evidencia; no son dependencias de la aplicación ni modelos de IA. Los primeros resultados fallidos permanecen en carpetas locales separadas para trazabilidad.

## Interfaz y evidencia

`scripts/validate_phase03.py` ejecuta Application/MainWindow reales, bloquea socket.connect, HTTPBridge y Camera._open, alimenta solo Frames `fixture_prueba` y usa dataset temporal. No es una maqueta de screenshots. Carpeta local ignorada `evidencias/fase03/validacion/`:

- automatico_original.png, automatico_procesada.png, automatico_mascara.png.
- automatico_ampliado.png, diagnostico.png.
- configuracion_vision.png, calibracion_hsv.png.
- dataset.png y report.json.

Se inspeccionaron visualmente estas capturas dentro del monitor 1366×768. Original sin anotaciones, procesada con colores/cajas/centroides/objetivo/ROI/ArUco y máscaras reales; fixture identificado, sin CNN/confianza/destino/acción inventados. La etiqueta forma permanece sin modelo. STOP visible en todas las vistas.

20 comprobaciones de geometría (cinco tamaños × cuatro secciones), **cero problemas** en la ejecución corregida. Solicitudes: 1024×768,1280×720,1366×768,1600×900,1920×1080. El mínimo 1200×650 hace que 1024 se limite realmente a 1200×768: **1024×768 no se admite**. Las otras cuatro geometrías se aplicaron completas. Maximización/restauración y redimensionamiento comprobados; cliente maximizado físico 1366×697. 1600/1920 se verificaron geométricamente: no se presenta como inspección visual en un monitor de esas dimensiones ni se entregan capturas con zonas negras fuera del monitor. La validación de esas dos resoluciones en pantalla física queda pendiente.

## Rendimiento local, exclusivamente fixtures

200 muestras después de diez calentamientos por resolución; mismo proceso, percepción completa HSV/objetos/ArUco/overlays. Escena fija sintética, sin compresión, red, exposición o latencia de cámara:

- QVGA 320×240: media **5.452 ms**, p95 **9.357 ms**, rendimiento secuencial calculado **183.4 FPS**. CPU 1.578 s en 1.201 s de pared (OpenCV puede usar varios hilos).
- VGA 640×480: media **34.578 ms**, p95 **45.922 ms**, rendimiento secuencial calculado **28.9 FPS**. CPU 11.531 s en 7.283 s de pared.

Los FPS anteriores son capacidad de procesamiento de la escena de prueba, **no FPS de ESP32-CAM ni inferencia CNN**. Con alimentación de fixtures limitada a 12 FPS el trabajador toma solo nuevos frames y descarta los que hayan quedado sustituidos. No acumula cola ni procesará infinitamente el mismo ID.

Ráfaga de software de diez fixtures a 0.2 s: **10 originales de prueba**, destino temporal; **0 originales reales**. Cien muestras RSS durante otra ventana de ~12.903 s: mínimo 92,995,584 B, máximo 108,470,272 B, delta final inicial de ventana +946,176 B. CPU 12.656 s durante esa ventana (~0.98 núcleos equivalentes). La diferencia de +36,241,408 B desde antes de construir Tk hasta el final incluye inicialización/cachés; no se interpreta como fuga. La ventana corta no demuestra ausencia universal de fugas: el resultado acotado, deques y cancelación limitan acumulación de frames; queda prueba prolongada con cámara física. Resultados pueden variar con carga, resolución y número de contornos.

## PDF y dataset

Tres páginas A4, patrones propuestos de 100 mm, margen blanco >=20 mm, nombres fuera de patrón y regla. Se verificó la generación y se renderizó el PDF final: OpenCV detectó **[0], [1], [2]** en las páginas correspondientes; tamaños de página 210×297 mm. Se inspeccionaron las tres páginas sin recortes. PNGs y validation.json locales en `evidencias/fase03/marcadores/`. Impresión al 100 % y detección física pendientes.

Dataset real existente comprobado: **cubo 0, cilindro 0, prisma_triangular 0**, sin nuevas muestras reales. Los diez fixtures de evidencia se guardaron en TemporaryDirectory y se excluyeron del contador; no se copiaron al dataset del propietario. Ningún original real, derivado, manifest, log, evidencia privada ni entorno se publica.

## Auditoría y publicación

Se revisan índice, árbol publicable e historial alcanzable de `feat/fase-03-vision` con `scripts/audit_publication.py` y Gitleaks 8.30.1 con redacción completa. Se agregó exclusión específica de `dataset/derived/`; archivos privados locales y respaldos permanecen ignorados. PDF público contiene únicamente marcadores/instrucciones y se marca binary en .gitattributes para preservar bytes. Se verifican SHA remoto, upstream, main base y visibilidad PUBLIC después de push. No merge, force ni cambios de visibilidad.

El informe local de cierre conserva resultados concretos de auditoría y sincronización. Estas herramientas detectan patrones genéricos y valores privados conocidos; no prueban ausencia de secretos desconocidos ni validan hardware. No se publican capturas, por lo que sus píxeles no son parte del escaneo de Git.

## Reproducir

Desde PowerShell en la raíz:

```powershell
.\.venv\Scripts\python.exe scripts\check_software.py --output evidencias\fase03\final
.\.venv\Scripts\python.exe scripts\validate_phase03.py
.\.venv\Scripts\python.exe -m compileall -q app ui hardware control ai dataset tests scripts main.py
.\.venv\Scripts\python.exe -m pip check
.\INICIAR_APLICACION.bat --smoke-ui
.\.venv\Scripts\python.exe scripts\audit_publication.py --ref feat/fase-03-vision --report evidencias\fase03\audit.json
.\.tools\gitleaks_portable\gitleaks.exe git . --log-opts="feat/fase-03-vision" --redact=100
```

## Pendientes

Alimentación y rueda al energizar son puerta prioritaria. Después: FL/ruedas, STOP/caducidad físicos, calibración de brazo, recuperación de fuente de cámara, VGA/QVGA y controles verdaderamente expuestos, orientación/luz/HSV/ROI reales, marcadores impresos, captura balanceada por sesiones, revisión/split, CNN, difusa, heurística y autonomía. Entrega académica 30/11/2026; la fecha no elimina estas condiciones. No se certifica seguridad física ni cámara real por pasar pruebas sintéticas.

## Inventario de cambios

Nuevos:

- `ai/perception.py`, `ai/transforms.py`, `app/vision_config.py`.
- `hardware/camera_controls.py`.
- `dataset/burst.py`, `dataset/quality.py`, `dataset/tools.py`.
- `ui/vision_panel.py`.
- `scripts/generate_markers.py`, `scripts/validate_phase03.py`.
- `tests/test_vision_transforms.py`, `tests/test_perception.py`, `tests/test_dataset_advanced.py`, `tests/test_phase03_ui.py`, `tests/vision_fixtures.py`.
- `docs/VISION_Y_DATASET_FASE03.md`, `docs/VALIDACION_FASE03.md`, `docs/recursos/estaciones_aruco.pdf`.

Modificados:

- `app/config.py`, `app/models.py`, `app/application.py` y `config.example.json`.
- `hardware/camera.py`, `ai/vision.py`, `dataset/capture.py`.
- `ui/components/widgets.py`, `ui/main_window.py`, `ui/tabs/automatico.py`, `ui/tabs/dataset.py`, `ui/tabs/configuracion.py`.
- `scripts/audit_publication.py`, `.gitignore`, `.gitattributes`.
- `README.md`, `ESTADO_PROYECTO_ROBOT_INTELIGENTE.md`, `docs/ARQUITECTURA.md`, `docs/DESIGN_SYSTEM.md`, `docs/PLAN_FASE03.md`.

No se borró ningún archivo anterior. El contenido previo de la bitácora es prefijo byte por byte del nuevo archivo. Los ocho archivos de pruebas anteriores, `scripts/check_software.py`, requisitos, control y firmware no presentan diferencias respecto al commit base.

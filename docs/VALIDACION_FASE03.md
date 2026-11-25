# Validación de software — Fase 03

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

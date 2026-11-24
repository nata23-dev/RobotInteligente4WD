# Informe UX/UI — Fase 01.1, 24/11/2026

## Alcance y base estable

Rediseño de presentación sobre el commit `68ebbe0`, realizado en la rama `ui/fase-01-1`. Se mantuvieron Python 3.12, Tkinter/ttk y Pillow. No se agregaron dependencias de ejecución. No se modificaron los módulos de comunicación, seguridad, control, captura, configuración interna, firmware, entrada principal o requisitos. Las 50 pruebas existentes se conservan sin cambios.

Se revisaron bitácora, README, documentación de arquitectura/API/validación física, componentes de `ui/` y capturas de Fase 01. Las cuatro imágenes de referencia se aportaron en la conversación; `referencias_ui/` no estaba presente. Se utilizaron como referencia conceptual, sin convertir sus cifras o estados en datos del robot.

## Cambios y comparación

- **Navegación:** antes, pestañas tradicionales y tema oscuro; ahora, barra lateral compacta, tema claro, título de sección, indicador de simulación y STOP GLOBAL persistente en cabecera. Se mantienen los cambios de propietario, STOP y desarmado existentes. Configuración conserva el modo vigente para diagnóstico.
- **Automático:** antes, lista vertical extensa de campos pendientes; ahora, cámara original/procesada, cuatro paneles compactos de IA simultáneos, métricas sin inventar valores, ocho etapas neutrales del ciclo, registro incremental y acciones. Iniciar/Pausar permanecen deshabilitados.
- **Manual:** antes, controles que requerían desplazamiento para llegar a la base; ahora, locomoción y ambos servos visibles a la vez en el monitor de 1366×768. Se conservan diez patrones, ruedas individuales ±1, pulso, activar, liberar con confirmación, ángulo, ajuste fino, apertura, cierre provisional y HOME. Se añadió esquema físico FL/FR/RL/RR; el estado sigue siendo lógico.
- **Dataset:** antes, captura con etiquetas y contadores simples; ahora, totales reales por forma/color, progreso frente a meta, última imagen y almacenamiento. Meta inicial 150 por clase, editable como preferencia visual privada. Ráfaga deshabilitada. Se excluyen fixtures, duplicados, archivos faltantes y rutas fuera del destino al presentar totales.
- **Configuración:** antes, editor JSON principal; ahora, siete categorías de formularios tipados, contraseña oculta, edición de patrones, intercambio lateral, calibración y mantenimiento. Guardar utiliza las validaciones y el bloqueo de robot armado originales. Las opciones futuras se muestran como pendientes/deshabilitadas.

Comparación visual generada ejecutando el commit base sin modificarlo, siempre en simulación:

- [Automático antes](../evidencias/ui_fase01_1/antes_68ebbe0/0_antes.png) y [después](../evidencias/ui_fase01_1/0_automatico_1366.png).
- [Manual antes](../evidencias/ui_fase01_1/antes_68ebbe0/1_antes.png) y [después](../evidencias/ui_fase01_1/1_manual_1366.png).
- [Dataset antes](../evidencias/ui_fase01_1/antes_68ebbe0/2_antes.png) y [después](../evidencias/ui_fase01_1/2_dataset_1366.png).
- [Configuración antes](../evidencias/ui_fase01_1/antes_68ebbe0/3_antes.png) y [después](../evidencias/ui_fase01_1/3_configuracion_1366.png).

## Archivos y componentes

Modificados: `ui/theme.py`, `ui/main_window.py`, `ui/components/widgets.py` y las cuatro pantallas de `ui/tabs/`; `.gitignore`, README, arquitectura y bitácora. Nuevos: `ui/components/icons.py`, `ui/preferences.py`, `ui/dataset_view.py`, `tests/test_ui_redesign.py`, `tests/ui_redesign_validate.py`, `docs/DESIGN_SYSTEM.md` y este informe.

Componentes: Card, Badge, Metric, Video, EventLog, PageStack, ScrollFrame, botones/etiquetas comunes, confirmaciones y sistema de iconos lineales. Tokens de paleta obligatoria centralizados, con variantes de texto de mayor contraste. Segoe UI y Consolas; espacios de 4/8 px como base. Sin animaciones ni recursos remotos.

`PageStack` mantiene el contrato de navegación empleado por las pruebas originales, pero oculta/desmonta la página inactiva para no recorrer sus campos mediante Tab. La señal del controlador y el refresco de video conservan 80 ms; la telemetría se limita a unos 240 ms y se fuerza su actualización tras navegar. El registro añade eventos en lugar de recrear su texto en cada frame. Manifiesto, thumbnails y preferencias se leen en el trabajador existente; Tk solo aplica los resultados recibidos.

## Pruebas ejecutadas

La línea base pasó **50/50** antes de modificar la interfaz. La suite ampliada pasa **62/62**: las 50 originales y 12 nuevas. Las nuevas cubren navegación sin órdenes involuntarias, estados pendientes/deshabilitados, campos tipados y persistencia privada, contraseña oculta, rechazo de formularios inválidos y cambios estando armado, intercambio de laterales sin perder campos sin guardar, confirmaciones, STOP GLOBAL/cambio de modo contra simulador, selector procesado sin imagen ficticia, conservación de aspecto, contadores de manifiesto, meta persistente, contraste de texto y distribución inicial/compacta con una miniatura guardada de prueba.

En las pruebas nuevas se bloquea expresamente `HTTPBridge.request` para impedir cualquier contacto con hardware real. Los fixtures de imagen se usan solo en memoria o carpetas temporales y no se incorporan al dataset real.

Otras comprobaciones aprobadas:

- `compileall` sobre aplicación, módulos y pruebas.
- `pip check`: sin dependencias rotas.
- `main.py --smoke-ui`: cuatro secciones, inicio desarmado y cierre.
- `tests/ui_validate.py`: prueba original sin modificar, con pulso manual y STOP simulados.
- `tests/ui_redesign_validate.py`: 43 revisiones geométricas/escala/categoría, sin desbordamientos ni recortes detectados; STOP visible.

Las 43 revisiones comprenden 16 combinaciones de resolución/sección (1280×720, 1366×768, 1600×900 y 1920×1080), cuatro vistas maximizadas en monitor físico, siete categorías de formularios y ocho vistas con escalados tipográficos virtuales 125 %/150 % en geometría 1920×1080, y ocho vistas adicionales de la ventana inicial y del área útil compacta 1280×650. Se compara el tamaño aplicado con el solicitado: se corrigió el límite máximo predeterminado de Tk que, de otro modo, reducía ventanas al monitor disponible.

También se mantuvo una sesión simulada mientras la interfaz renovaba su señal de salud y se solicitó STOP mediante el botón global. El tiempo observado incluye la espera del propio guion de prueba y NO constituye un benchmark de red ni una garantía temporal física. Los valores y tiempos exactos de cada ejecución están en `evidencias/ui_fase01_1/validacion_geometria.json` y `resultados_checks.json`.

## Inspección visual y correcciones

Las capturas reales de las cuatro pantallas se inspeccionaron y se corrigieron campos de IA recortados en altura, un control de meta que salía del panel, flechas demasiado pequeñas, barras de desplazamiento innecesarias y contraste de texto pequeño sobre fondos suaves. Se añadió cobertura del tamaño inicial y de 1280×650 de área útil, compactando campos de IA y captura sin ocultar controles; la miniatura del Dataset se prepara con altura acotada para no desplazar la meta. La auditoría amplía la verificación anterior, que solo comprobaba desbordamientos horizontales. Se cancelan los callbacks `after` al destruir la ventana para evitar avisos Tcl en aperturas/cierres sucesivos de pruebas.

La ejecución repetida de múltiples raíces Tk encontró un cierre intermitente de un trabajador mientras quedaban objetos gráficos de pruebas anteriores por recoger. El fixture nuevo realiza la recolección de ciclos en el hilo principal entre ventanas. Se conserva el error de cierre, no se amplían timeouts y no se modifican seguridad/despacho para ocultarlo. La suite completa y la repetición de pruebas UI se ejecutan después de esa limpieza.

Las capturas usan el identificador nativo de la ventana de la aplicación para evitar incluir otras aplicaciones del escritorio. El monitor físico tiene **1366×768**; el cliente maximizado capturado mide aproximadamente **1366×697**, al excluir decoraciones/área reservada por Windows. Los campos esenciales, ambas columnas de Manual y STOP permanecen visibles en ese espacio.

Se intentaron capturas con geometría nativa 1920×1080: el layout alcanzó exactamente ese tamaño, pero el capturador devolvió negro en las zonas fuera del monitor físico. Esas imágenes incompletas se descartaron. **1600×900 y 1920×1080 se entregan como validación geométrica, no como inspección visual completa en otro monitor.** El escalado de 125 %/150 % es una prueba tipográfica de Tk, no una modificación ni una validación del escalado global de Windows.

## Evidencias y reproducción

Todo se guarda en `evidencias/ui_fase01_1/`, excluido de Git conforme a la política previa de evidencias privadas:

- Cuatro PNG de la aplicación actual y cuatro PNG del commit base en `antes_68ebbe0/`.
- `unittest.txt`, `compileall.txt`, `pip_check.txt`, `smoke_ui.txt`, `ui_original.txt`, `ui_redesign.txt`.
- `validacion_geometria.json` y `resultados_checks.json`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app ui hardware control ai dataset tests main.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py --smoke-ui
.\.venv\Scripts\python.exe tests\ui_validate.py
.\.venv\Scripts\python.exe tests\ui_redesign_validate.py
```

## Límites y cierre

No hubo comunicación con ESP32 ni ESP32-CAM físicos. No se midieron rendimiento de Wi-Fi, FPS reales, PWM, corriente, posición o agarre. La validación física sigue pendiente; CNN, difusa, heurística y navegación no se implementaron. La clave permanece oculta en el formulario y privada en la configuración local; HTTP del firmware sigue sin cifrado, tal como en la base estable.

No hay excepciones funcionales a la restricción de mantener comunicación y seguridad intactas. Se conserva el commit base y se crea un commit local del rediseño en su rama tras las verificaciones. La Fase 02 no se inició.

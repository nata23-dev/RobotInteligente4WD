# Plan de Fase 03 — actualización de implementación

## Estado vigente — 24/11/2026

La solicitud de Fase 03 autorizó implementar software sin contactar hardware. Se implementaron 03.1 (orientación, ajustes digitales, escalado y adaptación remota bloqueada), 03.2 (visor 3:1, vistas, ampliación, diagnóstico), 03.3 (HSV, contornos, objetivo visual, ROI, ArUco e imprimibles) y 03.4 (ráfagas, calidad, derivados, sidecar y división por sesiones). Ver [guía](VISION_Y_DATASET_FASE03.md) y [validación](VALIDACION_FASE03.md). Los apartados siguientes preservan el plan histórico previo.

Verificado en software mediante fixtures y regresión protegida. Pendiente físico: fuente/capacidades reales de ESP32-CAM, VGA/QVGA, orientación/luz/HSV/ROI, marcadores impresos y captura de originales reales. Hardware bloquea alimentación, movimiento al encender, FL y brazo. Fases posteriores: CNN, difusa, heurística y máquina autónoma; Iniciar/Pausar siguen deshabilitados. No fusionar esta rama con main en esta entrega.

Fecha: 24/11/2026. Este documento registra alcance futuro; no describe funciones terminadas. La Fase 02.1 conserva la arquitectura, pantalla Automático y firmware. La entrega académica continúa prevista para el 30/11/2026; el calendario no elimina las puertas de seguridad.

## Puertas previas

El operador cargará baterías y diagnosticará alimentación sin dar por confirmada la causa de la pérdida de Wi-Fi/potencia. Debe investigarse el movimiento de una rueda desde la energización y verificarse que los motores permanezcan detenidos incluso antes de terminar `setup()`. No se prescriben ni implementan cambios eléctricos o de firmware en esta fase de consolidación.

Para recuperar pruebas de actuadores: ruedas suspendidas, brazo apoyado, corte físico accesible, fuente y conexiones verificadas. Cerrar formalmente los ocho sentidos de ruedas (FL ambiguo), detención automática de pulso, STOP físico, caducidad de sesión, desplazamientos y brazo. Un estado lógico desarmado no es una medición de seguridad física. Autonomía bloqueada hasta resolver y verificar la incidencia de arranque.

## Fase 03.1 — cámara real

Investigar primero el firmware instalado en ESP32-CAM y las funciones que realmente expone para OV5640. Preservar su fuente/configuración funcional cuando pueda recuperarse. Partir del stream reportado 320×240, 10–12 FPS y orientación cercana a 90°, sin asumir capacidad de ajustes remotos por el modelo de sensor.

Evaluar captura **VGA 640×480 real** como primera propuesta; comparar resolución, calidad JPEG, FPS, estabilidad y latencia con control simultáneo. Ampliar píxeles en la PC no aumenta resolución capturada. Estudiar iluminación, enfoque/nitidez, brillo, contraste, saturación, exposición y balance de blancos solo si firmware/hardware lo permiten. No prometer autofocus ni endpoints sin verificarlos.

Preparar orientación configurable 0°/90°/180°/270°. Conservar original recibido y diferenciar transformaciones de procesamiento, ROI y overlays. Evitar colas de imágenes atrasadas y medir edad desde recepción por separado de latencia completa de cámara. No sustituir video perdido por imágenes artificiales.

## Fase 03.2 — Automático centrado en cámara

Mantener paleta clara y seguridad existente. Proponer 70–75 % del área principal para un único visor cuando la ventana lo permita, con original/procesada/máscara seleccionables y vista ampliada o completa. Respetar aspecto; evitar deformación, recortes involuntarios, paneles duplicados, información redundante y superposiciones innecesarias. STOP GLOBAL debe permanecer accesible también en vista ampliada.

Prioridades de contenido: video; estado del sistema; figura/color detectados cuando existan; clase/confianza CNN reales cuando haya modelo; destino; acción y decisión resumida; avance de ciclo; piezas clasificadas; conexión, permiso y alertas. Diagnóstico técnico detallado irá a paneles secundarios. Separar control manual y autónomo; mantener deshabilitada autonomía hasta su integración y validación. Los módulos pendientes se identifican brevemente, sin predicciones inventadas.

## Fase 03.3 — procesamiento de imágenes

Implementar y calibrar segmentación HSV, identificación de colores, morfología, contornos, centroides y bounding boxes. Producir observaciones estructuradas con error lateral, tamaño aparente, proximidad relativa y selección/seguimiento del objetivo. Evitar afirmar distancia métrica sin calibración o sensores que la respalden. Calibrar región de agarre y zona ciega con el montaje de altura fija.

Incorporar detección de ArUco DICT_4X4_50 y visualización de resultados: ID 0 → cubos, ID 1 → cilindros, ID 2 → prismas triangulares. La disponibilidad de OpenCV/ArUco ya comprobada mediante fixtures no sustituye pruebas de carteles físicos. CNN clasifica la forma de la pieza; el marcador identifica la estación. Esta etapa de visión no autoriza por sí sola movimientos autónomos.

## Fase 03.4 — herramientas del dataset

Mantener captura individual original, etiquetas de forma/color y sesión, metadatos y preview; extender a ráfagas espaciadas, calidad, ROI, detección de duplicados y organización por sesiones. Usar principalmente la cámara real. Las aproximadamente 450 imágenes iniciales (150 por forma) son una meta ajustable, no un dataset ya producido ni garantía de suficiencia.

Conservar originales sin overlays. Separar grupos/sesiones para entrenamiento, validación y prueba antes de aumentos; no mezclar frames vecinos entre conjuntos ni contar aumentos como originales. Declarar limitaciones si hay una sola instancia por forma/color. CNN, lógica difusa y heurística completas requieren fases de implementación/evaluación posteriores; no se presentan como terminadas por tener contratos vacíos.

## Evidencia y aceptación futura

Registrar configuración de cámara efectivamente admitida, dimensiones recibidas, condiciones de luz, FPS, errores y comparación visual. Guardar transformaciones con trazabilidad al original. Verificar que el nuevo layout no altere heartbeat, STOP, salud, exclusión de modos ni frescura de observaciones. Ejecutar regresión sin hardware antes de cualquier prueba física autorizada.

El código está preparado para revisión y planificación. La autonomía no está autorizada: alimentación, movimiento al encender, parada física, FL y brazo siguen abiertos. No se comienza Fase 03 sin nuevas instrucciones del propietario.

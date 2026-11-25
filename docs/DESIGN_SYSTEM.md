# Sistema de diseño — Robot Inteligente 4WD, Fase 01.1

## Identidad y alcance

Aplicación Tkinter/ttk de escritorio con tema claro, superficies tranquilas, iconografía lineal y jerarquía de supervisión industrial. Las cuatro imágenes adjuntas son referencias conceptuales de composición y no evidencia de software. Al comenzar no existía `referencias_ui/`; se utilizaron los adjuntos de la conversación. No se copiaron cifras, estados, predicciones ni fotografías de brazo como datos del sistema.

Se mantiene la tecnología y todas las validaciones de control. No hay dependencias visuales nuevas, imágenes generadas, fuentes remotas, animaciones ornamentales, inferencia ni navegación autónoma. Pillow ya existente rasteriza iconos propios, mantiene relación de aspecto y adapta previews.

## Tokens

Fuente única: `ui/theme.py`, diccionario `COLORS`.

- `background`: #F5F7FA; fondo general.
- `surface`: #FFFFFF; tarjetas y formularios.
- `surface_secondary`: #EDF2F7; estados vacíos, registros y pistas.
- `border`: #DCE4ED; divisores y bordes discretos.
- `primary`: #426FA8; acciones, iconos y métricas.
- `primary_soft`: #E7EFF9; sección activa e información.
- `text_primary`: #243247; títulos y cuerpo.
- `text_secondary`: #64748B; tono secundario de referencia.
- `success`: #398575; conexión física comprobada.
- `warning`: #B58A42; simulación, permiso y precauciones.
- `danger`: #C34848; STOP y errores.
- `neural_accent`: #7976B1; identidad de módulos neuronales/difusos.

Variantes de texto: `muted_text` #59697E, `primary_text` #365F93, `neural_text` #625C95, `danger_text` #A83D3D, `warning_text` #795B25 y `success_text` #286354. Mantienen la paleta y mejoran el contraste de texto pequeño en fondos suaves. Los pares de texto activos utilizados se comprueban en pruebas con relación mínima 4.5:1. Los controles deshabilitados tienen tono distinto y nunca aparentan estar habilitados.

## Tipografía, espacio y forma

Segoe UI es la familia principal. Título de página 23 pt, secciones de tarjeta 14 pt, cuerpo 10 pt, etiquetas/telemetría 9 pt, métricas 16–19 pt en negrita. Consolas 9 pt para registro. Los módulos compactos de IA utilizan encabezados 10 pt para conservar los cuatro paneles simultáneos en 1366×768; el título principal y los paneles de operación conservan su jerarquía mayor.

Escala base de espacios: 4, 8, 12, 16, 24 y 32 px. Borde de tarjeta de 1 px y radio decorativo de aproximadamente 10 px. Sin sombras costosas ni degradados. Los Canvas se usan para bordes, estado vacío y esquema compacto de ruedas; grid/pack gobiernan el layout general, no coordenadas rígidas de pantalla.

## Componentes reutilizables

- `Card`: superficie con título/icono opcionales y borde redondeado discreto.
- `Badge`: estado contextual; neutral, primario, aviso, éxito, error o IA.
- `Metric`: etiqueta y valor real o guion cuando no hay medición.
- `Video`: viewport con aspecto conservado, vacío informativo, acceso a configuración y métricas de frame. La vista procesada indica pendiente y no muestra una imagen original etiquetada como procesada.
- `EventLog`: inserción incremental con hora y categoría, máximo de 150 eventos, scrollbar y limpieza exclusivamente visual.
- `PageStack`: contrato `add/select/index` y evento de navegación compatible con las pruebas originales, sin pestañas tradicionales. Solo la página activa participa en el layout/foco.
- `ScrollFrame`: desplazamiento limitado a formularios extensos; la barra aparece cuando hace falta y acepta rueda sobre sus campos.
- Factores comunes `button`, `label`, `set_value` y `confirm`. Confirmaciones nativas de Windows con ventana propietaria para activación/liberación/cambio de hardware.
- Iconos de `ui/components/icons.py`: robot, cámara, capas, reloj, seguridad, ruedas, brazo, ajustes e IA; se rasterizan una vez y se almacenan en caché.

Los botones primarios y STOP tienen estados hover/pressed/focus/disabled coherentes. El foco de teclado es visible. Las entradas de contraseña utilizan máscara; los valores privados nunca se insertan en registros ni títulos. No se necesita ni se expone un editor JSON como interfaz principal.

## Composición

Barra lateral de 184 px con identidad, cuatro accesos, conexión y versión de fase. Cabecera con título/subtítulo, simulación o hardware y STOP GLOBAL. Pie persistente con autorización local, conexión, estado remoto disponible, modo y métricas. La notificación inferior distingue error de información. El área de contenido ocupa el resto.

Automático distribuye aproximadamente 62 % de la región de trabajo a cámara y 38 % a cuatro contratos de IA en una cuadrícula 2×2. Debajo están las ocho etapas neutrales del ciclo y el registro compacto con acciones. No se marca Buscar como activo sin un ciclo real. Piezas clasificadas y CNN permanecen en guion; el Dataset vacío sí muestra cero tras leer sus archivos.

Manual muestra conexión/armado, locomoción y brazo en columnas simultáneas, y diagnóstico de cuatro ruedas con esquema de posición. Las ruedas reportan dirección ordenada y no velocidad medida. La activación y liberación mantienen confirmaciones y todos los comandos siguen atravesando el controlador/despachador existentes.

Dataset combina tres métricas, video, tres campos de captura, captura simple, ráfaga deshabilitada, distribución por forma/color, preview de última imagen y meta. La meta es una preferencia de UI separada (`ui.local.json`), no un nuevo parámetro del control. Los datos se leen en el trabajador existente y se aplican por eventos en Tk.

Configuración agrupa Conectividad, Hardware, Calibración, Visión artificial, Inteligencia artificial, Estaciones y Mantenimiento. Los valores se convierten a tipos y pasan por `app.config.validate` y `Application.update_config` sin modificar esas funciones. HOME y destinos fijados por contrato se presentan como lectura; los campos futuros permanecen deshabilitados.

## Adaptabilidad y rendimiento

Objetivos de tamaño: 1280×720, 1366×768, 1600×900, 1920×1080. Se comprueba el cliente realmente aplicado; Tk limita el máximo al monitor por defecto y la ventana declara un máximo amplio para no confundir una solicitud con una geometría alcanzada. La vista maximizada en el monitor de 1366×768 usa su área de trabajo, excluyendo la barra de tareas.

La automatización comprueba límites de contenedores y altura solicitada de textos/controles, además de presencia de STOP. Los campos principales de Automático y Manual no necesitan scroll en el monitor físico. Solo las categorías largas de Configuración pueden desplazarse; guardar y STOP permanecen fuera de ellas. Se revisan también escalados tipográficos virtuales de 125 % y 150 % en geometría 1920×1080; no se cambia el escalado de Windows del usuario.

La señal de salud y el video conservan su ciclo de 80 ms. La telemetría visual se actualiza aproximadamente cada 240 ms; los StringVar solo cambian si cambia el texto. El registro añade eventos sin reconstruirse en cada tick. La lectura del manifiesto, thumbnails y preferencias utiliza `Application.job`; no se añaden trabajadores de comunicación ni bucles de heartbeat. No se acumulan frames ni se reconstruyen widgets con cada imagen.

## Seguridad visual

Simulación siempre se identifica explícitamente. Los datos de su API no se llaman latencia Wi-Fi. Sin verificación no hay estados verdes de conexión ni posiciones físicas inferidas. Se diferencia autorización local del estado lógico del firmware. Una parada no confirmada se destaca en rojo. Navegar conserva el desarmado y STOP originales; Configuración no cambia de propietario. Iniciar/Pausar autonomía y ráfaga permanecen deshabilitados. `Alt+1..4` cambia de sección; `Esc` solicita STOP. No existen atajos de movimiento repetido.
## Evolución Fase 03 — 24/11/2026

Conserva paleta/tipografías y cuatro secciones. Automático elimina las métricas y tarjetas IA superiores: visor y contexto se reparten 3:1, con única imagen Original/Procesada/Máscara, máscara seleccionable y Ampliar/Restaurar. La ampliación oculta contexto; STOP GLOBAL permanece en la cabecera y Escape conserva STOP. Ciclo neutral de ocho pasos y controles Iniciar/Pausar deshabilitados permanecen abajo. Diagnóstico/eventos se despliegan bajo demanda; campos CNN/difusa/heurística no inventan resultados.

Video usa ampliación bicúbica/reducción Lanczos, centrado y bandas, caché por generación/ID/tamaño y redibujo al cambiar viewport. Reporta dimensiones recibidas aparte de orientadas. `fixture_prueba` se identifica en badge y fuente. El footer agrega resolución recibida; no estima latencia física de captura.

Visión artificial incorpora controles digitales y orientación, editor HSV por color con límites en cuadrícula, máscara sobre el único stream y consulta de píxel, ROI/seguimiento/overlays. Se desplaza verticalmente sin scroll horizontal. Dataset incorpora diálogos de ráfaga y revisión, ambos con STOP y Escape. Mínimo 1200×650; 1024×768 no soportado por ancho. Se revisaron las cuatro secciones a 1280,1366,1600,1920; las dos mayores solo geométricamente, por monitor físico 1366×768. Capturas y límites en el informe Fase 03.


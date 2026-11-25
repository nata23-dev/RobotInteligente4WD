# Visión, cámara y dataset — Fase 03

Implementación de software del 24/11/2026. No se contactó hardware. La autonomía continúa bloqueada por alimentación, movimiento inesperado al encender y validaciones físicas pendientes.

**Actualización 03.1-R:** Original y Dataset ahora visualizan directamente Camera fresca, sin depender del trabajador de percepción. La captura en hardware integrado requiere estado remoto explícito desarmado/en reposo y confirmado hace como máximo 0.75 s; desconectarse no habilita capturar. El almacenamiento utiliza journal recuperable para CSV/JSONL/originales/derivados. Ante varios objetos del color etiquetado se omite el recorte y se pide revisión. Herramientas permite persistir aceptación/rechazo/sin revisar; rechazadas fuera del split y no revisadas bloquean `training_ready`. El split agrupa también duplicados exactos de originales/derivados entre sesiones, comprueba archivos y resume clases/colores. Las divisiones se invalidan al cambiar datos/revisiones. Los detalles de la corrección y límites del almacenamiento están en [la validación 03.1-R](VALIDACION_FASE03.md); las descripciones históricas de escrituras separadas o selección por mayor área de abajo quedan sustituidas por esta corrección.

## Cámara y capacidades

Se revisaron los ZIP del controlador y V7, las referencias extraídas y el sketch Robodacta de Descargas. Ninguno contiene la implementación de la ESP32-CAM (`esp_camera_init`, servidor de stream o controles de sensor). No se recuperó la fuente exacta instalada. El stream y QVGA/10–12 FPS siguen siendo reportes anteriores del operador.

La [documentación oficial del controlador Espressif](https://github.com/espressif/esp32-camera/blob/master/README.md) incluye soporte OV5640; eso no demuestra qué controles expone el binario de este equipo. El [ejemplo oficial CameraWebServer](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/app_httpd.cpp) registra GET `/status` y GET `/control?var=<nombre>&val=<entero>`; el controlador del ejemplo reconoce, entre otros, `framesize`, `quality`, `brightness`, `contrast`, `saturation`, `sharpness`, `whitebal`, `exposure_ctrl`, `aec_value`, `hmirror` y `vflip`. Los identificadores y rangos dependen de la versión y del sensor. **Son endpoints del ejemplo consultado, no endpoints confirmados del firmware instalado.** La aplicación no los llama ni construye URLs basándose en ellos. Tampoco confirma autofocus.

`hardware/camera_controls.py` prepara el catálogo de capacidades y rechaza aplicar ajustes remotos hasta disponer de evidencia del firmware. En Configuración → Visión artificial se muestra «Pendiente de verificar con cámara real». No hay control remoto habilitado de resolución/JPEG/exposición/enfoque.

La cámara sigue utilizando un único trabajador FFmpeg y un último Frame. Cada apertura/reconexión crea una generación UUID; el ID crece dentro de la instancia. La frescura usa reloj monotónico desde recepción, no latencia completa desde exposición. No se cambian automáticamente VGA/QVGA, URL ni parámetros de hardware.

## Transformaciones y contratos

`Frame` conserva BGR original, ID, recepción, FPS, generación y fuente. Los consumidores no modifican su array. `normalize` crea otra imagen, aplica rotación **horaria** 0/90/180/270 y después inversión horizontal/vertical en ese orden. La rotación intercambia dimensiones cuando corresponde.

El resultado lleva juntos Frame, Observation, imagen normalizada, imagen para análisis, máscaras y overlay. Observation incorpora dimensiones orientadas, perfil completo, tiempo de proceso, objetos, marcadores y objetivo. No se superponen resultados sobre otro frame. Se puede mostrar el último resultado terminado aunque la cámara ya tenga otro frame: la imagen y sus anotaciones corresponden siempre al mismo ID, deben seguir frescas y pertenecer a la misma generación. Al perder video, caducar o cambiar generación, `VisionWorker.snapshot()` devuelve resultado nulo.

Un único trabajador de percepción toma el último frame disponible, omite identidades ya procesadas y guarda un solo resultado. Sus métricas usan deques de longitud fija. No tiene referencia al Dispatcher. Application lo detiene antes de sustituir la cámara y lo cierra al salir. La calibración hace trabajos puntuales, limitados a uno pendiente, sobre el mismo stream; nunca crea una segunda Camera. Toda operación Tk/PhotoImage permanece en el hilo principal.

Original en Automático/Dataset significa **original orientado**, sin ajustes digitales ni overlays. El original recibido se guarda aparte. Procesada utiliza ajustes digitales y anotaciones; Máscara muestra rojo/verde/azul/combinada. No se simula video al perderlo.

Brillo local −40…40, contraste/saturación 0.7…1.3, gamma 0.7…1.4 y nitidez 0…1 son opcionales. Neutros: 0/1/1/1/0. Gamma usa LUT con exponente 1/gamma; nitidez utiliza máscara de desenfoque moderada. Restablecer digitales recupera neutros. Estos cambios no aumentan resolución física y pueden cambiar HSV: calibrar con el perfil definitivo y evitar excesos.

El visor escala en ambos sentidos conservando aspecto, centra con bandas y usa bicúbica al ampliar/Lanczos al reducir. Su caché incluye generación, ID y tamaño disponible. Se repinta al redimensionar, incluso antes del siguiente tick. Las métricas distinguen resolución recibida y dimensiones de la vista; el escalado de pantalla nunca cambia el original.

## HSV, objetos y seguimiento

Los perfiles son provisionales. OpenCV BGR→HSV: H 0…179, S/V 0…255. Rojo usa dos intervalos; verde y azul uno. Cada intervalo contiene `[Hmin,Smin,Vmin,Hmax,Smax,Vmax]`. La validación impide mínimos invertidos. Apertura/cierre con kernels impares 1…15 eliminan ruido y rellenan discontinuidades; área mínima absoluta y máxima relativa filtran contornos externos.

Para cada candidato: caja `(x,y,ancho,alto)`, centroide por momentos, área de contorno, área relativa, posición normalizada, error X, tamaño aparente y calidad de segmentación por solidez (área/área de casco convexo). La solidez no es confianza CNN ni garantía de buen objeto.

Convención: X/Y normalizadas = centroide/(dimensión−1); X=0 izquierda, X=1 derecha. Error lateral = `2*X−1`: −1 izquierda, 0 centro, +1 derecha. La referencia es el **centro de la imagen orientada**, no el centro desplazado de la ROI. Proximidad visual = raíz cuadrada del área relativa: un tamaño aparente adimensional, sin centímetros, sin pose y sin calibración métrica. Figuras grandes pueden parecer más próximas que figuras pequeñas a igual distancia.

Selección determinista: maximiza área relativa × solidez − 0.10 × valor absoluto de error X. Una vez adquirido, conserva el candidato del mismo color más cercano al centroide previo dentro del radio normalizado configurable. Si desaparece, devuelve objetivo nulo y «Objetivo perdido»; no reutiliza como válido el candidato viejo. Después del número configurado de frames perdidos permite otra adquisición. Estados: Sin objetivo / Objetivo detectado / Objetivo seguido / Objetivo perdido. Se reinicia al cambiar generación. Es seguimiento sencillo, no identidad inequívoca entre objetos muy próximos del mismo color.

La forma y confianza siguen siendo desconocidas. No se sustituyó CNN con aproximación de contornos. La proximidad y selección no generan movimientos.

## Calibración integrada

1. Iniciar una única cámara desde Conectividad, solo cuando las condiciones físicas lo permitan.
2. En Visión artificial elegir orientación/inversiones; mantener digitales neutros al comenzar.
3. Seleccionar rojo/verde/azul. Editar límites H/S/V, incluyendo ambos intervalos de rojo. Combinada permite inspeccionar la unión.
4. Ajustar apertura/cierre y áreas. La previsualización usa el borrador validado sin guardarlo y se actualiza mientras exista video fresco.
5. Pulsar la máscara para consultar BGR/HSV del píxel correspondiente de la imagen de análisis. Las coordenadas compensan el escalado. No se aceptan consultas sobre resultados caducados.
6. Restablecer HSV recupera perfiles iniciales. Guardar y aplicar persiste atómicamente la configuración completa y requiere robot desarmado. Detiene los trabajadores previos; exige iniciar video otra vez.
7. Ajustar ROI normalizada `(x,y,ancho,alto)` dentro de [0,1], con extensión dentro de imagen. Es posición visual aproximada de garra; su ocupación **no confirma sujeción**.

Los grupos de overlays (objetos, objetivo, eje, ROI, marcadores) se activan por separado. La ROI física y HSV definitivos requieren robot real y luz representativa.

## ArUco e impresión

DICT_4X4_50: ID 0 Cubos, ID 1 Cilindros, ID 2 Prismas triangulares. Los demás IDs se detectan como desconocidos. Cada marcador incluye esquinas, centro, tamaño aparente (media de lados en píxeles), posición normalizada, error X, validez de detección y estación opcional. No clasifica piezas ni estima distancia/pose 3D.

Recurso: [estaciones_aruco.pdf](recursos/estaciones_aruco.pdf), tres páginas A4 vectoriales. Patrón negro de **100 × 100 mm**, margen blanco mínimo 20 mm, nombre fuera del patrón y regla de 100 mm. Imprimir al **100 %, sin ajustar a página**. Medir la regla y el patrón con regla física; montar plano, con margen blanco visible y luz uniforme.

`scripts/generate_markers.py` genera los tres patrones y comprueba sus IDs antes de escribir el PDF. Para regenerarlo se necesita ReportLab como herramienta de documentación; no se añade a requirements de la aplicación. Se renderizó el PDF final con PyMuPDF y OpenCV detectó 0/1/2 en las páginas correspondientes. Esto prueba el recurso digital, no el papel impreso o la cámara real. No hay intrínsecos/distorsión/tamaño medidos, por tanto no se expone pose métrica.

## Dataset y control de calidad

Forma es etiqueta humana (cubo/cilindro/prisma_triangular); color es etiqueta humana en captura y observación HSV en percepción; ArUco es estación. Meta inicial ajustable: 150 originales por forma, ~50 por combinación, 450 total. No hay imágenes nuevas de cámara real en esta fase.

Capturar original conserva PNG BGR recibido sin filtros/rotación/overlays y el manifiesto CSV previo. Ráfaga permite 1…100 imágenes, intervalo 0.2…60 s; perfil inicial 10 y 1 s. Se valida seguridad durante toda la espera y antes de escribir. Cada toma requiere ID nuevo y fresco. Cancelar, cerrar su ventana, cambiar etiquetas/sesión, perder cámara, caducar, reconectar con nueva generación, armar, mover, reconfigurar o cerrar la aplicación termina la ráfaga con progreso y motivo. No hay espera de ráfaga en el hilo Tk ni renovación de control desde cámara. El armado de la aplicación se rechaza mientras hay una escritura de captura en curso; STOP usa su canal independiente.

Indicadores por original: resolución, brillo medio de gris, varianza de Laplaciano, hash SHA-256 del array/dimensiones, dHash de 64 bits, duplicado exacto, similitud por distancia Hamming, número de candidatos y área relativa insuficiente. Todos los umbrales están en Configuración → Mantenimiento. Los valores son provisionales: sombras, patrones o fondos con textura pueden engañar nitidez y similitud. Baja resolución, brillo/nitidez, falta de objeto y similitud son advertencias; rechazar duplicados exactos es opcional. Frescura y seguridad son rechazos obligatorios. No se elimina automáticamente ningún original.

El manifiesto CSV original no cambia de columnas. `metadata/vision_v2.jsonl` es complementario versionado: ID, ruta original, frame/generación/fuente, etiquetas/sesión, transformación, calidad, revisión `sin_revisar`, recorte y ROI. Se enlaza con fecha UTC y dimensiones originales del CSV por ruta/ID. Los originales anteriores conservan sus registros aunque no tengan sidecar.

Se genera un recorte si hay un candidato del color humano indicado: el mayor área, con margen configurable, límites recortados a imagen, sobre imagen **orientada sin ajustes digitales ni overlays**. Guarda `derived/forma/sesion/<id_original>.png`, separado del original y con la misma etiqueta humana. La caja es una propuesta de entrenamiento para revisión, no etiqueta automática de forma. Si hay varias piezas del mismo color, el operador debe revisar el recorte.

Herramientas → Revisar calidad y recortes muestra registros y advertencias. No certifica automáticamente una muestra. Los archivos CSV/PNG y sidecar son escrituras separadas: un fallo de disco al crear derivado/sidecar puede dejar el original ya conservado en CSV; revisar y recuperar metadatos antes de entrenar. No se borra el original ante ese fallo posterior.

Herramientas → Preparar división agrupa **sesiones completas** con semilla 42 y propuesta 70/15/15. Guarda un manifiesto, no mueve/copía archivos. Originales y derivados comparten conjunto. Se requieren tres sesiones independientes como mínimo y presencia de las tres clases en cada conjunto; de lo contrario explica el impedimento. No fuerza porcentajes repartiendo frames vecinos. El operador debe usar una misma sesión para una misma adquisición y no renombrar frames vecinos para eludir el agrupamiento. Los aumentos pertenecen al entrenamiento posterior y nunca cuentan como originales.

`fixture_prueba` se excluye de contadores y división. Dataset real, derivados, metadatos, perfiles privados y capturas se excluyen de Git.

## Migración y límites físicos

Schema 2 agrega `vision`, `dataset_options` y `schema_version`. Solo migra un schema anterior completo, aplicando defaults de las nuevas secciones sin modificar los campos anteriores. Rechaza campos desconocidos, parciales, tipos bool donde se espera número, NaN y rangos inválidos. Leer no reescribe el archivo; Guardar y aplicar hace reemplazo atómico. La configuración privada real permaneció byte por byte igual a su copia inicial. Timeout efectivo **0.18 s**, heartbeat **0.25 s**, clave, URLs, patrones, pulsos y servos preservados; 0.30 s sigue siendo una propuesta previa no aplicada.

Antes de pruebas físicas: resolver alimentación y rueda que se mueve al energizar; comprobar parada desde arranque, FL/sentidos, pulso, STOP/caducidad y brazo con procedimiento del plan físico. Después recuperar fuente de cámara y controles verificables. Con robot desarmado y actuadores sin energía, probar primero VGA 640×480 desde la interfaz original **solo si se confirma su ajuste**, anotar dimensiones recibidas y comparar QVGA. No editar firmware ni probar URLs adivinadas. Evaluar luz, orientación y ajustes neutros, medir FPS/edad/errores, calibrar HSV/ROI e imprimir/verificar ArUco. Capturar sesiones diversas y balanceadas, revisar calidad/recortes y dividir antes de aumentos. CNN, difusa, heurística y autonomía requieren fases posteriores y autorización física independiente.

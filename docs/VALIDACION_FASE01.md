# Informe de validación de software — 24/11/2026

## Fuentes revisadas y conservación

Se analizaron los ocho archivos del ZIP V7: aplicación, firmware V6 de referencia, configuración, LEEME, dependencias, lanzador, pruebas y preview. Se recuperaron diez patrones, límites y configuración vacía de calibración. La interfaz se construyó nueva. Se leyó la bitácora histórica completa; su sección 13 y la solicitud actual sustituyen las decisiones antiguas de ampliar V7.

Los archivos aparecieron progresivamente en la carpeta durante el trabajo. Antes se había encontrado una copia del sketch en Documentos y la V7 en Descargas. Al recibirse el ZIP oficial del firmware se revisaron sketch y LEEME y se compararon ambas fuentes: mismo código operativo; diferencias en cabecera y credenciales. La distribución oficial contiene cuatro claves vacías intencionalmente. La copia local preconfigurada tenía una API_KEY menor de 16 caracteres y `validSecrets()` no le permitiría iniciar la red. Se documentó sin modificarla. No se compiló ni cargó ningún firmware.

SHA-256 V7: `7d1d47c8f8a2e807f2aec4bcd121780443ff7b1a20559cfc3b80aae5bfd3d559`.
SHA-256 sketch de distribución: `a4ca67346103487ca02e28da7caf10967dcf15aad5a11a7f4e70bf9b2b306cd6`.
ZIPs y copias con credenciales permanecen locales y excluidos de Git. La copia pública de firmware procede directamente del ZIP sin modificación y con claves vacías. La bitácora se amplía al final, preservando bytes históricos.

## Entorno y dependencias reales

Windows con pantalla física 1366×768. Se encontraron Python 3.13 y 3.8 globales, sin 3.12. Se instaló Python 3.12.10 x64 en `.runtime/` desde el instalador oficial firmado, sin añadir PATH, asociar archivos, instalar launcher ni usar pip global. Se creó `.venv/` independiente; Tcl/Tk 8.6 funciona.

El índice de paquetes ofrecía versiones posteriores de OpenCV, NumPy, Pillow y Requests. Se eligió un conjunto conservador, con ruedas x64/3.12 realmente instaladas y probadas: opencv-contrib-python 4.12.0.88 (`cv2.__version__=4.12.0`), NumPy 2.2.6, Pillow 12.0.0, Requests 2.32.5. Transitivas resueltas: certifi 2026.11.20, charset-normalizer 3.5.3, idna 3.20 y urllib3 2.8.0. El archivo lock conserva el resultado. No hay TensorFlow ni otras distribuciones de cv2.

## Resultados disponibles

- `unittest discover -s tests`: **50 pruebas aprobadas** en la ejecución integrada previa al cierre de documentación. Cubren configuración/persistencia, patrones/pulsos/servos, HTTP con servidor loopback, auth, challenge/sesión, secuencias, heartbeat, caducidad, STOP enclavado, cancelación, exclusión de modos, pérdidas, interlocks, frames, cierre, dataset temporal y ausencia de claves públicas.
- Casos de carrera adicionales incluidos: STOP mientras espera respuesta de armado; STOP por un transporte distinto con el emisor ordinario bloqueado; armado tardío no restaura autorización local; no renovación indefinida tras perder señal del controlador.
- `compileall` sin errores en módulos de aplicación, pruebas y entrada.
- `pip check`: `No broken requirements found`.
- `INSTALAR.bat` ejecutado con éxito sobre el entorno; verifica Python x64, instala desde requirements y prueba imports/ArUco.
- `main.py --smoke-ui`: arranque gráfico, cuatro pestañas, Automático por defecto y cierre correcto, en simulación.
- `tests/ui_validate.py`: sin solicitudes al arranque; ocho combinaciones de tamaño/pestaña sin desbordamientos horizontales detectados. Monitor real 1366×768: capturas inspeccionadas. Tamaño 1920×1080: validación geométrica programática en el mismo monitor, no inspección física sobre una pantalla 1080p.
- Un pulso manual y STOP por cambio a Dataset se ejercitaron en la interfaz **contra el simulador exclusivamente**.
- OpenCV ArUco generó/detectó IDs 0, 1 y 2 sobre fixtures temporales. Verifica disponibilidad de la dependencia, no navegación real.
- PNG de captura preserva todos los píxeles de su fixture de prueba, etiquetas/metadatos correctos y rechazo de frames viejos. Fixtures temporales no cuentan como dataset real.

La evidencia de ejecución y capturas se guarda en `evidencias/`, excluida de Git para no publicar datos privados automáticamente. La suite final puede repetir la comprobación sin equipo físico con los comandos del README.

## Defectos encontrados y corregidos

Se corrigió una posible autorización tardía tras STOP durante arm, usando generación local y parada posterior; STOP quedó independiente del transporte secuenciado. Se impidió emitir STOP al primer cambio de pestaña sin conexión, conservando el requisito de inicio sin solicitudes. El cliente descarta órdenes atrasadas en cola. Se serializó el cambio de configuración y cierre con tareas de archivos, y se recrea el servicio desarmado cuando corresponde.

La revisión gráfica mostró ventana parcialmente debajo de la barra de tareas al solicitar altura completa de pantalla. Se limitó tamaño inicial al espacio útil y se verificó la vista maximizada. Se corrigieron callbacks que podían conservar una referencia al despachador anterior después de configurar. Se añadió validación de schema/tipos/límites al estado recibido y contador de errores HTTP. Se ajustó deadtime del simulador al fin nominal del pulso.

## Límites y puertas pendientes

No hubo conexiones al ESP32 ni a una cámara física, ni mediciones de Wi-Fi, PWM, corriente, posición, colisión o agarre. No hay dataset real creado, modelo entrenado ni autonomías implementadas. La captura real y su reconexión se validarán con la ESP32-CAM; el software probado utiliza backend FFmpeg y timeouts sujetos a su soporte.

El simulador replica el contrato lógico, con reloj evaluado al consultar/actuar, y no certifica tareas FreeRTOS ni fenómenos eléctricos. El cliente HTTP usa timeout de conexión/lectura, sin promesa de tiempo real duro. El cierre informa un trabajador que no termine; una parada sin state válido se muestra no confirmada. Si no hay clave válida, STOP público puede ejecutarse pero su confirmación autenticada falla.

Fase 01 implementada y validada localmente en software. La puerta física queda abierta y explícitamente pendiente. Antes de Fase 02: ejecutar el plan físico progresivo y obtener autorización. No se desarrollaron CNN, inferencia definitiva, reglas difusas, heurística autónoma ni navegación ArUco.

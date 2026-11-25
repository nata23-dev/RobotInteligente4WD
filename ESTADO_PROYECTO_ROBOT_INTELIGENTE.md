# Robot Inteligente — Estado, decisiones y plan maestro

**Versión:** 1.3 | **Actualizado:** 2026-11-24 | **Entrega:** 2026-11-30
**Proyecto provisional:** Robot móvil inteligente para la detección, recolección y clasificación de figuras geométricas.
**Asignatura:** Inteligencia Artificial. **Zona horaria:** México centro.

> Documento vivo de continuidad. No es el informe final ni una evidencia de pruebas. Actualizar al terminar cada sesión y conservar la versión más reciente en la carpeta del proyecto de ChatGPT y en el repositorio local. Los datos marcados como propuestos o pendientes no deben presentarse como resultados. No incluir credenciales reales.

## 1. Contexto y objetivo

Se sustituyó la plataforma hexápoda inicialmente planteada por un robot Robodacta 4WD con ruedas Mecanum, ESP32 principal, ESP32-CAM OV5640 y brazo robótico. Se busca integrar los cuatro parciales de IA en una aplicación Python única: heurística, procesamiento de imágenes, CNN y lógica difusa. La computadora procesa video y decide; el ESP32 ejecuta órdenes de actuadores mediante Wi-Fi. El robot debe funcionar físicamente durante la exposición y no solo en video.

**Alcance mínimo propuesto:** una figura visible a la vez en una superficie plana controlada; localizar, clasificar por forma, aproximarse en lazo visual, cerrar garra, trasladar o desplazar la pieza de manera controlada y liberarla en su zona de clasificación. Repetir con nuevas piezas. El usuario coloca las figuras antes de iniciar cada ciclo si es necesario; no dirige el robot durante el ciclo autónomo. Tres destinos diferenciados por forma; preferir destinos accesibles con giro de brazo a altura fija, y si no son físicamente posibles, calibrar maniobras cortas del chasis hacia zonas marcadas. No asumir que puede levantar objetos. La elección final de destinos se decide con pruebas físicas antes de desarrollar toda la autonomía. Varias figuras simultáneas, navegación global, reconocimiento de obstáculos y mejoras de interfaz son opcionales; no bloquean la entrega mínima.

## 2. Estado verificado y antecedentes

| Componente | Estado al 24/11 | Evidencia o condición |
|---|---|---|
| Chasis 4WD Mecanum | Armado | Confirmación del usuario |
| Motores | Probados anteriormente | Ruedas individuales responden en la posición correspondiente |
| Brazo | Armado, funcional según usuario | Garra y movimiento horizontal izquierda/derecha; no hay elevación activa |
| Figuras | Fabricadas según usuario | Plantilla previa: 9 piezas, cubo/cilindro/prisma triangular en rojo, azul y verde, nominal 3 cm. Verificar piezas reales |
| Wi-Fi | Probado anteriormente | No se ha revalidado la configuración actual |
| Avance | Calibración histórica parcial | 350 ms: 21, 20, 20.5 cm; media 20.5 cm. No extrapolar sin medir |
| Lateral | Prueba histórica parcial | Izquierda/derecha invertidas con deriva longitudinal. V5 corregía patrones; falta confirmar en hardware |
| Aplicación Python V7 | Recuperada y revisada; 4/4 pruebas locales sin hardware | ZIP original aportado el 24/11; control, calibración y cámara implementados; no consta validación física ni CNN autónoma |
| Cámara OV5640 | Antecedente de transmisión funcional descrito en firmware v6 | URL exacta de stream y visualización Python pendientes de prueba actual; no reflashear sin necesidad |
| OpenCV | Segmentación HSV preliminar implementada | Prueba sintética de rojo aprobada; cámara real y extracción de datos para IA pendientes |
| CNN, heurística autónoma, lógica difusa | Pendientes | Implementación, integración y validación pendientes |
| Informe, diagramas finales, presentación, video y ZIP | Pendientes | Capturar evidencia desde hoy |

### 2.1 Configuraciones históricas que NO se deben mezclar

- Firmware `Robot4WD_Nate_Integral_Camara_Brazo_v6.ino` recuperado: tres servos (pinza 21, derecho 23, izquierdo 22); centros 90/80/120°. Ruedas FL 26/25, FR 33/32, RL 13/12, RR 14/27. Es antecedente, **no configuración final de dos servos**.
- Firmware `Robot4WD_Nate_Brazo4SG90_v4.ino` recuperado: dos servos (pinza GPIO21 y base GPIO18), giro inicial 75°, límites 35–115°, garra abierta 60°, cierre aún por calibrar en ese archivo. Conversaciones posteriores mencionan cierre 35° e inicial 45°; no usar como valor definitivo sin probar con pieza real.
- Otras versiones antiguas mencionaban asignaciones distintas (incluidas pinza 23, giro/izquierdo 21 y derecho 22); verificar versión real cargada y conexiones antes de emitir órdenes. No inferir pines a partir de nombres de izquierda/derecha del brazo.
- En v6: cámara AP `ESP32CAM-CARRO`, cámara 192.168.4.1, ESP32 principal 192.168.4.200, respaldo 192.168.10.1. UART histórico GPIO14 de cámara a GPIO16/RX del principal, 115200 baudios, masa común. No es requisito usar UART si HTTP funciona; comprobar montaje y firmware actuales.
- API histórica v6: `/api/state`, `/api/drive`, `/api/pulse`, `/api/arm`, `/api/servo`, `/api/centros`. Parámetros y contrato deben verificarse en código real; no reutilizar sin comprobar. En v6 existe límite de motor de 600 ms y ENA/ENB con jumpers (velocidad fija). Verificar en versión actual.
- Mantener alimentación adecuada, GND común y límites mecánicos seguros. No conectar/desconectar con energía, no forzar servos, no accionar simultáneamente ruedas y brazo hasta comprobar estabilidad eléctrica. Hubo problemas previos de Wi-Fi con tres servos.

**Registro de hardware definitivo (completar antes de programar):**

| Elemento | GPIO / valor físico confirmado el 24/11 o posterior |
|---|---|
| Firmware principal actualmente cargado | PythonBridgeV6 es el firmware del ZIP más reciente; versión instalada todavía por verificar |
| Código Python más reciente / ruta | `Robot4WD_Aplicacion_Unificada_V7.zip` → `Robot4WD_Unificado.py` + `config.json`; conservar original privado |
| FL, FR, RL, RR (dos pines cada uno) | V4: 26/25, 33/32, 13/12, 14/27; confirmación física pendiente |
| Pinza / giro (GPIO) | V4: GPIO21 / GPIO18; confirmación física pendiente |
| Ángulos apertura / cierre / centro / destinos | PythonBridgeV6: apertura 60°, límite inferior 35° (cierre con pieza pendiente de confirmar), centro 75°, giro 35–115°; destinos pendientes |
| IP ESP32 y URL de video | PythonBridgeV6: AP Robot4WD_Nate, IP esperada 192.168.4.1; stream 192.168.4.2:81/stream es ejemplo, no confirmado |
| Fuente de alimentación, masa y jumpers | PENDIENTE |
| Altura garra, alcance y dimensiones piezas | PENDIENTE |
| Campo visual y zona ciega cercana | PENDIENTE |
| Tipo de transporte (sujeción o deslizamiento) | PENDIENTE |

### 2.2 Revisión directa del firmware aportado — 24/11/2026, v1.1

Fuente: `Texto pegado.txt` aportado por el usuario, 533 líneas lógicas. Identificado como Robot Nate V4, basado en V3, para ESP32 principal; es una versión de calibración, no un programa Python. El usuario cree que fue la última versión utilizada; no se ha comprobado qué binario está cargado. No confundir revisión estática con ejecución física.

- Ruedas FL 26/25, FR 33/32, RL 13/12, RR 14/27; las cuatro banderas de inversión son falsas. Patrones F, B, L, R, FL, FR, BL, BR, TL, TR y pruebas individuales TFL/TFR/TRL/TRR. Persisten antecedentes de inversión lateral; verificar antes de cambiar patrones.
- Garra GPIO21 (id 0), base GPIO18 (id 1). Inicio de garra 60°, intervalo de software 15–60° (15° NO es cierre seguro); giro 75°, rango 35–115°. Cierre 35° es dato histórico por reconfirmar, no una constante del archivo. PWM 50 Hz, 500–2400 µs; paso 2° cada 80 ms. Cierre de garra limitado a 5° por solicitud.
- Motores sin PWM de velocidad (ENA/ENB con jumpers según el código); movimiento único fijo 350 ms, pausa secuencial 450 ms. `POTENCIA_PRUEBA=180` solo determina signo en escritura digital. Arranque sin activar servos ni movimientos intencionales.
- API HTTP V4: `/motor?d=F`, `/secuencia`, `/brazo/activar-uno?id=0`, `/brazo/liberar-uno?id=0`, `/brazo/liberar`, `/brazo/mover?id=0&angulo=60`, `/parar`. `/brazo/activar` rechaza activación conjunta. No hay endpoint de estado estructurado. La parada congela objetivos y conserva sujeción; no corta alimentación.
- `peticionActivarServo` rechaza activar otro servo si uno está activo. `peticionMotor` y `peticionSecuencia` rechazan movimiento con cualquier servo activo. `peticionMoverServo` detiene ruedas. Estas restricciones hacen inviable transportar una pieza con la garra activa; no resolverlas liberando la garra ni eliminando protecciones sin validar alimentación.
- V4 usa exclusivamente WIFI_AP del ESP32 principal con IP esperada 192.168.4.1; el panel solo muestra una URL de cámara introducida manualmente. No implementa conexión a la red de la cámara, ni captura de video, ni UART. Si la cámara mantiene su propio AP histórico en 192.168.4.1, hay dos redes aisladas con IP coincidente. Propuesta condicionada a prueba: conservar firmware de cámara, unir ESP32 principal a su AP con IP distinta (p. ej. 192.168.4.200) y, si se necesita respaldo, AP de diagnóstico en otra subred. Alternativa: ambos dispositivos en una red local común. Verificar URL de stream real, no asumir puerto o ruta. No copiar credenciales del archivo al informe, repositorio ni ZIP.

**Decisión técnica propuesta:** conservar V4 como respaldo privado sin publicar credenciales. Una actualización de firmware principal orientada a API permitirá pulsos acotados configurables, estado JSON, dos servos activos solo después de validar estabilidad eléctrica, movimiento de ruedas con servos sosteniendo posición (sin cambio de ángulo simultáneo), parada prioritaria y vencimiento de órdenes/sesión. No dar por medida la posición del servo: es posición ordenada, sin sensor de realimentación. Probar con ruedas elevadas y brazo apoyado, después en piso, sin forzar la garra. Toda IA, ajustes de calibración y secuencias permanecerán en una sola aplicación Python. No se ha modificado, compilado ni cargado un firmware nuevo en esta revisión.

**Siguiente acción inmediata:** encender el robot en condiciones seguras, conectarse al AP del carro y abrir http://192.168.4.1/; confirmar si aparece el panel Robot 4WD Nate - V4 y enviar captura sin credenciales. Si aparece otra versión, recuperar esa versión antes de modificar. Después comprobar cámara por separado, alimentación y sujeción simultánea bajo supervisión; decidir arquitectura de red y firmware final.


### 2.3 Recuperación de la aplicación V7 y PythonBridgeV6 — 24/11/2026, v1.2

**Esta sección sustituye las propuestas de reescritura y comprobación por navegador de la sección 2.2.** El usuario aportó `Robot4WD_Aplicacion_Unificada_V7.zip` (8 archivos): `Robot4WD_Unificado.py`, `ESP32_Puente_Python_V6.ino`, `config.json`, `INICIAR_APLICACION.bat`, `requirements.txt`, `LEEME.txt`, `pruebas_sin_hardware.py`, `preview.png`. Es el paquete más reciente identificado, no prueba de que el firmware esté instalado. La V6 PythonBridge no es la V6 histórica de tres servos.

- Python/Tkinter: pestañas Conducción, Brazo, Cámara/OpenCV, Calibración, IA/Autonomía, Configuración/OTA. Video en hilo, registro de actividad, guardado de capturas, patrones editables, intercambio de laterales, mediciones CSV y configuración JSON. La pestaña IA es un marcador de trabajo pendiente, no un modo autónomo.
- Pines confirmados en código: FL 26/25, FR 33/32, RL 13/12, RR 14/27; garra GPIO21 (35–60°, inicio 60°), giro GPIO18 (35–115°, inicio 75°). Paso 2° cada 65 ms. Se pueden activar ambos servos y mover ruedas con servos activos; no hay bloqueo de movimientos simultáneos. No probar concurrencia hasta validar fuente y montaje.
- Pulsos configurables 50–700 ms, inicial 150 ms en JSON. ENA/ENB con jumpers: sin PWM de velocidad. Patrón adelante [-1,1,-1,1], atrás [1,-1,1,-1], izquierda [1,1,-1,-1], derecha [-1,-1,1,1], giro izquierda [-1,-1,-1,-1], giro derecha [1,1,1,1]; orden FL, FR, RL, RR. Laterales ya intercambiados respecto a V4; verificar comportamiento real. JSON del ZIP tiene calibración vacía; 20.5 cm/350 ms es antecedente, no está guardado allí.
- API HTTP con cabecera X-Robot-Key: GET `/api/health`, `/api/state`, `/api/drive?fl=...&fr=...&rl=...&rr=...&ms=...`, `/api/servo?nombre=garra|base&grado=...`, `/api/release?nombre=...`, `/api/stop`; POST `/api/update` (OTA opcional, evitar durante pruebas iniciales). No registrar ni publicar valores de credenciales existentes; usar ejemplos y configuración local excluida de la entrega. `/api/health` devuelve PythonBridgeV6. `/api/state` reporta posiciones ordenadas, no medidas.
- OpenCV: `detectar_colores` convierte BGR→HSV, segmenta rojo (dos rangos), verde y azul, aplica apertura morfológica 5×5, filtra contornos menores de 450 px², dibuja rectángulos y etiquetas; devuelve conteos por color y modifica la imagen. Falta producir datos por objeto (centroide, caja, área, ROI original, identificador) para CNN y control. Capturas para entrenamiento deben estar libres de anotaciones.
- Bloqueo de red: PythonBridgeV6 usa solo AP Robot4WD_Nate, IP 192.168.4.1; stream configurado 192.168.4.2:81/stream es explícitamente ejemplo. Si cámara y carro tienen AP separados con misma IP, no habrá acceso simultáneo con una sola interfaz Wi-Fi sin solución de red. Primero probar; si falla, evaluar conectar principal a AP de cámara con IP distinta o red común. Evitar reflashear cámara si se puede conservar transmisión.
- Seguridad por revisar antes de autonomía: `/api/stop` corta ruedas, pero no congela objetivos de servos; no es parada eléctrica ni total. El temporizador de motor depende de que el bucle siga atendiendo; no equivale a garantía ante bloqueo. Agregar cancelación de ciclo, caducidad de imágenes y órdenes, confirmación de estado lógico y exclusión de cambios de ángulo mientras se mueve el chasis. Valorar cambios mínimos del firmware solo si la red/seguridad lo exige. No asumir realimentación de agarre ni posición.
- Validación local realizada el 24/11: `python -m py_compile Robot4WD_Unificado.py pruebas_sin_hardware.py` sin errores; `python pruebas_sin_hardware.py` **4/4 OK** (simulación de orden, patrones, límites de pulsos/servos, segmentación sintética de rojo). No se abrió la GUI ni se compiló/cargó firmware; no hubo prueba física ni de stream. El manual menciona Python 3.14 en el PC; verificar versión real y compatibilidad del entorno de entrenamiento/inferencia antes de instalar dependencias de CNN.

**Decisión:** ampliar V7, no reescribirla. Mantener el ZIP original como respaldo. Siguiente paso: abrir la aplicación existente, conectarse al AP del carro con ruedas suspendidas y brazo apoyado, pulsar Conectar / Verificar ESP32. Si aparece PythonBridgeV6 y estado JSON, comprobar cámara y luego pruebas físicas escalonadas. Si no conecta, diagnosticar red y versión antes de cargar otro .ino. No enviar movimientos durante la primera comprobación.

## 3. Decisiones técnicas propuestas

| Tema | Decisión |
|---|---|
| Ejecución | Python en PC; única aplicación, módulos internos separados y comentados |
| Hardware | Conservar dos servos y dos L298N; no rehacer brazo |
| Visión | OpenCV: HSV para segmentar colores, máscara, morfología, contornos, centroide y área, recorte RGB para CNN |
| CNN | Keras/TensorFlow; tres formas, no nueve clases; cada forma con tres colores |
| Control | Lógica difusa Mamdani o Sugeno de orden cero; salida dirección/corrección y duración de pulso, no PWM si los EN tienen jumpers |
| Heurística | Máquina de estados, condiciones de confianza, estabilidad, pérdida de video, límites y parada |
| Comunicación | HTTP local; conservar firmware si cumple. Actualizarlo una sola vez si faltan comandos seguros; parámetros en JSON. OTA opcional solo si ya está validada |
| Datos | Capturar con cámara real en sesiones distintas; separar sesiones antes de aumentar datos; prueba independiente |
| Entorno | Fondo mate uniforme y contrastante, iluminación estable, suelo plano, una figura por ciclo inicialmente |
| Seguridad | Inicio sin movimiento; paro manual, watchdog en ESP32, comandos acotados, no arrancar automáticamente al reconectar; abortar si hay fallo |
| Evidencias | Guardar originales desde primera prueba; logs, CSV, métricas y fotos reales |

### 3.1 Flujo integrado

ESP32-CAM -> frame -> OpenCV (máscara, contorno, centroide y área) -> ROI a CNN (clase y confianza) y variables de control difuso (error horizontal y proximidad visual) -> heurística arbitra estados, valida y autoriza acción -> API HTTP -> ESP32 -> ruedas/servos -> nuevo frame. Clase neuronal selecciona el destino físico. El sistema difuso debe intervenir en la aproximación real, no solo mostrar valores. El control manual sirve para pruebas y contingencia, no sustituye autonomía.

### 3.2 Heurística: estados iniciales

`INACTIVO -> BUSCAR -> DETECTAR/CLASIFICAR -> ALINEAR -> APROXIMAR -> TOMAR -> TRASLADAR -> SOLTAR -> FINALIZAR/BUSCAR`.

- Si no hay detección: detenerse; búsqueda con pulsos limitados solo en área despejada; si se agota el tiempo, abortar.
- Si confianza CNN inferior a umbral calibrado o clase inestable en varios frames: no recoger; adquirir nuevas imágenes y, si persiste, abortar.
- Si existe objetivo estable y fuera del centro: aplicar corrección difusa; medir de nuevo.
- Si está alineado y lejos: avanzar según duración difusa; medir de nuevo.
- Si está en zona de agarre calibrada: parar chasis, ejecutar cierre de garra y traslado por clase. Si hay zona ciega final, usar únicamente un pulso final calibrado con límites.
- Si no hay sensor de agarre: cierre ordenado no demuestra agarre real; registrar verificación visual si existe, de lo contrario reportar limitación y evaluar éxito por observación.
- Si se pierde cámara, falla comunicación, expira tiempo, hay paro manual o error de hardware: cancelar órdenes, detener actuadores de locomoción y exigir rearme explícito. No liberar garra automáticamente si puede causar caída. Watchdog local indispensable si se corta Wi-Fi.
- Registrar estado, transición, regla, imagen, clase/confianza, error, proximidad, duración, orden y respuesta.

### 3.3 Procesamiento de imágenes

1. Conectar a stream real o captura periódica según firmware.
2. Limitar ROI a campo alcanzable; convertir BGR a HSV; calibrar umbrales por color (rojo puede requerir dos intervalos de tono).
3. Máscara combinada, apertura/cierre morfológicos moderados, contornos y filtros de tamaño. Elegir objetivo único; en futuro, selección determinista.
4. Calcular bounding box, centroide, proporción de área y color. Expandir recorte con margen; redimensionar y preparar canales igual que durante entrenamiento.
5. Mostrar y guardar originales, máscaras, contornos, ROI, centroide y clasificación.
6. Calibrar con las figuras reales, distintos ángulos y fondo. Área aparente es una aproximación relativa dependiente de forma, orientación y cámara, no distancia absoluta. Preferir calibración por clase o variable visual alternativa si el área no es monotónica.

### 3.4 Red neuronal

Propuesta simple: entrada RGB 64x64; Conv2D 16 + ReLU + MaxPool; Conv2D 32 + ReLU + MaxPool; Conv2D 64 + ReLU + MaxPool; GlobalAveragePooling (o Flatten si se valida mejor); Dense 64 ReLU; Dropout 0.25; Dense 3 Softmax. Adam, categorical/sparse categorical crossentropy según etiquetas, batch 16–32, máximo inicial 30 épocas con early stopping y restauración de mejores pesos. Parámetros son iniciales y no resultados. Guardar arquitectura real y configuración de entrenamiento.

Dataset: objetivo inicial 100–150 imágenes originales por forma (300–450 totales), equilibradas por color; aumentar si evaluación insuficiente. Capturar sesiones variadas de iluminación, distancia, orientación. Separar 70/15/15 por sesión o aproximadamente 80/10/10 si las sesiones lo requieren; no dividir frames consecutivos aleatoriamente ni colocar versiones aumentadas en evaluación. Augmentación moderada solo en train. Las nueve piezas físicas limitan la generalización a objetos nuevos; reconocerlo. Guardar originales, recortes/etiquetas, manifest de sesiones/splits, script de captura/entrenamiento/evaluación, semilla, historial, modelo `.keras`, métricas y gráficos. Objetivo interno inicial: ≥90% exactitud en prueba independiente si se logra, nunca inventar métricas. Informar precisión, recall, F1 por clase, matriz de confusión, número de ejemplos y errores; también medir inferencia en vivo. Umbral de confianza inicial 0.80, ajustar con validación y congelar antes de prueba final.

### 3.5 Lógica difusa

Entradas propuestas: error horizontal normalizado `e = (cx - W/2)/(W/2)` en [-1,1]; proximidad visual `p` en [0,1] a partir de área aparente calibrada por forma (0 lejos, 1 zona de agarre). Pertenencias iniciales triangulares/trapezoidales solapadas: error izquierda / centro / derecha; proximidad lejos / media / cerca. Definir puntos tras calibración, no convertir arbitrariamente a cm. Salidas: corrección firmada y pulso de movimiento; preferir Sugeno orden cero con consecuentes numéricos y promedio ponderado para simplificar, o Mamdani si se justifica. Guardar funciones de pertenencia y reglas, visualizar grados y salida real. Duraciones y signos se calibran sobre robot con límites de firmware. Sin PWM real, la duración de pulso controla desplazamiento aproximado, no velocidad instantánea.

| Error | Lejos | Medio | Cerca |
|---|---|---|---|
| Izquierda | Corregir izq. largo | Corregir izq. medio | Corregir izq. corto |
| Centro | Avance largo | Avance medio | Detener / verificar agarre |
| Derecha | Corregir der. largo | Corregir der. medio | Corregir der. corto |

La inferencia debe interpolar duraciones con pertenencias parciales, no ser únicamente un if/else. Ejecutar un eje a la vez si el chasis no permite control combinado; heurística hace arbitraje y limita acciones. Probar signo, salida suave, saturación y parada cerca, pérdida de frame y baja confianza. Guardar gráficas de membresías, tabla y registros reales.

## 4. Plan de ejecución y criterios de salida

Fecha actual martes 24/11; fecha límite lunes 30/11; meta interna tener prototipo y entregables completos domingo 29/11. No asumir disponibilidad horaria del equipo; distribuir trabajo en paralelo.

| Fecha | Trabajo crítico | Criterio para darlo por terminado |
|---|---|---|
| Mar 24 | Auditar archivos y firmware, verificar cableado, alimentar y probar manual, video Python, agarre y depósito por forma a altura fija; calibrar pulsos/zonas. Preparar estructura y primeras evidencias | Una app conecta, muestra video, mueve/para, abre/cierra; tres destinos mecánicamente viables. Firmware/pines/IP reales registrados |
| Mié 25 | OpenCV, calibrar ROI/HSV/centroide/proximidad; capturar y etiquetar datos en sesiones; diagramas preliminares | Tres formas detectables en tres colores, ROI reproducible, manifest y splits guardados |
| Jue 26 | Entrenar/evaluar CNN; implementar y probar inferencia difusa; estados heurísticos y seguridad | Modelo entrenado y métricas reales; pruebas de reglas con entrada registrada; API segura |
| Vie 27 | Integrar los cuatro parciales en app y ejecutar ciclos físicos; corregir fallos de mayor impacto | Al menos un ciclo completo real por cada forma sin control manual durante el ciclo; logs y video de prueba |
| Sáb 28 | Validación repetida, contingencias, congelar configuración y código; capturas; completar informe/diagramas/README | 3 intentos por forma como mínimo (9), registro de éxito/error; objetivo interno ≥8/9 y al menos una prueba correcta por forma. Si no se alcanza, informar y corregir |
| Dom 29 | Revisión final del PDF, presentación, video real, dataset/modelo, código, ZIP, ensayo y permisos de enlace | ZIP extraído y probado, PDF revisado, video accesible sin cuenta del propietario, ensayo de todos; listo para subir |
| Lun 30 | Margen de contingencia, corrección crítica únicamente, entrega Classroom | Un ZIP y URL, confirmación de subida, demostración presencial preparada |

**Plan de contingencia:** si una pieza no puede ser recogida a altura fija, primero adaptar soporte/superficie y posición de estación sin añadir actuadores. Si desplazamiento lateral deriva, usar giros y avances cortos calibrados con feedback de cámara; reducir recorrido y número de objetos por ciclo. Si stream falla, diagnosticar alimentación/red/URL y considerar capturas periódicas de la misma cámara si soportadas. Si CNN falla, ampliar datos reales y ajustar encuadre; no sustituir CNN por color o formas codificadas. Si plazo aprieta, recortar estética, OTA, navegación global y clasificación simultánea, nunca uno de los cuatro parciales ni evidencia real. No prometer autonomía ni métricas no verificadas.

## 5. Aplicación y estructura de código propuesta

Una interfaz con video, controles manuales, calibración, captura dataset, predicción, visualización difusa, estado de heurística, inicio/paro autónomo, y registro exportable. Separar hilo de video y tareas de red para no bloquear UI; mantener una sola autoridad de control, evitar órdenes simultáneas, descartar frames viejos. Tkinter o la interfaz existente si ya funciona. No añadir un segundo programa de operación; scripts de entrenamiento/evaluación son complementos reproducibles, no cuatro prototipos separados.

```text
app.py
robot_client.py          # HTTP / actuadores / seguridad
vision.py                # Parcial 2
cnn.py                   # Parcial 3, inferencia
fuzzy.py                 # Parcial 4
heuristics.py            # Parcial 1, estados
controller.py            # Integración
config.example.json      # Sin contraseñas reales
requirements.txt
scripts/capture_dataset.py
scripts/train.py
scripts/evaluate.py
firmware/                # .ino principal y código de cámara utilizado, cuando disponible
```

Conservar código real de fabricante si se utiliza y es distribuible, indicar procedencia. Si no está disponible, documentar firmware preinstalado y procedimiento exacto; intentar recuperar fuente original exigida por rúbrica. Congelar versiones realmente usadas. No incluir entornos virtuales, cachés, credenciales ni archivos innecesarios. Mantener copia local del firmware funcional antes de tocarlo.

## 6. Matriz de cumplimiento de la rúbrica

| Requisito | Evidencia entregable | Estado |
|---|---|---|
| Heurística integrada | Código, diagrama estados, reglas y log de transiciones reales | Pendiente |
| Procesamiento imágenes | Código, máscaras, contornos, ROI y secuencia real | Pendiente |
| RNA/CNN | Código, arquitectura, dataset, pesos, métricas, inferencia y destino por forma | Pendiente |
| Lógica difusa | Código, membresías, reglas, entradas/salidas y pulsos reales | Pendiente |
| Integración cuatro parciales | Ciclos de extremo a extremo, video y logs | Pendiente |
| Construcción, conexiones, comunicación | Fotografías y esquemáticos editable + PDF/imagen, firmware y protocolo | Parcial |
| Documento final PDF | Secciones y extensión exigidas, fuentes IEEE | Pendiente |
| Presentación | Archivo utilizado en exposición | Pendiente |
| README | Instalación, conexiones, configuración, dependencias, ejecución, seguridad y limitaciones | Pendiente |
| ZIP y video Drive | Organización, archivos completos, enlace probado, una entrega | Pendiente |

### 6.1 Documento final

- Portada: institución, asignatura, nombre definitivo, integrantes, docente, fecha. Datos y nombres oficiales por confirmar; antecedentes de equipo IA: Barrera Dueñas Topilzin Natanael, Martínez Cortez Irving Josué, Martínez Hernández Leonardo y Moreno Medrano Paul; verificar composición del equipo antes de portada.
- Índice solo de temas con páginas; funcional si se puede sin añadir subtemas innecesarios.
- Introducción: 1 cuartilla; contexto, problema, objetivo, justificación y solución.
- Materiales y métodos: 2 cuartillas; componentes, herramientas, arquitectura, esquemáticos, CNN, protocolos y metodología.
- Desarrollo: 5 cuartillas; manual técnico de armado/operación, código representativo, imágenes, heurística, visión, CNN/dataset/entrenamiento, lógica difusa, integración, comunicaciones e interfaz.
- Resultados: 2 cuartillas; evidencia física, métricas CNN, visión, reglas, lógica difusa, integración, fallos, limitaciones y análisis.
- Mejoras: 0.5–1 cuartilla.
- Conclusiones: 0.5–1 cuartilla, **un único párrafo por equipo**, primera persona plural.
- Referencias: IEEE, fuentes reales consultadas; no APA. Portada e índice aparte del cuerpo. Cuerpo previsto: 11–12 cuartillas, sin contar portada, índice y referencias.
- Priorizar rúbrica sobre convenciones generales; capturas reales legibles y revisión de paginación.

### 6.2 Organización exacta de entrega

```text
NombreProyecto.zip  # sustituir por nombre definitivo acordado
  01_Documentacion/
  02_Diagramas_y_Esquematicos/
  03_Codigos_Fuente/
    01_Heuristica/
    02_Procesamiento_de_Imagenes/
    03_Redes_Neuronales/
    04_Logica_Difusa/
    05_Integracion_del_Sistema/
  04_Dataset_y_Modelo_Entrenado/
  05_Evidencias/
  06_Presentacion/
  README.txt
```

Rúbrica permite omitir separación de cinco subcarpetas si el programa es integrado y cada bloque está identificado/comentado. Propuesta: conservar app y módulos juntos bajo `03_Codigos_Fuente/` para no romper imports, con mapa de archivos en README; si se usan subcarpetas, asegurar imports y ejecución desde ZIP extraído. Dataset incluye manifest y pesos. Video alojado en Drive, URL en Classroom; opcional copiar URL al README. Una sola entrega del equipo. Verificar permisos y ausencia de secretos.

### 6.3 Video y presentación

Video real: componentes, problema, recorrido del sistema, cámara/máscara/clase/confianza, membresías y acción difusa, estado/regla heurística, motores y garra, ciclos de cada forma, resultados y limitaciones. Capturar simultáneamente robot y pantalla o sincronizar grabaciones reales; no simular evidencia. Presentación sugerida: 8–10 diapositivas (problema, arquitectura, hardware, cuatro parciales, resultados, limitaciones/conclusión); repartir explicación entre integrantes y ensayar. La demostración en vivo es obligatoria aunque exista video.

## 7. Pruebas y registro

| ID | Prueba | Evidencia | Estado |
|---|---|---|---|
| HW01 | Arranque, reposo, Wi-Fi, paro y watchdog | Video/log | Pendiente |
| HW02 | Cuatro ruedas, direcciones y pulsos repetidos | Tabla y video | Parcial histórico |
| HW03 | Garra y giro, 3 formas, destinos a altura fija | Fotos/video | Pendiente con piezas |
| CV01 | Stream real y latencia/pérdida de imagen | Captura/log | Pendiente |
| CV02 | Detección de 9 combinaciones | Máscaras/CSV | Pendiente |
| NN01 | Evaluación independiente y matriz de confusión | CSV/gráficas/modelo | Pendiente |
| FU01 | Reglas, membresías, interpolación y pulsos | Gráficas/CSV | Pendiente |
| HE01 | Transiciones normales y fallos | Log | Pendiente |
| IN01 | Ciclo completo por forma y color (9 intentos mínimos) | Video y tabla | Pendiente |
| IN02 | Pérdida de cámara, Wi-Fi, paro y reinicio | Log/video seguro | Pendiente |
| PK01 | Instalación desde ZIP, PDF, enlaces, sin credenciales | Checklist | Pendiente |

CSV sugerido: `fecha,prueba,id_pieza,forma_real,color_real,clase_predicha,confianza,estado,regla,error_x,proximidad,pulso_ms,orden,respuesta,agarre_observado,deposito_correcto,tiempo_s,resultado,fallo,evidencia`. Una fila por evento o tabla separada por ciclo. No fabricar datos. Éxito físico significa pieza llega al destino correcto sin intervención manual durante el ciclo; reportar denominador, fallos y tasa. Las pruebas con una figura por ciclo y superficie controlada no demuestran navegación general.

## 8. Responsabilidades propuestas (asignar a integrantes)

- Control e integración hardware/app: firmware, calibración, seguridad, ciclos.
- Visión/dataset/CNN: capturas, entrenamiento, evaluación y exportación.
- Lógica difusa/heurística y pruebas: reglas, integración, logs y métricas.
- Documentación/diagramas/video/ZIP: recopilar evidencia y empaquetar desde el primer día. Todos explican el sistema completo y colaboran en pruebas.

## 9. Siguiente sesión: orden inmediato

1. Reunir el `.ino` realmente cargado, última carpeta Python y, si existe, código de cámara original. No cargar versiones viejas a ciegas. Obtener foto del montaje y conexión de ambos servos.
2. Encender con ruedas suspendidas para prueba inicial, brazo apoyado, comprobar ausencia de movimiento al arranque; luego probar en suelo despejado. Comprobar Wi-Fi, estado y video real en misma aplicación. Registrar direcciones/ángulos efectivos.
3. Probar garra con cubo, cilindro y prisma; comprobar físicamente agarre, transporte a altura fija y liberación. Medir altura, alcance y posibles destinos; elegir método de depósito viable. Verificar cámara ve las figuras hasta zona de toma o medir zona ciega.
4. Calibrar pulsos cortos, medir cada sentido varias veces y guardar config; validar paro y pérdida de conexión de forma segura. Solo después capturar dataset.

## 10. Bitácora y reglas de continuidad

### 2026-11-24 — v1.0

- Usuario confirma robot armado, brazo horizontal y garra funcionales, figuras físicas listas y rúbrica definitiva con fecha 30/11.
- Se recuperaron antecedentes v4/v6 y conversación V7, con discrepancias de pines y ángulos; pendiente localizar versión real en equipo.
- Se definió propuesta de alcance y arquitectura con cuatro parciales, plan de seis días y margen de entrega. No se ejecutaron pruebas nuevas ni se entrenó modelo en esta sesión.
- Próximo bloqueo: confirmar firmware/app, cámara y viabilidad mecánica de tres destinos antes de programar autonomía.

### 2026-11-24 — v1.1

- Recuperado y revisado el texto completo de V4 aportado por el usuario; se documentaron pines, API, límites y bloqueos.
- Identificados bloqueos de activación doble, transporte con garra activa, duración fija y red de cámara.
- No se efectuaron pruebas físicas ni cambios al firmware. Próximo paso: comprobar versión activa desde el panel y validar hardware y cámara.

### 2026-11-24 — v1.2

- Recuperado ZIP V7 con firmware PythonBridgeV6; se inspeccionaron sus ocho archivos y código relevante.
- Compilación sintáctica Python correcta y 4/4 pruebas sin hardware aprobadas. No equivale a validación física.
- Se cancela propuesta de reescritura completa; V7 es la base. Se conservan V4 y el ZIP como antecedentes privados.
- Próximo paso exacto: confirmar PythonBridgeV6 con el botón Conectar / Verificar ESP32; luego comprobar cámara real y mecánica. No se cambió código del robot.

### Plantilla para próximas sesiones

```text
Fecha y versión del documento:
Objetivo de sesión:
Archivos/commit utilizados:
Cambios realizados:
Configuración real verificada:
Pruebas y resultados (incluidos fallos):
Evidencias (rutas):
Decisiones aceptadas y motivo:
Pendientes / riesgos:
Próximo paso exacto:
```

Antes de cada sesión, leer esta bitácora y comprobar versión de código; al terminar, actualizar tablas, plan, configuración y evidencias. No borrar resultados históricos; marcar qué fue reemplazado. Mantener código y bitácora en control de versiones o copias fechadas. Este archivo debe guardarse como fuente del proyecto y adjuntarse/actualizarse si se inicia un nuevo chat; la mera descarga no garantiza su disponibilidad futura.


## 11. Arquitectura objetivo V8 — revisión y decisiones propuestas (24/11/2026, v1.3)

Esta sección fija la ruta técnica propuesta para aprobación del usuario y prevalece sobre propuestas previas incompatibles. Usuario solicita interfaz profesional, automática como pantalla principal, manual separada, visualización de decisiones y percepción, dataset tomado por la cámara del propio robot, comunicación fluida y actualizaciones sencillas. No se ha modificado el código ni comprobado hardware en esta revisión.

### 11.1 Auditoría del ZIP V7 (relectura directa)

- `Puente` valida órdenes y usa `urllib.request` con HTTP local y cabecera de autenticación; timeout por defecto 3 s, sin conexión persistente explícita. `salud()` exige literalmente PythonBridgeV6: versionar contrato/API y adaptar cliente si cambia firmware.
- `HiloCamara` usa `cv2.VideoCapture`, hilo daemon y cola de tamaño 1. La cola limita acumulación en Python, no en cámara/decodificador. No hay marca temporal de fotograma entregada al consumidor, ni reconexión robusta; reiniciar hilo puede solapar sesiones si `read()` se bloquea. `_actualizar_video` consume cada 80 ms y procesa HSV, PNG/base64 y render en hilo Tk. Separar visión de interfaz, gestionar ciclo de vida de captura, conservar último frame fresco con id y timestamp, detectar stale y descartar atrasados.
- `detectar_colores()` devuelve conteos por color y dibuja cajas sobre frame; no devuelve objetos estructurados, centro, área, máscara, recorte ni tracking. Captura manual existente guarda una copia original JPG, pero no etiqueta ni separa sesiones. Extender, no reemplazar sin necesidad.
- `RobotApp` agrupa control manual, brazo, cámara, calibración, IA preliminar y ajustes. `operacion_lock` serializa órdenes normales; STOP se envía por hilo separado. `parada_seq` cancela algunas órdenes pendientes, pero no evita todas las carreras, y nuevos movimientos limpian la emergencia. `conectado` depende de verificación, no de supervisión continua. No hay controlador autónomo, CNN ni lógica difusa.
- Firmware conserva FL 26/25, FR 33/32, RL 13/12, RR 14/27, garra 21, base 18. Dos servos activos simultáneamente permitidos; también movimiento de ruedas y cambio de objetivos de servo simultáneos, sin interlock eléctrico. Límites duros garra 35–60°, base 35–115°, referencias 60/75°. Paso 2°/65 ms; estado reporta ángulos ordenados, no medidos. Ruedas sin PWM, pulsos 50–700 ms. STOP solo corta ruedas; no cancela objetivos de servos ni enclava. El vencimiento motriz se evalúa en `loop()` tras `server.handleClient()`, por lo que no se debe afirmar un límite temporal duro garantizado ante bloqueo de servidor. OTA por HTTP con binario/particiones compatibles; no usar durante operación.
- `config.json` guarda patrones/ángulos/duración/URLs/mediciones; los límites físicos duros siguen en firmware. `requirements.txt` solo incluye OpenCV, no TensorFlow. LEEME menciona Python 3.14. Usar entorno virtual separado Python 3.12 x64 (compatibilidad documentada de TensorFlow 2.21 con Python 3.10–3.13); validar instalación/import/inferencia y fijar versiones realmente probadas. No desinstalar Python actual. Entrenamiento fuera del ciclo de control; CPU local inicialmente, Colab opcional para entrenar, inferencia local sin internet.

### 11.2 Decisiones de arquitectura

- Una aplicación de escritorio Tkinter/ttk (conservar tecnología para plazo), tema oscuro profesional, pestaña principal Automático y pestaña Manual independiente; Dataset y Ajustes/Diagnóstico como utilidades separadas. Un solo punto de entrada, sin ejecutar múltiples scripts para operar. Entrenamiento reproducible como script independiente invocable fuera del control; se puede ofrecer botón para lanzar proceso cuando robot detenido.
- Módulos propuestos: `main.py`, `ui/`, `hardware/bridge.py`, `hardware/camera.py`, `control/safety.py`, `control/controller.py`, `ai/vision.py`, `ai/classifier.py`, `ai/fuzzy.py`, `ai/heuristics.py`, `dataset/capture.py`, `training/train.py`, `tests/`, `config.example.json`, configuración local privada, `models/`, `logs/`. Adaptar código V7 gradualmente con pruebas de regresión; mantener ZIP original y commits/etiquetas de versiones. No introducir frameworks, microservicios o cloud innecesarios.
- Flujo: cámara -> último fotograma -> visión estructurada (color, bbox, centro, área normalizada, recorte) -> CNN de tres clases -> heurística de estados + lógica difusa -> árbitro de comandos/safety -> HTTP -> actuadores. Realimentación por imágenes posteriores a cada pulso y telemetría lógica. Mostrar razón de reglas, confianza, datos y acción real; no afirmar acceso a pensamientos ni agarre medido sin sensor.
- Hilos: UI en hilo principal; captura, visión/inferencia y control en trabajadores independientes, con colas acotadas y timestamps; logs a disco sin bloquear. Un solo propietario de órdenes manual/auto/dataset; cambio de modo detiene, cancela pendientes y requiere autorización nueva; STOP prioritario, enclavado en firmware y PC; congelar objetivos conservando sujeción cuando seguro; rearme explícito. Separar temporización motriz del manejo HTTP (evaluar tarea dedicada/temporizador y verificar bajo carga); validar timeout, pérdida de cámara, desconexión, heartbeat y ausencia de movimientos automáticos al arranque. No liberar servos automáticamente con pieza/estructura bajo carga. Corte físico de energía disponible.
- Contrato versionado: conservar API existente si viable, añadir identificador de orden, estado objetivo/ocupado, fallo, armado y parada/rearme; confirmar ACK no equivale a fin físico. No repetir órdenes motrices automáticamente ante respuesta perdida. Serializar control; límites de hardware en ESP32, calibración dentro de límites en JSON. Servos no cambian objetivo durante transporte; garra puede mantener PWM si alimentación validada. Carga OTA solo en mantenimiento detenido y con respaldo USB, no necesaria para ajustes de IA.

### 11.3 Red y rendimiento

- Opción preferida para conservar cámara si sigue siendo AP propio: PC y ESP32 principal conectados a AP de la cámara; cámara 192.168.4.1 y ESP32 principal 192.168.4.200 si subred/colisiones lo permiten. Actualmente V6 principal es solo AP y usa 192.168.4.1; si cámara sigue igual, no están en misma red. Verificar URL/ruta/puerto reales, capacidad AP y tráfico simultáneo; no reflashear cámara sin necesidad. Alternativa estable: router local común con cámara y controlador como STA (requiere que firmware de cámara lo permita); operación offline sin nube. Evitar dos AP con misma subred, dos interfaces o UART salvo necesidad probada.
- HTTP local para comandos pequeños y MJPEG para video; separar flujos, no mandar pesos/imágenes de vuelta al ESP32. Medir antes de sustituir protocolo; reutilizar conexión HTTP si servidor soporta keep-alive, evitar sondeo excesivo. Configurar inicialmente 320x240 o 640x480 JPEG/MJPEG y 10–15 FPS como objetivos de prueba, ajustar según visibilidad y latencia. Inferencia sobre ROI RGB 64x64 (propuesto), modelo cargado una vez y calentado antes de armar. Descartar imágenes viejas y esperar una observación nueva tras cada pulso; timestamp de recepción no mide latencia de captura exacta. Objetivos iniciales no medidos: RTT p95 <=150 ms, inferencia p95 <=100 ms, observación a orden p95 <=300 ms (excluye desplazamiento físico y latencia cámara no instrumentada), >=10 FPS recibidos, UI >=10 actualizaciones/s; stale inicial 500 ms sin frame nuevo recibido, ajustar con datos; medir 60 s de streaming concurrente y registrar p50/p95, FPS, fallos y prueba física de latencia cámara usando evento visible. Si no cumple, bajar resolución/calidad/ritmo, mejorar red, verificar energía y ajustar antes de migrar protocolo. No prometer tiempo real duro ni FPS sin pruebas.

### 11.4 Interfaz y observabilidad

Automático: video grande con cajas, centro objetivo, región de agarre, máscara/recorte opcionales, forma y confianza, color, centro/error/área, reglas difusas activas y pertenencias, estado heurístico, destino, orden ejecutada, respuesta y tiempos; registro de ciclo y contador de éxitos solo confirmados. Iniciar, pausar seguro, STOP/rearme siempre visibles; modo desconectado y simulación claramente marcados. Manual: video y controles Mecanum, giro/garra, pulsos y calibración, sin interferir con auto. Dataset: cámara real montada, clase/color/sesión/ID pieza, captura individual o ráfaga espaciada, vista previa y descarte, contadores; motor parado al guardar, automatizar posiciones solo bajo condiciones seguras. Ajustes: IP, stream, patrones, límites dentro de firmware, parámetros HSV/difusos, diagnóstico y exportación de logs. No inventar telemetría física.

### 11.5 Dataset y algoritmo

- Capturar 300–450 originales iniciales (100–150 por forma, colores equilibrados si nueve piezas previstas están confirmadas); p. ej. 3 sesiones independientes de 70/15/15 aproximado por grupo, procurando cada clase/color en cada conjunto. Separar por sesión/posición/instancia, no por fotogramas vecinos; si solo una instancia de cada forma/color, declarar limitación de generalización. Capturar distancias, orientaciones, iluminación, fondo y oclusiones leves representativas desde cámara montada. Guardar original sin overlays y ROI obtenido por mismo preprocesamiento de inferencia, etiquetas supervisadas por usuario, manifest con sesión y parámetros. Aumentos solo en entrenamiento; no contabilizar duplicados como fotos originales. CNN ligera 3 clases; no usar color para sustituir forma. Baja confianza/inconsistencia => detener o reobservar. Evaluar exactitud, matriz de confusión, precisión/recall por clase y casos reales. Guardar `.keras`, clases, normalización, tamaño entrada y hash/versionado. No entrenar durante conducción.
- Heurística: INACTIVO -> BUSCAR -> DETECTAR/CLASIFICAR -> ALINEAR -> APROXIMAR -> TOMAR -> TRANSPORTAR -> DEPOSITAR -> VERIFICAR -> FIN; FALLA/STOP desde cualquier estado. La lógica difusa genera magnitud de corrección/avance (pulsos, no velocidad PWM) a partir de error horizontal y proximidad aparente calibrada por forma; la heurística decide cuándo se aplica, y bloquea con datos dudosos. Realizar acciones discretas y reobservar para evitar sobrepasar. Destinos por clase en área controlada, definir geometría tras probar agarre; si no hay sensor de agarre, verificación visual solo si cámara permite o anotación observacional separada, nunca inventar estado confirmado. Si no se puede levantar, usar traslado/deslizamiento compatible o ajustar altura de superficie; no asumir capacidad vertical.

### 11.6 Ruta de implementación congelada por puertas de aceptación

1. G0, 24/11: respaldar V7 y comprobar firmware real, cámara real/red, electricidad y agarre/deposito de las tres formas. Confirmar versión e IP; decidir topología y destinos con mediciones. No modificar pines por suposición.
2. G1, 24–25/11: firmware puente estable (solo una actualización necesaria si se confirma), STOP/rearme/watchdog/interlocks, API versionada, medición bajo video. Pasar control manual, pérdida de enlace, cámara simultánea y pruebas eléctricas antes de armar autonomía.
3. G2, 25/11: refactor incremental V8, pestañas, captura/visión, dataset por sesiones. Validar UI no bloqueada y observaciones frescas.
4. G3, 26/11: CNN, reglas difusas y heurística probadas individualmente con fixtures, replay y logs; integrar en simulación explícita, luego ruedas suspendidas.
5. G4, 27/11: integración física progresiva, primero alineación y toma, después traslado/deposito y ciclo completo por las tres formas. Sin intervención durante ciclo.
6. G5, 28/11: pruebas repetidas con 9 intentos mínimo propuesto y meta 8/9, fallos y métricas honestas, freeze de código. 29/11 PDF, presentación, video, ZIP, prueba instalación/enlace; 30/11 contingencia y entrega. Documentar en paralelo.

Cambios futuros de patrones, tiempos, HSV, CNN, reglas, interfaz o destinos no requieren cargar firmware mientras se mantenga contrato y límites. Cambios de pines, PWM real, red no configurable, seguridad embebida o contrato sí pueden requerir firmware. Aceptar arquitectura antes de implementar; cualquier excepción se documenta con razón, prueba y efecto en fecha. Bloqueos vigentes: binario instalado, fuente original de cámara, enlace simultáneo, estabilidad eléctrica, capacidad física de agarre/deposito, compatibilidad de entorno y rendimiento real. Próximo paso: comprobación no motriz de V7 y cámara, luego validación física escalonada. No se ha ejecutado hardware ni medido latencia en esta revisión.

Referencias técnicas consultadas: https://www.tensorflow.org/install/pip ; https://www.tensorflow.org/install/source_windows ; https://github.com/espressif/esp32-camera . Registrar fecha de consulta y adaptar IEEE en el informe final si utilizadas.

## 12. Diseño de estación de clasificación y pruebas del día 1 — propuesta v1.4 (24/11/2026)

- Usuario propone tres cuadrados de cinta negra y carteles con las figuras. Se recomienda conservar la cinta y carteles para humanos, e incorporar marcadores ArUco reales generados con OpenCV, diccionario DICT_4X4_50, IDs 0=cubos, 1=cilindros, 2=prismas triangulares. No entrenar CNN para destinos: la CNN predice la forma de la pieza; ArUco localiza el destino mediante visión clásica. Los carteles serán blancos, con marcador negro de 10 cm de lado inicial, margen blanco libre, texto/dibujo negro separado, soporte vertical estable detrás o al costado del área, sin interferir con garra ni ruedas. Medir campo visual, altura y orientación antes de fijar montaje. No inventar patrón de marcador; generar con generateImageMarker y verificar detección de cada ID.
- Superficie clara mate, plana y despejada; cinta negra de 2–3 cm sin relieve. Propuesta inicial 150 x 160 cm, zonas 30 x 30 cm con separación aproximada 15 cm; ampliar según huella, radio de giro, alcance, visibilidad y capacidad de transporte. Empezar con una pieza por ciclo en una posición inicial conocida, luego múltiples si se valida. Evitar que piezas ya clasificadas se vuelvan objetivos; definir área de recogida mediante geometría/pose o posición inicial verificada, no asumir que la cinta por sí sola se detecta. Evitar carteles coloreados para no contaminar segmentación HSV.
- Navegación: fijar clase antes de tomar; heurística elige ID objetivo; buscar marcador con giros acotados, detener/reobservar entre pulsos, ignorar IDs ajenos; OpenCV extrae esquinas, centro y escala; difusa controla alineación y aproximación con parámetros específicos de destino; usar objetivo de depósito calibrado con desfase cámara-garra y posición relativa marcador/zona. Para distancia/pose métrica calibrar intrínsecos y tamaño real del marcador; de inicio usar tamaño aparente y referencia visual de depósito calibrada, no afirmar distancia exacta. Marcador debe seguir visible hasta una posición segura de depósito o usar último tramo corto previamente validado, sin avance ciego largo. Detener al perder referencia o agotar tiempo. Sin encoders ni sensores de agarre, no afirmar confirmación física automática; comprobar visualmente si es viable y registrar observación humana si no. Evitar navegación global/SLAM y trayectorias largas a tiempo fijo. Si traslado no es viable con altura fija, evaluar depósito por giro horizontal con estaciones alcanzables; no declarar éxito sin prueba.
- Hoy G0: respaldar ZIP y código; encender con ruedas suspendidas/brazo apoyado, comprobar red y botón Conectar/Verificar ESP32, capturar pantalla de versión. Probar cámara por separado desde su red si necesario, URL real, video con pieza cercana/lejana, campo visual. No reflashear cámara ni firmware hasta identificar versiones/red. Confirmar dimensiones del robot, altura fija de garra, alcance, altura y orientación cámara, tamaños/cantidad reales de figuras. Probar ruedas individuales y patrones cortos, corregir nombres desde config; verificar alimentación regulada y GND, servos por separado, luego ambos gradualmente y breve desplazamiento con garra manteniendo posición solo si no hay sobrecarga o reinicios, en zona segura. Probar agarre y soltar cada forma sobre mismo plano; cortar energía ante atasco/zumbido o comportamiento imprevisto. V6 STOP no enclava ni cancela objetivos de servos. No ejecutar autonomía con firmware actual. Registrar fotos, video, fallos y mediciones. Preparar área provisional con cinta después de medir robot; fabricar carteles definitivos tras comprobar cámara. No entrenar todavía ni capturar dataset masivo hasta estabilizar cámara/entorno y herramienta de etiquetas.
- Siguiente puerta G1: consolidar red compartida, seguridad y API; implementar detector ArUco en visión V8 y parámetros de destino en JSON, no en firmware. Probar detección y depósito primero de una sola clase, después tres. Referencia técnica: https://legacy-docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html (consultada 24/11/2026). Decisiones de medidas, diccionario e IDs propuestas, pendientes de prueba y aprobación física; ningún hardware probado hoy por el asistente.


## 13. Firmware principal 1.0.0 / API 1 — 24/11/2026

- El usuario decidió comenzar ordenadamente por el firmware principal y construir una aplicación nueva modular en VS Code, no ampliar la interfaz V7. Se mantiene el piso directamente como superficie, cinta negra y carteles ArUco; no se exige cartulina en el piso.
- Entregado `Robot4WD_Firmware_V1.zip` con sketch `Robot4WD_Firmware_V1/Robot4WD_Firmware_V1.ino` y `LEEME.txt` con contrato de API y procedimiento de prueba. Se conserva respaldo V7. Se verificó integridad del ZIP; no se compiló con SDK ESP32 ni se probó hardware. Versión candidata a congelar tras G1, no firmware físicamente validado.
- Cableado recuperado del ZIP V7: FL 26/25, FR 33/32, RL 13/12, RR 14/27, garra GPIO21 (35–60°, inicial 60°), base GPIO18 (35–115°, inicial 75°). ENA/ENB con jumper; pulsos 50–700 ms, no PWM de velocidad. No cambiar ESP32-CAM.
- Red propuesta: ESP32 principal AP+STA, cliente de ESP32CAM-CARRO por DHCP (IP serie a 115200); AP de diagnóstico independiente 192.168.10.1. Opcional IP estática .200 solo tras validar. Credenciales locales vacías en distribución; editar antes de cargar y no incluir en entrega.
- API 1: GET /api/health público y /api/state autenticado. POST /api/arm con challenge, /api/heartbeat, /api/drive, /api/servo/enable, /api/servo con session y seq crecientes; /api/stop público local enclavado, /api/release autenticado solo desarmado con confirmación. No compatible directamente con aplicación V7. Clave por X-Robot-Key; HTTP local no cifrado.
- Tarea FreeRTOS independiente de HTTP, heartbeat recomendado 250 ms, expiración 1200 ms, pulso máximo 700 ms, interbloqueos de movimiento y asentamiento estimado, STOP cancela objetivos y conserva PWM. No implica seguridad certificada, sensores de posición/agarre ni protección eléctrica. No rearmar automáticamente; heartbeat condicionado a salud del controlador y video fresco en automático. OTA ArduinoOTA opcional deshabilitada de inicio; requiere partición compatible, contraseña independiente y ambos servos liberados/desarmado.
- Próximo paso: editar credenciales, compilar en Arduino IDE con ESP32 Dev Module y ESP32Servo, subir al ESP32 principal con actuadores sin alimentación, comprobar IP y health sin movimiento y video simultáneo. Enviar captura de monitor serie y respuesta health. No iniciar autonomía antes de validar alimentación, interlocks, STOP, caducidad y mecánica.


## 14. Fase 01 — arquitectura base nueva y validación local (24/11/2026)

**Registro de continuidad v1.5.** Esta entrada aplica la solicitud actual y la decisión de la sección 13: aplicación nueva modular sobre Robot4WD 1.0.0/API 1; no ampliar la interfaz V7. Las decisiones anteriores se conservan como historial. Entrega académica: 30/11/2026. Fase 02 no iniciada.

### Arquitectura y archivos

Se crearon main.py; app/{application,config,models}.py; ui/main_window.py, theme.py, components/widgets.py y tabs/{automatico,manual,dataset,configuracion}.py; hardware/{bridge,protocol,camera,simulator}.py; control/{controller,safety,command_dispatcher}.py; ai/{vision,classifier,fuzzy,heuristics}.py; dataset/capture.py; pruebas de configuración, aplicación, HTTP, simulador, despacho, cámara/dataset y validación gráfica; instalador, lanzador, configuración pública y privada; requirements.txt y requirements-lock.txt; README y documentación técnica. Se reservaron training/, models/, calibration/, logs/ y evidencias/. Firmware oficial del ZIP copiado sin cambios y con credenciales vacías a firmware/; originales y copias históricas privadas en referencias_locales/ fuera de Git.

Interfaz oscura con cuatro pestañas, Automático principal y autonomía deshabilitada. Manual incluye diez patrones V7, ruedas individuales, pulsos, activación individual de servos, ángulos y pasos finos, HOME y liberación confirmada. Configuración persistente en JSON validado, editor de patrones/red/tiempos/límites, intercambio de laterales, calibración humana CSV y exportación de logs. Dataset captura originales PNG, etiquetas de forma/color/sesión y manifiesto CSV con recepción monotónica; ráfaga pendiente. Cámara separada con último frame, FPS, resolución, edad, pérdida y reconexión; sin imágenes sustitutas.

Despacho único de sesiones/secuencias y heartbeat; cola acotada, descarte de órdenes atrasadas y generación de cancelación. STOP invalida permiso inmediatamente y usa transporte independiente; confirma desarmado y objetivos congelados mediante state. Se distingue parada solicitada, confirmada lógicamente y no confirmada/pérdida. Salud del controlador principal con vencimiento de 650 ms; no heartbeat incondicional si se bloquea UI/control. Cambio entre Manual/Dataset/Automático detiene y desarma si había conexión; Configuración conserva propietario para diagnóstico. No hay órdenes al iniciar ni al cambiar pestañas sin conexión. Armado siempre explícito; no repetición automática de movimiento ni rearme.

### Protocolo, dependencias y referencias

GET health público y state autenticado; POST arm/challenge, heartbeat, drive, servo/enable, servo, stop público y release autenticado con confirm=1. X-Robot-Key, formularios, session/seq uint32 positivos, heartbeat 250 ms, sesión 1200 ms, pulso 50–700 ms, deadtime 50 ms, servo 2°/65 ms, asentamiento 800/200 ms. Garra 35–60°/HOME60; base 35–115°/HOME75; sin PWM de velocidad. No hay sensores físicos de posición, corriente o agarre.

Python 3.12.10 x64 instalado localmente bajo .runtime/ con instalador oficial firmado; .venv independiente, sin pip global. Tk 8.6. Dependencias verificadas: opencv-contrib-python 4.12.0.88, NumPy 2.2.6, Pillow 12.0.0 y Requests 2.32.5; transitivas exactas en lock. Una sola distribución de cv2. TensorFlow no instalado. Se consultó el índice real, se resolvieron ruedas x64 compatibles y se verificó ArUco DICT_4X4_50 para IDs 0/1/2 mediante fixtures. No es navegación ni validación de carteles físicos.

V7 se revisó completa y su calibración estaba vacía. Los diez patrones y laterales corregidos se conservaron sin certificación física nueva. Se encontró primero una copia preconfigurada del firmware con una API_KEY demasiado corta para validSecrets(); no se modificó. El ZIP oficial recibido después tiene claves vacías intencionalmente y el mismo código operativo. SHA-256 sketch oficial: a4ca67346103487ca02e28da7caf10967dcf15aad5a11a7f4e70bf9b2b306cd6. SHA-256 V7: 7d1d47c8f8a2e807f2aec4bcd121780443ff7b1a20559cfc3b80aae5bfd3d559. No se registran valores privados de claves en esta entrada.

### Pruebas y resultados reales

50 pruebas unittest aprobadas en la ejecución final (5.758 s), sin hardware. Cubren carga/validación/persistencia, patrones/pulsos/límites, formularios HTTP reales mediante loopback, autenticación, challenge/sesión/secuencias, heartbeat/caducidad, interlocks, STOP/cancelación, rechazo sin permiso, pérdida de red, exclusión de modos, frames recientes, cierre y originales/metadatos del dataset temporal. Incluyen carreras de STOP durante respuesta de arm y con transporte ordinario bloqueado. No se enviaron solicitudes al robot ni cámara físicos.

compileall y pip check correctos. INSTALAR.bat ejecutado con éxito; INICIAR_APLICACION.bat --smoke-ui abrió y cerró la interfaz simulada con cuatro pestañas e inicio desarmado. Validación gráfica programática: ocho combinaciones de pestaña/tamaño (1366x768 y 1920x1080) sin desbordamiento horizontal detectado; monitor físico 1366x768, capturas locales inspeccionadas; 1920x1080 solo comprobación geométrica, no otro monitor físico. Un pulso manual simulado y STOP por cambio a Dataset aprobados. Evidencias locales en evidencias/, excluidas de Git. Sin dataset real ni métricas físicas inventadas.

Se corrigieron carreras de autorización tardía, solicitudes involuntarias al primer cambio de pestaña, referencias antiguas a despachador tras configurar, sincronización de cierre/configuración, validación de estado remoto, contadores HTTP y tamaño inicial que invadía barra de tareas. Cierre incompleto informa error y deja evidencia en log.

### Límites y siguiente puerta

Fase 01 implementada y validada localmente en software. Pendiente validación de cámara/URL/red común, binario realmente cargado, seguridad temporal física, alimentación, pines/strapping, patrones, servos, agarre y depósito. No compilación/carga de firmware, pruebas eléctricas ni movimientos físicos desde esta sesión. Simulador lógico no representa fenómenos eléctricos ni garantiza tiempo real; timeouts de cámara dependen de FFmpeg. STOP no corta energía y ángulos reportados no son mediciones. CNN, inferencia, difusa, heurística y navegación autónoma siguen sin implementar y bloqueadas.

Documentación: README.md, docs/ARQUITECTURA.md, docs/CONTRATO_API.md, docs/PLAN_DE_PRUEBAS_FISICAS.md y docs/VALIDACION_FASE01.md. Git inicializado; commit de la fase se realiza tras revisión de pruebas, límites y auditoría del índice contra credenciales históricas, con configuración privada, ZIPs, entornos, cachés y logs excluidos. Consultar git log -1 para identificador.

**Próxima acción exacta:** operador realiza F01–F03 del plan físico sin movimiento: confirmar firmware instalado 1.0.0/API1, IP DHCP y red compartida, state autenticado desarmado y stream real. Después ejecutar secuencia controlada de STOP/caducidad, ruedas individuales, patrones, servos y alimentación con video. No avanzar a Fase 02 sin autorización.


## 15. Fase 01.1 — Rediseño integral UX/UI (24/11/2026)

Registro de continuidad v1.6. Base estable 68ebbe0 conservada; trabajo en rama ui/fase-01-1. Alcance exclusivo de presentación; no se inició Fase 02 ni se enviaron órdenes al robot/cámara físicos. Se revisaron bitácora, README, documentación, ui/ y capturas; las cuatro imágenes adjuntas se usaron como referencias conceptuales. referencias_ui/ no estaba presente; no se copiaron cifras, predicciones ni estados de las imágenes.

Se implementó tema claro con la paleta solicitada y variantes de contraste, Segoe UI, iconos lineales propios, paneles reutilizables y navegación lateral. STOP GLOBAL permanece en cabecera; Alt+1..4 cambia de sección y Esc solicita STOP. Se mantiene el cambio de propietario/desarmado/STOP mediante Controller.change_mode, sin modificarlo. Configuración conserva el modo para diagnóstico. Simulación se identifica siempre y sus tiempos no se presentan como Wi-Fi físico.

Automático: cámara original/procesada con aspecto conservado y vacío informativo, cuatro módulos de IA pendientes en cuadrícula, ocho etapas neutrales, registro compacto incremental y acciones deshabilitadas hasta integración. Manual: todos los controles previos, locomoción y ambos servos simultáneos, esquema FL/FR/RL/RR y estado lógico, sin posición o giro medidos. Dataset: manifiesto real por forma/color, progreso, última imagen y meta inicial 150/clase configurable en ui.local.json privado. Los contadores excluyen fixtures, duplicados, faltantes y rutas fuera del destino; no se crearon muestras reales ni artificiales en el dataset. Configuración: siete categorías de formularios tipados sobre el schema y validaciones originales; clave oculta, patrones, tiempos, límites, captura y mantenimiento. Guardar estando armado sigue rechazado.

Archivos modificados: ui/theme.py, ui/main_window.py, ui/components/widgets.py, ui/tabs/{automatico,manual,dataset,configuracion}.py, .gitignore, README y docs/ARQUITECTURA.md. Nuevos: ui/components/icons.py, ui/dataset_view.py, ui/preferences.py, tests/test_ui_redesign.py, tests/ui_redesign_validate.py, docs/DESIGN_SYSTEM.md y docs/VALIDACION_UI_FASE01_1.md. No se modificaron app/, control/, hardware/, ai/, dataset/, firmware/, main.py, requirements ni las pruebas originales. Sin nuevas dependencias de ejecución.

Línea base: 50/50 pruebas aprobadas antes del cambio. Suite final ampliada: 62/62 (50 originales intactas + 12 nuevas). Pruebas nuevas de navegación sin órdenes, formularios/persistencia/máscara, rechazo inválido/armado, intercambio lateral, confirmaciones, STOP/modos, vista procesada pendiente, aspecto de video, datos del manifiesto, meta y contraste. HTTPBridge se bloquea expresamente en las pruebas UI nuevas para impedir hardware real. compileall, pip check, main --smoke-ui, prueba gráfica original y validación ampliada aprobados. Los tiempos exactos están en evidencias/ui_fase01_1/resultados_checks.json y unittest.txt.

43 revisiones sin desbordamientos/recortes: 16 combinaciones de cuatro resoluciones y cuatro secciones, cuatro vistas maximizadas físicas, siete categorías de configuración y ocho vistas tipográficas virtuales a 125/150 % y ocho comprobaciones de ventana inicial/área útil compacta 1280x650, incluyendo miniatura guardada en prueba temporal. Se comprobaron tamaños aplicados exactos 1280x720, 1366x768, 1600x900 y 1920x1080; se corrigió el máximo predeterminado de Tk que limitaba la geometría al monitor. Monitor físico 1366x768; captura del área cliente maximizada aproximadamente 1366x697 por área reservada de Windows. Las capturas 1920x1080 intentadas contenían zonas negras fuera del monitor y se descartaron: tamaños mayores y escalados solo se validaron geométricamente, sin afirmar inspección en monitor físico 1080p ni modificar el escalado global de Windows.

Evidencias inspeccionadas: cuatro pantallas actuales y cuatro del commit 68ebbe0, logs de checks y JSON de layouts en evidencias/ui_fase01_1/, excluidos de Git. Se usa captura nativa de la ventana propia para no incluir otras aplicaciones del escritorio. Se corrigieron recortes verticales de IA, meta fuera de panel, flechas pequeñas, scrollbars innecesarias, contraste insuficiente y callbacks after pendientes al cerrar. Registro y telemetría incrementales; salud/video 80 ms y telemetría visual aproximadamente 240 ms. Lectura de manifiesto, thumbnails y preferencias en el trabajador de archivos existente.

Cierre: rediseño validado localmente con simulador. No hay evidencia nueva física ni IA implementada. Firmware y originales sin modificar; configuración privada y preferencias visuales fuera de Git. Commit local de la rama después de checks y auditoría; consultar git log -1. Próximo paso: revisión del operador de la interfaz y puerta física F01–F03 sin movimiento, manteniendo Fase 02 bloqueada hasta autorización.


## 16. Fase 02 / 02.1 — Consolidación y avances físicos reportados (24/11/2026)

Registro de continuidad v1.7. Se preserva todo el historial anterior. Las observaciones siguientes provienen del operador y de la solicitud de consolidación, salvo verificaciones locales expresamente indicadas. No se contactó al robot ni ESP32-CAM físicos ni se activaron actuadores en esta sesión. Robot temporalmente fuera de servicio; Fase 03 no iniciada.

### Firmware, red y cámara — reporte del operador

Firmware Robot4WD 1.0.0/API 1 compilado e instalado correctamente por el operador, con arranque inicialmente desarmado. Nombre de red corregido: ESP32-CAM-CARRO (con guion). Principal en Robot4WD_Diagnostico para diagnóstico. Comunicación inalámbrica entre ambos ESP32 y HTTP autenticado confirmados según operador; aplicación Python conectada al hardware real. DHCP principal observado 192.168.4.2, cámara 192.168.4.1 y diagnóstico 192.168.10.1. La dirección DHCP no se garantiza permanente.

MJPEG reportado en http://192.168.4.1:81/stream; video recibido en Python simultáneamente con control. Resolución observada 320x240 y aproximadamente 10–12 FPS. Orientación incorrecta cercana a 90° y calidad insuficiente todavía para detección confiable de figuras pequeñas. Pendiente evaluar resolución real, luz, enfoque/nitidez, contraste, saturación, JPEG y ajustes que admita el firmware de cámara. No se asumieron endpoints ni autofocus por el solo modelo OV5640.

El operador comunicó timeout 0.30 s y heartbeat 0.25 s, con p95 HTTP 32–47 ms en algunas pruebas estables. La lectura local actual confirmó URLs correspondientes y heartbeat 0.25 s, pero timeout persistido 0.18 s. Se registró la diferencia sin modificar configuración ni clave. Varias desconexiones fueron deliberadas por cambios de Wi-Fi para compartir capturas; no contar todos los errores acumulados como fallos espontáneos.

### Seguridad y ruedas — alcance parcial

Operador verificó armado explícito a nivel lógico, sesión autorizada, STOP GLOBAL e invalidación de sesión mediante estado de la aplicación. Tras interrumpir Wi-Fi reportó reconexión con firmware desarmado. Siguen pendientes medición exacta de caducidad, parada física bajo movimiento y cierre formal de detención automática; un estado lógico no es una prueba física completa.

Ruedas individuales reportadas: FL -1 adelante / +1 atrás, ambos pendientes de confirmación por ambigüedad verbal; FR -1 atrás / +1 adelante; RL -1 adelante / +1 atrás; RR -1 atrás / +1 adelante. Adelante provisional FL=-1, FR=+1, RL=-1, RR=+1; atrás FL=+1, FR=-1, RL=+1, RR=-1. Los patrones locales ya coinciden con esos signos; no se modificaron. Validación de ocho sentidos y finalización automática pendiente.

### Alimentación y arranque — incidencias prioritarias

Durante las pruebas del operador desaparecieron ambas redes Wi-Fi, con LED del ESP32 encendido. Una rueda que suele girar brevemente al encender mostró muy poca potencia, giró lentamente y se detuvo. Baterías aproximadamente una semana sin uso. Hipótesis principal: descarga/caída de voltaje; alternativas: regulación insuficiente, alimentación compartida, conexiones deficientes o reinicios. No hay mediciones eléctricas que confirmen causa. El operador cargará baterías antes de retomar pruebas físicas.

El giro inesperado de una rueda desde el encendido, antes de usar la aplicación, es una incidencia de seguridad prioritaria. Estados transitorios de GPIO, strapping, entradas L298N sin nivel definido, ENA/ENB permanentemente habilitados y secuencia de alimentación son causas posibles sin confirmar. La solución deberá mantener motores detenidos desde energización, antes de terminar setup(). No se implementaron cambios eléctricos ni firmware. Autonomía no autorizada hasta resolverlo y verificarlo físicamente.

Brazo: validación física, calibración definitiva, agarre, transporte y depósito pendientes. Se mantienen pines, límites y configuraciones existentes.

### Auditoría y consolidación local

Inicial: árbol limpio, main=68ebbe0 y ui/fase-01-1=46e20f8, sin tags ni remoto. La versión más completa era la rama visual. Se configuró origin al repositorio existente nata23-dev/RobotInteligente4WD y se comprobó que no había ramas/commits remotos iniciales. main avanzó por fast-forward a 46e20f8, sin reescribir ni borrar historial. Bundle y copias locales privadas preservados en .tools/backups/. Configuración actual intacta; copia histórica de firmware de Documentos preservada, pero no coincide con SSID/clave actuales y no se afirma que sea la fuente del binario instalado. Firmware rastreado sigue siendo distribución original con credenciales vacías; no se modificó ni cargó.

GitHub informó PUBLIC cuando la solicitud inicial exigía PRIVATE; se detuvo publicación y se informó. El propietario indicó después “Dejemoslo publico”. Se conserva PUBLIC por esa instrucción, sin cambiar visibilidad ni crear otro repositorio. No se solicitan tokens. Git 2.53.0.windows.1 y Credential Manager con cuenta nata23-dev disponibles; gh ausente. Metadatos GitHub confirmaron push/admin y dry-run confirmó transporte con escritura. Un endpoint específico de colaboradores devolvió 403 por alcance de integración, sin impedir las verificaciones alternativas. No se conceden permisos de apps externas.

Gitleaks 8.30.1 portátil del repositorio oficial, SHA-256 de descarga verificado; cero detecciones iniciales sobre los dos commits. Auditor específico scripts/audit_publication.py revisa referencias/blobs alcanzables, metadatos, índice y árbol publicable contra credenciales locales conocidas y rutas privadas, sin imprimir valores. Se complementan las herramientas, no se garantiza ausencia universal de secretos desconocidos. .gitignore amplía exclusiones de .env, secretos locales, claves/certificados, compilados, cachés/builds/editor; conserva plantillas y todo archivo local. Logs/capturas/ZIPs/configuraciones/entornos/dataset/modelos privados no se publican. Se repite revisión de staging e historial antes de push, solo main y sin force.

### Pruebas reales de software de esta consolidación

Primera corrida: 62 ejecutadas, 61 aprobadas, 1 fallida, 0 errores/omitidas, 15.484 s. Falló test_controller_failure_does_not_renew_forever porque “confirmada” también coincide con “no confirmada”: la prueba podía adelantarse al hilo STOP. Se fortaleció la espera al estado exacto Parada confirmada (estado lógico), conservando la aserción remota. Sin cambios de controlador ni debilitamiento de límites/tiempos. Segunda corrida: 62/62 en 14.906 s. Tras tres pruebas nuevas del auditor, 65 ejecutadas, 65 aprobadas, 0 fallos/errores/omitidas, 17.094 s.

scripts/check_software.py ejecuta unittest con red solo loopback y cámara física bloqueada; no modifica configuración. Nuevas pruebas usan secretos sintéticos en repositorios temporales para detectar historial codificado pese a limpieza del archivo actual, staging distinto de worktree y rutas privadas/plantillas, sin filtrar valores en informes. Cuatro secciones de la UI clara verificadas, STOP simulado, sin solicitudes al inicio. compileall, pip check y INICIAR_APLICACION.bat --smoke-ui correctos. Instalador e inicio revisados; dependencias sin cambios, sin pip global. Evidencias previas conservadas; informes, primer fallo y nuevas capturas en evidencias/consolidacion_2026_11_24/, ignorados por Git.

### Estado de fases y próxima implementación

Fase 01: infraestructura funcional y validación local. Fase 01.1: rediseño claro funcional. Fase 02: enlace y pruebas físicas iniciales reportadas, sin aceptación formal completa ni nuevo commit funcional independiente. Fase 02.1: consolidación, documentación y auditoría; publicación de main tras satisfacer condiciones. Resultado de sincronización se registra después del push. Pantalla Automático actual conservada; no se implementa rediseño nuevo ni IA.

Plan Fase 03.1: investigar firmware de ESP32-CAM y capacidades realmente expuestas; evaluar VGA real 640x480, JPEG/FPS/latencia, orientación 0/90/180/270, iluminación, enfoque/nitidez, brillo/contraste/saturación y exposición/balance si existen. No confundir ampliar píxeles con resolución real; separar original, transformaciones y overlays, descartar frames viejos.

Plan Fase 03.2: único visor protagonista 70–75 % cuando sea viable, original/procesada/máscara, ampliación/pantalla completa manteniendo aspecto y STOP; sin duplicaciones ni controles redundantes, diagnóstico secundario. Mostrar datos contextuales reales de figura/color/CNN/confianza/destino/acción/decisión/ciclo/conteo/conexión/permiso/alertas; módulos pendientes explícitos y autonomía bloqueada.

Plan Fase 03.3: HSV, colores, morfología, contornos, centroides, cajas, error lateral, área/proximidad relativas, selección/seguimiento, región de agarre y ArUco DICT_4X4_50 (0 cubos, 1 cilindros, 2 prismas triangulares). Plan Fase 03.4: captura individual/ráfagas, etiquetas/sesiones/metadatos, preview/calidad/ROI/duplicados y separación por sesiones antes de aumentos; meta inicial ajustable alrededor de 450 originales balanceados de cámara real. Nada de esto se declara implementado en esta consolidación.

Documentos: README actualizado, docs/CONSOLIDACION_FASE02_1.md y docs/PLAN_FASE03.md; plan físico actualizado sin borrar historia. Próximo paso: revisión externa del código consolidado; operador resuelve alimentación y movimiento al encender, confirma FL/seguridad/cámara/brazo. Preparado para planificar Fase 03, no para autonomía física ni para comenzar su implementación sin nuevas instrucciones.

Regresión final previa al commit de consolidación: 65/65, cero fallos/errores/omisiones, 16.797 s. Aplicación, interfaz, comunicación, seguridad, firmware, requisitos e instaladores intactos frente a 46e20f8; única corrección existente en la espera estricta de una prueba. git fsck sin corrupción; blobs sueltos no alcanzables conservados, sin purgar ni publicar.


### Publicación verificada de Fase 02.1 — 24/11/2026

Publicado commit 00bf0b52307e2a2706b60da98c611388cb34a445 (chore: consolidar fase 02 y preparar repositorio seguro) en https://github.com/nata23-dev/RobotInteligente4WD . Visibilidad PUBLIC por autorización posterior del propietario; no PRIVATE. Rama predeterminada y única rama publicada: main. HEAD, origin/main y ls-remote coincidieron, divergencia 0/0 y upstream origin/main. ui/fase-01-1 permanece local. GitHub y REST sin autenticación confirmaron identidad/visibilidad; README público coincide byte por byte con el blob local. Integración GitHub leyó README, bitácora, main.py, pruebas, informe y ejemplo; árbol remoto de 75 archivos verificado sin privados ni entornos. Auditor de origin/main: tres commits/76 blobs, cero hallazgos de credenciales conocidas; Gitleaks y staging sin detecciones. Historial anterior intacto, sin force ni repositorios adicionales. Informe inicial en evidencias/consolidacion_2026_11_24/remote_verification_inicial.json.

Se registra esta comprobación en un commit documental posterior y se verifica de nuevo su sincronización final. No se ejecutan cambios funcionales ni Fase 03. Seguridad física, alimentación y movimiento al encender siguen abiertos; pruebas de software finales 65/65 en 16.797 s y sin hardware físico.


## 17. Fase 03 — Visión y herramientas del dataset (24/11/2026)

Registro de continuidad v1.8. El propietario autorizó implementar completamente el software 03.1–03.4 sin contactar ni accionar hardware. Se parte de main/origin/main 4bd6ba6d0953637f84c83e6d47c7f50bb6a5fc43, limpio y sincronizado. Trabajo en feat/fase-03-vision, sin integrar en main. Se preservó respaldo privado de configuración y contenido anterior de esta bitácora. SVG descarga.svg utilizado únicamente como referencia visual; no se copiaron sus estados o predicciones como datos.

03.1 implementada en software: orientación horaria 0/90/180/270, inversiones, ajustes digitales moderados con neutros/reset, escalado proporcional en ambos sentidos, redibujado ante resize, generación por apertura/reconexión, configuración schema 2 y migración. La lectura migra en memoria sin reescribir. Archivo privado real idéntico byte por byte al respaldo; timeout 0.18 s, heartbeat 0.25 s, URLs, clave, patrones y límites conservados. No se aplicó propuesta 0.30 s. No se recuperó firmware de ESP32-CAM en ZIPs/referencias revisados; documentación Espressif no demuestra capacidades del binario instalado. Adaptación remota rechaza controles no verificados. VGA/QVGA, JPEG, exposición, balance, nitidez y enfoque físicos pendientes.

03.2 implementada: Automático con único visor 3:1, Original orientada sin análisis, Procesada con overlays reales y Máscara por color/combinada; ampliación/restauración, contexto compacto, diagnóstico/eventos desplegables y ciclo neutral de ocho etapas. STOP visible/Escape conservados; Iniciar/Pausar deshabilitados. No resultados CNN, distancias métricas, acciones o decisiones autónomas ficticias. Dataset comparte orientación; calibración integra editor HSV por color, máscara y consulta de píxel del mismo stream. Formularios y diálogos respetan hilo Tk y STOP.

03.3 implementada: un trabajador independiente procesa el último frame una sola vez por identidad, mantiene un resultado y descarta caducados/generaciones anteriores. Frame, Observation e imágenes derivadas viajan asociados. HSV rojo con dos intervalos, verde/azul, apertura/cierre, áreas, contornos, cajas, centroides, área relativa, posición/error lateral y solidez. Seguimiento visual determinista con estados sin objetivo/detectado/seguido/perdido, sin conservar válido un objetivo perdido. Proximidad es tamaño relativo sin calibración. ROI normalizada no confirma agarre. ArUco DICT_4X4_50 identifica estaciones 0/1/2, distingue desconocidos, sin pose o distancia física. No acceso de percepción al despachador.

PDF público docs/recursos/estaciones_aruco.pdf: tres páginas A4, patrón propuesto 100×100 mm y margen blanco >=20 mm, nombres fuera y regla para medir impresión al 100 %. Generación y render final detectados como [0], [1], [2]; tres páginas inspeccionadas. Validación digital no sustituye impresión/cámara reales. ReportLab/PyMuPDF se usaron bajo .tools ignorado; dependencias de ejecución/lock de aplicación intactos.

03.4 implementada: originales PNG y CSV previo conservados, ráfagas configurables/cancelables (inicial 10,1 s), frame nuevo/fresco por captura, guardas durante toda espera y antes de escritura. Cancelación ante armado/movimiento, pérdida/caducidad/reconexión, etiquetas incompatibles, reconfiguración y cierre. Captura tiene mutex separado de Safety: armado de UI se rechaza durante escritura; STOP no espera imágenes. Calidad provisional con brillo, Laplaciano, resolución, SHA-256, dHash, detección/área; advertencias y rechazo opcional de duplicados. Sidecar JSONL v2, recortes orientados sin digitales/overlays y etiqueta humana, revisión y split agrupado por sesiones 70/15/15 con rechazo si faltan sesiones/clases. Ver limitaciones de fallos de disco y balance en docs/VISION_Y_DATASET_FASE03.md.

Pruebas protegidas: base 65/65 en 24.812 s; cámara 71/71 en 22.000 s; percepción 80/80 en 35.656 s; dataset 89/89 en 31.531 s; integración 94/94 en 59.890 s. Final 96 ejecutadas/96 aprobadas, cero fallos/errores/omisiones, 34.906 s. Las 65 anteriores permanecen intactas. Se corrigieron altura de visor de calibración y repintado inmediato al abrir diagnóstico; la prueba nueva de Escape requiere foco antes de generar el evento. Conservadas corridas fallidas para trazabilidad. compileall, pip check y BAT --smoke-ui correctos. Sin cambios en control/, HTTPBridge, protocolo, simulador, firmware o requisitos. Red de pruebas solo loopback; evidencia gráfica bloquea toda red y cámara física.

Evidencia real de aplicación con fixture_prueba en evidencias/fase03/validacion/: Original/Procesada/Máscara, ampliación, diagnóstico, configuración/calibración y Dataset. Inspeccionadas visualmente en monitor 1366×768. Veinte comprobaciones de layout, cero desbordamientos; 1280/1366/1600/1920 aplicados y STOP visible. 1600/1920 solo comprobación geométrica, pendiente monitor físico mayor. 1024×768 no admitido por mínimo 1200×650. Maximizar/restaurar comprobados, cliente físico 1366×697. No se entregan capturas con zonas negras fuera del monitor como evidencia de 1080p.

Rendimiento de percepción completa sobre 200 fixtures tras calentamiento: QVGA media 5.452 ms/p95 9.357 ms/~183.4 FPS secuenciales; VGA media 34.578 ms/p95 45.922 ms/~28.9 FPS. No son FPS ni latencia de cámara. Ventana estable de ~12.903 s: CPU 12.656 s, RSS 92,995,584–108,470,272 B, delta final +946,176 B; no prueba exhaustiva de ausencia de fugas. Ráfaga de diez fixtures temporal completada; dataset real sigue cubo=0,cilindro=0,prisma_triangular=0. No muestras reales nuevas ni fixtures copiados al dataset del propietario.

Publicación: repositorio PUBLIC por decisión vigente; solo rama feat/fase-03-vision después de auditoría específica y Gitleaks redactado. Nuevos derivados excluidos de Git, PDF declarado binary. No publicar configuración, claves, dataset, capturas privadas, modelos, respaldos ni entornos. Se verifican SHA/upstream/remoto y main sin cambios después de push; resultado exacto local en evidencias/fase03/remote_verification.json y en respuesta final. No force push ni merge a main.

Pendiente físico/bloqueado: alimentación y giro desde energización, FL/ruedas/STOP/caducidad físicos, brazo, capacidades reales de cámara, evaluación VGA/QVGA, HSV/ROI reales, marcadores impresos y captura balanceada. Pendiente fases siguientes: CNN, difusa, heurística, máquina de estados y autonomía. Entrega académica 30/11/2026. No se certifica ninguna de esas pruebas físicas ni se autoriza movimiento autónomo.


## 18. Fase 03.1-R — Correcciones de revisión externa (24/11/2026)

Registro v1.9. Revisión solicitada sobre bd91084c3e07cbbf6827c0ac1e66e0b11e25b2f4 en feat/fase-03-vision, con árbol inicial limpio y fetch. No Fase 04, nuevas capacidades remotas, contacto con hardware ni cambios de firmware. Configuración privada respaldada y conservada byte por byte, incluyendo timeout 0.18 s, heartbeat 0.25 s, direcciones, clave, patrones y límites.

Se confirmaron y corrigieron: dependencia de Original de VisionWorker; admisión de captura con estado remoto desconocido; carreras de órdenes y captura; registros parciales entre PNG/CSV/derivado/JSONL; falta de revisión persistente y de agrupamiento de duplicados entre sesiones; reconfiguring enclavado si la cola está llena; reconstrucción de trabajadores tras una detención incompleta.

Original y Dataset usan Camera fresca directamente, con orientación y caché compartida; IA sin resultado declara Sin observación vigente. Procesada/Máscara siguen exigiendo percepción válida. En hardware integrado se requiere conexión y estado explícitamente desarmado, actuadores libres y sin mantenimiento con confirmación de 0…0.75 s; simulación se distingue y no se agrega modo solo cámara. Un mutex de admisión se comparte con Dispatcher tanto al encolar como al ejecutar; cierra la ventana entre dequeue y ejecución, sin bloquear STOP ni heartbeat. Guardas se repiten durante almacenamiento y ráfagas.

Almacenamiento con journal y respaldos de metadatos: commit completo o rollback/recuperación al volver a abrir/leer. Se prueban fallos PNG, manifiesto, recorte y JSONL, cierre durante escritura y proceso terminado abruptamente con os._exit(73). Se restaura exactamente el estado anterior y no se borran originales previos. La recuperación requiere disco disponible y una instancia escritora por destino; no se certifica apagón, corrupción de disco o escritura concurrente entre procesos. Ante varios objetos del mismo color se registra ambigüedad y se omite recorte automático.

Revisión persistente en metadata/reviews.json: sin_revisar/aceptada/rechazada, accesible en Dataset → Herramientas. Decisiones conservadas incluso si falta archivo. Rechazadas excluidas del split; no revisadas mantienen training_ready=False. Se agrupan sesiones enlazadas por duplicados exactos de originales y derivados; se comprueba existencia, etiquetas incompatibles y tres clases por conjunto. Informe reproducible con cantidades por conjunto/clase/color. Cambiar revisión o capturar invalida el split. No se entrena CNN.

Si no puede programarse configuración se restablece reconfiguring. Si un trabajador no termina, no se crean reemplazos duplicados: órdenes/capturas se bloquean y se exige reinicio. Sin alterar tiempos de comunicación, límites o autonomía.

Base protegida 96/96 en 26.219 s; integración con 96 anteriores intactas 96/96 en 34.734 s. Primera ampliación 112/112 en 37.188 s. Ejecución intermedia de 115 detectó pérdida de decisión de rechazo para archivo faltante y un montaje de prueba que instalaba el hook después de empezar Queue.get; ambos corregidos sin modificar pruebas anteriores ni relajar aserciones. Después: 115/115 en 41.797 s. Regresión de cierre incluyendo estado nulo y rechazo de reconfiguración tras fallo de ciclo de vida: 115 ejecutadas/115 aprobadas, 0 fallos/errores/omitidas, 41.172 s. Diecinueve pruebas nuevas en tests/test_external_review.py. compileall, pip check y BAT --smoke-ui correctos. validate_phase03.py con carpeta de salida separada: 20 layouts sin problemas, diez fixtures temporales, cero originales reales. Capturas reales de aplicación con percepción fallida y revisión persistente inspeccionadas en evidencias/fase03_1R/validacion; sin red ni cámara físicas. Resumen de cierre en evidencias/fase03_1R/cierre/unittest_summary.json.

Archivos y explicación completos en docs/VALIDACION_FASE03.md, sección Revisión externa 03.1-R. Nuevos dataset/storage.py y ui/video_source.py; modificaciones puntuales de Application, Dispatcher, captura/herramientas y UI. Control solo añade exclusión de captura y antigüedad de estado; sin cambios de protocolo, secuencias, heartbeat o STOP. La guía se actualiza para señalar qué descripciones históricas quedaron corregidas.

Git: commit único solicitado fix: corregir regresiones y robustecer vision y dataset, auditor del proyecto y Gitleaks antes de publicar solo feat/fase-03-vision. Se conserva PUBLIC y main=4bd6ba6; sin force ni merge. SHA final, auditoría y sincronización quedan en respuesta e informe local evidencias/fase03_1R/remote_verification.json tras verificarse. Privados, dataset, journals, respaldos, capturas y entornos no se publican.

Pendientes físicos sin cambios: alimentación y rueda al energizar, FL/ruedas/STOP/caducidad, brazo, cámara/HSV/ROI, marcadores impresos y captura real. CNN/difusa/heurística/autonomía pendientes. Entrega académica 30/11/2026; ninguna prueba de esta revisión autoriza acciones físicas.


## 19. Fase 03.3-C — Recuperación segura de comunicaciones (25/11/2026)

Registro v1.10. Base revisada a69eb0334620dae3f18cf0e9fbee0610b2de2960, feat/fase-03-vision inicialmente limpia y sincronizada 0/0. El operador reportó conexión ~20 s seguida de desconexión, con/sin video, vía ESP32-CAM-CARRO y Robot4WD_Diagnostico, incluso con baterías recién cargadas. No se atribuye causa física ni temporizador confirmado al fallo inicial.

Mediciones físicas aportadas por el operador, NO reproducidas en desarrollo: vía CAM principal 192.168.4.2, ICMP 20/20 media42/máx134 ms, segunda serie17/20 con3destinos inaccesibles/máx366; health15/15 máx~297; state timeout0.30 s20/20 máx453 y timeout1.0 s solo diagnóstico20/20 máx937. Directo192.168.10.1, ping29/30 media42/máx151; HTTP30/30 máx157. Serie state200 consultas autenticadas timeout0.30:197 válidas/3communication_lost en1,44,73;98.5%,p50 94/p95 312/máx422 ms; consultas inmediatamente siguientes correctas. Se conservan procedencia y límites en docs/COMUNICACIONES_Y_RECUPERACION.md.

Archivo privado leído al inicio ya guardaba timeout0.30 s y heartbeat0.25 s, avance legítimo respecto al histórico0.18; respaldo y comparación byte por byte idénticos al cerrar. Sin modificación de claves, direcciones, pulsos, servos, pines, firmware o arquitectura Wi-Fi. No contacto con hardware, movimientos ni carga de firmware en esta sesión.

Diagnóstico de código confirmado: el APIError invalidaba connected y el polling condicionado a connected dejaba de realizarse, sin recuperación suficiente. Se agrega supervisión desarmada automática tras la primera verificación explícita, en el mismo trabajador de despacho y sin colas de intentos. Estados separados: Sin verificar/Conectando/Conectado/Inestable/Perdida/Reconectando/Recuperada-desarmado/Remoto desconocido. Disponibilidad, frescura, autorización, remoto y STOP no se confunden.

Recuperación con health y state, autenticación/API1, espera0.5/1/2/3 s con tasa acotada y máximo3s entre intentos fallidos posteriores. No rearme automático ni reenvío de movimientos/activaciones. Fallo operativo conserva STOP inmediato, invalidación de generación/sesión y cancelación de cola; recuperación posterior usa lectura y no repite STOP ciegamente. Remoto inseguro/armado/ocupado solicita STOP prioritario y exige confirmar reposo. Respuestas de generaciones anteriores, cierre o configuración no pueden restaurar conexión. No nuevos trabajadores por reintento.

Transportes por propósito, mismo emisor/contador de secuencias: control y STOP connect/read configurados (0.30/0.30 en este equipo); heartbeat cada0.25 con connect/read<=0.15; recuperación sololectura desarmada connect<=0.30/read1.0. Requests no impone con ello un límite absoluto total. Se suspende telemetría periódica durante autorización armada, se conserva el supervisor anterior y se solicita STOP si no se confirma heartbeat durante0.75s. No se amplía caducidad firmware1200ms. No se presentan ángulos/PWM/ruedas viejos como actuales; incrementos sobre ángulo no reciente se rechazan y objetivos explícitos mantienen el protocolo. Validación temporal física pendiente.

State se fecha desde inicio de solicitud, sin ampliar frescura0.75s ni frame_max_age. Captura real exige conexión/estado reciente, reposo explícito y trabajador vivo, bloqueada durante pérdida/desconocimiento; ráfagas cancelables conservadas. Camera/Original permanecen independientes del control. Fallo interno no previsto enclava estado desconocido/cierre, sin filtrar texto arbitrario de excepciones ni crear reemplazos.

Métricas en ventana60s/hasta500 solicitudes: éxitos/fallos/tipos, p50/p95/máximo, respuesta válida/edad, contadores acumulados separados, errores consecutivos de supervisión/peticiones diferenciados, reconexiones, cortes y estado de STOP/remoto. Transiciones/cortes acotados. UIcompacta y detalles en Configuración→Mantenimiento; Exportar registros incluye comunicaciones.json sanitizado. Sin claves, cabeceras, challenge, sesión ni cuerpos arbitrarios. No una notificación por cada intento.

Nueva herramienta scripts/diagnose_communications.py: GET exclusivo health/state, IP/origen privado o loopback, cantidad/intervalo/timeout/JSON configurables, credenciales desde configuración sin mostrarlas ni guardarla. Se ejecutó solo --help y pruebas de función/CLI en loopback con clave ficticia. Fixture200 solicitudes con fallos1/44/73:197 válidas,3errores,3cortes, siguientes consultas correctas; evidencia local evidencias/fase03_3C/diagnostico_fixture_200.json. No representa validación física ni latencias de radio.

Regresiones: base115/115 en51.078s; primera integración115/115 en50.750s. Primera ampliación135 tuvo130aprobadas/4fallos/1error en98.546s; se corrigieron montajes nuevos de prueba y sobrecoste de layout/recorte de diagnóstico sin tocar115pruebas anteriores ni frescura. Después135/135 en72.969s,137/137 en59.015s,139/139 en63.719s y140/140 en58.921s. Cierre con fallo interno sanitizado y exportación diagnóstica:141ejecutadas/141aprobadas,0fallos/0errores/0omitidas,69.016s;115anteriores intactas y26nuevas. Resumen definitivo en evidencias/fase03_3C/final_publicacion/unittest_summary.json.

validate_phase03.py:20layouts sin problemas,10fixtures temporales/cero imágenes reales. Capturas inspeccionadas de conexión inestable, reconectando, recuperada/desarmada y diagnóstico con video activo, siempre fixture_prueba. Layout inicial resuelto antes del primer frame y paneles ocultos sin redibujado innecesario. compileall,pipcheck,BAT--smoke-ui correctos. Sin dependencias nuevas. Pruebas físicas pendientes independientes de estos resultados.

Documentación: README, docs/COMUNICACIONES_Y_RECUPERACION.md, docs/VALIDACION_FASE03.md y este registro conservando el historial. Commit separado fix: implementar recuperacion segura de comunicaciones; Gitleaks y auditor antes de publicar solo feat/fase-03-vision. PUBLIC conservado, sin force ni merge y main=4bd6ba6. Verificación de SHA/upstream/archivos públicos en evidencias/fase03_3C/remote_verification.json tras push. Ningún privado, log, dataset, respaldo o entorno se publica.

Siguiente puerta: operador verifica recuperación desarmada en ambas redes, con actuadores sin energía y corte físico, sin generadores de carga simultáneos; debe recuperarse supervisión, no sesión. Si STOP/remoto desconocido, mantener bloqueo y comprobar físicamente. Sigue pendiente causa Wi-Fi y rueda al energizar, alimentación/ruedas/brazo/cámara/HSV/ROI/ArUco impreso/dataset. CNN,difusa,heurística y autonomía pendientes. No avanzar fase ni autorizar movimiento por reconectar.

# Arquitectura de Fase 01

## Componentes y autoridad

`main.py` compone una sola aplicación. `Application` crea un `Dispatcher`, un `Controller`, una `Camera` y un servicio de captura del dataset. Tkinter contiene presentación y callbacks breves. No se usa la interfaz de V7 como base; se recuperaron sus diez patrones y límites validados en código, sin atribuirles validación física actual.

El flujo autorizado es interfaz → Controller/Command → Dispatcher → HTTPBridge → firmware. El despachador es el único asignador de secuencias para movimiento, servos y heartbeat. El firmware conserva límites físicos y su vigilancia propia. Los contratos de `ai/` no pueden emitir órdenes directamente. `Observation` representa valores desconocidos con `None`. La autonomía lanza `NotImplementedError` y el botón Iniciar está deshabilitado.

## Trabajadores y colas

- **Hilo Tkinter:** actualiza widgets cada 80 ms, consume eventos acotados y renueva la señal de vida del controlador. Renderiza únicamente el último frame de la pestaña visible. Nunca realiza solicitudes HTTP ni abre/cierra captura de cámara.
- **Despacho:** cola de 8 tareas, una solicitud ordinaria a la vez, heartbeat prioritario cada 250 ms y consulta de estado aproximadamente cada 350 ms. Descarta órdenes secuenciadas con más de 300 ms en cola. No espera físicamente a que termine un pulso; el firmware reporta ocupación y aplica interlocks.
- **Seguridad:** supervisión independiente cada 50 ms. Si el hilo de despacho muere o el controlador principal deja de actualizar su señal durante 650 ms, invalida autorización y solicita STOP. El heartbeat verifica la misma señal antes de enviarse; no renueva una sesión indefinidamente con la aplicación principal bloqueada.
- **STOP:** invalida sesión y generación local, cancela tareas pendientes y usa otro transporte HTTP en un hilo independiente. No espera a la cola ni al cliente ordinario bloqueado. Consulta state después para confirmar desarmado, ruedas apagadas y objetivos de servo congelados. Una carrera con armado tardío provoca otra parada. La clave nunca es necesaria para solicitar STOP, pero sí para confirmar state.
- **Cámara:** un trabajador FFmpeg con timeout de apertura/lectura configurable, reconexión espaciada y un solo slot protegido para el último frame. Cada reconexión reinicia FPS. Al detener elimina el frame y espera liberación; si el backend no termina, rechaza iniciar otro trabajador.
- **Archivos/ciclo de vida:** cola de 8 tareas para captura, CSV, configuración, exportación y apertura/cierre de cámara. Un mutex serializa estas tareas y el cierre. El cambio de configuración cancela autorizaciones, cierra transportes/cámara y crea componentes desarmados; no conserva conexión verificada.
- **Logging:** QueueHandler y QueueListener con cola de 2000 registros y archivo rotatorio de 1 MB, tres respaldos. No se registran cabeceras, URLs, cuerpos de red ni claves.
- **Percepción futura:** contratos `Vision`, `Classifier`, `FuzzyControl`, `Observation` y buzón de una observación. No hay trabajador de inferencia activo ni mediciones CNN en esta fase.

Todas las colas tienen capacidad fija. Los frames se reemplazan; no se acumulan ni se despachan movimientos atrasados como una secuencia de reproducción. Las tareas pendientes se cancelan por generación al detener. Las operaciones ya recibidas por firmware dependen también de su sesión y secuencia.

## Invariantes de seguridad

1. Arranque sin solicitudes ni autorización local; automático visible e inactivo.
2. Verificar requiere health compatible y state autenticado; nunca arma.
3. Armado explícito solo en modo manual, con controlador sano y sin STOP pendiente.
4. Drive/enable/servo requieren propietario manual, generación vigente, sesión y conexión verificadas. Un interlock rechazado consume secuencia y no provoca reenvío.
5. Cambiar entre Manual, Dataset y Automático detiene/desarma cuando existe conexión o una operación activa. Con sistema sin conectar solo invalida localmente; no emite solicitudes al cambiar pestañas de inicio. Configuración no modifica el propietario para poder diagnosticar.
6. Pérdida de enlace, rechazo de sesión, autenticación o protocolo invalidan la autorización. No se rearma al volver la red.
7. Liberación individual requiere confirmación explícita y estado remoto desarmado. STOP conserva PWM y no libera carga.
8. Control autónomo está totalmente bloqueado. La incorporación futura deberá condicionar la salud a video fresco, percepción e inferencia sanas; el bloqueo actual impide cualquier movimiento automático con o sin video.
9. Cerrar intenta STOP si hubo conexión, espera trabajadores y libera cámara. No envía solicitudes a un equipo nunca conectado.

`requests` impone timeout de conexión y de lectura, no tiempo real duro ni límite absoluto ante un servidor que entregue bytes indefinidamente. El supervisor y transporte STOP independiente reducen esta dependencia; el vencimiento físico sigue perteneciendo al firmware. Los timeouts FFmpeg dependen del backend instalado. Se informa si un trabajador no termina y se bloquea el reinicio correspondiente.

## Configuración, física y métricas

Configuración JSON validada y reemplazo atómico en archivo privado. Límites: garra 35–60°, base 35–115°, HOME 60°/75°, pulso 50–700 ms, ENA/ENB con jumper. Las referencias HOME no son configurables fuera del firmware; se pueden restringir intervalos que las incluyan. Patrones de dirección pueden editarse sin reflashear. No hay estimación automática de distancia por tiempo en esta fase.

Pines: FL 26/25, FR 33/32, RL 13/12, RR 14/27, garra 21, base 18. No se modifica firmware ni ESP32-CAM. GPIO12 requiere revisar comportamiento de arranque físicamente.

Se calculan FPS sobre hasta 31 recepciones, dimensiones y edad monotónica desde recepción. HTTP p50/p95 y última muestra usan hasta 500 solicitudes; no son percentiles de ejecución física. Tiempo del controlador mide servicio de una orden en Python, sin el tiempo de cola ni la finalización mecánica. Errores de comunicación se contabilizan. La vista inicial muestra N/D y nunca verde sin comprobación.

Objetivos futuros: 10–15 FPS, HTTP p95 ≤150 ms, inferencia p95 ≤100 ms y observación→envío p95 ≤300 ms. Ninguno se presenta como resultado físico. La edad del frame no mide latencia de exposición/codificación/transmisión.

## Decisiones y evolución

Se conserva el historial de la bitácora y se aplica su decisión más reciente (sección 13): aplicación nueva y API 1, por encima de propuestas previas de ampliar V7. La calibración V7 está vacía; 20.5 cm/350 ms permanece antecedente. La distribución del firmware del ZIP carece de credenciales intencionalmente; una copia local preconfigurada tenía una clave inferior al mínimo, por lo que esa copia no iniciaría la red sin corrección manual. No fue modificada.

Antes de implementar la autonomía: aprobar la puerta física, estabilizar video y entorno, capturar datos reales por sesiones y autorizar Fase 02. Después, implementar percepción e inferencia fuera del hilo gráfico, extender la señal de salud a esas etapas y probar primero mediante replay/simulación explícita.

## Presentación Fase 01.1 — 24/11/2026

La capa `ui/` utiliza tema claro, tokens comunes e iconos lineales propios. La navegación lateral se implementa mediante `PageStack`, compatible con `select/index` y el evento de cambio utilizado por las pruebas originales. Solo se muestra la página activa. La selección invoca el mismo `Controller.change_mode` de la Fase 01; Configuración conserva el propietario actual. El botón STOP GLOBAL está en la cabecera, fuera de páginas y áreas desplazables.

Los formularios sustituyen al editor JSON y producen exactamente el schema existente, pasando por `validate` y `Application.update_config` sin cambios. `ui/preferences.py` conserva exclusivamente la meta visual del Dataset en `ui.local.json`, excluido de Git. `ui/dataset_view.py` lee originales existentes desde el manifiesto, excluye fixtures, faltantes, duplicados y rutas fuera del destino; prepara un thumbnail en el trabajador de archivos existente. No modifica `dataset/capture.py` ni genera entrenamiento.

`Card`, `Badge`, `Metric`, `Video`, `EventLog`, `ScrollFrame` y helpers de formulario/confirmación centralizan la presentación. El hilo gráfico conserva su señal de vida cada 80 ms y limita la telemetría a unos 240 ms. La conversión de video mantiene aspecto y descarta repintados del mismo ID/tamaño; no se crean widgets por fotograma. Las capturas de evidencia usan el identificador de la propia ventana, evitando incluir otras aplicaciones del escritorio.

Sin cambios en `app/`, `control/`, `hardware/`, `ai/`, `dataset/`, `firmware/`, `main.py` ni requisitos de ejecución. Tampoco se modificaron las 50 pruebas originales. La diferencia queda limitada a presentación, sus pruebas y documentación. Consultar `DESIGN_SYSTEM.md` y `VALIDACION_UI_FASE01_1.md` para geometría, contraste, evidencias y límites de escalado.

# Comunicaciones y recuperación segura — Fase 03.3-C

Fecha: 25/11/2026. Base revisada `a69eb0334620dae3f18cf0e9fbee0610b2de2960`, rama `feat/fase-03-vision`. No se contactó al robot ni ESP32-CAM durante el desarrollo, no se modificó firmware y la autonomía permanece deshabilitada.

## Diagnóstico confirmado en código

El despachador anterior consultaba state cada ~350 ms únicamente mientras `safety.connected` fuera verdadero. Un APIError ponía esa variable en falso, invalidaba la sesión y solicitaba STOP. No existía un ciclo que volviera a verificar health/state al quedar desconectado. Por tanto, un error transitorio podía dejar la supervisión desconectada indefinidamente aunque la siguiente consulta física hubiera tenido éxito. Esto explica el enclavamiento de la aplicación, **no demuestra la causa del fallo inalámbrico inicial ni un temporizador físico de 20 segundos**.

## Evidencia física comunicada por el operador

Los siguientes datos fueron aportados por el operador y no reproducidos por el agente. Fecha 25/11/2026, baterías recién cargadas, fallo similar con/sin video y mediante ambas redes:

- ESP32-CAM-CARRO, principal observado en 192.168.4.2: ICMP inicial 20/20, media 42 ms, máximo 134 ms. Segunda serie: 17/20 respuestas válidas, tres destinos inaccesibles y máximo 366 ms.
- health: 15/15, máximo aproximado 297 ms. state con timeout 0.30 s: 20/20, máximo 453 ms. state con timeout 1.0 s solo diagnóstico: 20/20, máximo 937 ms.
- Robot4WD_Diagnostico, principal 192.168.10.1: ping 29/30, media 42 ms y máximo 151 ms. Primera serie HTTP 30/30, máximo 157 ms.
- Serie prolongada autenticada: 200 consultas state, timeout 0.30 s, 197 satisfactorias y tres `communication_lost` en consultas 1,44,73; éxito 98.5 %, p50 94 ms, p95 312 ms, máximo satisfactorio 422 ms. Las consultas inmediatamente posteriores fueron satisfactorias.

Son observaciones compatibles con interrupciones transitorias. No permiten atribuir causa a radio, alimentación, firmware, servidor, cliente o interferencias. El problema ocurre también sin video y con conexión directa; no se cambió la arquitectura inalámbrica por inferencia.

La configuración privada leída al comenzar esta revisión ya guardaba **timeout 0.30 s y heartbeat 0.25 s**, avance legítimo del operador respecto al registro histórico de 0.18 s. Se respaldó localmente y permaneció idéntica byte por byte. El ejemplo público conserva sus defaults; esta corrección no reescribe el archivo privado ni cambia parámetros de control.

## Estados y autoridad

La disponibilidad de enlace, la frescura de state, la sesión local, el armado remoto y la confirmación de STOP son datos separados. `control/communication.py` mantiene un registro acotado de transiciones y cortes, sin autoridad para crear sesiones.

- **Sin verificar:** inicio; no se abre conexión ni se programa recuperación antes de una verificación explícita.
- **Conectando:** verificación solicitada por el operador, health y state autenticado/versionado.
- **Conectado:** identidad válida y estado suficientemente reciente; inicialmente desarmado/en reposo para admitir supervisión segura.
- **Conexión inestable:** primer fallo de supervisión; autorización invalidada y estado no utilizable. No tolera movimientos durante el fallo.
- **Comunicación perdida:** fallos consecutivos; se conservan reintentos espaciados y movimiento bloqueado.
- **Reconectando:** intento de lectura en curso. No es confirmación de conexión ni de reposo.
- **Conexión recuperada / desarmado:** health/state válidos, recientes y reposo lógico confirmado; cola anterior descartada y sesión local cero. Después vuelve a Conectado. Armar requiere otra acción explícita.
- **Estado remoto desconocido:** falta confirmación utilizable, hay estado armado/ocupado inesperado o STOP no confirmado. No habilita captura real ni armado.

Secuencia típica: Conectado → primer error/Conexión inestable → STOP prioritario e invalidación → Reconectando → Recuperada/desarmado si las lecturas son válidas. Fallos sucesivos llevan a Comunicación perdida; un STOP fallido puede destacar Estado remoto desconocido. El diagnóstico conserva las transiciones aunque la interfaz compacta muestre solo la actual. La cámara tiene estado propio y puede seguir mostrando frames frescos con control desconectado.

## Política de recuperación

Se reutiliza **el mismo trabajador de Dispatcher**: no hay otro emisor de órdenes, cola de reconexiones ni trabajadores creados por intento. Después de la primera solicitud explícita de verificación, la recuperación desarmada permanece habilitada hasta cierre/configuración. Consultas: health sin clave y state con la clave local existente. Se validan Robot4WD 1.0.0/API 1, estructura de estado y autenticación.

Espera progresiva después de cada intento fallido: **0.5, 1, 2 y 3 s**, manteniendo máximo 3 s entre intentos posteriores. Es una supervisión continua con tasa acotada, no un número infinito de solicitudes pendientes: solo hay un intento en curso y se espera desde su finalización. Cada intento hace como máximo health y state. Un fallo de recuperación no reenvía movimientos ni repite STOP a ciegas; mantiene la autorización invalidada. Si se obtiene un estado armado, ocupado, en mantenimiento, con direcciones/objetivos no seguros, solicita STOP por el canal prioritario y exige otra comprobación de reposo.

El primer fallo operativo conserva el comportamiento conservador: pone conexión en falso, invalida generación/sesión, cancela órdenes pendientes y solicita STOP inmediato, incluso si había sesión armada. Los resultados de health/state de generaciones anteriores o recibidos después del cierre/suspensión se descartan. Una respuesta antigua no puede volver a marcar connected=True. El armado y la activación/movimiento de actuadores **nunca se reintentan automáticamente**.

STOP mantiene su transporte y trabajador propios. ACK y state de confirmación se distinguen; si falla, se muestra No confirmado. Si después solo una lectura válida prueba reposo, se informa «Reposo confirmado por lectura; STOP previo sin confirmar», sin inventar recepción del comando. Cambiar configuración suspende recuperación e invalida la generación inmediatamente, antes de esperar la tarea de ciclo de vida. Si la cola de trabajos rechaza la configuración, se reanuda la supervisión anterior y se limpia `reconfiguring`. Cerrar cancela nuevos intentos; una llamada HTTP ya en curso debe terminar o vencer antes de cerrar su transporte.

## Timeouts y heartbeat

No se cambiaron el timeout privado de control ni heartbeat, pulsos, servos o caducidad firmware de **1200 ms**. Se separan sesiones/transporte por propósito, pero **Dispatcher sigue siendo el único asignador de secuencias y autorización**:

- Control y STOP: connect/read usan cada uno el timeout efectivo configurado; en este equipo **0.30/0.30 s**.
- Heartbeat: connect/read usan cada uno `min(timeout_control,0.15 s)`. Se mantiene intervalo objetivo **0.25 s**, sin ampliar la vigencia del firmware.
- Recuperación exclusivamente de lectura desarmada: connect `min(timeout_control,0.30 s)`, read **1.0 s**. El transporte rechaza cualquier acción distinta de health/state.
- Diagnóstico independiente: timeout solicitado por operador para ambas fases; solo GET health/state.

Los timeouts Requests son por conexión/lectura, **no un límite absoluto de duración total**. Una respuesta exitosa puede exceder 0.30 s, y el envío gradual de bytes puede mantener una lectura durante más tiempo. No se garantiza tiempo real ni cancelación instantánea de un socket bloqueado.

Durante sesión armada se **suspenden las consultas periódicas de telemetría** y se prioriza heartbeat en el único trabajador. Verificar de nuevo exige detener antes. El supervisor independiente invalida y solicita STOP si no hay confirmación de heartbeat durante **0.75 s**, aunque la UI siga dando señal de salud. Sigue vigente también la vigilancia anterior del controlador. Esto es conservador; no vuelve tolerable un fallo durante movimiento ni certifica tiempo de parada físico.

Consecuencia visible: sin telemetría reciente no se muestran posiciones/PWM/ruedas antiguas como actuales; el ACK de armado se identifica como tal. Los controles de objetivo explícito conservan el protocolo y sus interlocks. Un ajuste incremental basado en un ángulo antiguo se rechaza: no se calcula usando datos obsoletos. Se requiere detener y recuperar state para volver a disponer de esa referencia. Esta decisión evita retrasar heartbeat para aparentar telemetría continua.

## Frescura y dataset

El límite de state sigue siendo **0.75 s**, contado desde **el inicio de su solicitud**, no desde la recepción. Una respuesta correcta de 0.9 s demuestra disponibilidad pero no constituye estado reciente para conexión segura/captura. El transporte de recuperación puede esperar más para diagnosticar, sin ampliar la frescura ni generar permiso.

La captura real conserva guardas 03.1-R: conexión verificada, desarmado y reposo explícitos, sin mantenimiento/sesión/órdenes activas, cámara nueva/fresca y mutex de almacenamiento. Comunicación perdida o estado desconocido impiden captura. Las ráfagas comprueban estas condiciones durante la espera y al guardar, y se cancelan cuando dejan de cumplirse. No se guarda una ráfaga aprovechando un estado anterior al corte. La imagen original de Camera sigue siendo independiente del enlace de control y de percepción.

## Métricas e interfaz

Ventana móvil de **60 s**, hasta 500 solicitudes: éxitos/fallos, tipos de error, p50/p95 y máximo de solicitudes satisfactorias, última latencia, edad de última respuesta válida. Se conservan totales acumulados separados. Por protocolo válido se entiende estructura/API aceptada; su frescura se informa aparte y puede impedir utilizar state. Los fallos consecutivos de supervisión se mantienen hasta recuperar un estado utilizable; `consecutive_request_errors` distingue la secuencia de peticiones individuales. Así, health exitoso seguido de state fallido no oculta una recuperación todavía fallida.

También se registra número de recuperaciones, duración del corte actual/último, hasta 100 cortes/transiciones, motivo categorizado y estado de STOP/remoto. Categorías: conexión, connect_timeout, read_timeout, autenticación, configuración, protocolo/respuesta inválida y respuesta demasiado antigua. No se almacenan cabeceras, clave, cuerpo arbitrario, URL privada ni texto de excepciones Requests en métricas.

La barra lateral y el footer presentan estado compacto y separan cámara/ESP32. Los detalles están en **Configuración → Mantenimiento**, en Seguridad, registros y diagnóstico. Los reintentos no generan una notificación por cada consulta. La UI solo actualiza los paneles técnicos visibles y resuelve su layout inicial antes de recibir frames, preservando el presupuesto de frescura. STOP permanece accesible, incluido Escape.

Exportar registros agrega `comunicaciones.json` con la instantánea sanitizada (métricas, cortes, transiciones, estado remoto y STOP), junto a los logs locales. Su destino permanece bajo `evidencias/`, excluido de Git. Los datos del diagnóstico no contienen clave, cabeceras, challenge ni ID de sesión.

## Herramienta de diagnóstico reproducible

`scripts/diagnose_communications.py` solo admite health/state, orígenes HTTP privados o loopback y credenciales cargadas del archivo privado. No guarda la configuración ni envía STOP, armado, movimiento o servos. Parámetros: `--address`, `--count`, `--interval`, `--timeout`, `--endpoint`, `--output`. Cantidad 1…10000, intervalo 0.05…60 s y timeout 0.05…5 s. Valores amplios son diagnósticos y no alteran control/firmware. La espera entre consultas comienza después de finalizar la anterior.

Ejemplos **para ejecución posterior por el operador**, no ejecutados contra hardware durante esta revisión:

```powershell
.\.venv\Scripts\python.exe scripts\diagnose_communications.py --address 192.168.10.1 --endpoint state --count 200 --interval 0.5 --timeout 0.30 --output evidencias\diagnostico_directo.json
.\.venv\Scripts\python.exe scripts\diagnose_communications.py --address 192.168.4.2 --endpoint health --count 30 --interval 1 --timeout 1 --output evidencias\diagnostico_health_camara.json
```

El JSON incluye resultados individuales, tiempos, categoría de error, resumen, duración de cortes, interrupción/cantidad completada y solo estado remoto mínimo. No incluye clave, challenge, sesión, direcciones de configuración o cabeceras. Ctrl+C guarda las muestras completadas. El diagnóstico no rearma, recupera autorización ni sustituye la aplicación de control. En desarrollo solo se ejecutó --help y pruebas de CLI/función contra loopback con credenciales ficticias.

## Validación física posterior y pendientes

1. Resolver o contener físicamente alimentación y giro al energizar; actuadores sin energía para esta comprobación de comunicaciones, robot desarmado, corte físico accesible. Esta corrección no repara el arranque eléctrico.
2. Confirmar red/IP actual sin asumir DHCP permanente; abrir aplicación y verificar explícitamente. Registrar estado inicial y diagnóstico, sin armar ni habilitar servos.
3. Ejecutar serie de lectura indicada arriba en cada red, primero con video detenido y después activo, anotando condiciones, FPS y errores. No ejecutar múltiples generadores de carga simultáneamente para evaluar la recuperación normal.
4. Con el robot desarmado, interrumpir/restablecer deliberadamente Wi-Fi. Observar Conexión inestable/perdida → Reconectando → Recuperada/desarmado, sesión local cero, cola descartada y reposo lógico reciente. Confirmar que no hace falta pulsar Verificar para recuperar supervisión y que **no se rearma**.
5. Si aparece Estado desconocido o STOP no confirmado, conservar bloqueo y comprobar físicamente; no usar la reconexión como permiso. Revisar tiempos, duración de corte y motivo en Mantenimiento/exportación local. Una respuesta de state lenta puede ser válida para diagnóstico y rechazada para captura: comprobar esa diferencia.
6. Verificar video independiente cuando la cámara siga accesible y bloqueo/cancelación de captura real durante el corte. Guardar evidencia local sin publicar credenciales ni dataset.
7. Pruebas armadas de heartbeat, pulsos y parada física requieren autorización y puerta física independientes; no forman parte de esta implementación. No aumentar TTL firmware ni los tiempos de seguridad para ocultar errores de radio.

Pendientes: causa del fallo inalámbrico inicial, validación real de reconexión/STOP y rendimiento con ambas redes, alimentación/rueda de arranque, ruedas/brazo, cámara/HSV/ROI, marcadores impresos y dataset real. CNN, difusa, heurística y autonomía siguen pendientes; no se avanzó de fase.

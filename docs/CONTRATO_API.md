# Robot4WD 1.0.0 / API 1

Fuente: `Robot4WD_Firmware_V1.zip`, sketch y LEEME originales inspeccionados el 24/11/2026. SHA-256 del sketch distribuido: `a4ca67346103487ca02e28da7caf10967dcf15aad5a11a7f4e70bf9b2b306cd6`. Copia sin cambios en `firmware/`. PythonBridgeV6 no es compatible.

## Transporte

HTTP local. Respuesta JSON con `ok`, errores con `ok:false,error:<identificador>`. `Cache-Control: no-store`. Todos los endpoints salvo health y stop requieren cabecera `X-Robot-Key`. Mutaciones mediante POST con formulario `application/x-www-form-urlencoded`; el firmware también admite parámetros de query, pero este cliente siempre usa formulario. No enviar JSON como cuerpo de órdenes.

GET `/api/health`: público. Devuelve `firmware:"Robot4WD"`, `version:"1.0.0"`, `api_version:1`, `sta_connected` y `ok:true`. El cliente rechaza otra identidad o versión.

GET `/api/state`: autenticado. Campos: `api_version`, `armed`, `maintenance`, `reason`, `challenge`, `last_seq`, `motor_activo`, `motor_remaining_ms`, `directions` en orden FL/FR/RL/RR, `garra`, `base`, `garra_objetivo`, `base_objetivo`, `servo_garra_activo`, `servo_base_activo`, `brazo_ocupado`, `heartbeat_remaining_ms`, `sta_connected`, `sta_ip`, `diag_ip`, `ok`. GET state no renueva la sesión. Los ángulos son comandos PWM, no sensores.

POST `/api/arm`: `challenge` uint32 obtenido de state. Solo desarmado, sin mantenimiento ni motor. Devuelve `session` uint32 y `lease_ms:1200`. No activa actuadores. Rota challenge; nunca se repite automáticamente.

POST `/api/heartbeat`: `session,seq`. Renueva la sesión por 1200 ms. Intervalo recomendado 250 ms. Ambos enteros positivos uint32; una sola fuente asigna secuencias estrictamente crecientes.

POST `/api/drive`: `session,seq,fl,fr,rl,rr,ms`. Cuatro signos -1/0/1, al menos uno diferente de cero. Duración 50–700 ms. Rechaza motor activo, servo ocupado o menos de 50 ms desde detener ruedas. No renueva pulso ni heartbeat. ENA/ENB con jumper: velocidad fija, sin PWM de velocidad.

POST `/api/servo/enable`: `session,seq,nombre` (`garra` o `base`). Activación individual a HOME (60° o 75°). Puede provocar salto físico. Asentamiento lógico inicial 800 ms. Si ya está activo, devuelve éxito sin repetir activación. Rechaza nueva activación con ruedas o servos ocupados.

POST `/api/servo`: `session,seq,nombre,grado`. Garra 35–60°, base 35–115°. Requiere servo activado y actuadores libres. Paso máximo 2° cada 65 ms; al alcanzar objetivo, asentamiento lógico 200 ms. ACK acepta objetivo; no certifica movimiento físico ni agarre.

POST `/api/stop`: sin clave, sesión ni secuencia. Apaga ruedas, congela objetivos de servo en último ángulo ordenado, desarma, elimina sesión/secuencia y rota challenge. Conserva PWM de servos. Devuelve `ok:true,armed:false`. El cliente consulta state mediante su transporte independiente antes de indicar parada confirmada. Un ACK perdido o sin state válido deja parada no confirmada.

POST `/api/release`: `nombre,confirm=1`, autenticado, sin sesión ni secuencia. Requiere desarmado, motor apagado y fuera de mantenimiento. Quita PWM individualmente. Confirmación humana con brazo/carga apoyados es obligatoria en UI.

## Secuencias, errores y caducidad

Los comandos secuenciados válidos consumen `seq` incluso si el interlock los rechaza. Parámetros inválidos detectados antes de `acceptCommand` no la consumen. El cliente incrementa localmente sin reutilizar números; puede haber saltos, nunca retroceso. No reintenta movimiento ni redirecciona solicitudes. `requests.Session` reutiliza conexión cuando el servidor lo permite y no configura reintentos automáticos.

- 400: parámetros requeridos o límites inválidos, confirmación faltante.
- 403: `unauthorized`.
- 409: `not_armed`, `invalid_session`, `old_sequence`, `cannot_arm`, `invalid_challenge`, `actuators_busy`, `servo_not_enabled`, `stop_before_release`, `servo_attach_failed`.
- 404: ruta desconocida.

El firmware vigila desde una tarea FreeRTOS separada: fin de pulso, vencimiento de heartbeat a 1200 ms y cambio de generación STA. STOP no es un corte eléctrico. La aplicación aplica timeout inicial de conexión/lectura de 180 ms, configurables entre 50 y 300 ms, y nunca rearma automáticamente. Un fallo de comunicación invalida permiso local y solicita STOP; ante estado incierto el operador verifica y puede cortar alimentación.

## Simulador

Implementa las mismas acciones y formas de parámetros, autorización, challenge, sesión, secuencias, ocupación, pasos/asentamiento de servo, deadtime, STOP y caducidad. Su reloj es inyectable en pruebas. El tiempo se evalúa al consultar o actuar; no contiene sensores ni reproduce detalles eléctricos, planificación FreeRTOS, OTA o comportamiento de radio. `online=False` permite inyectar pérdida de enlace en pruebas. El mismo motor simulado atiende el despacho normal y el STOP bajo mutex, sin red. Las pruebas del cliente HTTP utilizan un servidor exclusivamente en loopback para comprobar los mensajes reales.

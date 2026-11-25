# Objetivos locales del brazo — Fase 03.4-R

Fecha: 25/11/2026. Se conservan GPIO21 para garra, GPIO18 para base; garra 35°–60°, base 35°–115°, HOME base 75°. El firmware permanece intacto. El operador reportó ambos servos funcionales; las comprobaciones de esta entrega usan simulador, sin accionar hardware.

En Manual → Base → **Objetivo…**, prepare un ángulo absoluto con el campo, slider, presets 35/55/75/95/115 o pasos ±1°/±5°. Slider, pasos y presets del diálogo solo editan el borrador: **Enviar** es la acción que solicita el movimiento. Los botones explícitos existentes Centro 75° y Abrir/Cerrar conservan su solicitud directa. Nunca se envían movimientos al abrir el diálogo.

Primero verifique conexión y arme explícitamente con la zona despejada. Activar requiere confirmación y puede ir a HOME según firmware. Espere a que termine el asentamiento antes de solicitar otro objetivo: un rechazo `actuators_busy` no se reintenta. Enviar registra el objetivo aceptado solo después de un ACK en la sesión y generación vigentes. Activar por sí mismo no se toma como una medición ni como un ACK de objetivo HOME: podría ser una activación idempotente de un servo ya conectado.

El texto **ACK objetivo** expresa la última orden aceptada, nunca posición medida, movimiento terminado o agarre. La telemetría sigue suspendida durante sesiones armadas. Los pasos usan un borrador introducido explícitamente o una referencia ACK vigente; sin referencia requieren escribir un ángulo o elegir preset. Un error invalida la referencia aceptada, al igual que STOP, pérdida de conexión, recuperación, cambio de sesión, liberación o configuración. Un ACK tardío después de STOP no puede restaurarla. Después de invalidación vuelva a establecer un objetivo explícito.

Para identificar el sentido real, apoye el brazo, despeje el área, pruebe desde un objetivo seguro con pasos pequeños y registre la observación en el campo del diálogo. No se presupone que incrementar grados sea girar a la derecha. Esta anotación es local al diálogo, no cambia los patrones ni los límites. No ensaye extremos si el montaje real no los permite: los presets no son una certificación mecánica.

STOP GLOBAL y Escape están disponibles en el diálogo. STOP conserva la política anterior del firmware; no desconecta alimentación ni garantiza que el PWM del servo se libere. Para Liberar, desarme, espere reposo, sujete brazo/carga y confirme. No se amplían límites ni se ejecutan barridos automáticos.

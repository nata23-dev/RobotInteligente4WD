# Consolidación y publicación — Fase 02.1

Fecha: 24/11/2026. Proyecto: Robot Inteligente 4WD. Repositorio existente: [nata23-dev/RobotInteligente4WD](https://github.com/nata23-dev/RobotInteligente4WD). Entrega académica: 30/11/2026.

## Decisión de visibilidad y autorización

La solicitud inicial exigía repositorio privado. La consulta inicial mediante la integración GitHub devolvió `visibility:public`, propietario `nata23-dev`, nombre correcto, permisos `push/admin` y repositorio vacío. Se detuvo la publicación y se informó al propietario. Su instrucción posterior fue **«Dejemoslo publico»**. Esa decisión sustituye el requisito inicial de privado; se conserva el repositorio público existente, sin cambiar visibilidad ni crear otro.

No se publican credenciales aunque el repositorio sea público. No se conceden permisos a aplicaciones externas. No se usa force push, mirror ni publicación de todas las ramas/tags.

## Estado inicial y estrategia Git

Árbol de trabajo inicialmente limpio. Dos commits: `68ebbe0` (Fase 01) y `46e20f8` (Fase 01.1). `main` apuntaba al primero y `ui/fase-01-1` al segundo. Sin etiquetas ni remoto. No se encontró implementación adicional o commit independiente de Fase 02: se registran las verificaciones físicas parciales comunicadas por el operador, no una funcionalidad nueva inventada.

Se configuró `origin` con `https://github.com/nata23-dev/RobotInteligente4WD.git`. `git ls-remote --heads origin` y fetch no encontraron ramas iniciales; no existían README/licencia ni contenido remoto que integrar. Se avanzó `main` con `git merge --ff-only ui/fase-01-1`, conservando los dos commits y la rama visual local. Solo se prepara `main` para publicación. Se conservó un bundle local de todas las referencias previas y copias privadas de configuración/bitácora en `.tools/backups/`, ignoradas por Git.

Git 2.53.0.windows.1 disponible. `gh` no estaba instalado. Se utilizó la integración GitHub para metadatos y Git Credential Manager ya configurado con la cuenta `nata23-dev` para transporte Git, sin extraer ni imprimir sus tokens. Un push `--dry-run` confirmó acceso de escritura, sin publicar objetos. Un endpoint adicional de permisos de colaborador devolvió 403 por alcance de la integración; no invalida los permisos `push/admin` de los metadatos ni la comprobación del transporte Git. No fue necesario solicitar credenciales al usuario ni instalar GitHub CLI.

## Estado real del software

Fase 01 implementada: aplicación modular única, HTTP API 1, clave, challenge/sesión/secuencias, heartbeat, despacho central, STOP independiente, vigilancia, cámara concurrente, JSON persistente, simulador, logs y captura de originales PNG con CSV. Fase 01.1 implementada: tema claro, navegación lateral, cuatro secciones y configuración mediante formularios.

Automático sigue mostrando un visor original/procesado pendiente, módulos de IA sin resultados ficticios, ocho etapas y controles autónomos deshabilitados. No se realizó el nuevo rediseño centrado en cámara. Manual, Dataset y Configuración permanecen funcionalmente iguales; no se cambió arquitectura, pines, protocolo ni firmware.

CNN, difusa, heurística, procesamiento estructurado y navegación ArUco son contratos/estados pendientes. Dataset tiene captura individual y presentación, no ráfagas, ROI ni divisiones definitivas. Entrenamiento/modelos no están implementados. La operación real requiere validación física; no se deduce seguridad eléctrica de las pruebas del simulador.

## Observaciones del operador y diferencias con archivos

La bitácora registra los avances comunicados: firmware 1.0.0/API 1 instalado, SSID correcto `ESP32-CAM-CARRO`, principal DHCP observado `192.168.4.2`, cámara `192.168.4.1`, diagnóstico `192.168.10.1`; HTTP autenticado, stream/control simultáneos, MJPEG 320×240 aproximadamente 10–12 FPS, orientación incorrecta cercana a 90° y p95 32–47 ms durante algunas pruebas estables. Son reportes del operador, no mediciones realizadas en esta consolidación.

La configuración privada efectivamente guardada coincide con las URLs reportadas y heartbeat 0.25 s, pero contiene **timeout 0.18 s**, frente al ajuste 0.30 s comunicado. Se preservó sin modificar. Los patrones adelante/atrás siguen iguales a los de V7 y coinciden con los signos provisionales reportados; FL requiere confirmación. No se cerraron formalmente ocho sentidos ni detención automática.

El firmware rastreado permanece como distribución original, con credenciales vacías y SSID histórico. Una copia histórica de Documentos también se preservó localmente, pero no coincide con la clave/SSID reportados actualmente. No se presenta como la fuente exacta del binario instalado. No se cambió, compiló ni cargó firmware; corresponde recuperar su fuente funcional privada en la siguiente comprobación del operador.

La bitácora y algunos documentos históricos decían Fase 02 pendiente o cámara no probada. Se conservó el historial y se añadieron datos actuales con procedencia explícita. README y plan físico remiten al estado vigente y a [PLAN_FASE03.md](PLAN_FASE03.md), sin implementar esa fase.

## Pruebas actuales y corrección de consolidación

Se ejecutaron todas las pruebas existentes con Python 3.12.10 x64 del entorno del proyecto y un cerco adicional que permite solo loopback para el servidor HTTP de pruebas y bloquea la apertura de la cámara física. La configuración real no se sustituye en disco ni se utiliza para accionar hardware.

Primera ejecución: **62 ejecutadas, 61 aprobadas, 1 fallida, 0 errores y 0 omitidas, 15.484 s**. Falló `test_controller_failure_does_not_renew_forever`. Su espera comprobaba que el texto contuviera `confirmada`, condición que también satisface `no confirmada`: podía evaluar `armed` antes de que el hilo STOP completara su solicitud.

Se fortaleció la espera para exigir exactamente `Parada confirmada (estado lógico)` y se conservó la aserción de firmware desarmado. No se alteró la lógica funcional ni se relajaron tiempos, límites o aserciones. Ejecución posterior de las 62 existentes: **62/62, 14.906 s**. Tras añadir tres pruebas del auditor: **65 ejecutadas, 65 aprobadas, 0 fallidas, 0 errores y 0 omitidas, 17.094 s**. Los tiempos son de ejecución local; las cifras históricas de 50/62 no se tomaron como garantías.

Las tres pruebas nuevas usan repositorios Git temporales con valores sintéticos generados en memoria: verifican detección de un secreto histórico codificado aunque el árbol actual esté limpio, inspección del índice diferente del archivo actual, rutas privadas/plantillas y ausencia del valor en el reporte. No debilitan las pruebas del robot.

Regresión final después de consolidar documentación y exclusiones: **65/65, cero fallos/errores/omisiones, 16.797 s**, con los mismos bloqueos de hardware. La revisión de diferencias confirmó que aplicación, UI, control, comunicación, firmware, pines, requirements e instaladores permanecen intactos respecto a `46e20f8`. `git fsck --full` no informó corrupción; señaló blobs sueltos no alcanzables, que se conservaron y no forman parte de las referencias publicadas.

Comandos:

```powershell
.\.venv\Scripts\python.exe scripts\check_software.py --output evidencias\consolidacion_2026_11_24
.\.venv\Scripts\python.exe -m compileall -q app ui hardware control ai dataset tests scripts main.py
.\.venv\Scripts\python.exe -m pip check
.\INICIAR_APLICACION.bat --smoke-ui
.\.venv\Scripts\python.exe scripts\audit_publication.py
```

Las cuatro secciones se abrieron y capturaron en simulación, sin órdenes al inicio. STOP GLOBAL permaneció visible y confirmó estado lógico en el simulador. `compileall`, `pip check` y el inicio por BAT resultaron correctos. Instalador revisado: usa 3.12 x64/venv, dependencias bloqueadas y errores visibles; no se reinstalaron paquetes globales. No hubo cambios en requirements; el entorno sigue correspondiendo al lock.

Evidencias locales: `evidencias/consolidacion_2026_11_24/`. Se conservan primera ejecución y fallo, resumen final, capturas nuevas, GUI y salidas. Las evidencias anteriores no se eliminaron ni sobrescribieron. Los informes se guardan fuera del índice para no publicar información privada accidentalmente.

## Auditoría de secretos

Gitleaks **8.30.1**, portátil bajo `.tools/`, obtenido del repositorio oficial y ZIP verificado contra sus checksums SHA-256. Escaneo con redacción completa, sin allowlists para ocultar hallazgos. Primera revisión de ambos commits existentes: cero detecciones. Se revisan nuevamente historial y staging antes de publicar.

Complemento específico `scripts/audit_publication.py`: todas las referencias locales o refs explícitas, blobs históricos alcanzables, metadatos commit/tag, índice y archivos publicables del árbol de trabajo. Compara, solo en memoria, las credenciales actuales del robot y referencias privadas, incluyendo representaciones UTF-8/UTF-16, URL y Base64. No obtiene tokens de Git/GitHub. Los informes identifican archivo/tipo/ubicación/estado, nunca valor, snippet ni fingerprint de la clave. Las plantillas y firmware público no contienen claves reales conocidas.

`.gitignore` amplía protección de `.env`/variantes, secretos locales del firmware, certificados/claves, compilados, cachés, builds y metadatos del editor. Se conservan ejemplos. Configuración privada, entornos, backups, ZIPs originales, logs, imágenes/manifiestos, modelos y evidencias permanecen locales. No se elimina material por quedar ignorado, y se revisa el índice/historial por separado porque ignorar no retira un archivo ya rastreado.

Limitaciones: patrones genéricos y valores locales conocidos no prueban ausencia de secretos desconocidos; no se auditan píxeles de capturas porque no se publican. No se publica ningún ZIP ni binario. Las referencias alcanzables a publicar pasan el escaneo; no se reescribe historial ni se eliminan referencias. Si apareciera una credencial histórica, el push debe detenerse y requerir decisión del propietario para saneamiento/rotación.

## Bloqueos físicos y siguiente fase

Probable descarga de baterías/caída de tensión sin medición confirmatoria; alternativas: regulación insuficiente, alimentación compartida, conexiones o reinicios. El giro breve de una rueda al encender es incidencia prioritaria. Pines transitorios/strapping, entradas L298N indefinidas, jumpers y secuencia de alimentación son hipótesis, no diagnósticos. Resolver desde energización, no solo después de `setup()`, antes de permitir autonomía.

Pendientes: FL y ocho sentidos, parada física y vencimiento exactos, calibración de desplazamientos, brazo, agarre/transporte/depósito, orientación/calidad de cámara, nuevo Automático, visión, dataset, CNN, difusa, heurística e integración. El código queda preparado para revisión externa y planificación de Fase 03; no para movimiento autónomo. Fase 03.1–03.4 solo se documentaron.

## Publicación y comprobación

La rama estable prevista es `main`, con todo el historial local preservado y sin publicar `ui/fase-01-1` por separado. El commit de consolidación se publica únicamente después de auditoría y pruebas. La comprobación posterior contrasta `HEAD`, `origin/main` y `git ls-remote`, vuelve a consultar visibilidad/propietario/rama en GitHub y lee archivos del remoto. El resultado se incorpora a la bitácora y al informe local de verificación; no basta con que push termine correctamente.

La visibilidad correcta en esta tarea es **PUBLIC por instrucción posterior del propietario**. No se debe describir la publicación como privada. Al ser público, puede revisarse sin conceder acceso a terceros; una integración conectada puede requerir selección del repositorio por su propietario, pero esta tarea no modifica esos permisos.

### Verificación efectuada — 24/11/2026

Se publicó [00bf0b52307e2a2706b60da98c611388cb34a445](https://github.com/nata23-dev/RobotInteligente4WD/commit/00bf0b52307e2a2706b60da98c611388cb34a445), mensaje `chore: consolidar fase 02 y preparar repositorio seguro`. `HEAD`, `origin/main` y `git ls-remote` coincidieron, con upstream `origin/main` y divergencia 0/0. Única rama remota: `main`; la rama visual se conserva solo localmente.

GitHub y una consulta REST sin credenciales confirmaron propietario `nata23-dev`, visibilidad PUBLIC y rama predeterminada `main`. Se leyó el README público sin autenticación y sus bytes coincidieron con el blob local. La integración leyó README, bitácora, entrada, prueba de despacho, informe y configuración de ejemplo desde el commit publicado. El árbol remoto contenía 75 archivos, con fuentes, pruebas, documentación y ejemplos requeridos; sin configuraciones privadas ni entornos. Auditor específico de `origin/main`: tres commits/76 blobs únicos revisados, cero hallazgos conocidos. Gitleaks sobre esos tres commits y staging: cero detecciones.

Este registro documental se agrega después de esa comprobación, preservando el commit verificado. El último hash posterior se comprueba otra vez frente al remoto y se entrega en el informe final al propietario; la verificación local queda en `evidencias/consolidacion_2026_11_24/remote_verification.json`. No hubo accionamiento ni comunicación con el hardware físico.

# Bitácora de despliegue en Producción

**Fecha de ejecución:** 26 de septiembre de 2026. **Instancia nueva:** distinta de QA. **Primera release desplegada:** `22ee1ece314a857dc855378c24d4dbc15aaef0e1`, etiqueta `qa-verde-videojuegos-22ee1ec`, con ocho etapas en verde y 19/19 pruebas en QA. Los incidentes siguientes son de preparación y conectividad del destino; no se desplegó el parche vulnerable ni se corrigió código de la aplicación en Producción.

| Fase / observación real | Diagnóstico y acción | Comprobación posterior |
|---|---|---|
| Instancia recién creada: `docker: command not found`, Compose y Git ausentes | Se instalaron Docker Engine y Git en Amazon Linux 2023 y el plugin Compose; el usuario `ec2-user` obtuvo acceso a Docker. | En la EC2 nueva se observaron Docker Engine 25.0.16 y Compose v5.5.1; el repositorio se clonó desde el tag aprobado en HEAD `22ee1ec`. |
| Preparación de la base separada: existía el rol `foro_prod` pero no la base `foro_prod` | Se comprobó ese estado desde QA con el administrador del RDS y se creó solo la base faltante, propiedad del rol previsto. No se atribuye una causa no observada a la creación parcial del rol. | Conexión con `foro_prod` a la base `foro_prod` y permiso para crear tablas confirmados. |
| Transferencia por SSH a la nueva EC2: `Connection timed out` al puerto 22 | Cambió la IP pública del cliente y el grupo de seguridad solo admitía la anterior. Se autorizó la nueva IP para SSH y acceso web. | La conexión SSH respondió; `scp -3 -p` transfirió `.env`, el manifiesto y las imágenes completas. Las reglas antiguas deben revisarse al cerrar el despliegue. |
| Primera solicitud de salud justo después de `docker compose up`: `curl: (56) Recv failure: Connection reset by peer` | La API aún aparecía `health: starting`. El mismo comando reintentó sin modificar código ni configuración. | `/salud` devolvió HTTP 200, `entorno=produccion`, PostgreSQL y S3 `ok`; ambos contenedores terminaron `healthy`. Se registra el transitorio, sin llamarlo falla persistente. |
| Verificador del host: falta `httpx` en el Python de la EC2 | Se creó un entorno virtual separado en el host y se instaló `httpx==0.28.1`. La aplicación ya disponía de su dependencia dentro de la imagen aprobada. | `pipeline/verificar_produccion.py` pasó primero 11/11 con base vacía, y después **12/12** con la reseña y el detalle disponibles. El log original 12/12 está archivado en [`reportes/entrega_final/verificacion_produccion_22ee1ec.log`](../reportes/entrega_final/verificacion_produccion_22ee1ec.log); los logs originales 11/11 y 12/12 también permanecen en el destino. |

## Actualización: promoción del diseño gamer

Se detectó antes de desplegar que el verificador de Producción buscaba el texto literal sin acento `Resenas publicadas`, mientras la portada rediseñada empleaba otro texto. El selector se corrigió en QA para usar el identificador estable `id="titulo-publicaciones"` (commit `9424272`); después se reconstruyeron/validaron las imágenes en QA y se repitió el pipeline completo: ocho etapas `OK` y 19/19 pruebas. Esto fue una corrección del **verificador en QA**, no una reparación de la aplicación en Producción.

Se transfirieron el manifiesto y ambos tar de `9424272` al destino. Sus SHA-256 coincidieron con el manifiesto de QA. El tag aprobado se descargó en la EC2 de Producción, se cargaron las imágenes y se ejecutó `docker compose up -d --no-build --pull never`. El contenedor API pasó de la imagen original `sha256:ee1546ddd03dedbcde2b0d162c9759f59ac16f83751a76a0109cf49d212b48b3` a `sha256:8afbda2d22c83af6b6c8f2350c8091dbc7a7f978fb7c2ac6b714472c59615a96`; el moderador mantuvo `sha256:34e2181a7df3797d8a0e4b5cca8d0a37a6caf75bd8eec1f8644c58e450c4e9c9`. Durante el arranque hubo un `Connection reset by peer` transitorio, seguido de `/salud` HTTP 200 y ambos contenedores `healthy`. El verificador de destino terminó **12/12**; [log original archivado](../reportes/entrega_final/verificacion_produccion_diseno_gamer_9424272.log). No se observó un defecto de aplicación que exigiera corregir código en Producción. El respaldo de `22ee1ec` permanece disponible.

## Actualización: Pulso Pixel v2

La interfaz Pulso Pixel v2 se preparó y ejecutó en QA sobre el commit `0ec86bb`. El [pipeline verde](../reportes/pipeline_verde_pulso_pixel_v2.txt) confirmó ocho etapas `OK` y 19/19 pruebas. Se verificaron en el destino los hashes y Image IDs del [manifiesto de QA](../reportes/entrega_final/manifest_pulso_pixel_v2.json) antes de activar los contenedores con `docker compose up -d --no-build --pull never`. La release anterior quedó disponible como respaldo.

El primer bloque de activación terminó antes de completar la espera de salud. El diagnóstico posterior, sin cambiar código ni configuración, confirmó ambos servicios sanos, la imagen API esperada y respuestas HTTP 200 de salud, portada y detalle. El [verificador original archivado](../reportes/entrega_final/verificacion_produccion_pulso_pixel_v2_0ec86bb.log) pasó **12/12** controles. No se observó un defecto de código en el destino.

QA respaldó de forma privada y retiró de su base 75 publicaciones y 45 comentarios generados por el pipeline después de archivar la evidencia. Se conservaron cuatro publicaciones ajenas a las pruebas y 17 adjuntos privados; Producción no participó en la limpieza.

## Veredicto y límites

Los tar recibidos coincidieron por SHA-256 con el manifiesto de QA; los Image IDs cargados coincidieron con los examinados en QA. Se ejecutó `docker compose up -d --no-build --pull never`. La API, RDS, S3 y moderador respondieron correctamente; la vista moderada rechazó sesión anónima (HTTP 403). Dos cuentas de demostración produjeron una reseña y cuatro comentarios; la portada mostró un extracto y solo tres comentarios, y el detalle mostró el contenido completo y los cuatro comentarios.

No se observó un defecto de código de aplicación en Producción que exigiera nueva remediación. Se usa HTTP sobre `8080`, restringido al cliente configurado en el grupo de seguridad; HTTPS está pendiente. No se incluyen contraseñas, contenido de `.env` ni URL de base en esta bitácora.

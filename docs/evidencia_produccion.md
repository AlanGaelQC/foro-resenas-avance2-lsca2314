# Evidencia de Producción — Entrega Final

**Estado verificado:** 27 de septiembre de 2026. Producción funciona en una **EC2 nueva**, distinta de la instancia de QA. Los identificadores de recursos y direcciones de acceso se conservan en las capturas privadas para la entrega académica.

## Release actual: imágenes y formulario (a2123c5)

El candidato `a2123c5ee46aed07dc066bb8cfd3ff62241f9184`, etiqueta `qa-verde-imagenes-a2123c5`, pasó las [ocho etapas y 27/27 pruebas en QA](../reportes/entrega_final/pipeline_imagenes_a2123c5.log), con árbol limpio y [veredicto PERMITIDO](../reportes/entrega_final/veredicto_imagenes_a2123c5.json). El [manifiesto](../reportes/entrega_final/manifest_imagenes_a2123c5.json) registra los Image IDs y hashes SHA-256 de ambos tar. Se transfirieron y verificaron estos artefactos y la etiqueta aprobada en la EC2 de Producción. Las imágenes se cargaron sin reconstrucción; el checkout quedó en el commit aprobado, y los contenedores `api` y `moderador` ejecutaron exactamente las imágenes examinadas en QA.

El [log original de Producción](../reportes/entrega_final/verificacion_produccion_imagenes_a2123c5.log), copiado a QA, registra **16/16** controles: checkout e imágenes correspondientes al manifiesto, hashes de los tar, contenedores saludables, RDS, S3, moderador, autorización, portada, detalle y acceso anónimo a la imagen de una reseña publicada. La respuesta de `/salud` indicó `entorno=produccion`, base de datos y S3 `ok`. Permanecen disponibles los tar y el manifiesto de `8d1b742` como respaldo. El commit posterior de evidencias no sustituyó el código aprobado.

Las mejoras de imagen y formulario no transfieren las publicaciones de QA a Producción: las bases de datos son distintas. El despliegue creó la tabla de control de envíos en la base de Producción; las reseñas existentes permanecieron. El verificador acredita lectura de una imagen pública; no sustituye una captura visual de las pantallas ni una prueba manual de publicación nueva.

## Promoción histórica: Pulso Pixel v2 (0ec86bb)

El candidato `0ec86bb`, fijado por la etiqueta `qa-verde-pulso-pixel-v2-0ec86bb`, pasó [ocho etapas y 19/19 pruebas en QA](../reportes/pipeline_verde_pulso_pixel_v2.txt), con árbol limpio y [veredicto PERMITIDO](../reportes/entrega_final/veredicto_pulso_pixel_v2.json). El [manifiesto](../reportes/entrega_final/manifest_pulso_pixel_v2.json) registra hashes SHA-256 e Image IDs de las dos imágenes. En el destino se verificaron los hashes de ambos archivos y que los contenedores activos usaran exactamente los Image IDs aprobados. No se reconstruyeron imágenes allí.

Tras el arranque, la comprobación de solo lectura observó ambos contenedores sanos; salud, portada y detalle de una reseña existente respondieron HTTP 200. El [log original del verificador](../reportes/entrega_final/verificacion_produccion_pulso_pixel_v2_0ec86bb.log), copiado desde el destino, terminó **12/12** y comprende integridad, entorno, base de datos, S3, moderador y autorización. La release anterior se conservó para reversión.

Después de archivar la evidencia se limpiaron **75 reseñas y 45 comentarios** creados por el pipeline **solo en QA**; cuatro publicaciones ajenas permanecieron, entre ellas una reseña de videojuegos. Un respaldo privado y 17 adjuntos de prueba en S3 se conservaron para permitir recuperación. Esta limpieza no modificó los datos del destino ni el veredicto QA archivado.

Nota histórica de esa promoción: posteriormente se incorporaron capturas de QA y Producción al PDF académico entregado por separado. Son capturas del proceso, no una captura nueva de la release `a2123c5`; el verificador tampoco sustituye la inspección visual.

## Segunda promoción: diseño gamer (histórica)

El 26 de septiembre de 2026 se activó en la misma EC2 de Producción el commit `94242727087285c0e7c26e9eb71ce5fef5b336dd`, etiqueta `qa-verde-diseno-9424272`. En QA se observaron ocho etapas `OK`, árbol limpio y **19/19** pruebas; ver [`pipeline_verde_diseno_gamer_9424272.txt`](../reportes/pipeline_verde_diseno_gamer_9424272.txt) y el [veredicto](../reportes/entrega_final/veredicto_diseno_gamer_9424272.json). El cambio del verificador de Producción se hizo en QA antes de repetir el pipeline; el resultado anterior `22ee1ec` se conserva como primera promoción y respaldo.

| Control | Resultado observado |
|---|---|
| Origen e integridad | [Manifiesto de QA](../reportes/entrega_final/manifest_diseno_gamer_9424272.json) ligado a `9424272`; `api.tar` SHA-256 `36a5f37b27aa95cb0d5589952ed94c6881ba897f9193b492412f58a7c1195075` y `moderador.tar` SHA-256 `8e31bbb21d2d72b0cc337b5e0cc4d2dd39858e29027cd37e6386b53bac6bb4ba`, ambos comprobados en Producción. |
| Imágenes | API `sha256:8afbda2d22c83af6b6c8f2350c8091dbc7a7f978fb7c2ac6b714472c59615a96`; moderador `sha256:34e2181a7df3797d8a0e4b5cca8d0a37a6caf75bd8eec1f8644c58e450c4e9c9`. Los contenedores activos coincidieron con estos IDs; no se reconstruyeron en el destino. |
| Salud | Ambos servicios `healthy`; `/salud` HTTP 200 con `entorno=produccion`, PostgreSQL y S3 `ok`; portada HTTP 200. La primera petición durante el arranque recibió un `Connection reset by peer`; el reintento respondió HTTP 200 y se confirmó `healthy`. |
| Verificación | [`verificacion_produccion_diseno_gamer_9424272.log`](../reportes/entrega_final/verificacion_produccion_diseno_gamer_9424272.log) registra **12/12** controles con reseña y detalle existentes, incluidos integridad de imágenes, servicios y acceso anónimo denegado a la vista de moderador. El original permanece archivado en la EC2 de Producción. |
| Respaldo | Se conservaron los tar y el manifiesto originales en el destino para la reversión. Durante esa segunda promoción, el checkout del destino fue el tag aprobado `qa-verde-diseno-9424272`; la rama de evidencias contiene commits posteriores. |

La dirección pública puede cambiar tras reiniciar la EC2. Esta nota pertenece a la promoción histórica: la plantilla académica recibió después capturas del proceso. El resultado del verificador no sustituye la comprobación visual de una versión concreta.

## Primera promoción: 22ee1ec (histórica)

### Trazabilidad de la release

| Control | Evidencia observada |
|---|---|
| Candidato de videojuegos aprobado **en QA** | `22ee1ece314a857dc855378c24d4dbc15aaef0e1`, etiqueta `qa-verde-videojuegos-22ee1ec`; pipeline completo `PERMITIDO`, **8/8** etapas y **19/19** pruebas. Ver `reportes/pipeline_verde_videojuegos.txt`, `reportes/entrega_final/veredicto_videojuegos.json`. El commit posterior que archiva estos reportes no cambia las imágenes de esta release. |
| Artefactos aprobados | `reportes/entrega_final/manifest_videojuegos.json` conserva el manifiesto generado en QA. En el destino se verificaron SHA-256 de ambos tar y sus Image IDs antes de iniciar los contenedores. |
| API | Image ID `sha256:ee1546ddd03dedbcde2b0d162c9759f59ac16f83751a76a0109cf49d212b48b3`; SHA-256 de `api.tar`: `ed9b0fc24fff53e9e7e7e3a9ae8518f4648151781c74cc80bda268598aa9ed7b`. |
| Moderador | Image ID `sha256:34e2181a7df3797d8a0e4b5cca8d0a37a6caf75bd8eec1f8644c58e450c4e9c9`; SHA-256 de `moderador.tar`: `5fdb728e760185122e1b1d65966b24e3991b088f0b46ded6e909bfccda471ebf`. |
| Promoción | Se transfirieron `.env`, manifiesto y tar por `scp -3 -p`; `docker image load` restauró las imágenes. Durante la primera promoción, el destino ejecutó el checkout aprobado en `22ee1ec` y se utilizó `docker compose up -d --no-build --pull never`. **No se reconstruyó el código en Producción.** |
| Aislamiento de configuración | `ENTORNO=produccion`, base y usuario PostgreSQL `foro_prod` separados de la base `foro` de QA, `PREFIJO_S3=produccion/adjuntos/`; mismo RDS y bucket, con claves de sesión y moderador propias. El archivo `.env` en Producción tiene permisos `600`; no se publica. |
| Salud y autorización | Contenedores `api` y `moderador` `healthy`; `/salud` HTTP 200 (`entorno=produccion`, PostgreSQL `ok`, S3 `ok`), `/salud/dependencias` HTTP 200 (`moderador=ok`), portada HTTP 200, petición anónima a vista de moderador HTTP 403. |
| Verificador del destino | `pipeline/verificar_produccion.py`: **11/11** con base vacía, después **12/12** con reseña existente, incluido detalle. Log original del resultado **12/12**, transferido desde la EC2 de Producción y versionado en [`reportes/entrega_final/verificacion_produccion_22ee1ec.log`](../reportes/entrega_final/verificacion_produccion_22ee1ec.log). El original también permanece en el destino; el primer resultado 11/11 se conserva como antecedente. La comprobación del detalle valida HTTP 200; las capturas muestran además el conteo de cuatro comentarios. |

## Evidencia visual y límites

- Captura inicial de Producción: portada antes de publicar una reseña.
- Captura posterior: reseña de **Luis** sobre *Midnight Club 3* con cuerpo recortado; contador de **cuatro comentarios** y **solo tres visibles** en la tarjeta. Comentarios publicados por otra cuenta (**Angel**).
- Captura de detalle: autor, calificación y cuerpo completo; contador de **cuatro comentarios**. La imagen enviada muestra el comienzo de la lista: para evidenciar los cuatro, adjuntar también una captura al desplazarse hasta el final.
- Las capturas proporcionadas durante la ejecución se incorporaron después al PDF académico entregado por separado; no se versionaron como archivos de imagen en este repositorio. La captura de la aplicación en ese PDF corresponde a una release histórica, y los registros de QA y Producción documentan la promoción posterior de `a2123c5`. Para comprobar identificadores y estado actuales de las instancias, consultar la consola AWS.
- La vista previa enriquecida autorizada y el escape de XSS fueron verificados en QA. En Producción se verificó el acceso anónimo denegado y se comprobó que ambos Image IDs son idénticos a los de QA; el verificador actual **no realiza una prueba autenticada de XSS en Producción**.
- El sitio se sirvió por **HTTP** (`COOKIE_SEGURA=false`) en una IP efímera: hay un límite de transporte que debe indicarse en la entrega. El puerto 8080 está restringido a la IP cliente autorizada en el grupo de seguridad; HTTPS no se presenta como implementado.

Los errores reales de preparación y el reinicio transitorio de la API están en [bitacora_produccion.md](bitacora_produccion.md). Ninguno implicó publicar el parche vulnerable en Producción.

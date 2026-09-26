# Evidencia de Producción — Entrega Final

**Estado verificado:** 26 de septiembre de 2026. Producción funciona en una **EC2 nueva** (`i-089d62a1e8fdea7bb`, nombre interno `ip-172-31-30-151`, tipo `t2.small`); QA permanece en `i-05cc3223adae222ef`. La IP pública observada durante las capturas fue `98.81.185.30`, que puede cambiar al reiniciar la instancia.

## Trazabilidad de la release

| Control | Evidencia observada |
|---|---|
| Candidato de videojuegos aprobado **en QA** | `22ee1ece314a857dc855378c24d4dbc15aaef0e1`, etiqueta `qa-verde-videojuegos-22ee1ec`; pipeline completo `PERMITIDO`, **8/8** etapas y **19/19** pruebas. Ver `reportes/pipeline_verde_videojuegos.txt`, `reportes/entrega_final/veredicto_videojuegos.json`. El commit posterior que archiva estos reportes no cambia las imágenes de esta release. |
| Artefactos aprobados | `reportes/entrega_final/manifest_videojuegos.json` conserva el manifiesto generado en QA. En el destino se verificaron SHA-256 de ambos tar y sus Image IDs antes de iniciar los contenedores. |
| API | Image ID `sha256:ee1546ddd03dedbcde2b0d162c9759f59ac16f83751a76a0109cf49d212b48b3`; SHA-256 de `api.tar`: `ed9b0fc24fff53e9e7e7e3a9ae8518f4648151781c74cc80bda268598aa9ed7b`. |
| Moderador | Image ID `sha256:34e2181a7df3797d8a0e4b5cca8d0a37a6caf75bd8eec1f8644c58e450c4e9c9`; SHA-256 de `moderador.tar`: `5fdb728e760185122e1b1d65966b24e3991b088f0b46ded6e909bfccda471ebf`. |
| Promoción | Se transfirieron `.env`, manifiesto y tar por `scp -3 -p`; `docker image load` restauró las imágenes. El destino conserva el checkout del tag aprobado en `22ee1ec` y se ejecutó `docker compose up -d --no-build --pull never`. **No se reconstruyó el código en Producción.** |
| Aislamiento de configuración | `ENTORNO=produccion`, base y usuario PostgreSQL `foro_prod` separados de la base `foro` de QA, `PREFIJO_S3=produccion/adjuntos/`; mismo RDS y bucket, con claves de sesión y moderador propias. El archivo `.env` en Producción tiene permisos `600`; no se publica. |
| Salud y autorización | Contenedores `api` y `moderador` `healthy`; `/salud` HTTP 200 (`entorno=produccion`, PostgreSQL `ok`, S3 `ok`), `/salud/dependencias` HTTP 200 (`moderador=ok`), portada HTTP 200, petición anónima a vista de moderador HTTP 403. |
| Verificador del destino | `pipeline/verificar_produccion.py`: **11/11** con base vacía, después **12/12** con reseña existente, incluido detalle. Log original del resultado **12/12**, transferido desde la EC2 de Producción y versionado en [`reportes/entrega_final/verificacion_produccion_22ee1ec.log`](../reportes/entrega_final/verificacion_produccion_22ee1ec.log). También permanece en la EC2 en `/home/ec2-user/verificacion_produccion_con_resena_22ee1ec.log`; la primera corrida 11/11 está en `/home/ec2-user/verificacion_produccion_22ee1ec.log`. La comprobación del detalle valida HTTP 200; las capturas muestran además el conteo de cuatro comentarios. |

## Evidencia visual y límites

- Captura inicial de Producción: portada sin reseñas en `98.81.185.30:8080`.
- Captura posterior: reseña de **Luis** sobre *Midnight Club 3* con cuerpo recortado; contador de **cuatro comentarios** y **solo tres visibles** en la tarjeta. Comentarios publicados por otra cuenta (**Angel**).
- Captura de detalle: autor, calificación y cuerpo completo; contador de **cuatro comentarios**. La imagen enviada muestra el comienzo de la lista: para evidenciar los cuatro, adjuntar también una captura al desplazarse hasta el final.
- Las capturas fueron proporcionadas durante la ejecución; **aún deben insertarse en la plantilla oficial o versionarse en `docs/evidencias/`** antes de afirmar que están adjuntas al repositorio. Conviene que el encuadre incluya la URL y, en consola AWS, los Instance IDs de ambas EC2.
- La vista previa enriquecida autorizada y el escape de XSS fueron verificados en QA. En Producción se verificó el acceso anónimo denegado y se comprobó que ambos Image IDs son idénticos a los de QA; el verificador actual **no realiza una prueba autenticada de XSS en Producción**.
- El sitio se sirvió por **HTTP** (`COOKIE_SEGURA=false`) en una IP efímera: hay un límite de transporte que debe indicarse en la entrega. El puerto 8080 está restringido a la IP cliente autorizada en el grupo de seguridad; HTTPS no se presenta como implementado.

Los errores reales de preparación y el reinicio transitorio de la API están en [bitacora_produccion.md](bitacora_produccion.md). Ninguno implicó publicar el parche vulnerable en Producción.

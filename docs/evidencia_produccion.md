# Evidencia de Producción · pendiente de EC2 nueva

**Estado:** plantilla. No existe aún despliegue verificado de esta Entrega Final.

| Dato verificable | Evidencia a añadir |
|---|---|
| Instance ID de la EC2 **nueva** y fecha de creación | `[PENDIENTE-AWS]` captura consola y `aws ec2 describe-instances` |
| Commit y veredicto verde de QA | `[PENDIENTE-QA]` `veredicto.json`, fecha y carpeta de la corrida completa |
| Imágenes examinadas en etapa 06 | `[PENDIENTE-QA]` `06_image_ids.json` y manifiesto de empaquetado |
| Transferencia a Prod | `[PENDIENTE-AWS]` comprobación SHA-256 de tar antes de `docker image load` |
| Identidad de imágenes de Prod | `[PENDIENTE-AWS]` Image IDs exactos tras `docker image load`, cotejados con QA |
| Configuración separada | `[PENDIENTE-AWS]` `ENTORNO=produccion`, base/usuario y prefijo S3 distintos; no incluir secretos |
| Disponibilidad y navegación | `[PENDIENTE-AWS]` salud API/moderador, portada y detalle, capturas comparables a QA |
| Vista previa corregida | `[PENDIENTE-AWS]` solo moderador autorizado; texto XSS inerte y negritas funcionales |
| Errores observados | `[PENDIENTE-AWS]` referencia a cada registro en `bitacora_produccion.md`; si no ocurre ninguno, escribirlo con las comprobaciones que lo sustentan |

Los problemas de despliegue y configuración de la nueva EC2 se documentan allí. Los defectos de código descubiertos durante la verificación regresan a QA, se corrigen y exigen otra corrida verde completa antes de transferir nuevas imágenes.

La comprobación técnica preparada se ejecutará **en la EC2 de Producción** con
`python3 pipeline/verificar_produccion.py URL --manifest /ruta/manifest_release.json --tars /ruta/release`; requiere `httpx`, Docker e imágenes ya cargadas y falla si IDs, hashes o salud no coinciden. Comprobar el detalle de una reseña y la vista moderada con contenido de prueba exige disponer de esos datos y documentar sus resultados reales.

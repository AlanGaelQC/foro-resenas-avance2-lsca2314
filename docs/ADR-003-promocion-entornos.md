# ADR-003 — Promoción de artefactos y entornos QA/Producción

**Estado:** propuesto (andamio). Los detalles con `[PENDIENTE-AWS]` se cierran con
el inventario real del Learner Lab.

## Contexto

La Entrega Final exige dos instancias: QA (la del Avance 2) y una Producción
**nueva**. A Producción solo llega el código ya remediado y en verde. El defecto
del profesor se detecta y corrige en QA; los errores de despliegue del destino se
documentan allí.

## Decisión 1 — Construir una vez, promover la misma imagen

No se reconstruye en Producción (un `git clone` + rebuild podría traer
dependencias distintas y romper la identidad de lo probado). El flujo:

1. Construir las dos imágenes del candidato **antes** del pipeline completo en QA; la etapa 06 registra los Image IDs que examina Trivy.
2. `pipeline/promover.sh`: exige veredicto PERMITIDO en modo completo, commit y
   árbol actuales limpios, además de igualdad entre ambos Image IDs actuales y
   `reportes/06_image_ids.json` producido por la etapa 06. **No reconstruye**.
   Exporta con `docker image save`, calcula SHA-256 y escribe
   `reportes/manifest_release.json` con commit, tags, Image IDs y hashes.
3. `[PENDIENTE-AWS]` Transferir los `.tar` por SSH a la EC2 nueva, verificar
   hashes, `docker image load`, y `docker compose up` **sin build ni `:latest`**.
4. Comprobar que los Image IDs cargados coinciden con el manifiesto.

Se usa export/import porque no se presupone ECR. Si el Lab lo permitiera, se
podría usar un registro con digests sin cambiar el contrato. `[PENDIENTE-AWS]`
verificar disponibilidad de ECR. Un checksum detecta cambios de bytes, no
autentica quién aprobó: la confianza viene del canal, permisos y origen
controlado del manifiesto.

## Decisión 2 — Datos separados en un mismo RDS/bucket

`[DECISIÓN-ALAN]` Con permisos de estudiante, la ruta realista es **compartir**
la RDS/bucket del Avance 2 y separar por **base+usuario** (Producción) y
**`PREFIJO_S3` distinto** en S3, no crear una segunda RDS/bucket. Se documenta el límite: dos
bases en el mismo RDS no dan el aislamiento de dos servidores. No se copia el
`.env` de QA: Producción tiene su propia `CLAVE_SESION`, su usuario de BD, su
prefijo y `MODERADOR_PASS` propio. `[PENDIENTE-AWS]` comprobar que los permisos
permiten ese aislamiento.

## Decisión 3 — Verificación del destino (no reusar T1 de QA)

`pipeline/verificar_produccion.py` corre en la EC2 nueva y compara los Image IDs y SHA-256 de los tar con el manifiesto de QA. También exige `entorno == "produccion"` (T1 de QA exige
`"qa"` y fallaría siempre en Producción). Comprueba salud, BD, S3, conexión al moderador y vistas públicas; una inspección autorizada de contenido de prueba aún requiere una cuenta y reseña reales en la EC2 nueva. Un fallo
del destino marca la release como no aceptada aunque QA hubiera pasado; el error
se documenta en `docs/bitacora_produccion.md` y, si es de código, vuelve a QA
para un nuevo verde antes de re-promover.

## Decisión 4 — HTTPS

`[PENDIENTE-AWS/verificar]` Let's Encrypt emite certificados para direcciones IP
desde enero de 2026; su viabilidad en la EC2 (IP alcanzable en 80/443, IP
estable, renovación ~6 días) se comprueba. Si no es viable en el Lab, se documenta
HTTP como limitación (`COOKIE_SEGURA=false`), sin fingir HTTPS.

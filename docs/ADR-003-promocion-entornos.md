# ADR-003 — Promoción de artefactos y entornos QA/Producción

**Estado:** primera release de videojuegos `22ee1ec` aprobada y desplegada en la EC2 nueva `i-089d62a1e8fdea7bb`; promoción posterior del rediseño `9424272` (tag `qa-verde-diseno-9424272`) aprobada 8/8 y 19/19 en QA, verificada **12/12** en el destino el 26 de septiembre de 2026. Consultar [evidencia_produccion.md](evidencia_produccion.md) y [bitacora_produccion.md](bitacora_produccion.md).

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
3. Transferir los `.tar` por SSH a la EC2 nueva, verificar
   hashes, `docker image load`, y `docker compose up` **sin build ni `:latest`**.
4. Comprobar que los Image IDs cargados coinciden con el manifiesto.

Se usó export/import sin depender de ECR. La disponibilidad de ECR no se evaluó ni fue condición de la promoción. Un checksum detecta cambios de bytes, no
autentica quién aprobó: la confianza viene del canal, permisos y origen
controlado del manifiesto.

## Decisión 2 — Datos separados en un mismo RDS/bucket

La configuración aplicada comparte el RDS y el bucket del Avance 2, pero usa una **base y usuario propios** (`foro_prod`) y el **prefijo S3** `produccion/adjuntos/`. La aplicación en Producción comprobó acceso a RDS y S3; QA continúa usando la base `foro`. Dos bases dentro del mismo RDS no equivalen a dos servidores aislados. No se copió el `.env` de QA: Producción tiene `CLAVE_SESION`, `MODERADOR_PASS` y allowlist de moderadores propios. El archivo privado se transfirió con permisos 600.

## Decisión 3 — Verificación del destino (no reusar T1 de QA)

`pipeline/verificar_produccion.py` corre en la EC2 nueva y compara los Image IDs y SHA-256 de los tar con el manifiesto de QA. También exige `entorno == "produccion"` (T1 de QA exige
`"qa"` y fallaría siempre en Producción). Comprueba salud, BD, S3, conexión al moderador y vistas públicas; se comprobó el detalle de una reseña real creada en la EC2 nueva. La petición anónima a la vista moderada obtuvo HTTP 403; la prueba autenticada de escape XSS se ejecutó en QA sobre los mismos Image IDs, no en la instancia nueva. Un fallo
del destino marca la release como no aceptada aunque QA hubiera pasado; el error
se documenta en `docs/bitacora_produccion.md` y, si es de código, vuelve a QA
para un nuevo verde antes de re-promover.

## Decisión 4 — HTTPS

En esta ejecución no se configuró un certificado ni un dominio estable. El navegador accede por HTTP a `8080` y `COOKIE_SEGURA=false`; el acceso de red se limita a la IP cliente mediante el grupo de seguridad. HTTPS queda como trabajo posterior y se documenta como limitación, sin afirmar que se haya verificado su viabilidad en el Learner Lab.

# ADR-003 — Promoción de artefactos y entornos QA/Producción

**Estado:** se promovieron únicamente releases aprobadas en QA. La actual, **Pulso Pixel v2** (`0ec86bb`, tag `qa-verde-pulso-pixel-v2-0ec86bb`), obtuvo **8/8 etapas y 19/19 pruebas en QA** y **12/12 controles en el destino**. Las releases anteriores `22ee1ec` y `9424272` permanecen como antecedentes y respaldo. Consultar [evidencia_produccion.md](evidencia_produccion.md) y [bitacora_produccion.md](bitacora_produccion.md).

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
4. Comprobar que los Image IDs cargados coinciden con el manifiesto y, tras
   iniciar Compose, que `.Image` de cada contenedor activo coincide también.
   En los despliegues documentados esta segunda comprobación se hizo mediante
   comandos manuales; aún no forma parte del verificador de la release auditada.

Se usó export/import sin depender de ECR. La disponibilidad de ECR no se evaluó ni fue condición de la promoción. Un checksum detecta cambios de bytes, no
autentica quién aprobó: la confianza viene del canal, permisos y origen
controlado del manifiesto.

## Decisión 2 — Datos separados en un mismo RDS/bucket

La configuración aplicada comparte el RDS y el bucket del Avance 2, pero usa una **base y usuario propios** (`foro_prod`) y el **prefijo S3** `produccion/adjuntos/`. La aplicación en Producción comprobó acceso a RDS y S3; QA continúa usando la base `foro`. Dos bases dentro del mismo RDS no equivalen a dos servidores aislados. No se copió el `.env` de QA: Producción tiene `CLAVE_SESION`, `MODERADOR_PASS` y allowlist de moderadores propios. El archivo privado se transfirió con permisos 600.

## Decisión 3 — Verificación del destino (no reusar T1 de QA)

`pipeline/verificar_produccion.py` corre en la EC2 nueva y compara los Image IDs de los tags cargados y SHA-256 de los tar con el manifiesto de QA. También exige `entorno == "produccion"` (T1 de QA exige
`"qa"` y fallaría siempre en Producción). Comprueba salud, BD, S3, conexión al moderador y vistas públicas; se comprobó el detalle de una reseña real creada en la EC2 nueva. La petición anónima a la vista moderada obtuvo HTTP 403; la prueba autenticada de escape XSS se ejecutó en QA sobre los mismos Image IDs, no en la instancia nueva. Un fallo
del destino marca la release como no aceptada aunque QA hubiera pasado; el error
se documenta en `docs/bitacora_produccion.md` y, si es de código, vuelve a QA
para un nuevo verde antes de re-promover.

**Precisión de la auditoría del 27 de septiembre:** el script no consulta la
imagen del contenedor activo. Además, si no hay reseñas, omite la comprobación
del detalle y devuelve éxito con 11/11 y un aviso `PENDIENTE`. La corrida final
archivada sí tuvo una reseña y 12/12; las comprobaciones manuales verificaron
las imágenes en ejecución. Automatizar identidad y completitud sigue pendiente
en A-02 de la [revisión final](auditoria/revision_final_2026-09-27.md).

## Decisión 4 — HTTPS

En esta ejecución no se configuró un certificado ni un dominio estable. El navegador accede por HTTP a `8080` y `COOKIE_SEGURA=false`; el acceso de red se limita a la IP cliente mediante el grupo de seguridad. HTTPS queda como trabajo posterior y se documenta como limitación, sin afirmar que se haya verificado su viabilidad en el Learner Lab.

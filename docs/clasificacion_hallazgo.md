# Clasificación del hallazgo — Entrega Final

> **Estado:** hallazgo reproducido y remediado en QA el 2026-09-25; el
> candidato con la vista pública también pasó el pipeline completo en QA.

## Identificación

| Campo | Valor |
|---|---|
| Componente (render) | `app/moderador/formato.py` → `formatear_vulnerable()`, llamado en `app/moderador/main.py` endpoint interno `POST /vista-previa` |
| Frontera de acceso | `app/api/main.py` endpoint `POST /moderacion/resenas/{resena_id}/vista-previa` (autentica al moderador y hace proxy al servicio interno) |
| Origen del dato | El cuerpo de una reseña **guardada**, escrito por cualquier usuario del foro |
| Punto de interpretación | El servicio de moderación devuelve `HTMLResponse` sin escapar el contenido del usuario |
| Procedencia del defecto | Parche oficial `tema4_foro/vista_previa_resena.py` portado a FastAPI. SHA-256 del original **verificado, coincide**: `01b9b2d46ed7691baf83e2349750eb3ac51ab3d0cea8135652b8cd7fe3f5902a` |

## Tipo

**Cross-Site Scripting (XSS) almacenado, CWE-79.** Un usuario ordinario publica
una reseña cuyo cuerpo contiene `<script>…</script>`. Ese cuerpo se guarda. Cuando
un **moderador** abre la vista previa de esa reseña (por `resena_id`), el servicio
de moderación la renderiza a HTML **sin escapar**, por lo que el script del
atacante puede ejecutarse en su navegador —un actor con más capacidad—. Es
almacenado (no reflejado): el contenido malicioso vive en la base y lo
desencadena un tercero (el moderador) al verlo.

Verificado por HTTP local con dos identidades (ver `evidencia_local/`): en estado
vulnerable el `<script>` vuelve crudo; remediado, vuelve escapado.

## Severidad

**Alta** (hipótesis razonada; no se asigna un CVSS numérico ni "Crítica" sin
análisis del vector real):

- **Impacto:** ejecución de código en el navegador del moderador. La cookie de
  sesión es `HttpOnly` (`app/api/main.py` la marca así), por lo que **no** puede
  leerse directamente desde JavaScript; pero una XSS aún permite hacer peticiones
  autenticadas en el mismo origen y manipular el DOM. Esta aplicación no ofrece
  aprobación o rechazo manual por el moderador; no se le atribuyen esos permisos. El impacto no es "robo directo de cookie", es abuso de la
  sesión del moderador.
- **Facilidad de explotación:** el atacante solo necesita escribir una reseña con
  la carga; no requiere autenticación especial más allá de una cuenta de foro.
- **Condición necesaria:** que un moderador abra la vista previa de esa reseña.
  Verificado con dos identidades (autor ≠ moderador): no es un auto-ataque, es
  contenido de un tercero ejecutándose en la sesión del moderador.

## ¿Falso positivo?

No. La detección es real:

1. **DAST (la vía principal, independiente de la construcción):** las pruebas
   T10c/T10d/T10e en `pipeline/pruebas_flujo.py` ejercen el endpoint real con dos
   identidades y comprueban que el `<script>` del autor vuelve escapado. Falla en
   rojo, pasa en verde. Verificado por HTTP local (`evidencia_local/`).
2. **SAST (defensa localizada, no cobertura general):** la regla propia
   `foro-vista-previa-sin-escape` marca el uso de `formatear_vulnerable()` en
   `app/**/*.py` (1 ERROR en rojo, 0 en verde, verificado con semgrep). Se
   reconoce su límite: es un marcador del nombre de función, no un detector
   general de XSS; una concatenación directa en `HTMLResponse` no coincidiría. Por
   eso la vía que gobierna es la DAST.

**Corrida roja real en QA (2026-09-25 22:17–22:18 UTC):** el pipeline completo
sobre `84443a479c5a52c8efaab8ac49e2679f058d7b39` devolvió código **1** y
`BLOQUEADO`. La etapa **04** detectó un hallazgo `ERROR` de Semgrep; la etapa
**08** falló solo en T10d (17 de 18 pruebas pasaron). T10c confirmó que la cuenta
moderadora inició sesión y T10e que la vista conservaba la negrita; T10d obtuvo
HTTP 200 pero no el escape exigido del `<script>` procedente de otra cuenta.
Los controles 01, 02, 03, 05, 06 y 07 terminaron `OK`. Archivos:
`reportes/corridas/20260925T221825549474340Z-bloqueado/04_sast_semgrep.txt`,
`08_pruebas_flujo.txt` y `veredicto.json` en la misma carpeta. La prueba HTTP
inspecciona la respuesta, **no ejecuta JavaScript en un navegador real**; esa
es una limitación de la evidencia.

El campo `arbol: CON CAMBIOS SIN CONFIRMAR` de esta corrida se debe al borrado
temporal de los SBOM versionados antes de que el orquestador consultara Git;
los regeneró la etapa 07. Ese defecto del registro se corrigió en un commit
posterior, sin alterar la corrida histórica.

**Corridas verdes reales en QA:** sobre `30a764bedee0538abe0a0282a2cf8d1431ce24fa`
la remediación devolvió código 0 y `PERMITIDO` (18/18 pruebas; T10d y T10e
pasaron), archivada en
`reportes/corridas/20260925T224110120081948Z-permitido/`. Sobre
`ca2529a80c15563bb4dae031ab0a4dca0ae6ac2e` la vista pública también
devolvió código 0 y `PERMITIDO` (19/19 pruebas; T11 mostró tres comentarios
en la portada), archivada en
`reportes/corridas/20260925T235905408924320Z-permitido/`. Las ocho etapas
terminaron `OK` en ambas. El campo `arbol` aún se imprimió como modificado en
estas dos corridas, aunque `git status --short --branch` al terminarlas mostró
un HEAD sin modificaciones. El candidato `4333a32`, con el registro corregido,
obtuvo un tercer verde final: código 0, `PERMITIDO`, `arbol: limpio`, ocho etapas
`OK` y 19/19 pruebas el 2026-09-26 00:06:21 UTC. Véanse
`reportes/pipeline_verde.txt` y `reportes/entrega_final/veredicto_verde.json`.
El manifiesto histórico de `4333a32` está en
`reportes/entrega_final/manifest_release.json`; el commit posterior `bc539cb`
solo versiona su evidencia. La release vigente y su manifiesto se identifican
en [estado_release_actual.md](estado_release_actual.md); no se reutiliza el
veredicto histórico para un candidato distinto.

## Nota sobre la cobertura previa

La regla `foro-plantilla-sin-escape` del Avance 2 solo cubre plantillas `*.html`
(busca el filtro `|safe`). El parche portado se arma en Python con `HTMLResponse`
y **no** contiene `|safe`, por lo que esa regla **no** lo habría detectado
—verificado con la propia regex—. Esto es la "brecha de cobertura" que el propio
documento del profesor contempla: se documenta y se cierra con la regla nueva y
la prueba dinámica, en lugar de fingir que el pipeline ya lo cubría.

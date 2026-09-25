# Clasificación del hallazgo — Entrega Final

> **Estado:** borrador construido a partir del análisis del código. Los valores
> marcados `[pendiente-corrida QA]` se completan con la salida real del pipeline
> cuando se ejecute en QA; no se inventan.

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
de moderación la renderiza a HTML **sin escapar**, y el script del atacante se
ejecuta en el navegador del moderador —un actor con más capacidad—. Es
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

`[pendiente-corrida QA]` etapa que detuvo el pipeline completo, código de salida
y ruta del reporte de la corrida roja real sobre QA (con la app y la BD arriba).

## Nota sobre la cobertura previa

La regla `foro-plantilla-sin-escape` del Avance 2 solo cubre plantillas `*.html`
(busca el filtro `|safe`). El parche portado se arma en Python con `HTMLResponse`
y **no** contiene `|safe`, por lo que esa regla **no** lo habría detectado
—verificado con la propia regex—. Esto es la "brecha de cobertura" que el propio
documento del profesor contempla: se documenta y se cierra con la regla nueva y
la prueba dinámica, en lugar de fingir que el pipeline ya lo cubría.

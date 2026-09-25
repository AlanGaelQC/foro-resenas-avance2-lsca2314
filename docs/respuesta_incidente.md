# Respuesta a incidentes — Entrega Final

> Contención y prevención se documentan **por separado**, como pide el
> documento oficial. La contención frena el riesgo mientras se prepara el arreglo
> real; la prevención elimina la causa. Una no sustituye a la otra.

## 1. Contención inmediata (frenar el sangrado)

Acción que se aplicaría **ahora mismo**, antes de tener el arreglo de código
listo, para que el endpoint vulnerable no siga expuesto en QA:

- **Restringir el acceso al endpoint.** La vista previa exige estar en la lista
  `MODERADORES`; como contención adicional se puede vaciar esa lista
  temporalmente (`MODERADORES=`), con lo que la API responde 403 a todos y no hay
  a quién servirle el render vulnerable hasta que exista la corrección. Es
  reversible por configuración y no toca el código.
- Registrar inicio, responsable y comprobación de que el endpoint quedó
  inaccesible.

**Qué NO es contención suficiente:** dejar el endpoint apagado de forma
permanente no satisface la remediación —el requisito pide conservar la
funcionalidad—. La contención es temporal; el cierre real es la prevención.

## 2. Prevención (eliminar la causa raíz)

El arreglo de código que elimina la clase de falla, conservando la funcionalidad
pedida (negrita y saltos de línea):

- Cambiar la llamada del endpoint de moderación (`app/moderador/main.py`) de
  `formato.formatear_vulnerable()` a `formato.formatear_seguro()` — diff de una
  línea, verificado por HTTP local (rojo→verde).
- `formatear_seguro()` **escapa** todo el texto del usuario (`html.escape`) y
  **después** aplica el marcado permitido (negrita `**…**`, salto `\n`) sobre los
  segmentos ya escapados. Un `<script>` del usuario queda como `&lt;script&gt;`
  (texto inerte); `**bien**` sigue viéndose como **bien**.
- Verificado localmente: la versión segura escapa el `<script>` y conserva
  `<b>…</b>` y `<br>`. La regla SAST deja de marcar y la prueba DAST pasa.

**Por qué es prevención y no parche cosmético:** no se comenta ni se borra la
función, no se desactiva la regla ni se baja el umbral. Se corrige el
tratamiento del contenido, que es la causa. El diff de remediación puede tocar
más de un archivo (renderizador, endpoint, prueba) y eso es legítimo; el criterio
es que explique y elimine la causa.

## 3. Recuperación

- Rehabilitar el endpoint (restaurar la lista `MODERADORES`) ya con el
  renderizador seguro.
- Correr el pipeline completo en QA → verde.
- Promover a Producción la versión remediada (solo la que pasó verde).

## 4. Alcance observado

`[pendiente-corrida QA]` Qué se demostró exactamente (petición, respuesta,
contexto del moderador) y qué no. La reproducción académica no prueba que
hubiera usuarios reales comprometidos; se describe el vector, no un incidente
real de producción.

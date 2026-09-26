# ADR-002 — Vista previa del moderador y vista pública

**Estado:** implementado y validado funcionalmente en QA; tematización editorial pendiente de corrida completa.
**Contexto:** Entrega Final. El parche del tema 4 añade una "vista previa con
formato enriquecido para el moderador"; además el proyecto agrega una vista
pública tipo feed. Ambas se documentan aquí.

**Tema editorial:** reseñas de videojuegos escritas por jugadores. El título
del hilo identifica el juego y el cuerpo relata la experiencia; la nota de 1 a 5,
los adjuntos y los comentarios ya existían en el modelo. No se representa cada
juego como entidad distinta, ni se calcula una nota global por videojuego. La
referencia a plataformas de reseñas es funcional; no hay integración con Steam.

## Decisión 1 — Dónde vive el endpoint del parche

`PARCHE.md` pide integrar la vista previa **dentro del servicio de moderación** y
registrar la ruta con `resena_id`. Se cumple así (corrige una versión previa que
lo había puesto solo en la API):

- El **renderizado** (la lógica del parche, `formatear_vulnerable`/`seguro`) vive
  en `app/moderador/` con el endpoint interno `POST /vista-previa`. Ahí está el
  defecto. El servicio de moderación no publica el puerto 8001.
- La **API** expone `POST /moderacion/resenas/{resena_id}/vista-previa`: autentica
  y autoriza al moderador, carga la reseña por `resena_id`, y reenvía su cuerpo al
  servicio de moderación por la red interna de Docker (igual que ya hace con
  `/moderar`). La API es la frontera de autenticación; el moderador el back-end.

**Las dos interfaces son distintas, a propósito** (no son la misma ruta):
- Ruta **pública** (API): `POST /moderacion/resenas/{resena_id}/vista-previa`,
  autenticada, con `resena_id`. La API resuelve el `resena_id` → cuerpo de la
  reseña.
- Ruta **interna** (moderador): `POST /vista-previa`, sin autenticar (no publica
  puerto) y **sin `resena_id`**: recibe `{texto}` y devuelve HTML. El moderador
  no tiene base de datos ni conoce reseñas; por eso el `resena_id` vive en la API
  y el servicio interno solo renderiza texto. El parche original combina ambas
  cosas en un solo endpoint Flask; aquí se separan por la arquitectura de dos
  servicios, conservando `resena_id` en la frontera pública.

Así se respeta la ubicación y la interfaz del parche (servicio de moderación +
`resena_id`), sin exponer 8001 a Internet, y el `moderador` sigue sin acceder a
la base ni conocer usuarios (recibe texto, devuelve HTML). El porte de Flask a
FastAPI se documenta como adaptación de framework.

## Decisión 2 — Autorización del moderador (Opción A)

Un moderador es un usuario cuyo correo está en la variable de entorno
`MODERADORES` (lista por comas). La dependencia `_es_moderador()` exige **sesión
válida Y** pertenencia a la lista, comprobada en el servidor. Una sesión iniciada
por sí sola recibe 403.

**Cierre de la escalada de privilegios** (bug detectado en revisión): que un
correo esté en `MODERADORES` no basta, porque el registro público aceptaría a
quien lo reclamara primero. Por eso:

- El registro público **rechaza** (403) cualquier correo que esté en
  `MODERADORES`: quedan reservados.
- La(s) cuenta(s) de moderador se **aprovisionan al arrancar** (`_sembrar_moderadores`)
  con la contraseña de `MODERADOR_PASS`, de forma idempotente. Nadie puede
  reclamar ese correo por el formulario.

Sigue **sin** rol ni columna en la base (sin migración) y **sin** cola global: el
flujo de publicación automática no cambia. La prueba del pipeline usa esa cuenta
preaprovisionada (login con `MODERADOR_PASS`), no la registra.

Alternativas descartadas: cola humana con estado `pendiente_revision` (cambia el
flujo central y varias pruebas, sin exigirlo el parche); vista para el autor
(otra audiencia, no es la vista del moderador que pide F4).

**Alcance honesto:** la vista previa es la herramienta de inspección del
moderador; en un sistema real precedería a una aprobación humana. Aquí la
moderación automática sigue decidiendo la publicación. No se presenta un panel
posterior como si fuera una vista previa a la decisión.

## Decisión 3 — Renderizado seguro por segmentos

El renderizado NO usa el filtro `|safe` sobre contenido del usuario (verificado:
la regla SAST seguiría marcándolo, y quitar `|safe` de un string con `<b>` ya
mostraría las etiquetas como texto). En su lugar, `formatear_seguro()`:

1. Escapa todo el texto del usuario con `html.escape`.
2. Aplica negrita (`**…**` → `<b>…</b>`) y salto (`\n` → `<br>`) sobre el texto
   ya escapado, emitido por el servidor.

Así el marcado permitido lo controla el servidor y el contenido del usuario nunca
reintroduce etiquetas activas. Enlaces enriquecidos: **fuera de alcance** por
ahora; el parche solo pide negrita y saltos. Si se acuerdan, se validaría esquema
y se escaparían atributos, con pruebas aparte.

## Decisión 4 — Vista pública (feed)

La portada muestra doce reseñas por página, un extracto del cuerpo y, para cada
una, hasta tres comentarios publicados recientes. La consulta utiliza
`ROW_NUMBER() OVER (PARTITION BY hilo_id ...)` y filtra por posición en la base:
no descarga comentarios descartados. Los conteos se agrupan por reseña, y los
autores se cargan por lote. La vista de detalle muestra el texto íntegro y los
comentarios publicados. El paginado de comentarios del detalle queda como
límite declarado si el volumen lo exige; no se afirma que ya exista.

La publicación automática sigue siendo quien aprueba o rechaza la reseña. La
vista interna del moderador permite inspección autorizada sobre una reseña ya
guardada, pero el sistema no introduce una aprobación humana que no existe.

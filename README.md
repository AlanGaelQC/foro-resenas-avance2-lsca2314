# Pulso Pixel · Foro de reseñas de videojuegos · Entrega Final

Proyecto de **Herramientas de tecnologías de la información**, Tecmilenio (LSCA2314), tema 4: foro y reseñas. **Pulso Pixel** reúne opiniones de jugadores sobre videojuegos: cada persona puede escribir su reseña, calificarla de 1 a 5, añadir una imagen y conversar en los comentarios. Un segundo servicio aplica reglas de moderación antes de publicar. La Entrega Final introduce la vista previa enriquecida del moderador, demuestra y corrige una XSS suministrada en el parche del profesor, y añade una portada con extractos y tres comentarios por reseña. El título identifica el juego según lo escribe el autor; no existe catálogo de juegos ni puntuación agregada por videojuego.

**Estado verificado:** la vulnerabilidad XSS del parche se detectó y corrigió en QA. Producción ejecuta el código `a2123c5ee46aed07dc066bb8cfd3ff62241f9184`: [verificación 16/16](reportes/entrega_final/verificacion_produccion_imagenes_a2123c5.log), [veredicto de QA 8/8 y 27/27](reportes/entrega_final/veredicto_imagenes_a2123c5.json) y [manifiesto](reportes/entrega_final/manifest_imagenes_a2123c5.json). Consulta el [estado resumido](docs/estado_release_actual.md). Los commits posteriores archivan las evidencias sin cambiar el código aprobado.

**Diseño desplegado:** identidad Pulso Pixel, arte arcade original, reseñas de videojuegos y lectura compacta expandible del contenido largo. El commit que archiva esta documentación es posterior al commit aprobado para las imágenes. Los resultados históricos de las releases anteriores permanecen en los reportes archivados.

**Revisión final, 27 de septiembre:** la [auditoría con reproducciones locales](docs/auditoria/revision_final_2026-09-27.md) identifica cuatro familias de huecos en los controles automáticos. Sus correcciones se validaron en QA (8 etapas, 21 pruebas) y en Producción (15 controles). Los [diagramas actualizados](docs/arquitectura.md) muestran las dos EC2, el RDS/bucket compartidos y la promoción manual de los mismos artefactos.

**Alcance:** la experiencia se inspira en leer reseñas breves de videojuegos y abrirlas para ver todo el texto y la conversación, como ocurre en comunidades de jugadores. Es un foro propio: no usa cuentas, catálogo, votos de utilidad, horas jugadas ni API de Steam. Conserva la calificación de 1 a 5 del proyecto original.

**Funciones de la release actual:** el formulario exige 10 caracteres útiles en el cuerpo (el título no cuenta) y utiliza un identificador de envío para que reenviar exactamente el mismo formulario redirija al hilo creado. Las imágenes de reseñas publicadas también se muestran en «Mis publicaciones» y en los recuadros pequeños de la portada, manteniendo el fondo arcade. Las publicaciones duplicadas anteriormente no se borran automáticamente.

## Recorrido del usuario

1. Una persona se registra, inicia sesión y publica una reseña. El servicio `moderador` decide `publicado` o `rechazado` antes de guardarla. El autor puede consultar sus rechazos y el motivo.
2. La portada pública presenta hasta doce reseñas por página: título, autor, calificación, extracto del cuerpo, total de comentarios y **como máximo tres comentarios publicados** por tarjeta.
3. Al entrar a `/hilos/{id}`, una reseña larga se puede expandir para ver el cuerpo completo. También se ven la información pública del autor y todos los comentarios publicados. Ni los correos ni los motivos de rechazo se revelan en esas vistas.
4. Un moderador autorizado puede pedir la vista previa de una reseña guardada mediante `POST /moderacion/resenas/{id}/vista-previa`. La API verifica la sesión y delega el formato al servicio interno. No hay aprobación humana: la publicación sigue dependiendo de las reglas automáticas.

La selección de tres comentarios ocurre en PostgreSQL mediante `ROW_NUMBER() ... PARTITION BY hilo_id`; la portada pagina las reseñas. Jinja escapa el texto público y la vista del moderador, una vez remediada, escapa el texto **antes** de añadir `<b>` y `<br>`.

## Arquitectura y límites

| Componente | Responsabilidad | Acceso |
|---|---|---|
| `api` FastAPI | Web, sesiones, autorización, reseñas, RDS, adjuntos S3 | Puerto 8080 de cada EC2 |
| `moderador` FastAPI | Veredicto previo a publicación y renderizado enriquecido | Solo red interna de Docker, puerto 8001 |
| RDS PostgreSQL | Usuarios, reseñas, comentarios | 5432 únicamente desde el security group de la aplicación |
| S3 | Adjuntos privados con URLs firmadas | Permisos de la instancia, sin claves AWS en el repositorio |
| Pipeline de QA | Ocho controles; una decisión final bloqueante | Ejecutado sobre la instancia QA y el commit candidato |

QA usa la instancia del Avance 2. Producción es una **EC2 distinta de QA**; la release actual `a2123c5` siguió a las promociones históricas `22ee1ec`, `9424272`, `0ec86bb` y `8d1b742`, todas aprobadas en QA. Ambas instancias usan el mismo RDS y bucket: Producción se separó mediante base y usuario PostgreSQL `foro_prod` y prefijo S3 `produccion/adjuntos/`. Salud y conectividad se comprobaron en el destino; compartir servidor y bucket impone un límite de aislamiento. El diagrama y los flujos están en [docs/arquitectura.md](docs/arquitectura.md).

## Pipeline: la condición de promoción

| Etapa | Comprobación | Bloqueo |
|---|---|---|
| 01 | Secretos en código e historial (gitleaks) | Hallazgo o error operativo |
| 02 | Dependencias de Python (pip-audit) | Supera el umbral configurado |
| 03 | Patrones peligrosos de Python (bandit) | Supera el umbral |
| 04 | Reglas del foro y llamada vulnerable de la vista previa (semgrep) | ERROR |
| 05 | Infraestructura y contenedores (checkov) | Supera el umbral |
| 06 | Imágenes construidas (trivy) | HIGH/CRITICAL corregibles; registra Image IDs |
| 07 | SBOM CycloneDX de **ambos** servicios | Formato o inventario inválido |
| 08 | Pruebas HTTP de negocio, autorización, XSS y feed | Cualquier prueba fallida |

El orquestador `pipeline/orquestador.sh` corre **las ocho etapas aunque alguna falle**, deja `reportes/veredicto.json` y archiva cada corrida en `reportes/corridas/`. Un error de herramienta bloquea: no se interpreta como escaneo limpio. Antes de empaquetar, `pipeline/promover.sh` verifica el commit, el árbol limpio y que los dos Image IDs actuales coincidan con los que examinó Trivy en la etapa 06. **El empaquetado por sí solo no despliega:** la transferencia y verificación en la EC2 nueva quedaron comprobadas y constan en la evidencia de Producción.

### Hitos de QA

| Hito | Commit local | Comprobación |
|---|---|---|
| Parche del profesor portado **sin corregir** | `215be19` | Correr primero el pipeline original y conservar el resultado: es posible que no detecte XSS |
| Cobertura añadida | `84443a4` | La regla y T10d deben bloquear por la falla real |
| Remediación | `30a764b` | Texto de usuario escapado, negritas y saltos preservados |
| Vista pública | `ca2529a` | Feed, comentario máximo y paginación |
| Candidato funcional aprobado | `4333a32` (etiqueta `qa-verde-4333a32`) | Ocho controles `OK`, árbol limpio y 19/19 pruebas; imágenes examinadas y empaquetadas |
| Interfaz genérica aprobada | `2e2b811` (etiqueta `qa-verde-interfaz-2e2b811`) | Ocho controles `OK`, árbol limpio y 19/19 pruebas; imágenes examinadas y empaquetadas |
| Primera promoción: videojuegos | `22ee1ec` (etiqueta `qa-verde-videojuegos-22ee1ec`) | Ocho controles `OK`, 19/19 pruebas y manifiesto `reportes/entrega_final/manifest_videojuegos.json`; destino 12/12 |
| Diseño gamer histórico | `9424272` (etiqueta `qa-verde-diseno-9424272`) | Ocho controles `OK`, 19/19 pruebas; destino 12/12 |
| Pulso Pixel v2, histórica | `0ec86bb` (etiqueta `qa-verde-pulso-pixel-v2-0ec86bb`) | Ocho controles `OK`, 19/19 pruebas; [manifiesto](reportes/entrega_final/manifest_pulso_pixel_v2.json) y verificación 12/12 del destino |
| Revisión final, histórica | `8d1b742` (etiqueta `qa-verde-revision-final-8d1b742`) | Ocho controles `OK`, 21/21 pruebas y verificación 15/15 del destino |
| **Release actual: imágenes y formulario** | `a2123c5` (etiqueta `qa-verde-imagenes-a2123c5`) | Ocho controles `OK`, 27/27 pruebas; [manifiesto](reportes/entrega_final/manifest_imagenes_a2123c5.json) y [verificación 16/16](reportes/entrega_final/verificacion_produccion_imagenes_a2123c5.log) del destino |

Estas corridas se ejecutaron en la EC2 de QA. El commit `bc539cb` archiva los reportes históricos del candidato `4333a32`; la evidencia verde de videojuegos se archivó en `72d64f4` después de aprobar y exportar el commit `22ee1ec`. **Cada veredicto y manifiesto certifica solo el commit que nombra**. A Producción llegaron exclusivamente releases aprobadas, nunca el parche vulnerable. Los commits de evidencias son posteriores a sus commits aprobados y no se usaron para reconstruir imágenes en el destino. Los problemas de configuración observados se registran en `docs/bitacora_produccion.md`; un futuro defecto de código tendría que volver a QA para otro ciclo completo.

## Configuración y ejecución

Partir de `.env.ejemplo`, crear `.env` **fuera del control de versiones** y completar RDS, bucket, región, prefijo S3, `CLAVE_SESION`, `MODERADORES` y `MODERADOR_PASS`. Generar una contraseña aleatoria para el moderador, por ejemplo con `python3 -c 'import secrets; print(secrets.token_urlsafe(24))'`. El arranque rechaza el marcador `CAMBIA_ESTE_VALOR`; el registro público rechaza correos reservados. Si una cuenta con ese correo existía previamente con otra credencial, el arranque se detiene para inspeccionarla.

En QA, después de comprobar `.env` y credenciales AWS de la instancia:

```bash
bash pipeline/preparar_herramientas.sh
docker compose build
docker compose up -d
docker compose ps
bash pipeline/orquestador.sh
```

El orquestador carga la contraseña moderadora desde el `.env` local para su prueba HTTP y no la escribe en el reporte. No se suben claves, `.env` ni capturas con secretos. [La guía de QA](docs/guia_qa.md) explica los commits y cómo conservar el rojo y el verde. El [README del Avance 2](docs/README.md) conserva instrucciones de base e infraestructura.

## Evidencia y decisiones

- `docs/clasificacion_hallazgo.md`: CWE-79, impacto, falso positivo y corridas reales en QA.
- `docs/respuesta_incidente.md`: contención temporal separada de la corrección permanente.
- `docs/ADR-002-vista-previa.md` y `docs/ADR-003-promocion-entornos.md`: decisiones y límites del diseño.
- `docs/evidencia_local/`: reproducción HTTP local de Claude; **no equivale** a evidencia de QA.
- `docs/declaracion_ia.md`: plantilla para que Alan declare únicamente trabajo que hizo y verificó.

**Entrega:** incorporar las capturas del antes/después de QA y de la Producción ya verificada a la plantilla oficial, y completar en primera persona `docs/declaracion_ia.md` y la autoevaluación. El log final del destino está archivado; los Image IDs y hashes de la release actual están en `reportes/entrega_final/manifest_imagenes_a2123c5.json`. Los manifiestos anteriores se conservan como evidencia histórica.

**Evolución propuesta (fuera de esta entrega):** respuestas enlazadas a comentarios concretos; cuentas verificadas de desarrolladores y una sección de noticias sin autocalificaciones. Esta función requeriría un tipo de publicación y reglas de autorización nuevos, migración de datos, pruebas de moderación y un ciclo QA → verde → promoción propio.

# Trama · Foro de restaurantes y cafeterías · Entrega Final

Proyecto de **Herramientas de tecnologías de la información**, Tecmilenio (LSCA2314), tema 4: foro y reseñas. **Trama** reúne experiencias sobre restaurantes y cafeterías: cada persona puede escribir una reseña de su visita, calificarla de 1 a 5, añadir una imagen privada y conversar en los comentarios. Un segundo servicio aplica reglas de moderación antes de publicar. La Entrega Final introduce la vista previa enriquecida del moderador, demuestra y corrige una XSS suministrada en el parche del profesor, y añade una portada con extractos y tres comentarios por reseña. El título identifica el lugar reseñado; aún no existe un catálogo de establecimientos, mapa ni puntuación agregada por lugar.

**Estado:** QA completado: corrida bloqueada por XSS, remediación, portada pública, candidato `4333a32` con ocho controles `OK` y 19/19 pruebas, e imágenes empaquetadas. La evidencia está en `reportes/pipeline_bloqueado.txt`, `reportes/pipeline_verde.txt` y `reportes/entrega_final/`. Falta crear y verificar la EC2 nueva de Producción y reunir las capturas. [Procedimiento y evidencia de QA](docs/guia_qa.md) · [Arquitectura detallada](docs/arquitectura.md).

**Candidato visual posterior:** se renovaron las plantillas de portada, detalle y acceso para mostrar claramente el antes y después. Este cambio de interfaz todavía requiere reconstrucción y un nuevo pipeline completo en QA. El manifiesto y el verde documentados arriba siguen correspondiendo exclusivamente a `4333a32`.

## Recorrido del usuario

1. Una persona se registra, inicia sesión y publica una reseña. El servicio `moderador` decide `publicado` o `rechazado` antes de guardarla. El autor puede consultar sus rechazos y el motivo.
2. La portada pública presenta hasta doce reseñas por página: título, autor, calificación, extracto del cuerpo, total de comentarios y **como máximo tres comentarios publicados** por tarjeta.
3. Al entrar a `/hilos/{id}`, se ve el contenido completo, la información pública del autor y todos los comentarios publicados. Ni los correos ni los motivos de rechazo se revelan en esas vistas.
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

QA es la instancia del Avance 2. Producción será **una EC2 nueva** y recibirá únicamente las imágenes de un commit remediado con pipeline completo en verde. Si se comparten RDS y bucket, se separan **base y usuario** de PostgreSQL y **prefijo `PREFIJO_S3`** de S3; esta decisión requiere comprobación de permisos del Learner Lab. El diagrama y los flujos están en [docs/arquitectura.md](docs/arquitectura.md).

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

El orquestador `pipeline/orquestador.sh` corre **las ocho etapas aunque alguna falle**, deja `reportes/veredicto.json` y archiva cada corrida en `reportes/corridas/`. Un error de herramienta bloquea: no se interpreta como escaneo limpio. Antes de empaquetar, `pipeline/promover.sh` verifica el commit, el árbol limpio y que los dos Image IDs actuales coincidan con los que examinó Trivy en la etapa 06. **El empaquetado no despliega:** la transferencia y verificación en la EC2 nueva se completan con datos reales de AWS.

### Hitos de QA

| Hito | Commit local | Comprobación |
|---|---|---|
| Parche del profesor portado **sin corregir** | `215be19` | Correr primero el pipeline original y conservar el resultado: es posible que no detecte XSS |
| Cobertura añadida | `84443a4` | La regla y T10d deben bloquear por la falla real |
| Remediación | `30a764b` | Texto de usuario escapado, negritas y saltos preservados |
| Vista pública | `ca2529a` | Feed, comentario máximo y paginación |
| Candidato aprobado | `4333a32` (etiqueta `qa-verde-4333a32`) | Ocho controles `OK`, árbol limpio y 19/19 pruebas; imágenes examinadas y empaquetadas |

Estas corridas se ejecutaron en la EC2 de QA. El commit posterior `bc539cb` archiva los reportes; **las imágenes y el manifiesto corresponden a `4333a32`**, no a ese commit de documentación. La versión con fallo deliberado nunca se promueve a Producción. Un error real de configuración o despliegue en Producción se registra allí; un defecto de código vuelve a QA y exige otro verde.

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

**Pendiente:** consolidar capturas del antes/después en QA, crear la EC2 nueva, verificar Producción y anotar errores efectivamente observados. QA es `i-05cc3223adae222ef`; el manifiesto exportado y los Image IDs están en `reportes/entrega_final/`. No se completan con datos supuestos.

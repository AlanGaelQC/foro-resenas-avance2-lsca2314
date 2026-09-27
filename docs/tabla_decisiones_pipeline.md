# Tabla de decisiones del pipeline

Foro y reseñas · LSCA2314 · Avance 2 y actualización para la Entrega Final

Este documento responde la pregunta de la calificación: **por qué esta etapa y
por qué con ese umbral**. Cada control está aquí porque cubre un riesgo concreto
de *esta* aplicación, no porque apareciera en una actividad anterior. Al final
se listan los controles que decidí **no** incluir y por qué.

## Qué es esta aplicación, en términos de riesgo

Un foro de reseñas donde cualquier persona se registra, publica texto y sube
imágenes, y ese contenido lo leen los demás usuarios. Eso define de dónde viene
el peligro:

- El contenido lo escribe gente desconocida, y se guarda y se vuelve a mostrar.
- Hay archivos subidos por usuarios que terminan en un bucket de S3.
- Hay una base de datos con credenciales, correos y contraseñas derivadas.
- Hay una pieza que decide qué se publica (el moderador). Si esa pieza se puede
  esquivar, el foro pierde su único control de contenido.
- Los contenedores corren en dos EC2 de AWS Academy: QA y Producción. Ambas
  comparten RDS y bucket, con bases y prefijos distintos; esa separación lógica
  no garantiza por sí misma aislamiento de permisos.

## Los ocho controles

| # | Riesgo de la aplicación | Control y alcance | Herramienta | Umbral o regla de bloqueo | Justificación | Evidencia | Riesgo residual |
|---|---|---|---|---|---|---|---|
| 01 | La contraseña de RDS, la llave de sesión o las credenciales de AWS Academy terminan en el repositorio, o quedan vivas en el historial aunque se borren después | Escaneo de secretos sobre el árbol de trabajo y el historial de git, con dos reglas propias para la cadena de conexión y para `CLAVE_SESION` | gitleaks 8.21.2 | **Cero** secretos detectados. Cualquier hallazgo bloquea | Con la llave de sesión se falsifican cookies y se suplanta a cualquier usuario; con la cadena de conexión se entra a la base completa. Además el profesor resta puntos por credenciales en el repo aunque sean de prueba. No existe un número tolerable de secretos filtrados | `reportes/01_secretos.txt` y `.json` | Un secreto con formato que ninguna regla reconoce. Se mitiga con `.env` fuera de git y revisión del diff antes de cada commit |
| 02 | Una vulnerabilidad conocida en FastAPI, SQLAlchemy, Jinja2 o boto3 es una vulnerabilidad de mi foro, y no la voy a ver leyendo mi propio código | Análisis de composición sobre los dos `requirements.txt` fijados (lo que realmente se instala en cada imagen) | pip-audit 2.10.1 | **Cero** vulnerabilidades conocidas, directas o transitivas | Las versiones están fijadas, así que el umbral duro es sostenible: si aparece una, se sube la versión y listo. Auditar el entorno del pipeline en vez de los requirements mediría otra cosa | `reportes/02_dependencias.txt` | Vulnerabilidad publicada después de la última corrida. Se mitiga volviendo a correr el pipeline antes de cada promoción |
| 03 | Errores clásicos que yo mismo puedo escribir: `shell=True`, hash débil para contraseñas, deserialización insegura, TLS sin verificar | SAST general sobre todo `app/` | bandit 1.9.4 | **Cero** hallazgos con severidad ≥ MEDIA **y** confianza ≥ MEDIA (`-ll -ii`) | Filtrar por severidad y confianza a la vez evita el ruido que hace que se deje de leer el reporte. Los LOW se reportan sin bloquear: en su mayoría son avisos de estilo defensivo cuyo costo no se justifica frente al riesgo real aquí | `reportes/03_sast_bandit.txt` y `.json` | Fallo lógico que bandit no modela (por ejemplo, autorización mal puesta). Lo cubren las etapas 04 y 08 |
| 04 | **Que algo se publique sin pasar por el moderador**, que suban archivos saltándose la validación, SQL inseguro, falta de timeout o vista previa que devuelva HTML del autor sin escapar | SAST dirigido con ocho reglas propias, incluida la detección del parche XSS (`pipeline/reglas_semgrep_foro.yml`) | semgrep 1.177.0, reglas locales | **Cero** hallazgos de severidad ERROR. Los WARNING se reportan sin bloquear | Las reglas comprueban convenciones de este foro y el uso de la función vulnerable del parche. Los WARNING de depuración describen un riesgo distinto y se conservan en el reporte | `reportes/04_sast_semgrep.txt` y `.json` | Una evasión escrita de forma que no coincida con ninguna regla. La etapa 08 complementa el análisis sobre la aplicación en ejecución |
| 05 | Bucket con acceso público, base sin cifrar o alcanzable desde Internet, contenedor corriendo como root | Análisis estático de `infra/*.tf` y de los dos Dockerfile | checkov 3.3.17 | **Cero** checks fallidos, salvo los ocho IDs justificados en `pipeline/excepciones_checkov.txt`; deben aparecer aprobados los seis checks obligatorios de cifrado, acceso público y usuario no root | La política usa cero fallos con excepciones nombradas porque esta salida de Checkov no proporciona severidades comparables. Los checks aprobados acreditan la configuración **declarada**, no el estado del recurso desplegado | `reportes/05_iac.txt`, generado en la corrida real de entrega | Diferencia entre Terraform y AWS real. Verificar cifrado, políticas y red mediante consultas de lectura y capturas |
| 06 | La imagen que despliego arrastra paquetes del sistema base (openssl, zlib, libc) con CVE conocidos, aunque mi código y mis dependencias estén limpios | Escaneo de las dos imágenes ya construidas | trivy 0.74.0 | **Cero** vulnerabilidades HIGH o CRITICAL **con parche disponible** (`--ignore-unfixed`) | Lo que corre en la instancia es la imagen, no el repositorio. Se ignoran las que no tienen corrección porque bloquear por algo que no puedo arreglar detiene el despliegue sin darme ninguna acción posible | `reportes/06_imagen.txt` | Vulnerabilidades sin parche disponible, que quedan aceptadas a conciencia, y CVE publicados después de la corrida |
| 07 | Desconocer las dependencias declaradas y sus versiones dificulta investigar un CVE | Generación de SBOM desde los requirements de ambos servicios y comprobaciones básicas de su JSON | cyclonedx-py 4.6.1 (CycloneDX JSON) | El archivo debe poder leerse, identificar CycloneDX y contener **≥ 1 componente**. Archivo vacío, JSON ilegible o componentes ausentes bloquean | Es entregable obligatorio. El inventario archivado contiene 9 dependencias directas de API y 3 del moderador; el script no valida el esquema CycloneDX completo | `reportes/sbom_cyclonedx.json`, `reportes/sbom_cyclonedx_moderador.json`, `reportes/07_sbom.txt` | No inventaría todas las dependencias transitivas instaladas ni paquetes del SO. Trivy escanea vulnerabilidades de la imagen en 06; eso no amplía automáticamente el SBOM entregado |
| 08 | Todo lo anterior mira archivos. Nada de eso prueba que el anónimo no publique, que el moderador **de verdad** detenga el contenido prohibido de punta a punta, ni que el texto del usuario se muestre escapado | Pruebas contra la aplicación en ejecución: salud, registro, login, autorización, moderación de hilos y de comentarios, XSS almacenado, validación de adjuntos y aislamiento entre usuarios | `pipeline/pruebas_flujo.py` (httpx) | **Todas** las pruebas deben pasar. Cero fallos tolerados | Cada prueba corresponde a un requisito funcional o de autorización del proyecto, no a una preferencia. Un `/salud` en 200 solo dice que el proceso vive: no demuestra ninguna de estas comprobaciones, y por eso esta etapa existe aparte | `reportes/08_pruebas_flujo.txt` | Solo cubre los flujos que escribí. No sustituye a un análisis dinámico exhaustivo |

## La decisión final

Las ocho etapas terminan en **un solo veredicto**. La puerta de control
(`pipeline/orquestador.sh`) no lee la pantalla: lee el archivo de estado que
cada etapa escribió en `reportes/estado_NN.json`, y aplica cuatro reglas:

1. Todas las etapas corren siempre, aunque una falle. Detenerse en la primera
   escondería el resto de los hallazgos y perdería su evidencia.
2. Un estado distinto de `OK` en una etapa bloqueante impide la promoción.
3. `ERROR_OPERATIVO` bloquea igual que `HALLAZGO`. **Un escáner que no arrancó
   no es un escáner que no encontró nada.** Un timeout, un reporte vacío, un
   JSON ilegible o un binario ausente nunca se leen como "sin vulnerabilidades".
4. Si falta el archivo de estado de una etapa, cuenta como `NO_EJECUTADO` y
   bloquea: la ausencia de evidencia no es evidencia de ausencia.

El código de salida del pipeline es lo que decide si se puede promover: `0`
permite, `1` bloquea. Esa lógica está probada en los cuatro casos con
`pipeline/probar_puerta.sh` (todo OK → permite; hallazgo → bloquea; error
operativo → bloquea; estado ausente → bloquea).

Cada corrida queda archivada en `reportes/corridas/<fecha>-<veredicto>/` junto
con el commit analizado, para que la evidencia de la corrida roja no se pierda
al remediar.

En la entrega se conservan ambos inventarios: `sbom_cyclonedx.json` para la API
y `sbom_cyclonedx_moderador.json` para el moderador. El segundo incluye
`pydantic`, dependencia que no aparece en el inventario de la API.

## Riesgos residuales confirmados en la auditoría

| Riesgo | Estado de la revisión final |
|---|---|
| Gitleaks excluye `.env` anidados/históricos y `reportes/` | A-01 reproduce la omisión con cadenas sintéticas. El barrido independiente de 60 commits sin esas exclusiones no detectó secretos. Corregir la cobertura requiere una nueva validación; conservar el rojo histórico no exige mantener el hueco |
| El verificador inspecciona tags cargados; QA no vincula automáticamente las pruebas con los contenedores escaneados | A-02: las comprobaciones manuales cubrieron la promoción observada. Falta automatizar origen, identidad activa y completitud de los controles |
| La suite QA continúa escribiendo si T1 identifica Producción | A-03: debe interrumpirse antes de cualquier escritura en un destino distinto de QA |
| T11 acepta un feed sin los comentarios del hilo probado | A-04: exigir los tres recientes de su tarjeta y los cuatro en el detalle |
| QA y Producción del laboratorio publican HTTP:8080 con `COOKIE_SEGURA=false` | Cookie firmada sin protección de transporte. HTTPS y cookie Secure siguen pendientes; no atribuirlos a la infraestructura actual |

Reproducciones, alcance y criterios de cierre en la
[revisión final del 27 de septiembre](auditoria/revision_final_2026-09-27.md).
Esta actualización documental no cambia los ocho controles ni sus umbrales.

## Qué decidí NO cubrir, y por qué

| Control descartado | Por qué no está |
|---|---|
| DAST con OWASP ZAP | La instancia del Learner Lab tiene memoria limitada y ya corre dos contenedores. Un escaneo completo de ZAP compite por esa memoria y tarda más que toda la ventana de la demostración. En su lugar, la etapa 08 prueba dirigidamente los flujos que importan en este foro, incluida la autorización entre usuarios, que un escaneo automático no sabe evaluar. Riesgo residual: no hay descubrimiento automático de vulnerabilidades web fuera de las que probé |
| Gestor de secretos (OpenBao / AWS Secrets Manager) | AWS Academy no garantiza permisos para Secrets Manager ni para crear los roles que necesitaría. La configuración va por variables de entorno con `.env` fuera de git, y la etapa 01 comprueba que siga así. Riesgo residual: los secretos viven en un archivo de la instancia; quien entre a la instancia los ve |
| Firma de imágenes (cosign) y registro privado (ECR) | La Final exporta imágenes en QA y las transfiere por SSH a otra EC2, sin ECR. SHA-256 comprueba integridad; no autentica quién aprobó la release. Se confía en el origen del manifiesto, permisos y canal controlados. No se implementó firma de artefactos; véase ADR-003 |
| Escaneo de licencias | Es un requisito legal, no de seguridad, y no forma parte de los criterios del Avance 2 |
| Análisis de la imagen base con políticas de cumplimiento (CIS) | El endurecimiento del Dockerfile (versión fija, sin root, HEALTHCHECK, sin secretos) ya lo revisa checkov en la etapa 05. Una política CIS completa añadiría hallazgos que no puedo remediar sobre una imagen oficial de Python |
| Kubernetes | Es opcional en el Avance 2 y suma puntos, pero consume memoria de la instancia. La consigna dice explícitamente no arriesgar la entrega por el bono |

## Nota sobre las herramientas del Avance 1

El Avance 1 usaba gitleaks, checkov, semgrep, bandit y pip-audit sobre código
del profesor. Las cinco siguen aquí, pero no por inercia: cada una
quedó porque cubre un riesgo de este foro, con un umbral que elegí para este
proyecto y, en el caso de semgrep, con reglas escritas desde cero para esta
aplicación. Se añadieron trivy (la imagen es lo que se despliega), el SBOM
(inventario y entregable obligatorio) y las pruebas de flujo (lo único que
demuestra que el moderador funciona de punta a punta).

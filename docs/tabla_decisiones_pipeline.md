# Tabla de decisiones del pipeline

Foro y reseñas · LSCA2314 · El Reto, Avance 2

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
- Todo corre en contenedores sobre una instancia de AWS Academy con credenciales
  temporales.

## Los ocho controles

| # | Riesgo de la aplicación | Control y alcance | Herramienta | Umbral o regla de bloqueo | Justificación | Evidencia | Riesgo residual |
|---|---|---|---|---|---|---|---|
| 01 | La contraseña de RDS, la llave de sesión o las credenciales de AWS Academy terminan en el repositorio, o quedan vivas en el historial aunque se borren después | Escaneo de secretos sobre el árbol de trabajo y el historial de git, con dos reglas propias para la cadena de conexión y para `CLAVE_SESION` | gitleaks 8.21.2 | **Cero** secretos detectados. Cualquier hallazgo bloquea | Con la llave de sesión se falsifican cookies y se suplanta a cualquier usuario; con la cadena de conexión se entra a la base completa. Además el profesor resta puntos por credenciales en el repo aunque sean de prueba. No existe un número tolerable de secretos filtrados | `reportes/01_secretos.txt` y `.json` | Un secreto con formato que ninguna regla reconoce. Se mitiga con `.env` fuera de git y revisión del diff antes de cada commit |
| 02 | Una vulnerabilidad conocida en FastAPI, SQLAlchemy, Jinja2 o boto3 es una vulnerabilidad de mi foro, y no la voy a ver leyendo mi propio código | Análisis de composición sobre los dos `requirements.txt` fijados (lo que realmente se instala en cada imagen) | pip-audit 2.10.1 | **Cero** vulnerabilidades conocidas, directas o transitivas | Las versiones están fijadas, así que el umbral duro es sostenible: si aparece una, se sube la versión y listo. Auditar el entorno del pipeline en vez de los requirements mediría otra cosa | `reportes/02_dependencias.txt` | Vulnerabilidad publicada después de la última corrida. Se mitiga volviendo a correr el pipeline antes de cada promoción |
| 03 | Errores clásicos que yo mismo puedo escribir: `shell=True`, hash débil para contraseñas, deserialización insegura, TLS sin verificar | SAST general sobre todo `app/` | bandit 1.9.4 | **Cero** hallazgos con severidad ≥ MEDIA **y** confianza ≥ MEDIA (`-ll -ii`) | Filtrar por severidad y confianza a la vez evita el ruido que hace que se deje de leer el reporte. Los LOW se reportan sin bloquear: en su mayoría son avisos de estilo defensivo cuyo costo no se justifica frente al riesgo real aquí | `reportes/03_sast_bandit.txt` y `.json` | Fallo lógico que bandit no modela (por ejemplo, autorización mal puesta). Lo cubren las etapas 04 y 08 |
| 04 | **Que algo se publique sin pasar por el moderador**, que suban archivos saltándose la validación, que el texto del usuario entre en una consulta SQL, o que la llamada al moderador se quede colgada sin timeout | SAST dirigido con siete reglas propias escritas para este foro (`pipeline/reglas_semgrep_foro.yml`) | semgrep 1.177.0, reglas locales | **Cero** hallazgos de severidad ERROR. Los WARNING se reportan sin bloquear | Es el control que defiende la pieza distintiva del tema. Ninguna herramienta genérica sabe que en mi aplicación el único módulo autorizado a poner el estado `publicado` es `app/api/moderacion.py`. Los WARNING (depuración encendida) describen higiene, no una vía de evasión | `reportes/04_sast_semgrep.txt` y `.json` | Una evasión escrita de forma que no coincida con ninguna regla. Por eso la etapa 08 vuelve a comprobar lo mismo, pero contra la aplicación corriendo |
| 05 | Bucket con acceso público, base sin cifrar o alcanzable desde Internet, contenedor corriendo como root: los dos requisitos de infraestructura se pierden por configuración, no por código | Análisis estático de `infra/*.tf` y de los dos Dockerfile | checkov 3.3.17 | **Cero** checks fallidos, salvo los ocho IDs listados y justificados uno por uno en `pipeline/excepciones_checkov.txt`; además deben aparecer aprobados los seis checks obligatorios de cifrado, acceso público y usuario no root | Checkov (edición abierta) no entrega escala de severidad, así que un umbral tipo "solo HIGH" sería atribuirle algo que no produce. La política compatible con su salida es cero fallos con excepciones nombradas. El reporte incluye también los checks que **pasaron**: ahí está la prueba de que el bucket no es público y la base está cifrada | `reportes/05_iac.txt`, generado en la corrida real de entrega | Diferencia entre lo que describe el `.tf` y lo que realmente existe en AWS. Se mitiga con las consultas de AWS CLI y las capturas de cada recurso |
| 06 | La imagen que despliego arrastra paquetes del sistema base (openssl, zlib, libc) con CVE conocidos, aunque mi código y mis dependencias estén limpios | Escaneo de las dos imágenes ya construidas | trivy | **Cero** vulnerabilidades HIGH o CRITICAL **con parche disponible** (`--ignore-unfixed`) | Lo que corre en la instancia es la imagen, no el repositorio. Se ignoran las que no tienen corrección porque bloquear por algo que no puedo arreglar detiene el despliegue sin darme ninguna acción posible | `reportes/06_imagen.txt` | Vulnerabilidades sin parche disponible, que quedan aceptadas a conciencia, y CVE publicados después de la corrida |
| 07 | Cuando salga un CVE nuevo, responder "¿mi foro usa esa librería, en qué versión?" sin un inventario cuesta horas de revisar imágenes a mano | Generación y validación del SBOM de los dos servicios | cyclonedx-py 4.6.1 (CycloneDX JSON) | El archivo debe existir, ser CycloneDX válido y traer **≥ 1 componente**. Un SBOM vacío o corrupto bloquea | Es entregable obligatorio del Avance 2, y es un control de evidencia: sin inventario válido no hay promoción. Alcance declarado: cubre las dependencias Python de ambos servicios, no los paquetes del sistema operativo de la imagen base (esos los cubre la etapa 06) | `reportes/sbom_cyclonedx.json`, `reportes/07_sbom.txt` | El SBOM refleja los `requirements.txt`, no lo instalado en la imagen final si alguien la modifica a mano |
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

## Qué decidí NO cubrir, y por qué

| Control descartado | Por qué no está |
|---|---|
| DAST con OWASP ZAP | La instancia del Learner Lab tiene memoria limitada y ya corre dos contenedores. Un escaneo completo de ZAP compite por esa memoria y tarda más que toda la ventana de la demostración. En su lugar, la etapa 08 prueba dirigidamente los flujos que importan en este foro, incluida la autorización entre usuarios, que un escaneo automático no sabe evaluar. Riesgo residual: no hay descubrimiento automático de vulnerabilidades web fuera de las que probé |
| Gestor de secretos (OpenBao / AWS Secrets Manager) | AWS Academy no garantiza permisos para Secrets Manager ni para crear los roles que necesitaría. La configuración va por variables de entorno con `.env` fuera de git, y la etapa 01 comprueba que siga así. Riesgo residual: los secretos viven en un archivo de la instancia; quien entre a la instancia los ve |
| Firma de imágenes (cosign) y registro privado (ECR) | Las imágenes se construyen y se consumen en la misma instancia, sin pasar por un registro. Firmar protegería contra la manipulación en tránsito, que aquí no existe. Cuando en la entrega final haya una segunda instancia de Producción, esta decisión hay que revisarla |
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

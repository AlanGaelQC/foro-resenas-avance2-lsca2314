# Declaración de uso de IA

Foro y reseñas · LSCA2314 · El Reto, Avance 2
Autor: Alan Gael Quintanilla Clemente

## 1. Qué herramientas de IA usé

| Herramienta | Para qué |
|---|---|
| Claude (Anthropic; la versión exacta no quedó registrada) | Generar un primer andamio del proyecto, proponer la arquitectura inicial, los controles del pipeline y borradores de documentación. La ejecución presentada inicialmente por esta herramienta se trató solo como simulación y no como evidencia entregable. |
| ChatGPT/Codex (OpenAI, GPT-5) | Revisar el andamio, corregir código y controles, explicar los comandos y guiar la creación y validación real de EC2, S3, RDS, contenedores y las corridas roja y verde. |

## 2. En qué partes del proyecto se usó IA

| Parte | Cómo se usó la IA | Qué revisé y ejecuté personalmente |
|---|---|---|
| `app/api/` | Se utilizó IA para el borrador de la API FastAPI y para revisar validaciones, sesiones, persistencia y manejo de adjuntos. | Levanté la aplicación en mi EC2, probé registro e inicio de sesión, publicaciones aceptadas y rechazadas, calificaciones inválidas, escape de XSS y adjuntos reales en S3. |
| `app/moderador/` | Se utilizó IA para separar la moderación en un servicio propio y definir reglas de léxico, enlaces, contacto, texto vacío y uso excesivo de mayúsculas. | Verifiqué que el moderador estuviera en un contenedor separado, sin puerto público, y comprobé que el contenido prohibido fuera rechazado con un motivo visible para su autor. |
| `Dockerfile`, `Dockerfile.moderador` y `docker-compose.yml` | Se utilizó IA para proponer imágenes sin root, `HEALTHCHECK`, red interna y restricciones del contenedor. | Construí las dos imágenes. Corregí la ausencia de Buildx, fijé la imagen base por digest y retiré `pip`, `setuptools` y `wheel` de las imágenes finales para eliminar hallazgos corregibles de Trivy. |
| `infra/*.tf` | Se utilizó IA para describir S3, RDS, grupos de seguridad, cifrado y bloqueo de acceso público. | Creé los recursos reales desde mi instancia con AWS CLI, comparé sus propiedades con el código, ejecuté Checkov y validé Terraform 1.16.3 con el proveedor AWS 6.65.0. No ejecuté `terraform apply` sobre recursos ya creados fuera de su estado. |
| `pipeline/` | Se utilizó IA para proponer y corregir los ocho controles y la puerta con un veredicto único. | Instalé las herramientas, ejecuté las etapas en la EC2 y confirmé que un hallazgo, un error operativo o una etapa no ejecutada bloquean. Revisé los umbrales y las ocho excepciones documentadas de Checkov. |
| `pipeline/reglas_semgrep_foro.yml` | Se utilizó IA para redactar reglas propias de este foro. | Comprobé una de las reglas mediante un defecto real: publicar comentarios sin moderación. Semgrep detectó la asignación directa de `ESTADO_PUBLICADO` y la prueba T6b detectó el mismo problema durante la ejecución. |
| `docs/` | Se utilizó IA para producir borradores a partir de los requisitos y decisiones técnicas. | Contrasté la documentación con los recursos, comandos, commits y resultados reales antes de conservarla como parte de la entrega. |

## 3. Qué no delegué

Yo inicié y administré la sesión de AWS Academy, ejecuté los comandos en la
instancia EC2 y comprobé sus resultados. Creé y configuré el bucket S3 y la
instancia RDS de mi cuenta; configuré la red entre EC2 y RDS; construí y
levanté los contenedores; probé la aplicación desde el navegador; instalé las
herramientas; ejecuté el pipeline y revisé sus reportes. También decidí aceptar
o rechazar cada cambio después de observar su resultado. La selección de las
evidencias, la grabación del video, la explicación oral y la entrega final son
mi responsabilidad.

## 4. Errores o problemas que encontré y cómo los corregí

1. La instancia tenía un volumen de 8 GiB. Lo amplié a 20 GiB; el primer
   intento de `growpart` no obtuvo el número de partición, así que identifiqué
   explícitamente `/dev/xvda` y la partición `1`, y después extendí XFS.
2. Amazon Linux no incluía Docker Compose ni una versión suficiente de Buildx.
   Instalé ambos componentes, verifiqué sus hashes y confirmé el motor con una
   ejecución real antes de construir la aplicación.
3. Gitleaks detectó los secretos necesarios del `.env` de ejecución. En lugar
   de versionarlos o ignorar el riesgo, ajusté el control para excluir solamente
   ese archivo y verificar por separado que esté ignorado por Git, no rastreado
   y protegido con permisos `600`.
4. Checkov no estaba reuniendo correctamente los resultados de Terraform y de
   los dos Dockerfile. Separé los análisis y consolidé sus salidas para que los
   checks obligatorios tuvieran evidencia explícita.
5. Trivy encontró componentes vulnerables asociados con herramientas de
   construcción. Actualicé los paquetes y después retiré `pip`, `setuptools` y
   `wheel` de las imágenes finales, donde no eran necesarios. La nueva corrida
   quedó sin vulnerabilidades HIGH o CRITICAL corregibles.
6. Para demostrar el ciclo rojo→verde introduje el defecto controlado de
   publicar comentarios sin llamar al moderador. La corrida roja fue bloqueada
   por Semgrep y por T6b. Restauré la llamada de moderación, reconstruí la API y
   la corrida verde terminó con los ocho controles en `OK` y 13 de 13 pruebas.

## 5. Qué aprendí y qué puedo defender

Aprendí que un pipeline confiable no solo debe encontrar fallos: también debe
bloquear cuando una herramienta falla o cuando falta la evidencia de una
etapa. Puedo explicar la función de los ocho controles, sus umbrales y por qué
terminan en un solo veredicto. También puedo defender por qué RDS no tiene
acceso público y solo acepta PostgreSQL desde el security group de la EC2, por
qué el bucket S3 es privado y cifrado, por qué los contenedores no usan root y
por qué todo comentario debe pasar por el servicio de moderación antes de
publicarse. La parte más difícil fue distinguir entre un hallazgo real del
producto y un componente de construcción detectado dentro de la imagen; lo
resolví reduciendo la superficie de la imagen final en vez de ocultar el
resultado de Trivy.

## 6. Declaración

Declaro que entiendo el código y las decisiones que entrego, que puedo
explicarlas y defenderlas, y que las evidencias incluidas
(`reportes/corrida_roja.txt`, `reportes/corrida_verde.txt`, capturas y video)
son resultados reales obtenidos en mi propio entorno.

Firma: Alan Gael Quintanilla Clemente · Fecha: 17 de septiembre de 2026

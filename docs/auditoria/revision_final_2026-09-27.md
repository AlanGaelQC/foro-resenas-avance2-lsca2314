# Revisión final del proyecto Pulso Pixel

Fecha: 27 de septiembre de 2026, UTC. Alcance: revisión del repositorio, fuentes oficiales, evidencias suministradas y pruebas locales aisladas. **No es un nuevo veredicto del pipeline ni una certificación del estado actual de AWS.**

## Conclusión

**Estado de esta rama:** los cuatro parches descritos en A-01–A-04 ya están implementados localmente en `revision-final-quirurgica`, con pruebas sintéticas negativas que pasan. Aún no son un veredicto de QA ni una nueva promoción; requieren ejecutar el pipeline real en la instancia QA antes de incorporarse a `entrega-final`.

La corrección de la XSS es real; la evidencia archivada vincula el rojo, la remediación, el verde y la promoción de la release `0ec86bb`. Las capturas recuperadas muestran la aplicación y dos EC2 distintas. Los Dockerfiles ya corrigen la observación del profesor: ambos HEALTHCHECK consultan `/salud`.

Sin embargo, **no doy por cerrado el endurecimiento técnico**. Se reprodujeron cuatro familias de huecos: exclusiones demasiado amplias de secretos, verificación de imágenes cargadas en lugar de contenedores activos, pruebas de QA que continúan escribiendo aunque detecten Producción y una aserción incompleta de los comentarios del feed. Ninguno demuestra por sí mismo una fuga o que la release entregada esté equivocada; sí permiten errores futuros que el pipeline debería detener.

El objetivo de esta revisión es hacer explícitas esas diferencias y dejar criterios verificables de cierre. Las reproducciones están separadas de la evidencia real de QA/Producción. No se modificaron aplicación, datos, reglas de AWS ni scripts de promoción durante la auditoría.

## 1. Qué se contrastó

| Fuente | Uso en la revisión |
|---|---|
| `EntregaFinal_Reto_Instrucciones_LSCA2314.docx` | Siete pasos, entregables y declaración de IA requerida. |
| `EntregaFinal_Reto_Presentacion_LSCA2314.pptx` | Diapositiva 9: rúbrica de 35 puntos; diapositiva 11: cierre de la EC2 de Producción tras obtener evidencia. |
| `Plantilla_Evidencias_EntregaFinal_LSCA2314.docx` | Datos, siete apartados de capturas, autoevaluación y preguntas/reflexión. |
| Instrucciones oficiales del Avance 2 y de la Actividad 4 | Requisitos de la aplicación, contenedores, S3/RDS y controles del pipeline. |
| `tema4_foro/PARCHE.md` y `vista_previa_resena.py` | Defecto original y alcance real de la vista previa. |
| Repositorio remoto, todas las ramas y etiquetas obtenidas | Código, historial, documentación y reportes reales archivados. |
| Diez capturas originales suministradas | Rojo, hallazgo, diff, verde, instancias, verificador y vistas de QA/Producción. |
| Informe de Claude, `Markdown pegado(1).md` | Contraste independiente; no se aceptaron sus conclusiones sin comprobarlas. |

Se consultó el remoto con `git fetch` y `git ls-remote`: `entrega-final` y `diseno-gamer-v2` apuntaban a `6f5f42dcbc6d6d65f68bdaf1033c7de07394470a`. La rama `main` seguía en `430fc6a`, correspondiente al Avance 2. La etiqueta de la aplicación desplegada apunta a `0ec86bb5498fc8f91090edf3ec4e77498586644d`; los commits posteriores archivan evidencias y documentación. Son identidades distintas con funciones distintas.

Para el evaluador debe usarse el [enlace explícito a entrega-final](https://github.com/AlanGaelQC/foro-resenas-avance2-lsca2314/tree/entrega-final). Cambiar la rama predeterminada es una decisión de presentación; no requiere reconstruir la aplicación.

## 2. Hallazgos técnicos reproducidos

Las prioridades expresan el orden de corrección recomendado para este proyecto; no son puntuaciones CVSS.

### A-01 · Prioridad alta: el control de secretos excluye superficies relevantes

**Código:** `.gitleaks.toml`, sección global `allowlist.paths`; `pipeline/01_secretos.sh`, comprobación de `.env` y selección de historial.

El patrón `(^|/)\.env$` excluye cualquier archivo llamado `.env`, incluido uno anidado o presente solo en un commit antiguo. La protección adicional del script revisa únicamente el `.env` de la raíz que exista en el árbol actual. La exclusión de `reportes/` también afecta a evidencias que se suben con `git add -f`. Escanear una copia renombrada de un log antes de añadirlo fue una precaución manual útil; el pipeline no asegura que todos los futuros archivos pasen por ella.

Se ejecutó Gitleaks 8.21.2 con la configuración real y una cadena **sintética**, sin usar una credencial:

| Caso aislado | Salida | Hallazgos |
|---|---:|---:|
| Mismo marcador en `muestra.txt` | 1 | 1 |
| Mismo marcador en `reportes/muestra.txt` | 0 | 0 |
| Mismo marcador en `anidada/.env` | 0 | 0 |
| `.env` añadido a Git y eliminado en un commit posterior | 0 | 0 |
| Configuración ampliada sin esas dos exclusiones: reporte | 1 | 1 |
| Configuración ampliada sin esas dos exclusiones: `.env` histórico | 1 | 1 |

**Estado real del repositorio:** un escaneo independiente de los 60 commits, incluyendo las rutas que el pipeline excluía, terminó sin secretos detectados. Esto es un resultado favorable del escaneo, no una garantía universal de ausencia de credenciales. No se encontró `.env`, `.pem`, `.tfstate` o `.tfvars` real versionado.

**Cierre aplicado en esta rama:** la configuración base escanea historial y evidencias; el `.env` local se excluye solo en la configuración temporal del árbol, con comprobación de rastreo, ignore y permisos. La validación real en QA queda pendiente.

**Criterio original:** escanear todo el historial y las evidencias versionadas; limitar la excepción al `.env` local, ignorado, no rastreado y con permisos 600. Detectar repositorios mediante Git: `[[ -d .git ]]` omite el historial de un worktree porque allí `.git` es un archivo. Añadir pruebas negativas de secreto en reporte y secreto retirado del historial. No publicar valores sensibles en las salidas de las pruebas.

### A-02 · Prioridad alta: identidad y completitud del verificador del destino

**Código:** `pipeline/verificar_produccion.py`, función `ejecutar()`.

El script consulta `docker image inspect` sobre el tag local. No consulta el Image ID del contenedor activo. Es posible cargar una imagen nueva y conservar un contenedor de la anterior: que el tag sea correcto no demuestra que el proceso servido por HTTP lo utilice.

Con dobles de HTTP y Docker se reprodujeron estos resultados:

| Escenario sintético | Resultado del verificador actual |
|---|---|
| Tags correctos, tar correctos, aplicación responde | 12/12, salida 0 |
| Tags correctos, contenedor anterior aún activo | 12/12, salida 0; no se consultó el contenedor |
| Sin reseñas para comprobar el detalle | Imprime `PENDIENTE`, 11/11, salida 0 |
| Image ID cargado distinto | Salida 1 |
| Tar alterado | Salida 1 |

**Alcance histórico:** durante el despliegue se hicieron comprobaciones manuales de `.Image` de los contenedores y de su salud, además del verificador. El hueco del script no demuestra que la promoción histórica fuera incorrecta. El log final sí terminó 12/12 con una reseña existente.

**Cierre aplicado en esta rama:** el verificador ahora comprueba el checkout contra el manifiesto, los Image ID de los contenedores activos, estado/health, hashes y un total explícito de 15 controles. La validación real en Producción queda pendiente.

**Criterio original:** comprobar contenedores del proyecto Compose esperado, estado y salud, `.Image` de ambos servicios, commit del checkout frente al manifiesto y URL local prevista. Mantener un total explícito de controles; un requisito pendiente no debe producir un verde completo. Registrar fecha UTC, commit, IDs y hashes comparados, sin secretos, para que el resultado sea auditable por sí mismo.

**Misma frontera en QA, comprobada por lectura:** la etapa 06 registra los tags escaneados y el HEAD actual; la 08 consulta una URL. No hay una comprobación automática que vincule el contenedor servido por esa URL con los IDs de la etapa 06, ni una prueba de que las imágenes existentes se construyeron con el código actual. Los comandos manuales de construcción cubrieron esa responsabilidad. Para cerrar la cadena automáticamente, registrar el origen de la construcción y verificar la identidad de los contenedores antes de las pruebas. Un label de commit por sí solo tampoco sustituye controlar el proceso de construcción.

### A-03 · Prioridad alta: la suite de QA escribe después de detectar Producción

**Código:** `pipeline/pruebas_flujo.py`, `main()`, prueba T1.

T1 comprueba que `/salud` declare `entorno=qa`. Cuando devuelve `produccion`, marca la prueba como fallida pero continúa con registros, publicaciones y comentarios. El resultado final bloquea la promoción, pero llega demasiado tarde para impedir esas escrituras.

La reproducción aislada devolvió `produccion` desde `/salud`: T1 falló y aun así se realizaron **19 llamadas POST sintéticas posteriores**, incluidas `/registro` y `/hilos`. No se enviaron solicitudes reales a ninguna EC2.

**Cierre aplicado en esta rama:** T1 termina antes de cualquier POST si `/salud` no confirma QA, PostgreSQL, RDS y S3; una reproducción local confirmó cero escrituras. La validación real en QA queda pendiente.

**Criterio original:** una comprobación previa obligatoria que termine antes del primer POST si el destino no es QA o su identidad no se puede establecer. La prueba negativa debe exigir cero escrituras para un destino Producción, salud inválida o error de conexión. Mantener el verificador de Producción separado de la suite que crea datos.

### A-04 · Prioridad media: T11 no garantiza los tres comentarios del hilo probado

**Código:** `pipeline/pruebas_flujo.py`, condición de `registrar("T11 ...")`.

La condición acepta `mostrados <= 3`, comprueba `Comentarios (4)` en toda la página y que no aparezca la marca del comentario antiguo. No exige que estén los tres comentarios recientes del hilo creado por la prueba. La expresión exacta, extraída mediante AST, devolvió verdadero con **cero** comentarios propios visibles y un contador de cuatro perteneciente a otra tarjeta.

La consulta SQL de la aplicación sí usa `row_number()` por hilo y límite de tres; las capturas de Producción muestran tres comentarios en portada y cuatro en detalle. El defecto reproducido está en la capacidad de la prueba para detectar una regresión.

**Cierre aplicado en esta rama:** T11a/T11b cubren cero y uno, y T11 identifica la tarjeta propia, exige tres recientes, contador cuatro y cuatro artículos en detalle. La validación real en QA queda pendiente.

**Criterio original:** identificar la tarjeta del hilo probado y exigir exactamente sus tres comentarios recientes, su contador total, exclusión del cuarto antiguo y los cuatro en el detalle. Comprobar también 0 y 1 comentarios. No depender de textos de otras tarjetas ni alterar el umbral para obtener verde.

## 3. Calidad de evidencia y documentación

| Observación comprobada | Acción concreta |
|---|---|
| Los reportes originales finales de las etapas 01, 02, 03, 05, 06 y 07 no están íntegramente versionados para la última corrida; hay resumen de ocho estados y registro de IDs de la 06. | Recuperar de la carpeta original de QA las salidas disponibles y estados por etapa, revisarlas por secretos y archivarlas con su procedencia. No recrearlas y llamarlas históricas. |
| `reportes/corridas/...` aparece en la narrativa, pero esas carpetas no están en el repositorio. | Distinguir la ubicación original en EC2 de las copias entregables con enlaces existentes. No afirmar que todas las corridas intermedias tienen copia íntegra publicada. |
| `.gitignore` omite evidencias nuevas de la Final salvo `git add -f`. | Añadir excepciones acotadas a las evidencias aprobadas, después de corregir A-01. Los archivos ya rastreados sí permanecen versionados. |
| El PNG anterior aún representaba una EC2 y el Avance 2. | Diagramas nuevos de arquitectura y promoción preparados en esta revisión, con dos EC2 y servicios compartidos. |
| La tabla de decisiones decía que no existía tránsito entre instancias y los documentos discrepaban sobre HTTPS. | Corregir el alcance: transferencia SSH manual; navegación HTTP como limitación real del laboratorio. |
| CKV_AWS_18 afirma que las llamadas a S3 quedan registradas en CloudTrail a nivel de cuenta. | Retirar esa garantía sin evidencia: los eventos de datos de objetos no están habilitados por defecto. La ausencia de logging por objeto es un riesgo residual, no una protección compensatoria demostrada. |
| El inventario SBOM contiene 9 dependencias de API y 3 del moderador, procedentes de sus requirements. | Identificarlo como inventario de dependencias directas declaradas. No equivale al grafo completo de paquetes instalados ni al SO. Para una mejora posterior, inventariar las imágenes finales y validar el esquema CycloneDX completo. |
| La imagen de prueba T8b solo contiene cabecera PNG y bytes de texto. | Sustituir el fixture por una imagen mínima válida y comprobar la recuperación real del objeto. Hoy la prueba acredita subida/redirección; no que un visor pueda decodificarla. El validador de la app comprueba firma inicial, no decodificación completa. |
| Los verificadores de entrega del Avance 2 buscan otros documentos/marcadores. | No utilizarlos para certificar la completitud de la Final: pueden pasar aunque `declaracion_ia.md` contenga `[COMPLETA AQUÍ]`. |

Fuente primaria de la precisión sobre CloudTrail: [AWS, Enabling CloudTrail event logging for S3 buckets and objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-cloudtrail-logging-for-s3.html), consultada durante esta revisión. Habilitar eventos de datos requeriría una decisión separada sobre el alcance y coste; esta revisión no los activó.

## 4. Lo que sí se verificó favorablemente

- **Remediación:** el endpoint activo llama a `formatear_seguro`; la función vulnerable permanece como referencia histórica sin llamada activa en la release. Quince entradas aisladas no introdujeron etiquetas activas; se conservaron negrita y saltos. `quote=False` es adecuado para el contexto de texto actual; no se verificó una inyección explotable por las comillas.
- **Plantillas:** 32 renderizados con Jinja, StrictUndefined, autoescape y contextos sintéticos —sesión/anonimato, paginación, vacío, comentarios y reseña larga— terminaron sin errores ni etiquetas/atributos de evento inyectados. Esto no sustituye una prueba visual de todos los navegadores.
- **HEALTHCHECK:** ambos ejecutan peticiones HTTP a `/salud`; una respuesta 200 produce éxito y un error de conexión produce fallo en la ejecución aislada del comando. La API devuelve 503 si falla BD o S3 obligatorio. El moderador tiene su comprobación propia.
- **Puerta del pipeline:** sus cuatro casos sintéticos existentes pasaron: ocho OK permiten; HALLAZGO, ERROR_OPERATIVO o una etapa sin estado bloquean. La prueba está marcada como sintética y no sustituye los escáneres.
- **Promoción:** exige verde completo, commit coincidente, árbol limpio e IDs iguales a los registrados por Trivy. Rechaza empaquetar un HEAD documental posterior con el veredicto de la release anterior. No reconstruye imágenes.
- **Contenedores:** digest de base fijo, usuario no root, filesystem de solo lectura, límites, capacidades retiradas y moderador sin puerto publicado. No se encontró una credencial embebida en los Dockerfiles.
- **Aplicación:** hash scrypt con sal y comparación constante; sesión firmada y caducidad; autorización del moderador en servidor; correos reservados al registro; comprobación de autor para contenido propio; HTML escapado; SQL construido mediante SQLAlchemy; archivos limitados por tamaño/tipo/extensión/firma; subida AES256 solicitada a S3.
- **Trazabilidad:** seis veredictos finales archivados son coherentes con los commits correspondientes; los manifiestos conservan el commit de origen. Los hashes publicados son valores de registros históricos: en este entorno no se dispone de los tar originales para recalcularlos.
- **Secretos:** Gitleaks ampliado sobre 60 commits terminó con cero hallazgos. Se comprobó sintaxis de los archivos Python de aplicación/pipeline y de los 14 scripts shell revisados.

## 5. Cifrado, infraestructura y límites que no deben confundirse

| Aspecto | Qué se sabe | Qué falta para certificar el estado actual |
|---|---|---|
| Navegador → API | La aplicación se sirvió por HTTP:8080 con `COOKIE_SEGURA=false`; las capturas lo muestran. | HTTPS y cookie Secure serían necesarios para ofrecerla como servicio público protegido. Restringir una IP en SG no cifra el transporte. No se atribuye a la rúbrica un requisito de dominio/certificado que no expresa. |
| RDS en reposo | Terraform declara `storage_encrypted=true`; los registros muestran RDS real y privado. | Leer `StorageEncrypted` del recurso actual. Un `SELECT 1` o un OK de Checkov no lo demuestra. |
| API → PostgreSQL | Conectividad privada y PostgreSQL funcional constan en los registros. | Comprobar TLS en la sesión real y configuración del servidor/cliente; no inferirlo del cifrado en reposo. |
| S3 | Terraform declara bloqueo público de cuatro opciones, AES256, versionado y denegación de transporte inseguro; el código solicita AES256 al subir. | Revisar cifrado, bloqueo efectivo, política, versionado y un objeto real mediante consultas de lectura, sin publicar la URL firmada. |
| Separación de entornos | Dos EC2 y redes Compose; bases y secretos de sesión distintos; prefijos S3 distintos dentro de recursos compartidos. | Revisar permisos efectivos de roles DB/IAM. Un prefijo es una convención, no una frontera de autorización por sí mismo. QA ha usado un usuario administrador del RDS. |
| Red y roles | Los registros muestran SG de aplicación y acceso RDS desde ambos SG. | Verificar reglas actuales, incluidas IP antiguas, SSH y 8080; IAM efectivo; ausencia de exposición de 5432/8001. No ampliar accesos para la auditoría. |
| IaC | Define un RDS y un bucket, heredados del Avance 2; no administra toda la EC2/DB lógica de Producción creada manualmente. | Declarar esa diferencia; no ejecutar `terraform apply/destroy` suponiendo que el estado administra todos los recursos reales. |
| Snapshot final | El nombre no incorpora entorno; `deletion_protection=true`. | El escenario de dos RDS colisionando no corresponde a este despliegue compartido. Planificar el cierre real, no confundir terminar EC2 con destruir RDS. |
| Actualizaciones de vulnerabilidades | El verde archivado refleja las herramientas y bases de vulnerabilidades utilizadas en esa corrida. | Una nueva afirmación de seguridad actual requeriría nuevos escaneos reales; no se ejecutó Trivy contra las imágenes de AWS desde este entorno. |

Estas son comprobaciones pendientes de infraestructura viva. Esta auditoría no utilizó claves privadas ni accedió a las EC2; no sustituye esas lecturas por suposiciones.

## 6. Requisitos oficiales y estado de cierre

| Criterio de la Final | Puntos | Evidencia/estado |
|---|---:|---|
| Detección y clasificación | 8 | Rojo `84443a4`, Semgrep ERROR, T10d fallida; XSS almacenado/CWE-79, severidad razonada y falso positivo analizado. |
| Remediación real | 10 | Diff `30a764b`: escapar antes del formato; función activa segura; funcionalidad conservada. |
| Pipeline, bloqueo y verde | 7 | Rojo y verde archivados; último verde `0ec86bb`, 8/8 y 19/19. Cerrar A-01 a A-04 mejora la fiabilidad futura; no altera esas corridas. |
| Documentación | 6 | Clasificación y contención/prevención existentes. Completar plantilla y declaración personal, precisar los límites identificados. |
| Promoción evidenciada | 4 | Manifiesto, log 12/12, contenedores y captura de dos EC2 distintas; falta integrar las evidencias en la plantilla oficial. |

**Orden oficial:** aplicar el parche vulnerable y detectarlo en QA; documentar contención y prevención; corregir; obtener verde completo; promover a una EC2 nueva. Un error exclusivo de configuración/despliegue de Producción se diagnostica y documenta en ese destino. Un cambio de código o de controles se valida primero en QA y se vuelve a promover. El requisito no autoriza instalar el parche vulnerable en Producción para reproducirlo allí.

La vista previa oficial es un renderizador; no implementa un flujo persistente de aprobar/rechazar. No hay fundamento para agregar de último momento una cola de aprobación humana como supuesto requisito pendiente.

**Pendientes personales oficiales:** `docs/declaracion_ia.md` sigue con cinco marcadores, y la plantilla final necesita datos, preguntas y reflexión de Alan. El libre uso de IA permite utilizarla; no elimina la instrucción expresa de declarar su uso. Esta revisión no inventa respuestas en primera persona.

## 7. Capturas recuperadas y revisadas

Los archivos originales se conservaron fuera del repositorio público. Se revisaron los píxeles, no solamente su texto extraído.

| Archivo original | Qué acredita visualmente | Uso en la plantilla |
|---|---|---|
| `image(20260927-040248).png` | Bloqueo con HALLAZGO en 04 y 08. | 1.1 Pipeline bloqueado. |
| `image(20260927-035500).png` | Regla, archivo, llamada vulnerable y un hallazgo bloqueante. | 1.2 Herramienta y hallazgo. |
| `image(20260927-040019).png` | Commit 30a764b y extracto del diff original. | 1.3 Remediación. |
| `image(20260927-040305).png` | Commit 0ec86bb, fecha de corrida, ocho OK, PERMITIDO y 19/19. | 1.4 Pipeline verde. |
| `image(20260927-031539).png` | QA y Producción con IDs distintos y estado en ejecución. | Apoya 1.5 y 1.6; identificar expresamente cada fila en sus apartados. |
| `image(20260927-024000).png` | Portada de Producción con URL, Midnight Club y tres comentarios de muestra. | 1.7 Aplicación en Producción. |
| `image(20260927-024014).png` | Detalle `/hilos/1`, contador cuatro y cuatro comentarios. | Complemento funcional de 1.7. |
| `image(20260927-032346).png` | Commit desplegado, ambos contenedores healthy y verificación original 12/12. | Complemento técnico de promoción/verificador. |
| `image(20260927-023821).png` y `image(20260927-023842).png` | Portada QA y detalle Megaman X con cero comentarios; URLs visibles. | Comparación entre entornos/datos. |

Las capturas son legibles al abrirlas a tamaño completo. Las de terminal tienen bastante espacio vacío: al integrarlas hay que conservar texto legible, sin reducirlas todas a miniaturas. Los originales muestran identificadores de cuenta/infraestructura; no se detectó una contraseña o clave privada visible en estas diez capturas. Su revisión no equivale a certificar cualquier otro archivo compartido.

## 8. Contraste con el informe de Claude

- **Confirmado:** rama de entrega actualizada, XSS remediada, plantillas personales pendientes, coherencia de la release y ausencia de secretos detectados en el barrido realizado.
- **Conclusión ampliada:** decir que solo quedan pendientes humanos es demasiado fuerte. Las reproducciones A-01 a A-04 aportan contraejemplos concretos de los controles actuales.
- **Cronología:** los commits preparados antes de sus corridas no prueban una entrega ficticia. La guía explica ejecutar sucesivos checkouts; las horas de ejecución del rojo y del verde son distintas. Debe explicarse ese procedimiento con honestidad, sin reescribir fechas ni afirmar que el commit nació después de la corrida roja.
- **Logs de Producción parecidos:** sus etiquetas son fijas; la semejanza no demuestra reciclaje. Añadir metadatos mejora procedencia.
- **`PENDIENTE-AWS` en promover.sh:** describe correctamente que esa invocación solo empaqueta. No invalida una transferencia posterior documentada. Su cabecera antigua puede aclararse, pero no debe hacer creer que el script despliega automáticamente.
- **`quote=False`:** no se identificó un exploit en su uso actual dentro de texto HTML. Cambiarlo por estética no cierra los huecos prioritarios.
- **Manifiesto 4333a32:** pertenece a la narración histórica de esa release. Se puede rotular mejor y enlazar la vigente; no se encontró un manifiesto final atribuible al commit equivocado.

## 9. Plan de cierre acotado

1. **Hecho localmente:** A-01, A-02, A-03 y A-04 están corregidos en `revision-final-quirurgica` y las pruebas negativas locales pasan.
2. Ejecutar el pipeline real en QA sobre ese commit; solo si queda verde se incorpora a la rama canónica. Mantener las ocho etapas y sus umbrales.
2. Validar esas correcciones en QA. Si cambia el código operativo del pipeline/verificador, emitir un veredicto propio del nuevo commit. Si la aplicación no cambia, no reconstruir imágenes sin necesidad, pero verificar origen e identidad antes de probarlas.
3. Si se adopta una nueva release, promover sus artefactos aprobados y verificar contenedores realmente activos en Producción. Conservar el último respaldo. Documentar cualquier incidencia concreta del destino.
4. Archivar detalles originales disponibles por etapa y las nuevas salidas reales, con metadatos y revisión de secretos. Preservar intacto el rojo histórico.
5. Ejecutar la comprobación pendiente de AWS en lectura; cerrar o declarar cada resultado, especialmente transporte, cifrado efectivo y reglas de acceso.
6. Integrar capturas y diagramas en la plantilla oficial; completar declaración de IA y reflexión personal. No crear una autoevaluación ficticia ni confundir el verificador del Avance 2 con una revisión de la Final.
7. Conservar la evidencia y acordar el cierre del laboratorio conforme a la instrucción del docente. Terminar la EC2 de Producción es una acción separada y destructiva; no se ejecutó en esta auditoría.

## Reproducciones y diagramas de esta revisión

- [Reproducciones locales de formato, verificador, destino QA, T11 y HEALTHCHECK](verificaciones_locales.py).
- [Reproducción de las exclusiones de Gitleaks](comprobar_gitleaks.py).
- [Salida real de las reproducciones locales](resultados_locales.txt).
- [Salida original del escaneo independiente de los 60 commits](escaneo_historial.txt).
- [Arquitectura, PNG](../diagrama_arquitectura.png) · [SVG](../diagrama_arquitectura.svg).
- [Promoción, PNG](../diagrama_promocion.png) · [SVG](../diagrama_promocion.svg).
- [Generador de ambos diagramas](../generar_diagrama.py).

Los cambios documentales se prepararon en la rama aislada `revision-final-quirurgica`; no constituyen una nueva aplicación desplegada. Esta revisión no garantiza una calificación ni la inexistencia de todos los defectos posibles: deja resultados reproducibles, límites concretos y criterios de cierre.

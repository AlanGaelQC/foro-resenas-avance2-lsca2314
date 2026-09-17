# ADR-001 · Decisiones técnicas del Avance 2

Foro y reseñas · LSCA2314
Estado: aceptado · Alcance: Avance 2 (la entrega final puede revisar varias)

Registro de las decisiones que dan forma al proyecto, con lo que se descartó y
por qué. Las decisiones sobre controles del pipeline y sus umbrales están en
`tabla_decisiones_pipeline.md`; aquí van las de la aplicación y su
infraestructura.

---

## 1. FastAPI en vez de Flask

**Decisión.** Backend en FastAPI con Uvicorn.

**Por qué.** La API llama al moderador en medio de cada publicación. Con FastAPI
esa llamada es asíncrona (`httpx.AsyncClient`), así que mientras se espera al
moderador el proceso puede atender otras peticiones. En Flask síncrono cada
publicación bloquea un trabajador durante toda la espera. Además la validación
de tipos de los formularios viene incluida, que es una capa menos de código mío
donde equivocarme.

**Descartado.** Flask, que habría servido igual para el alcance mínimo y es más
conocido; se descartó por el punto de la concurrencia. Django, demasiado marco
para dos modelos y siete rutas.

---

## 2. El moderador es un servicio HTTP, no una biblioteca

**Decisión.** `app/moderador/` es un contenedor aparte con su propia imagen, su
propio `requirements.txt` y su propio `/salud`. La API le habla por HTTP dentro
de la red de compose.

**Por qué.** El tema exige que la pieza distintiva sea un servicio separado, no
una función en el mismo proceso. Más allá del requisito, separarlo tiene tres
efectos reales: el moderador se puede reiniciar sin tirar el foro, sus
dependencias se mantienen al mínimo (cada librería extra ahí es superficie de
ataque sobre la decisión de qué se publica), y su caída es visible y explícita
en vez de convertirse en una excepción dentro de la API.

**Descartado.** Una cola de mensajes entre ambos. Habría desacoplado más, pero
la moderación tiene que ocurrir **antes** de publicar: con una cola el contenido
se publicaría primero y se retiraría después, que es exactamente lo que el tema
pide evitar.

---

## 3. Ante un fallo del moderador, se cierra la puerta

**Decisión.** Si el moderador no responde o responde algo que no se entiende, la
publicación falla con HTTP 503 y no se guarda nada.

**Por qué.** La alternativa es publicar sin revisar cuando el moderador está
caído, lo que convierte cualquier caída —o cualquier saturación provocada a
propósito— en la forma más fácil de meter contenido prohibido al foro. Es
preferible que el usuario reintente en un minuto.

**Descartado.** Un tercer estado "en revisión" con reintento posterior. Es la
solución correcta en un sistema real, pero exige un trabajador en segundo plano
y almacenamiento de pendientes; para el alcance del Avance 2 añade piezas sin
cambiar lo que se demuestra.

---

## 4. Toda publicación pasa por un solo módulo, y una regla lo vigila

**Decisión.** `app/api/moderacion.py` es el único lugar autorizado a devolver el
estado `publicado`. La regla propia `foro-publicacion-sin-moderacion` (etapa 04)
marca como ERROR cualquier asignación de ese estado fuera de ahí.

**Por qué.** La invariante más importante de esta aplicación —nada se publica
sin revisión— no se sostiene sola: basta que alguien escriba `estado="publicado"`
en una ruta nueva para romperla, y leyendo el diff es fácil que pase. Ponerla
como regla del pipeline la vuelve verificable en cada corrida.

**Comprobado.** Al introducir a propósito ese defecto en la ruta de comentarios,
la etapa 04 lo marcó en `app/api/main.py` y la etapa 08 detectó de forma
independiente que un comentario prohibido llegaba a publicarse. Dos controles
distintos, el mismo defecto.

---

## 5. Contraseñas con scrypt de la biblioteca estándar

**Decisión.** `hashlib.scrypt` con sal aleatoria por usuario y comparación en
tiempo constante.

**Por qué.** scrypt exige memoria además de cómputo, lo que encarece el ataque
por diccionario si se filtrara la tabla de usuarios. Está en la biblioteca
estándar, así que no agrega una dependencia más que auditar en la etapa 02.

**Descartado.** bcrypt vía passlib (una dependencia más para algo que ya tengo).
MD5 o SHA-256 a secas, que son rápidos y por eso inadecuados para contraseñas.

---

## 6. Sesión en cookie firmada

**Decisión.** Cookie firmada con `itsdangerous`, con caducidad, `HttpOnly` y
`SameSite=Lax`. La llave sale de `CLAVE_SESION` y no tiene valor por defecto.

**Por qué.** No hace falta una tabla de sesiones para identificar quién hace qué,
que es lo que pide el requisito. `HttpOnly` impide que el JavaScript de la
página lea la cookie si alguna vez hubiera un XSS; `SameSite=Lax` reduce CSRF.
Que la llave no tenga valor por defecto es deliberado: un default silencioso es
la forma más común de terminar firmando sesiones con una llave conocida.

---

## 7. Los adjuntos van a S3, y se sirven prefirmados

**Decisión.** El archivo se valida (tipo, extensión, firma real y tamaño) antes
de moderar. Solo si la reseña se aprueba se sube a S3 con un nombre generado
por el servidor; se entrega por URL prefirmada de 5 minutos a usuarios con
sesión. En la base solo se guarda la clave del objeto.

**Por qué.** Guardar archivos de usuarios en el disco del contenedor los pierde
en cada redespliegue, y guardarlos en la base es caro y lento. El nombre lo
genera el servidor porque el que manda el usuario es texto que él controla. La
URL prefirmada permite tener el bucket completamente privado y aun así mostrar
la imagen.

**Descartado.** Bucket público con URL directa. Es más simple y rompe el
requisito explícito de acceso público bloqueado.

---

## 8. PostgreSQL en RDS, con SQLite solo para desarrollo

**Decisión.** La aplicación persiste en RDS PostgreSQL. `URL_BASE_DATOS` admite
SQLite **únicamente** cuando `ENTORNO=desarrollo`.

**Por qué.** Poder correr la aplicación sin AWS acorta mucho el ciclo de prueba
del código. El alcance queda declarado: SQLite es para desarrollo local y **no
sustituye el requisito de RDS real**; la entrega corre contra RDS y ahí es donde
se toman las evidencias. En cualquier entorno distinto de `desarrollo`, la
aplicación se niega a arrancar sin `URL_BASE_DATOS`.

---

## 9. Pipeline en scripts de bash, sin Jenkins

**Decisión.** Ocho scripts numerados y un orquestador, todo en bash.

**Por qué.** Jenkins en la instancia significa otro contenedor con su propia
memoria y su propia superficie de ataque, en una instancia del Learner Lab que
ya corre dos servicios. Los scripts corren igual en mi máquina, en la instancia
y —sin cambios— dentro de un runner de CI cuando haga falta. El veredicto es el
código de salida, que es lo que cualquier orquestador va a leer después.

**Consecuencia para la entrega final.** Cuando exista la segunda instancia de
Producción, estos mismos scripts se ejecutan ahí sin modificación: lo único que
cambia es el `.env` y la URL de la aplicación.

---

## 10. La imagen base se fija por digest obtenido del propio `docker pull`

**Decisión.** Los Dockerfile parten de `python:3.11-slim` y
`pipeline/fijar_imagen_base.sh` reescribe esa línea como
`python:3.11-slim@sha256:<digest>` con el digest real descargado en la máquina.

**Por qué.** Una etiqueta como `3.11-slim` es móvil: mañana puede apuntar a otra
imagen, y entonces el escaneo de la etapa 06 deja de corresponder a lo que se
despliega. El digest se obtiene de la descarga real en vez de escribirse a mano,
para que el pin sea un dato verificado y no un valor copiado.

---

## 11. Estados explícitos en el pipeline, en vez de solo códigos de salida

**Decisión.** Cada etapa escribe `reportes/estado_NN.json` con uno de cuatro
estados: `OK`, `HALLAZGO`, `ERROR_OPERATIVO` o (por ausencia del archivo)
`NO_EJECUTADO`. La puerta decide leyendo esos archivos.

**Por qué.** Un código de salida distinto de cero no dice si la herramienta
encontró algo o si simplemente no arrancó, y tratar el segundo caso como
"limpio" es la falla clásica de estos pipelines. Con estados separados, un
binario ausente, un timeout o un JSON ilegible bloquean igual que un hallazgo,
y el reporte dice cuál de las dos cosas pasó. La lógica está probada en sus
cuatro casos con `pipeline/probar_puerta.sh`.

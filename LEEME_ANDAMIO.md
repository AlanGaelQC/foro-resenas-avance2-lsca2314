# Cómo usar este andamio

**Este archivo no es parte de la entrega: bórralo antes de subir el repositorio.**

Es el equivalente a lo que hace el profesor con sus andamios: el esqueleto ya
está armado y funcionando, y lo que falta es lo que solo puedes hacer tú en tu
cuenta y en tu instancia.

---

## Qué contiene esta versión

El código fuente y la puerta de control fueron revisados antes de preparar el
paquete. Los resultados definitivos se generarán en la instancia de QA:

| Pieza | Estado |
|---|---|
| Aplicación del foro (FastAPI) | Código preparado; debe validarse contra RDS y S3 reales en QA |
| Servicio de moderación | Código separado con cinco reglas y cierre seguro ante fallos |
| Dockerfile y Dockerfile.moderador | Sin root, con `HEALTHCHECK` y sin secretos; falta construirlos en QA |
| docker-compose.yml | Dos servicios, red interna y límites de privilegios; falta levantarlo en QA |
| Terraform de S3 y RDS | Descripción IaC preparada; la corrida real de Checkov será la evidencia |
| Pipeline de 8 etapas | Controles preparados; sus reportes deben generarse en QA |
| Puerta de control | Probada en sus 4 casos con `pipeline/probar_puerta.sh` |
| Ciclo rojo → verde | Se realizará sobre commits reales en el repositorio de QA |
| Documentación | README, ADR-001, tabla de decisiones, diagrama, guion del video |

## Qué falta, y solo lo puedes hacer tú

1. Crear el bucket S3 y la base RDS en **tu** cuenta de AWS Academy.
2. Construir y levantar los contenedores en **tu** instancia.
3. Generar `reportes/corrida_roja.txt` y `reportes/corrida_verde.txt` ahí.
4. Llenar `docs/declaracion_uso_ia.md` con lo que realmente hiciste.
5. Grabar el video y poner el enlace en `docs/enlace_video.txt`.
6. Llenar el documento de evidencias de la plataforma con las capturas.

---

## Ruta de trabajo, en orden de dependencias

### Paso 1 · Fijar la instancia (15 min)

Decide **una** instancia y no la cambies: el security group de la RDS va a
apuntar a ella, y esa misma instancia será tu entorno de QA en la entrega final.

```bash
# En la instancia, comprueba el punto de partida
cat /etc/os-release | head -2
python3 --version
docker --version && docker compose version
sudo dnf install -y python3.11 git     # Amazon Linux 2023 trae Python 3.9
```

Si Docker no está:

```bash
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
# Cierra la sesion SSH y vuelve a entrar para que el grupo tome efecto
```

### Paso 2 · Crear S3 y RDS (30–45 min, hazlo temprano)

Es lo que más tarda y lo que más se atora, por eso va antes que nada del código.
La RDS tarda varios minutos en quedar disponible.

Lo que tiene que quedar cierto al terminar:

- Bucket privado, **Block all public access** activado, cifrado activado.
- RDS PostgreSQL, **Public access = No**, **Encryption = activado**.
- Un security group de la base que acepte el puerto 5432 **solo** desde el
  security group de tu instancia.
- Tu instancia con el puerto 8080 abierto en su security group (recuerda: la IP
  pública cambia cuando reinicias el Learner Lab).

> Los pasos exactos de la consola cámbialos según lo que veas en pantalla: no
> sigas a ciegas una guía si la consola muestra otra cosa.

Cuando existan, confirma desde la instancia:

```bash
aws s3 ls s3://TU-BUCKET                       # debe responder sin error
nc -zv TU-ENDPOINT-RDS 5432                    # debe conectar
```

### Paso 3 · Configurar y levantar (20 min)

```bash
cp .env.ejemplo .env
nano .env        # bucket, region, URL_BASE_DATOS y CLAVE_SESION

# Genera la llave de sesion, no la inventes a mano:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

bash pipeline/fijar_imagen_base.sh     # fija el digest real de la imagen base
docker compose build
docker compose up -d
docker compose ps                       # moderador en healthy

curl http://localhost:8080/salud
# Esperado: base_datos "ok" y almacenamiento_s3 "ok"
```

Si `/salud` dice `base_datos: inalcanzable`, el problema está en el security
group de la RDS o en `URL_BASE_DATOS`, no en la aplicación.

### Paso 4 · Probar la aplicación a mano (15 min)

Entra a `http://<tu-ip>:8080`, regístrate, publica una reseña con imagen, y
publica una con contenido prohibido para ver el rechazo con su motivo. Deja el
bucket abierto en la consola: el objeto nuevo aparece ahí. **Esa es la captura
que demuestra que S3 se usa de verdad**, no solo que existe.

### Paso 5 · Correr el pipeline (20 min)

```bash
bash pipeline/preparar_herramientas.sh       # una sola vez
bash pipeline/probar_puerta.sh               # 4/4 esperado
bash pipeline/orquestador.sh                 # las 8 etapas
```

Si trivy no se instaló solo, instálalo antes de las corridas de entrega: sin él
la etapa 06 bloquea con `ERROR_OPERATIVO`, que es el comportamiento correcto
pero te impide llegar a verde.

```bash
trivy --version      # comprueba que quedó
```

### Paso 6 · Corrida roja y corrida verde (30 min)

**La corrida roja tiene que salir de un defecto real.** El que ya está
demostrado y funciona:

```bash
git checkout -b demostracion-bloqueo

# En app/api/main.py, funcion comentar(): sustituye el bloque que llama a
# moderacion.decidir_estado() por la asignacion directa:
#     estado=ESTADO_PUBLICADO,
#     motivo_moderacion="",
# (y quita el if del veredicto en la redireccion)

git add -A && git commit -m "Publica comentarios sin esperar al moderador"
docker compose up -d --build
set -o pipefail
bash pipeline/orquestador.sh 2>&1 | tee reportes/corrida_roja.txt
CODIGO_ROJO=${PIPESTATUS[0]}
# Esperado: etapa 04 y etapa 08 en HALLAZGO, DESPLIEGUE BLOQUEADO, salida 1
```

Después remedia la causa (vuelve a llamar al moderador) y:

```bash
git revert --no-edit HEAD      # o deshaz el cambio a mano
docker compose up -d --build
set -o pipefail
bash pipeline/orquestador.sh 2>&1 | tee reportes/corrida_verde.txt
CODIGO_VERDE=${PIPESTATUS[0]}
# Esperado: las 8 etapas en OK, DESPLIEGUE PERMITIDO, salida 0
```

Cada corrida queda además archivada sola en `reportes/corridas/` con su commit.

> No consigas el verde desactivando controles ni bajando umbrales. Si algo no
> pasa, arregla la causa o justifica la excepción por escrito.

### Paso 7 · Documentación y entrega (30 min)

```bash
bash verificar_entrega.sh     # debe llegar a 39/39
```

Antes de subir:

- Llena `docs/declaracion_uso_ia.md` con lo que **tú** hiciste. No lo dejes con
  los `[COMPLETAR]`.
- Pon el enlace del video en `docs/enlace_video.txt`.
- Borra este archivo (`LEEME_ANDAMIO.md`).
- Confirma que `.env` **no** está en el repositorio: `git ls-files | grep env`
  solo debe mostrar `.env.ejemplo`.

---

## Errores que te vas a encontrar (y la salida)

| Síntoma | Causa probable | Salida |
|---|---|---|
| `pip-audit`/`semgrep`/`checkov` no instalan | Python 3.9 del sistema | `sudo dnf install -y python3.11`; el script ya lo busca primero |
| `/salud` dice `base_datos: inalcanzable` | Security group de RDS, o la contraseña tiene caracteres que rompen la URL | Revisa el SG; codifica la contraseña en la URL (`@` → `%40`) |
| `almacenamiento_s3: inalcanzable` | Credenciales del Learner Lab caducadas | Vuelven a generarse al reiniciar el laboratorio: actualiza `.env` |
| La app no arranca: "Falta CLAVE_SESION" | `.env` no cargado | Es deliberado: no hay valor por defecto. Revisa `env_file` en compose |
| El contenedor se queda `unhealthy` | `/salud` responde 503 porque la base no está | Arregla la conexión, no el healthcheck |
| No puedes entrar por el puerto 8080 | La IP pública cambió al reiniciar el lab | Actualiza la regla del security group |
| `docker compose build` se queda sin memoria | Instancia pequeña sin swap o con demasiados procesos | Comprueba `free -h`, activa 2 GiB de swap y construye un servicio a la vez |
| El pipeline tarda mucho | Primera corrida de semgrep y checkov | Normal; las siguientes son más rápidas |

## Conviene saber

- `git` tiene que estar en la instancia **antes** de la corrida roja: la etapa
  01 escanea el historial, y sin `.git` solo revisa el árbol de trabajo.
- Si creaste el bucket y la base por consola o AWS CLI, usa `terraform validate`
  y Checkov sobre la descripción. `terraform plan` solo compara con recursos
  importados al estado; sin importarlos intentaría proponer duplicados.
- Guarda todo lo que hagas: en la entrega final este entorno se convierte en tu
  QA y vas a reconstruir lo mismo en una segunda instancia de Producción.

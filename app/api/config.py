"""
Configuracion de la API del foro.

Regla del Avance 2: cero credenciales en el codigo. Todo valor sensible se lee
de variables de entorno. Si falta una variable obligatoria la aplicacion NO
arranca, en vez de caer a un valor por defecto inseguro (un default silencioso
es la forma mas comun de acabar con una llave debil en produccion).
"""
import os


class ErrorDeConfiguracion(RuntimeError):
    """Falta una variable de entorno obligatoria o tiene un valor invalido."""


def _obligatoria(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ErrorDeConfiguracion(
            f"Falta la variable de entorno obligatoria {nombre}. "
            f"Revisa tu archivo .env (usa .env.ejemplo como guia)."
        )
    return valor


def _opcional(nombre: str, predeterminado: str = "") -> str:
    return os.environ.get(nombre, predeterminado).strip()


# --- Identidad del despliegue -------------------------------------------------
# ENTORNO separa configuracion por ambiente sin cambiar codigo.
ENTORNO = _opcional("ENTORNO", "desarrollo")
ENTORNOS_VALIDOS = {"desarrollo", "qa", "produccion"}
if ENTORNO not in ENTORNOS_VALIDOS:
    raise ErrorDeConfiguracion(
        f"ENTORNO debe ser uno de {sorted(ENTORNOS_VALIDOS)}; se recibio {ENTORNO!r}."
    )

# --- Base de datos ------------------------------------------------------------
# En el entregable apunta a la instancia RDS real (postgresql+psycopg2://...).
# El modo 'desarrollo' permite sqlite SOLO para probar el codigo sin AWS; no
# sustituye el requisito de RDS y asi esta declarado en docs/README.md.
URL_BASE_DATOS = _opcional("URL_BASE_DATOS")
if not URL_BASE_DATOS:
    if ENTORNO == "desarrollo":
        URL_BASE_DATOS = "sqlite:///./foro_desarrollo.db"
    else:
        raise ErrorDeConfiguracion(
            "Falta URL_BASE_DATOS. En ENTORNO distinto de 'desarrollo' debe "
            "apuntar a la base RDS real."
        )
if ENTORNO != "desarrollo" and not URL_BASE_DATOS.startswith(
    ("postgresql://", "postgresql+psycopg2://")
):
    raise ErrorDeConfiguracion(
        "En qa o produccion, URL_BASE_DATOS debe apuntar a PostgreSQL/RDS."
    )

# --- Almacenamiento de objetos (S3) ------------------------------------------
BUCKET_S3 = _opcional("BUCKET_S3")
REGION_AWS = _opcional("REGION_AWS", "us-east-1")
# Conserva las claves existentes de QA. Produccion puede usar otro prefijo
# dentro del mismo bucket, si el Learner Lab permite compartirlo.
PREFIJO_S3 = _opcional("PREFIJO_S3", "adjuntos/")
if not PREFIJO_S3 or PREFIJO_S3.startswith("/") or not PREFIJO_S3.endswith("/") or ".." in PREFIJO_S3:
    raise ErrorDeConfiguracion("PREFIJO_S3 debe ser una ruta relativa terminada en /.")
# Cuando esta vacio, la app opera sin adjuntos (modo degradado explicito).
ALMACENAMIENTO_ACTIVO = bool(BUCKET_S3)
if ENTORNO != "desarrollo" and not ALMACENAMIENTO_ACTIVO:
    raise ErrorDeConfiguracion("BUCKET_S3 es obligatorio en qa o produccion.")

# --- Servicio de moderacion (pieza tecnica distintiva) ------------------------
URL_MODERADOR = _opcional("URL_MODERADOR", "http://moderador:8001")
TIMEOUT_MODERADOR_SEG = float(_opcional("TIMEOUT_MODERADOR_SEG", "5"))

# --- Moderadores (Entrega Final: vista previa enriquecida) --------------------
# Lista de correos autorizados a usar la vista previa del moderador, separados
# por comas. No es un rol en la base: es configuracion por entorno, igual que el
# resto de la app. Un usuario con sesion valida cuyo correo NO este aqui recibe
# 403. Asi "moderador" no es algo que el formulario publico de registro pueda
# otorgarse a si mismo.
MODERADORES = frozenset(
    correo.strip().lower()
    for correo in _opcional("MODERADORES", "").split(",")
    if correo.strip()
)

# Contrasena con la que se aprovisiona la cuenta de cada correo en MODERADORES al
# arrancar. Los correos de moderador quedan RESERVADOS: el registro publico los
# rechaza. Si hay moderadores configurados, esta contrasena es OBLIGATORIA, debe
# ser distinta del marcador y tener al menos 10 caracteres: copiar el .env de
# ejemplo sin sustituirla crearia una cuenta moderadora con contrasena conocida.
MODERADOR_PASS = _opcional("MODERADOR_PASS", "")
if MODERADORES:
    if not MODERADOR_PASS or MODERADOR_PASS == "CAMBIA_ESTE_VALOR" or len(MODERADOR_PASS) < 10:
        raise ErrorDeConfiguracion(
            "Hay MODERADORES configurados pero MODERADOR_PASS falta, es el marcador "
            "de ejemplo o es demasiado corta. Define una contrasena real (>=10 "
            "caracteres) para la cuenta de moderador."
        )

# --- Sesiones -----------------------------------------------------------------
# Sin valor por defecto: una llave de firma predecible permite falsificar la
# cookie de sesion y suplantar a cualquier usuario del foro.
CLAVE_SESION = _obligatoria("CLAVE_SESION")
if len(CLAVE_SESION) < 32 or CLAVE_SESION == "CAMBIA_ESTE_VALOR":
    raise ErrorDeConfiguracion(
        "CLAVE_SESION debe ser aleatoria y tener al menos 32 caracteres."
    )
HORAS_SESION = int(_opcional("HORAS_SESION", "8"))
COOKIE_SEGURA = _opcional("COOKIE_SEGURA", "false").lower() == "true"

# --- Limites de subida de archivos -------------------------------------------
# Riesgo propio del foro: cualquier usuario autenticado sube archivos.
MAX_BYTES_ADJUNTO = int(_opcional("MAX_BYTES_ADJUNTO", str(2 * 1024 * 1024)))
TIPOS_ADJUNTO_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
EXTENSIONES_ADJUNTO_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}

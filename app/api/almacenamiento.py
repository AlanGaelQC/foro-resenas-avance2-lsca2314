"""
Uso real de S3: los adjuntos de las resenas viven en el bucket, no en la base
ni en el disco del contenedor.

El bucket es privado y con acceso publico bloqueado, asi que la imagen no se
sirve por URL publica: se entrega una URL prefirmada de corta duracion, generada
solo para usuarios con sesion valida.
"""
import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import (
    ALMACENAMIENTO_ACTIVO,
    BUCKET_S3,
    EXTENSIONES_ADJUNTO_PERMITIDAS,
    MAX_BYTES_ADJUNTO,
    REGION_AWS,
    TIPOS_ADJUNTO_PERMITIDOS,
)

SEGUNDOS_URL_PREFIRMADA = 300


class ErrorDeAlmacenamiento(RuntimeError):
    pass


class AdjuntoInvalido(ValueError):
    pass


_configuracion = Config(
    region_name=REGION_AWS,
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=10,
    signature_version="s3v4",
)


def _cliente():
    # Las credenciales salen del entorno o del rol de la instancia; nunca del codigo.
    return boto3.client("s3", config=_configuracion)


def validar_adjunto(nombre_archivo: str, tipo_contenido: str, contenido: bytes) -> str:
    """Valida tipo, extension, firma y tamano antes de tocar S3."""
    if len(contenido) == 0:
        raise AdjuntoInvalido("El archivo llego vacio.")
    if len(contenido) > MAX_BYTES_ADJUNTO:
        limite_mb = MAX_BYTES_ADJUNTO / (1024 * 1024)
        raise AdjuntoInvalido(f"El archivo supera el limite de {limite_mb:.1f} MB.")
    if tipo_contenido not in TIPOS_ADJUNTO_PERMITIDOS:
        raise AdjuntoInvalido(f"Tipo de archivo no permitido: {tipo_contenido}")
    extension = Path(nombre_archivo).suffix.lower()
    if extension not in EXTENSIONES_ADJUNTO_PERMITIDAS:
        raise AdjuntoInvalido(f"Extension no permitida: {extension or '(sin extension)'}")

    extensiones_por_tipo = {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "image/webp": {".webp"},
    }
    if extension not in extensiones_por_tipo[tipo_contenido]:
        raise AdjuntoInvalido("La extension no coincide con el tipo declarado.")

    firma_valida = {
        "image/jpeg": contenido.startswith(b"\xff\xd8\xff"),
        "image/png": contenido.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": (
            len(contenido) >= 12
            and contenido.startswith(b"RIFF")
            and contenido[8:12] == b"WEBP"
        ),
    }
    if not firma_valida[tipo_contenido]:
        raise AdjuntoInvalido("El contenido real del archivo no es una imagen permitida.")
    return extension


def subir_adjunto(contenido: bytes, extension: str, tipo_contenido: str) -> str:
    """Sube el adjunto y devuelve su clave en S3."""
    if not ALMACENAMIENTO_ACTIVO:
        raise ErrorDeAlmacenamiento("BUCKET_S3 no esta configurado.")
    # El nombre del archivo lo controla el usuario: no se reutiliza como clave.
    clave = f"adjuntos/{uuid.uuid4().hex}{extension}"
    try:
        _cliente().put_object(
            Bucket=BUCKET_S3,
            Key=clave,
            Body=contenido,
            ContentType=tipo_contenido,
            ServerSideEncryption="AES256",
        )
    except (BotoCoreError, ClientError) as error:
        raise ErrorDeAlmacenamiento(f"No se pudo subir el adjunto a S3: {error}") from error
    return clave


def url_prefirmada(clave: str) -> str:
    if not ALMACENAMIENTO_ACTIVO:
        raise ErrorDeAlmacenamiento("BUCKET_S3 no esta configurado.")
    try:
        return _cliente().generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_S3, "Key": clave},
            ExpiresIn=SEGUNDOS_URL_PREFIRMADA,
        )
    except (BotoCoreError, ClientError) as error:
        raise ErrorDeAlmacenamiento(f"No se pudo firmar la URL del adjunto: {error}") from error


def eliminar_adjunto(clave: str) -> None:
    """Elimina un objeto si la transaccion de base de datos no pudo terminar."""
    if not ALMACENAMIENTO_ACTIVO or not clave:
        return
    try:
        _cliente().delete_object(Bucket=BUCKET_S3, Key=clave)
    except (BotoCoreError, ClientError):
        # La operacion principal ya fallo; el error de limpieza se atiende por
        # el ciclo de vida/monitoreo sin ocultar la causa original.
        return


def revisar_conexion() -> str:
    """Comprueba que el bucket responde. Se usa en /salud."""
    if not ALMACENAMIENTO_ACTIVO:
        return "no_configurado"
    try:
        _cliente().head_bucket(Bucket=BUCKET_S3)
    except (BotoCoreError, ClientError):
        return "inalcanzable"
    return "ok"

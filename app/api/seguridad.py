"""
Registro, inicio de sesion e identificacion del usuario.

Decisiones:
- Derivacion de contrasenas con scrypt (hashlib, biblioteca estandar). No se usa
  MD5/SHA1: son rapidos de calcular y por eso malos para contrasenas. scrypt
  ademas pide memoria, lo que encarece el ataque por diccionario.
- Sesion en cookie firmada (itsdangerous) con caducidad. La cookie no lleva
  datos sensibles, solo el id de usuario, y va firmada con CLAVE_SESION.
"""
import hashlib
import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import CLAVE_SESION, HORAS_SESION

NOMBRE_COOKIE = "sesion_foro"
_SAL_BYTES = 16
_N, _R, _P = 2**14, 8, 1
_LONGITUD_DERIVADA = 32

_firmante = URLSafeTimedSerializer(CLAVE_SESION, salt="sesion-foro-resenas")


def derivar_credencial(contrasena: str) -> str:
    sal = os.urandom(_SAL_BYTES)
    derivado = hashlib.scrypt(
        contrasena.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P, dklen=_LONGITUD_DERIVADA
    )
    return f"scrypt${sal.hex()}${derivado.hex()}"


def verificar_credencial(contrasena: str, credencial_guardada: str) -> bool:
    try:
        algoritmo, sal_hex, derivado_hex = credencial_guardada.split("$")
    except ValueError:
        return False
    if algoritmo != "scrypt":
        return False
    derivado = hashlib.scrypt(
        contrasena.encode("utf-8"),
        salt=bytes.fromhex(sal_hex),
        n=_N,
        r=_R,
        p=_P,
        dklen=_LONGITUD_DERIVADA,
    )
    # Comparacion en tiempo constante: evita distinguir contrasenas por el
    # tiempo que tarda la comparacion byte a byte.
    return hmac.compare_digest(derivado.hex(), derivado_hex)


def crear_token_sesion(usuario_id: int) -> str:
    return _firmante.dumps({"uid": usuario_id})


def leer_token_sesion(token: str):
    """Devuelve el id de usuario o None si la firma es invalida o caduco."""
    if not token:
        return None
    try:
        datos = _firmante.loads(token, max_age=HORAS_SESION * 3600)
    except (BadSignature, SignatureExpired):
        return None
    return datos.get("uid")

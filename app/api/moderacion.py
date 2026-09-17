"""
Cliente del servicio de moderacion (pieza tecnica distintiva del tema 4).

Este modulo es la UNICA ruta legitima por la que un contenido puede quedar en
estado 'publicado'. Las rutas de la API no asignan ese estado por su cuenta:
piden aqui la decision. La regla propia de semgrep
(foro-publicacion-sin-moderacion) hace cumplir esa invariante en el pipeline.

Politica ante fallo: se cierra, no se abre. Si el moderador no responde, el
contenido no se publica y la peticion falla con 503. Publicar sin revisar
cuando el moderador esta caido convertiria una caida en una via de evasion.
"""
from dataclasses import dataclass, field

import httpx

from config import TIMEOUT_MODERADOR_SEG, URL_MODERADOR
from modelos import ESTADO_PUBLICADO, ESTADO_RECHAZADO


class ErrorDeModeracion(RuntimeError):
    """El servicio de moderacion no esta disponible o respondio algo invalido."""


@dataclass
class ResultadoModeracion:
    estado: str
    motivo: str = ""
    reglas: list = field(default_factory=list)


async def decidir_estado(texto: str, titulo: str = "") -> ResultadoModeracion:
    """Consulta al moderador y traduce su veredicto a un estado del foro."""
    carga = {"titulo": titulo, "texto": texto}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_MODERADOR_SEG) as cliente:
            respuesta = await cliente.post(f"{URL_MODERADOR}/moderar", json=carga)
            respuesta.raise_for_status()
            datos = respuesta.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ErrorDeModeracion(
            f"El servicio de moderacion no respondio correctamente: {error}"
        ) from error

    if not isinstance(datos, dict):
        raise ErrorDeModeracion("El moderador devolvio un cuerpo JSON invalido.")

    decision = datos.get("decision")
    if decision == "aprobado":
        return ResultadoModeracion(estado=ESTADO_PUBLICADO)
    if decision == "rechazado":
        reglas = datos.get("reglas_disparadas", [])
        if not isinstance(reglas, list):
            raise ErrorDeModeracion("El moderador devolvio reglas invalidas.")
        return ResultadoModeracion(
            estado=ESTADO_RECHAZADO,
            motivo=str(datos.get("motivo", "Contenido rechazado por moderacion."))[:300],
            reglas=reglas,
        )
    raise ErrorDeModeracion(f"Decision no reconocida del moderador: {decision!r}")


async def revisar_conexion() -> str:
    """Comprueba que el moderador responde. Se usa en /salud."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_MODERADOR_SEG) as cliente:
            respuesta = await cliente.get(f"{URL_MODERADOR}/salud")
            respuesta.raise_for_status()
    except httpx.HTTPError:
        return "inalcanzable"
    return "ok"

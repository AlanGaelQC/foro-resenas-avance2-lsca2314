"""
Servicio de moderacion: la pieza tecnica distintiva del tema "Foro y resenas".

Corre en su propio contenedor y en su propio proceso. La API del foro le pide
una decision ANTES de publicar; el servicio no escribe en la base ni conoce
usuarios: solo recibe texto y devuelve un veredicto con el motivo.

Reglas aplicadas (deliberadamente simples y auditables, no un modelo opaco):
  1. Lexico prohibido   - insultos y terminos de lista negra configurable.
  2. Spam de enlaces    - mas de N URLs en un texto corto.
  3. Datos de contacto  - telefonos y correos, tipicos del spam de resenas.
  4. Griteria           - proporcion alta de mayusculas en textos largos.
  5. Texto vacio        - contenido sin sustancia.
"""
import os
import re

from fastapi import FastAPI
from pydantic import BaseModel, Field

aplicacion = FastAPI(title="Servicio de moderacion", docs_url=None, redoc_url=None)

# Lista configurable por entorno para no tener que reconstruir la imagen.
_LEXICO_PREDETERMINADO = "idiota,estafa,fraude,basura,imbecil"
LEXICO_PROHIBIDO = {
    palabra.strip().lower()
    for palabra in os.environ.get("LEXICO_PROHIBIDO", _LEXICO_PREDETERMINADO).split(",")
    if palabra.strip()
}
MAX_ENLACES = int(os.environ.get("MAX_ENLACES", "2"))
LONGITUD_MINIMA = int(os.environ.get("LONGITUD_MINIMA", "10"))

_PATRON_ENLACE = re.compile(r"https?://|www\.", re.IGNORECASE)
_PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PATRON_TELEFONO = re.compile(r"(?:\+?\d[\d\s\-().]{8,}\d)")
_PATRON_PALABRA = re.compile(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]+")


class PeticionModeracion(BaseModel):
    texto: str = Field(default="", max_length=20000)
    titulo: str = Field(default="", max_length=300)


class RespuestaModeracion(BaseModel):
    decision: str
    motivo: str = ""
    reglas_disparadas: list[str] = []


def _proporcion_mayusculas(texto: str) -> float:
    letras = [caracter for caracter in texto if caracter.isalpha()]
    if len(letras) < 20:
        return 0.0
    mayusculas = [caracter for caracter in letras if caracter.isupper()]
    return len(mayusculas) / len(letras)


def revisar(texto: str, titulo: str = "") -> RespuestaModeracion:
    completo = f"{titulo} {texto}".strip()
    reglas: list[str] = []
    motivos: list[str] = []

    if len(completo) < LONGITUD_MINIMA:
        reglas.append("texto_insuficiente")
        motivos.append(f"El contenido debe tener al menos {LONGITUD_MINIMA} caracteres.")

    palabras = {palabra.lower() for palabra in _PATRON_PALABRA.findall(completo)}
    encontradas = sorted(palabras & LEXICO_PROHIBIDO)
    if encontradas:
        reglas.append("lexico_prohibido")
        motivos.append("El contenido incluye lenguaje no permitido en el foro.")

    if len(_PATRON_ENLACE.findall(completo)) > MAX_ENLACES:
        reglas.append("spam_enlaces")
        motivos.append(f"Se permiten como maximo {MAX_ENLACES} enlaces por publicacion.")

    if _PATRON_CORREO.search(completo) or _PATRON_TELEFONO.search(completo):
        reglas.append("datos_de_contacto")
        motivos.append("No se permiten correos ni telefonos en las resenas.")

    if _proporcion_mayusculas(completo) > 0.7:
        reglas.append("griteria")
        motivos.append("Evita escribir todo en mayusculas.")

    if reglas:
        return RespuestaModeracion(
            decision="rechazado", motivo=" ".join(motivos)[:300], reglas_disparadas=reglas
        )
    return RespuestaModeracion(decision="aprobado")


@aplicacion.post("/moderar", response_model=RespuestaModeracion)
def moderar(peticion: PeticionModeracion) -> RespuestaModeracion:
    return revisar(peticion.texto, peticion.titulo)


@aplicacion.get("/salud")
def salud():
    return {"estado": "vivo", "reglas_activas": 5, "lexico_cargado": len(LEXICO_PROHIBIDO)}

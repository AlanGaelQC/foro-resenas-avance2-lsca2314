"""Formato de la vista previa del moderador: función original y reparación.

La función vulnerable conserva la falla del parche para evidencia histórica. La
ruta activa usa la función que escapa la entrada del usuario.
"""

import html
import re

_PATRON_NEGRITA = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def formatear_vulnerable(texto_original: str) -> str:
    """Parche original portado sin corregir: NO escapa el contenido del usuario."""
    formateado = texto_original.replace("\n", "<br>")
    # Igual que el parche: sustituye pares de ** por <b> ... </b>.
    while "**" in formateado:
        formateado = formateado.replace("**", "<b>", 1)
        formateado = formateado.replace("**", "</b>", 1)
    return formateado


def formatear_seguro(texto_original: str) -> str:
    """
    Remediación: escapa primero, aplica marcado después.

    1. html.escape() convierte < > & " en entidades: cualquier <script> del
       usuario queda inerte como texto.
    2. Sobre el texto YA escapado se aplican solo dos transformaciones
       controladas que emite el servidor, no el usuario: negrita y salto de
       línea. Como el texto entre ** ya está escapado, no puede reintroducir
       etiquetas activas.
    """
    escapado = html.escape(texto_original, quote=False)
    # Negrita: los delimitadores ** los pone el usuario, pero <b>/</b> los emite
    # el servidor sobre contenido ya escapado.
    con_negrita = _PATRON_NEGRITA.sub(lambda m: f"<b>{m.group(1)}</b>", escapado)
    # Salto de línea: el \n del usuario ya no puede ser un <br> inyectado porque
    # cualquier '<' literal quedó como &lt; en el paso de escape.
    return con_negrita.replace("\n", "<br>")

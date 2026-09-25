"""Vista previa del parche del profesor, portada a FastAPI sin corregir el XSS.

El defecto se introduce en QA para probar el pipeline original antes de sumar
la detección específica y la remediación.
"""

def formatear_vulnerable(texto_original: str) -> str:
    """Parche original portado sin corregir: NO escapa el contenido del usuario."""
    formateado = texto_original.replace("\n", "<br>")
    # Igual que el parche: sustituye pares de ** por <b> ... </b>.
    while "**" in formateado:
        formateado = formateado.replace("**", "<b>", 1)
        formateado = formateado.replace("**", "</b>", 1)
    return formateado


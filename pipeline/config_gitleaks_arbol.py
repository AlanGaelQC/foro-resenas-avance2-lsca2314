"""Excluye solo el .env local de QA durante el escaneo del árbol actual.

El historial utiliza directamente .gitleaks.toml, sin esta excepción.
"""

from pathlib import Path
import re
import sys


def preparar(raiz: Path, destino: Path) -> None:
    raiz = raiz.resolve(strict=True)
    original = (raiz / ".gitleaks.toml").read_text(encoding="utf-8")
    marcador = "paths = [\n"
    if original.count(marcador) != 1:
        raise ValueError("la configuración de allowlist no tiene una única lista de rutas")
    ruta_env = re.escape(str(raiz / ".env"))
    if "'" in ruta_env:
        raise ValueError("la ruta del proyecto no admite comillas simples")
    # Gitleaks entrega File como ruta absoluta con --source absoluto. La
    # expresión queda anclada: /proyecto/anidada/.env no coincide.
    temporal = original.replace(marcador, f"paths = [\n  '''^{ruta_env}$''',\n", 1)
    destino.write_text(temporal, encoding="utf-8")


if __name__ == "__main__":
    preparar(Path(sys.argv[1]), Path(sys.argv[2]))

"""Verificación de lectura en la EC2 nueva tras desplegar imágenes aprobadas.

Ejecutar en Producción, donde están Docker, el manifiesto copiado de QA y el
contenedor cargado. No modifica datos ni asume que la base de QA sea Prod.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import httpx


def ejecutar() -> int:
    parser = argparse.ArgumentParser(description="Comprueba identidad y salud de la release en Producción")
    parser.add_argument("url", help="URL de la API de la EC2 nueva")
    parser.add_argument("--manifest", required=True, type=Path, help="Manifest_release.json copiado desde QA")
    parser.add_argument("--tars", required=True, type=Path, help="Directorio con api.tar y moderador.tar descargados")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    resultados = []

    def anotar(nombre: str, ok: bool, detalle: str = "") -> None:
        resultados.append(ok)
        print(f"[{'PASA' if ok else 'FALLA'}] {nombre}" + (f": {detalle}" if detalle else ""))

    try:
        manifiesto = json.loads(args.manifest.read_text(encoding="utf-8"))
        commit = manifiesto["source_commit"]
        for servicio in ("api", "moderador"):
            esperado = manifiesto[f"imagen_{servicio}"]
            if not esperado.get("tag") or not esperado.get("image_id") or not esperado.get("sha256_tar"):
                raise ValueError(f"faltan tag, image_id o sha256_tar de {servicio}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"[FALLA] Manifiesto incompleto o ilegible: {error}")
        return 1
    anotar("Manifiesto de release disponible", True, f"commit {str(commit)[:12]}")

    for servicio in ("api", "moderador"):
        datos = manifiesto[f"imagen_{servicio}"]
        try:
            consulta = subprocess.run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", datos["tag"]],
                capture_output=True, text=True, timeout=10, check=True,
            )
            actual = consulta.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            actual = "imagen no disponible"
        anotar(f"Image ID de {servicio} coincide con QA", actual == datos["image_id"])

        ruta_tar = args.tars / f"{servicio}.tar"
        try:
            hasher = hashlib.sha256()
            with ruta_tar.open("rb") as entrada:
                for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
                    hasher.update(bloque)
            suma = hasher.hexdigest()
        except OSError:
            suma = "no disponible"
        anotar(f"SHA-256 de {servicio}.tar coincide con QA", suma == datos["sha256_tar"])

    try:
        with httpx.Client(timeout=10, follow_redirects=False) as cliente:
            salud = cliente.get(f"{base}/salud")
            datos_salud = salud.json()
            if not isinstance(datos_salud, dict):
                raise ValueError("respuesta de salud inválida")
            anotar("API identifica entorno Producción", salud.status_code == 200 and datos_salud.get("entorno") == "produccion")
            anotar("RDS alcanzable", datos_salud.get("base_datos") == "ok")
            anotar("S3 alcanzable", datos_salud.get("almacenamiento_s3") == "ok")
            dependencias = cliente.get(f"{base}/salud/dependencias")
            anotar("Moderador alcanzable", dependencias.status_code == 200 and dependencias.json().get("moderador") == "ok")
            portada = cliente.get(base + "/")
            anotar("Portada con reseñas disponible", portada.status_code == 200 and "Resenas publicadas" in portada.text)
            restringida = cliente.post(f"{base}/moderacion/resenas/1/vista-previa")
            anotar("Vista del moderador rechaza sesión anónima", restringida.status_code == 403)
            coincidencia = re.search(r'href="(/hilos/\d+)"', portada.text)
            if coincidencia:
                detalle = cliente.get(base + coincidencia.group(1))
                anotar("Detalle de reseña disponible", detalle.status_code == 200)
            else:
                print("[PENDIENTE] La base de Producción no tiene reseñas para verificar el detalle.")
    except (httpx.HTTPError, ValueError, TypeError) as error:
        anotar("Flujos HTTP de Producción", False, str(error))

    print(f"Verificación: {sum(resultados)}/{len(resultados)} controles completados")
    return 0 if all(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(ejecutar())

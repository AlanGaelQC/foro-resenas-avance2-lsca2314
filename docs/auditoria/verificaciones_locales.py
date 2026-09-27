"""Auditoría aislada de la release 0ec86bb: sin Docker, AWS ni datos reales.

Uso: python3 docs/auditoria/verificaciones_locales.py
Los dobles de HTTP/Docker prueban decisiones del código, no un despliegue real.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
from html.parser import HTMLParser
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[2]


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class Respuesta:
    def __init__(self, status=200, datos=None, texto="", headers=None):
        self.status_code = status
        self.datos = datos
        self.text = texto
        self.headers = headers or {}

    def json(self):
        return self.datos


class ParserHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.etiquetas = []

    def handle_starttag(self, tag, attrs):
        self.etiquetas.append((tag, attrs))


def comprobar_formato():
    formato = cargar("formato_auditado", RAIZ / "app/moderador/formato.py")
    cargas = [
        "<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>", "</div><script>alert(1)</script>",
        '**<script>alert(1)</script>**', '" onmouseover=alert(1) x="',
        "&lt;img src=x onerror=alert(1)&gt;", "&#60;script&#62;alert(1)",
        "<iframe srcdoc='<script>alert(1)</script>'></iframe>",
        "**hola**\nsegunda línea", "<<script>script>alert(1)",
        "<a href=javascript:alert(1)>enlace</a>", "**</b><img src=x>**",
        "\x00<script>alert(1)</script>", "**" * 5000,
    ]
    for carga in cargas:
        parser = ParserHTML()
        parser.feed(formato.formatear_seguro(carga))
        assert all(tag in {"b", "br"} and not attrs for tag, attrs in parser.etiquetas)
    assert formato.formatear_seguro("**bien**\nlínea") == "<b>bien</b><br>línea"
    assert "<script>" in formato.formatear_vulnerable(cargas[0])
    print(f"FORMATO: {len(cargas)} entradas sin etiquetas activas; negrita y saltos conservados.")


def comprobar_verificador():
    falso_http = types.ModuleType("httpx")
    falso_http.HTTPError = type("HTTPError", (Exception,), {})
    with patch.dict(sys.modules, {"httpx": falso_http}):
        verificador = cargar("verificador_auditado", RAIZ / "pipeline/verificar_produccion.py")
    with tempfile.TemporaryDirectory(prefix="foro-verificador-") as temporal:
        directorio = Path(temporal)
        manifest = {"source_commit": "0ec86bb5498fc8f91090edf3ec4e77498586644d"}
        for servicio, letra in (("api", "a"), ("moderador", "b")):
            contenido = ("TAR SINTÉTICO " + servicio).encode()
            (directorio / f"{servicio}.tar").write_bytes(contenido)
            manifest[f"imagen_{servicio}"] = {
                "tag": f"foro-resenas-{servicio}:local",
                "image_id": "sha256:" + letra * 64,
                "sha256_tar": hashlib.sha256(contenido).hexdigest(),
            }
        ruta_manifest = directorio / "manifest.json"
        ruta_manifest.write_text(json.dumps(manifest))
        argv = ["verificar", "http://127.0.0.1:8080", "--manifest", str(ruta_manifest), "--tars", str(directorio)]

        def escenario(sin_resenas=False, contenedor_viejo=False, tar_invalido=False, tag_incorrecto=False):
            comandos = []

            class Cliente:
                def __init__(self, **kwargs): pass
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def get(self, url):
                    if url.endswith("/salud"):
                        return Respuesta(datos={"entorno": "produccion", "base_datos": "ok", "almacenamiento_s3": "ok"})
                    if url.endswith("/salud/dependencias"):
                        return Respuesta(datos={"moderador": "ok"})
                    texto = '<section id="titulo-publicaciones"></section>'
                    if not sin_resenas: texto += '<a href="/hilos/1">Reseña</a>'
                    return Respuesta(texto=texto)
                def post(self, url): return Respuesta(status=403)

            def docker(args, **kwargs):
                comandos.append(args)
                if args[:3] == ["docker", "image", "inspect"]:
                    servicio = "api" if "api" in args[-1] else "moderador"
                    actual = manifest[f"imagen_{servicio}"]["image_id"]
                    if tag_incorrecto: actual = "sha256:" + "f" * 64
                elif args[:1] == ["git"]:
                    actual = "0ec86bb5498fc8f91090edf3ec4e77498586644d"
                elif args[:3] == ["docker", "compose", "ps"]:
                    actual = f"contenedor-{args[-1]}"
                elif args[:2] == ["docker", "inspect"]:
                    servicio = "moderador" if "moderador" in args[-1] else "api"
                    letra = "c" if contenedor_viejo else ("b" if servicio == "moderador" else "a")
                    actual = "sha256:" + letra * 64 + "|running|healthy"
                else:
                    raise AssertionError(f"Comando no previsto: {args[0]}")
                return subprocess.CompletedProcess(args, 0, actual + "\n", "")

            if tar_invalido: (directorio / "api.tar").write_bytes(b"TAR ALTERADO")
            salida = io.StringIO()
            with patch.object(falso_http, "Client", Cliente, create=True), patch.object(verificador.subprocess, "run", docker), patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
                codigo = verificador.ejecutar()
            return codigo, salida.getvalue(), comandos

        codigo, salida, _ = escenario()
        assert codigo == 0 and "15/15" in salida
        print("VERIFICADOR/control: escenario completo y coherente => 15/15, salida 0.")
        codigo, salida, comandos = escenario(contenedor_viejo=True)
        assert codigo == 1 and "13/15" in salida and any(c[:2] == ["docker", "inspect"] for c in comandos)
        print("VERIFICADOR/control: contenedor anterior activo => bloqueo; inspección de identidad ejecutada.")
        codigo, salida, _ = escenario(sin_resenas=True)
        assert codigo == 1 and "14/15" in salida and "PENDIENTE" not in salida
        print("VERIFICADOR/control: sin reseñas => falta de detalle bloquea, 15/15 explícito.")
        codigo, _, _ = escenario(tag_incorrecto=True)
        assert codigo == 1
        print("VERIFICADOR/control: Image ID cargado distinto => salida 1.")
        codigo, _, _ = escenario(tar_invalido=True)
        assert codigo == 1
        print("VERIFICADOR/control: TAR alterado => salida 1.")


def comprobar_destino_etapa08():
    llamadas = []
    falso_http = types.ModuleType("httpx")
    falso_http.HTTPError = type("HTTPError", (Exception,), {})

    def get(url, **kwargs):
        if url.endswith("/salud"):
            return Respuesta(datos={"entorno": "produccion", "motor_base_datos": "postgresql", "base_datos": "ok", "almacenamiento_s3": "ok"})
        if url.endswith("/salud/dependencias"):
            return Respuesta(datos={"moderador": "ok"})
        return Respuesta(texto="Página sintética")

    def post(url, **kwargs):
        llamadas.append(url.rsplit(":8080", 1)[-1])
        return Respuesta(status=303, headers={"location": "/hilos/1"})

    class Cliente:
        def __init__(self, **kwargs): self.cookies = {"sesion_foro": "SINTETICA"}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, **kwargs): return get(url, **kwargs)
        def post(self, url, **kwargs): return post(url, **kwargs)

    falso_http.Client, falso_http.get, falso_http.post = Cliente, get, post
    falso_http.Response = Respuesta
    with patch.dict(sys.modules, {"httpx": falso_http}), patch.object(sys, "argv", ["pruebas", "http://127.0.0.1:8080"]):
        pruebas = cargar("flujo_auditado", RAIZ / "pipeline/pruebas_flujo.py")
    pruebas.MODERADOR_PASS = ""
    with contextlib.redirect_stdout(io.StringIO()):
        codigo = pruebas.main()
    assert codigo == 1 and not llamadas
    print("ETAPA08/control: /salud dice produccion => T1 falla antes de cualquier POST.")


def comprobar_t11():
    falso_http = types.ModuleType("httpx")
    falso_http.Client = object
    falso_http.Response = object
    with patch.dict(sys.modules, {"httpx": falso_http}):
        modulo = cargar("flujo_t11_auditado", RAIZ / "pipeline/pruebas_flujo.py")
    marcas = [f"hilo-c{i}" for i in range(4)]
    ajena = '<article class="tarjeta tarjeta-resena"><h3><a href="/hilos/otro">Otro</a></h3><h4>Comentarios (4)</h4></article>'
    correcto, _ = modulo.comprobar_feed("999", marcas, ajena, 200, "")
    assert correcto is False
    tarjeta = '<article class="tarjeta tarjeta-resena"><h3><a href="/hilos/999">Feed</a></h3><h4>Comentarios (4)</h4>' + ''.join(
        f'<p class="comentario-previo">{marca}</p>' for marca in marcas[1:]
    ) + '</article>'
    detalle = '<span class="contador">4</span>' + ''.join(
        '<article class="tarjeta comentario"></article>' for _ in marcas
    ) + ''.join(marcas)
    correcto, cantidad = modulo.comprobar_feed("999", marcas, tarjeta, 200, detalle)
    assert correcto is True and cantidad == 3
    print("T11/control: los tres comentarios del hilo probado y los cuatro del detalle se exigen por tarjeta.")


def comprobar_healthchecks():
    import urllib.request
    from urllib.error import URLError
    for archivo in ("Dockerfile", "Dockerfile.moderador"):
        texto = (RAIZ / archivo).read_text()
        comando = re.search(r'CMD python -c "([^\n]+)"', texto).group(1)
        for disponible in (True, False):
            class Estado:
                status = 200
            with patch.object(urllib.request, "urlopen", return_value=Estado(), side_effect=None if disponible else URLError("fallo sintético")):
                try:
                    exec(compile(comando, archivo, "exec"), {})
                except SystemExit as error:
                    codigo = error.code
                except URLError:
                    codigo = 1
            assert codigo == (0 if disponible else 1)
    print("HEALTHCHECK: ambos consultan /salud; respuesta 200 => éxito, conexión fallida => error.")


if __name__ == "__main__":
    print("PRUEBAS LOCALES SINTÉTICAS: no son evidencia de ejecución en AWS.")
    comprobar_formato()
    comprobar_verificador()
    comprobar_destino_etapa08()
    comprobar_t11()
    comprobar_healthchecks()

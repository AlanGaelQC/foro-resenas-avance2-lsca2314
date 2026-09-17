"""Pruebas HTTP de la aplicacion real para la etapa 08 del pipeline."""
import re
import secrets
import sys
import time
import uuid

import httpx

URL_BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
TIEMPO_ESPERA = 10.0
resultados: list[tuple[str, bool, str]] = []


def registrar(nombre: str, paso: bool, detalle: str = "") -> None:
    resultados.append((nombre, paso, detalle))
    marca = "PASA " if paso else "FALLA"
    print(f"  [{marca}] {nombre}" + (f" -- {detalle}" if detalle else ""))


def nuevo_correo() -> str:
    return f"prueba-{uuid.uuid4().hex[:12]}@example.com"


def esperar_aplicacion(intentos: int = 15) -> bool:
    for _ in range(intentos):
        try:
            respuesta = httpx.get(f"{URL_BASE}/salud", timeout=TIEMPO_ESPERA)
            if respuesta.status_code in (200, 503):
                return True
        except httpx.HTTPError:
            pass
        time.sleep(2)
    return False


def crear_usuario(cliente: httpx.Client, contrasena: str) -> tuple[str, int, int]:
    correo = nuevo_correo()
    registro = cliente.post(
        f"{URL_BASE}/registro",
        data={"correo": correo, "nombre": "Usuario Prueba", "contrasena": contrasena},
    )
    ingreso = cliente.post(
        f"{URL_BASE}/entrar", data={"correo": correo, "contrasena": contrasena}
    )
    return correo, registro.status_code, ingreso.status_code


def id_desde_redireccion(respuesta: httpx.Response) -> str | None:
    coincidencia = re.fullmatch(r"/hilos/(\d+)", respuesta.headers.get("location", ""))
    return coincidencia.group(1) if coincidencia else None


def main() -> int:
    print(f"Pruebas de flujo contra {URL_BASE}")
    if not esperar_aplicacion():
        registrar("La aplicacion responde", False, "no respondio /salud a tiempo")
        return 2

    contrasena = secrets.token_urlsafe(24)

    respuesta = httpx.get(f"{URL_BASE}/salud", timeout=TIEMPO_ESPERA)
    try:
        salud = respuesta.json()
    except ValueError:
        salud = {}
    registrar(
        "T1 QA usa PostgreSQL/RDS y alcanza S3",
        respuesta.status_code == 200
        and salud.get("entorno") == "qa"
        and salud.get("motor_base_datos") == "postgresql"
        and salud.get("base_datos") == "ok"
        and salud.get("almacenamiento_s3") == "ok",
        f"http {respuesta.status_code}; salud={salud}",
    )

    dependencias = httpx.get(
        f"{URL_BASE}/salud/dependencias", timeout=TIEMPO_ESPERA
    )
    try:
        cuerpo_dependencias = dependencias.json()
    except ValueError:
        cuerpo_dependencias = {}
    registrar(
        "T1b El servicio moderador esta disponible",
        dependencias.status_code == 200
        and cuerpo_dependencias.get("moderador") == "ok",
        f"http {dependencias.status_code}",
    )

    respuesta = httpx.post(
        f"{URL_BASE}/hilos",
        data={"titulo": "Intento anonimo", "cuerpo": "Texto suficientemente largo", "calificacion": "5"},
        timeout=TIEMPO_ESPERA,
        follow_redirects=False,
    )
    registrar(
        "T2 Un anonimo no puede publicar",
        respuesta.status_code == 401,
        f"http {respuesta.status_code} (se esperaba 401)",
    )

    marca_sucia = ""
    with httpx.Client(timeout=TIEMPO_ESPERA, follow_redirects=False) as usuario_a:
        _, codigo_registro, codigo_ingreso = crear_usuario(usuario_a, contrasena)
        registrar(
            "T3 Registro e inicio de sesion funcionan",
            codigo_registro == 303
            and codigo_ingreso == 303
            and "sesion_foro" in usuario_a.cookies,
            f"registro={codigo_registro}, ingreso={codigo_ingreso}",
        )

        marca_limpia = uuid.uuid4().hex[:10]
        respuesta_limpia = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={
                "titulo": f"Resena valida {marca_limpia}",
                "cuerpo": "El servicio fue puntual y el trato correcto, lo recomiendo.",
                "calificacion": "5",
            },
        )
        id_hilo = id_desde_redireccion(respuesta_limpia)
        portada = httpx.get(URL_BASE, timeout=TIEMPO_ESPERA).text
        registrar(
            "T4 El contenido aprobado aparece en la portada",
            respuesta_limpia.status_code == 303
            and id_hilo is not None
            and marca_limpia in portada,
            f"http {respuesta_limpia.status_code}",
        )

        marca_sucia = uuid.uuid4().hex[:10]
        respuesta_sucia = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={
                "titulo": f"Reclamo {marca_sucia}",
                "cuerpo": "Esto es una estafa y son unos imbecil, no vuelvo nunca.",
                "calificacion": "1",
            },
        )
        portada = httpx.get(URL_BASE, timeout=TIEMPO_ESPERA).text
        propias = usuario_a.get(f"{URL_BASE}/mis-publicaciones").text
        registrar(
            "T5 El moderador impide publicar contenido prohibido",
            respuesta_sucia.status_code == 303
            and respuesta_sucia.headers.get("location") == "/mis-publicaciones"
            and marca_sucia not in portada,
        )
        registrar(
            "T5b El autor ve el rechazo y su motivo",
            marca_sucia in propias
            and "rechazado" in propias
            and "lenguaje no permitido" in propias,
        )

        marca_xss = uuid.uuid4().hex[:10]
        carga_xss = f"<script>alert('{marca_xss}')</script> muy buena atencion en general"
        respuesta_xss = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={"titulo": f"Prueba render {marca_xss}", "cuerpo": carga_xss, "calificacion": "4"},
        )
        id_xss = id_desde_redireccion(respuesta_xss)
        pagina_xss = (
            httpx.get(f"{URL_BASE}/hilos/{id_xss}", timeout=TIEMPO_ESPERA).text
            if id_xss
            else ""
        )
        registrar(
            "T6 El contenido se publica escapado y no ejecutable",
            respuesta_xss.status_code == 303
            and marca_xss in pagina_xss
            and "&lt;script&gt;" in pagina_xss
            and "<script>" not in pagina_xss,
        )

        if id_hilo:
            marca_comentario = uuid.uuid4().hex[:10]
            respuesta_comentario = usuario_a.post(
                f"{URL_BASE}/hilos/{id_hilo}/comentarios",
                data={"cuerpo": f"que estafa {marca_comentario}, son unos imbecil"},
            )
            pagina_hilo = httpx.get(
                f"{URL_BASE}/hilos/{id_hilo}", timeout=TIEMPO_ESPERA
            ).text
            propias = usuario_a.get(f"{URL_BASE}/mis-publicaciones").text
            registrar(
                "T6b El moderador rechaza tambien comentarios",
                respuesta_comentario.status_code == 303
                and respuesta_comentario.headers.get("location") == "/mis-publicaciones"
                and marca_comentario not in pagina_hilo
                and marca_comentario in propias
                and "lenguaje no permitido" in propias,
            )
        else:
            registrar("T6b El moderador rechaza tambien comentarios", False, "sin hilo objetivo")

        respuesta = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={"titulo": "Rango invalido", "cuerpo": "Texto suficientemente largo", "calificacion": "9"},
        )
        registrar(
            "T7 Se rechaza una calificacion fuera del rango 1-5",
            respuesta.status_code == 400,
            f"http {respuesta.status_code}",
        )

        respuesta = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={"titulo": "Adjunto falso", "cuerpo": "Texto suficientemente largo", "calificacion": "3"},
            files={"adjunto": ("falsa.png", b"esto no es una imagen", "image/png")},
        )
        registrar(
            "T8 Se rechaza un archivo cuya firma no es de imagen",
            respuesta.status_code == 400,
            f"http {respuesta.status_code}",
        )

        marca_s3 = uuid.uuid4().hex[:10]
        png_minimo = b"\x89PNG\r\n\x1a\n" + b"evidencia-foro"
        respuesta_s3 = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={
                "titulo": f"Resena con imagen {marca_s3}",
                "cuerpo": "Publicacion valida con un adjunto almacenado de forma privada.",
                "calificacion": "5",
            },
            files={"adjunto": ("evidencia.png", png_minimo, "image/png")},
        )
        id_s3 = id_desde_redireccion(respuesta_s3)
        adjunto = usuario_a.get(f"{URL_BASE}/adjunto/{id_s3}") if id_s3 else None
        registrar(
            "T8b Un adjunto valido se guarda en S3 y genera URL prefirmada",
            respuesta_s3.status_code == 303
            and adjunto is not None
            and adjunto.status_code == 303
            and "X-Amz-" in adjunto.headers.get("location", ""),
        )

    with httpx.Client(timeout=TIEMPO_ESPERA, follow_redirects=False) as usuario_b:
        _, codigo_registro_b, codigo_ingreso_b = crear_usuario(usuario_b, contrasena)
        publicaciones_b = usuario_b.get(f"{URL_BASE}/mis-publicaciones").text
        registrar(
            "T9 Un usuario no ve rechazos de otro usuario",
            codigo_registro_b == 303
            and codigo_ingreso_b == 303
            and "sesion_foro" in usuario_b.cookies
            and marca_sucia not in publicaciones_b,
        )

    total = len(resultados)
    fallidas = [nombre for nombre, paso, _ in resultados if not paso]
    print("")
    print(f"Resultado: {total - len(fallidas)}/{total} pruebas pasaron")
    if fallidas:
        print("Pruebas fallidas:")
        for nombre in fallidas:
            print(f"  - {nombre}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

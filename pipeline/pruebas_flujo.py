"""Pruebas HTTP de la aplicacion real para la etapa 08 del pipeline."""
import os
import re
import secrets
import struct
import sys
import time
import uuid
import zlib

import httpx

URL_BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
TIEMPO_ESPERA = 10.0
# Correo del moderador de prueba. Debe coincidir con un correo listado en la
# variable de entorno MODERADORES del despliegue de QA para que T10b/c/d puedan
# ejercer la vista previa autorizada.
MODERADOR_PRUEBA = os.environ.get("MODERADOR_PRUEBA", "moderador.prueba@example.com")
# Contrasena de la cuenta de moderador preaprovisionada en QA (misma que la app
# usa para sembrarla, MODERADOR_PASS). No se registra por el formulario publico.
MODERADOR_PASS = os.environ.get("MODERADOR_PASS", "")
resultados: list[tuple[str, bool, str]] = []


def registrar(nombre: str, paso: bool, detalle: str = "") -> None:
    resultados.append((nombre, paso, detalle))
    marca = "PASA " if paso else "FALLA"
    print(f"  [{marca}] {nombre}" + (f" -- {detalle}" if detalle else ""))


def nuevo_correo() -> str:
    return f"prueba-{uuid.uuid4().hex[:12]}@example.com"


def imagen_png_prueba() -> bytes:
    """PNG decodificable (32x16), para comprobar la imagen desde el navegador."""
    def bloque(tipo: bytes, datos: bytes) -> bytes:
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos)))

    cabecera = struct.pack(">2I5B", 32, 16, 8, 2, 0, 0, 0)
    filas = b"".join(b"\x00" + bytes((24, 156, 126)) * 32 for _ in range(16))
    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", cabecera)
            + bloque(b"IDAT", zlib.compress(filas)) + bloque(b"IEND", b""))


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


def tarjeta_de_hilo(portada: str, identificador: str | None) -> str:
    """Extrae la tarjeta principal del hilo, sin mezclar comentarios de otros."""
    if identificador is None:
        return ""
    tarjetas = re.findall(
        r'<article class="tarjeta tarjeta-resena">(.*?)</article>',
        portada, re.DOTALL,
    )
    return next((tarjeta for tarjeta in tarjetas
                 if f'href="/hilos/{identificador}"' in tarjeta), "")


def comentarios_visibles(tarjeta: str) -> list[str]:
    return re.findall(r'<p class="comentario-previo">(.*?)</p>', tarjeta, re.DOTALL)


def comprobar_feed(id_hilo: str | None, marcas: list[str], portada: str,
                   codigo_detalle: int, detalle: str) -> tuple[bool, int]:
    tarjeta = tarjeta_de_hilo(portada, id_hilo)
    muestras = comentarios_visibles(tarjeta)
    correcto = (
        id_hilo is not None and len(marcas) == 4 and len(muestras) == 3
        and all(marca in " ".join(muestras) for marca in marcas[1:])
        and marcas[0] not in tarjeta and "Comentarios (4)" in tarjeta
        and codigo_detalle == 200 and '<span class="contador">4</span>' in detalle
        and all(marca in detalle for marca in marcas)
        and len(re.findall(r'<article class="tarjeta comentario">', detalle)) == 4
    )
    return correcto, len(muestras)


def main() -> int:
    print(f"Pruebas de flujo contra {URL_BASE}")
    if not esperar_aplicacion():
        registrar("La aplicacion responde", False, "no respondio /salud a tiempo")
        return 2

    try:
        respuesta = httpx.get(f"{URL_BASE}/salud", timeout=TIEMPO_ESPERA)
        salud = respuesta.json()
        if not isinstance(salud, dict):
            raise ValueError("respuesta de salud inválida")
    except (httpx.HTTPError, ValueError, TypeError):
        registrar("T1 QA usa PostgreSQL/RDS y alcanza S3", False,
                  "no se pudo establecer la identidad del entorno antes de escribir")
        return 2
    qa_valida = (
        respuesta.status_code == 200
        and salud.get("entorno") == "qa"
        and salud.get("motor_base_datos") == "postgresql"
        and salud.get("base_datos") == "ok"
        and salud.get("almacenamiento_s3") == "ok"
    )
    registrar(
        "T1 QA usa PostgreSQL/RDS y alcanza S3",
        qa_valida,
        f"http {respuesta.status_code}; entorno={salud.get('entorno')}",
    )
    if not qa_valida:
        print("ALTO: la etapa 08 no escribe datos fuera de QA o sin salud confirmada.")
        return 1

    contrasena = secrets.token_urlsafe(24)

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
    id_xss = None
    marca_xss = ""
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
        carga_xss = f"<script>alert('{marca_xss}')</script> **muy buena** atencion en general"
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
        png_minimo = imagen_png_prueba()
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

        if id_s3:
            portada_imagen = httpx.get(URL_BASE, timeout=TIEMPO_ESPERA).text
            detalle_imagen = httpx.get(
                f"{URL_BASE}/hilos/{id_s3}", timeout=TIEMPO_ESPERA
            ).text
            imagen_publica = httpx.get(
                f"{URL_BASE}/imagen/{id_s3}", timeout=TIEMPO_ESPERA,
                follow_redirects=False,
            )
            imagen_visible = (
                f'<img src="/imagen/{id_s3}"' in tarjeta_de_hilo(portada_imagen, id_s3)
                and f'<img src="/imagen/{id_s3}"' in detalle_imagen
                and imagen_publica.status_code == 200
                and imagen_publica.headers.get("content-type") == "image/png"
                and imagen_publica.headers.get("cache-control") == "no-store"
                and "location" not in imagen_publica.headers
                and imagen_publica.content == png_minimo
            )
        else:
            imagen_visible = False
        registrar(
            "T8c La imagen publicada aparece en portada y detalle sin sesion",
            imagen_visible,
        )
        sin_imagen = httpx.get(
            f"{URL_BASE}/imagen/{id_hilo}", timeout=TIEMPO_ESPERA
        ) if id_hilo else None
        registrar(
            "T8d Un hilo sin imagen no publica un adjunto",
            sin_imagen is not None and sin_imagen.status_code == 404,
        )

        # T11 - Feed publico: exige 3 comentarios recientes de ESTE hilo y 4
        # en su detalle. Verifica tambien los casos de cero y uno sin depender
        # del contador de otras tarjetas.
        tarjeta_vacia = tarjeta_de_hilo(httpx.get(URL_BASE, timeout=TIEMPO_ESPERA).text, id_hilo)
        detalle_vacio = usuario_a.get(f"{URL_BASE}/hilos/{id_hilo}") if id_hilo else None
        registrar(
            "T11a Un hilo nuevo muestra cero comentarios",
            bool(tarjeta_vacia) and not comentarios_visibles(tarjeta_vacia)
            and 'Ver reseña y 0 comentario(s)' in tarjeta_vacia
            and detalle_vacio is not None and detalle_vacio.status_code == 200
            and '<span class="contador">0</span>' in detalle_vacio.text,
        )

        if id_hilo:
            marca_unica = uuid.uuid4().hex[:10]
            respuesta_unica = usuario_a.post(
                f"{URL_BASE}/hilos/{id_hilo}/comentarios",
                data={"cuerpo": f"comentario de prueba {marca_unica}"},
            )
            tarjeta_unica = tarjeta_de_hilo(httpx.get(URL_BASE, timeout=TIEMPO_ESPERA).text, id_hilo)
            detalle_unico = usuario_a.get(f"{URL_BASE}/hilos/{id_hilo}")
            muestra_unica = comentarios_visibles(tarjeta_unica)
            un_comentario = (
                respuesta_unica.status_code == 303
                and len(muestra_unica) == 1 and marca_unica in muestra_unica[0]
                and 'Comentarios (1)' in tarjeta_unica
                and detalle_unico.status_code == 200
                and '<span class="contador">1</span>' in detalle_unico.text
                and marca_unica in detalle_unico.text
            )
        else:
            un_comentario = False
        registrar("T11b Un comentario aparece en portada y detalle", un_comentario)

        marca_feed = uuid.uuid4().hex[:8]
        r_feed = usuario_a.post(
            f"{URL_BASE}/hilos",
            data={
                "titulo": f"Feed {marca_feed}",
                "cuerpo": "Resena limpia para probar el feed publico con comentarios.",
                "calificacion": "5",
            },
        )
        id_feed = id_desde_redireccion(r_feed)
        marcas_c = []
        if id_feed:
            for i in range(4):
                mc = f"{marca_feed}c{i}"
                marcas_c.append(mc)
                usuario_a.post(
                    f"{URL_BASE}/hilos/{id_feed}/comentarios",
                    data={"cuerpo": f"comentario de prueba numero {i} {mc}"},
                )
        portada_feed = httpx.get(URL_BASE, timeout=TIEMPO_ESPERA).text
        detalle_feed = usuario_a.get(f"{URL_BASE}/hilos/{id_feed}") if id_feed else None
        feed_correcto, cantidad_muestra = comprobar_feed(
            id_feed, marcas_c, portada_feed,
            detalle_feed.status_code if detalle_feed else 0,
            detalle_feed.text if detalle_feed else "",
        )
        registrar(
            "T11 El feed muestra los 3 recientes de este hilo y 4 en detalle",
            feed_correcto,
            f"comentarios propios mostrados en portada: {cantidad_muestra}",
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

        # T10 - Un correo de moderador esta RESERVADO: el registro publico lo
        # rechaza, para que nadie se autoasigne el rol registrandolo primero.
        reserva = usuario_b.post(
            f"{URL_BASE}/registro",
            data={
                "correo": MODERADOR_PRUEBA,
                "nombre": "Intruso",
                "contrasena": secrets.token_urlsafe(24),
            },
        )
        registrar(
            "T10 El registro publico rechaza los correos de moderador",
            reserva.status_code == 403,
            f"http {reserva.status_code} (se esperaba 403)",
        )

        # T10b - Autorizacion: un usuario comun NO puede abrir la vista previa de
        # una resena. Debe recibir 403 aunque tenga sesion. Usa la resena con
        # XSS que escribio el usuario A (id_xss).
        objetivo = id_xss or 1
        acceso_no_mod = usuario_b.post(
            f"{URL_BASE}/moderacion/resenas/{objetivo}/vista-previa"
        )
        registrar(
            "T10b Un usuario comun no accede a la vista previa del moderador",
            acceso_no_mod.status_code == 403,
            f"http {acceso_no_mod.status_code} (se esperaba 403)",
        )

    # --- Vista previa del moderador con DOS identidades ---------------------
    # El moderador es una cuenta preaprovisionada (correo en MODERADORES,
    # contrasena en MODERADOR_PASS). NO se registra por el formulario publico. El
    # moderador previsualiza la resena con <script> que escribio OTRO usuario
    # (el usuario A, id_xss): ese es el vector real (XSS almacenado).
    if not MODERADOR_PASS:
        registrar(
            "T10c Vista previa del moderador (XSS, dos identidades)",
            False,
            "falta configurar MODERADOR_PASS para la cuenta de moderador de prueba",
        )
    elif id_xss is None:
        registrar(
            "T10c Vista previa del moderador (XSS, dos identidades)",
            False,
            "no se pudo crear la resena objetivo del usuario A",
        )
    else:
        with httpx.Client(timeout=TIEMPO_ESPERA, follow_redirects=False) as moderador:
            ingreso_mod = moderador.post(
                f"{URL_BASE}/entrar",
                data={"correo": MODERADOR_PRUEBA, "contrasena": MODERADOR_PASS},
            )
            sesion_mod_ok = (
                ingreso_mod.status_code == 303 and "sesion_foro" in moderador.cookies
            )
            registrar(
                "T10c El moderador preaprovisionado inicia sesion",
                sesion_mod_ok,
                f"ingreso={ingreso_mod.status_code} "
                f"(cuenta {MODERADOR_PRUEBA} debe existir en QA)",
            )

            previa = moderador.post(
                f"{URL_BASE}/moderacion/resenas/{id_xss}/vista-previa"
            )
            cuerpo_previa = previa.text if previa.status_code == 200 else ""
            # Seguridad: el <script> del usuario A debe volver ESCAPADO, no crudo.
            # Rojo (formatear_vulnerable): falla. Verde (formatear_seguro): pasa.
            registrar(
                "T10d La vista previa NO ejecuta el contenido del autor (XSS almacenado)",
                previa.status_code == 200
                and "<script>" not in cuerpo_previa
                and f"&lt;script&gt;alert('{marca_xss}')&lt;/script&gt;" in cuerpo_previa,
                f"http {previa.status_code}",
            )
            # Formato: la remediacion conserva la negrita pedida por el producto.
            registrar(
                "T10e La vista previa conserva el formato enriquecido (negrita)",
                "<b>muy buena</b>" in cuerpo_previa,
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

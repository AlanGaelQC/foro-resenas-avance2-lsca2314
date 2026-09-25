"""
API del foro de resenas (Avance 2 - LSCA2314).

Flujo completo: registro -> inicio de sesion -> publicar resena (con adjunto
opcional en S3) -> el servicio de moderacion decide si se publica o se marca
como rechazada -> comentarios sobre la resena, que pasan por la misma revision.
"""
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import almacenamiento
import moderacion
from config import (
    ENTORNO,
    COOKIE_SEGURA,
    ErrorDeConfiguracion,
    HORAS_SESION,
    MAX_BYTES_ADJUNTO,
    MODERADORES,
    MODERADOR_PASS,
    URL_BASE_DATOS,
)
from db import obtener_sesion, crear_tablas
from modelos import Comentario, ESTADO_PUBLICADO, ESTADO_RECHAZADO, Hilo, Usuario
from seguridad import (
    NOMBRE_COOKIE,
    crear_token_sesion,
    derivar_credencial,
    leer_token_sesion,
    verificar_credencial,
)

aplicacion = FastAPI(title="Foro y resenas", docs_url=None, redoc_url=None)
_PLANTILLAS = Jinja2Templates(directory=str(Path(__file__).parent / "plantillas"))
# autoescape viene activado por defecto en Jinja2 para .html: el contenido que
# escribe un usuario del foro se escapa al renderizarse (defensa contra XSS).


@aplicacion.on_event("startup")
def preparar_base():
    crear_tablas()
    _sembrar_moderadores()


def _sembrar_moderadores():
    """
    Aprovisiona la(s) cuenta(s) de moderador de forma administrativa, no por el
    registro publico.

    Para cada correo de MODERADORES:
      - Si no existe: se crea con MODERADOR_PASS.
      - Si existe y su credencial coincide con MODERADOR_PASS: es nuestra cuenta
        sembrada, se deja como esta (idempotente).
      - Si existe pero su credencial NO coincide: es una cuenta preexistente que
        alguien creo antes del allowlist (un okupa). NO se le concede el permiso
        en silencio: se DETIENE el arranque, para que se resuelva a mano.

    Asi el allowlist no autoriza a una cuenta cuya procedencia no es la siembra.
    """
    if not MODERADOR_PASS or not MODERADORES:
        return
    from db import SesionLocal

    sesion = SesionLocal()
    try:
        for correo in MODERADORES:
            existe = sesion.scalar(select(Usuario).where(Usuario.correo == correo))
            if existe is None:
                sesion.add(
                    Usuario(
                        correo=correo,
                        nombre="Moderador",
                        credencial=derivar_credencial(MODERADOR_PASS),
                    )
                )
            elif not verificar_credencial(MODERADOR_PASS, existe.credencial):
                raise ErrorDeConfiguracion(
                    f"El correo de moderador {correo} ya existe con una credencial "
                    f"que no fue sembrada por esta configuracion. No se le concede "
                    f"el permiso de moderador. Revisa y resuelve esa cuenta antes "
                    f"de activar el allowlist en esta base."
                )
        sesion.commit()
    except SQLAlchemyError:
        sesion.rollback()
    finally:
        sesion.close()


# --- Utilidades de sesion -----------------------------------------------------

def usuario_actual(peticion: Request, sesion: Session) -> Usuario | None:
    identificador = leer_token_sesion(peticion.cookies.get(NOMBRE_COOKIE, ""))
    if identificador is None:
        return None
    return sesion.get(Usuario, identificador)


def _exigir_sesion(peticion: Request, sesion: Session) -> Usuario | None:
    return usuario_actual(peticion, sesion)


def _es_moderador(usuario: Usuario | None) -> bool:
    """
    Autorizacion de moderador: sesion valida Y correo en la lista MODERADORES.

    Una sesion iniciada por si sola NO basta: se comprueba la pertenencia en el
    servidor. La lista viene de configuracion por entorno, no de un campo que el
    registro publico pueda asignarse.
    """
    return usuario is not None and usuario.correo.lower() in MODERADORES


def _redirigir(destino: str) -> RedirectResponse:
    return RedirectResponse(url=destino, status_code=303)


# --- Salud --------------------------------------------------------------------

@aplicacion.get("/salud")
def salud(sesion: Session = Depends(obtener_sesion)):
    """
    Indica si la aplicacion esta viva y si alcanza sus dependencias.

    Alcance declarado: este endpoint NO prueba autenticacion ni los flujos de
    negocio. Esas comprobaciones las hace la etapa 08 del pipeline.
    """
    estado_base = "ok"
    try:
        sesion.execute(select(1))
    except SQLAlchemyError:
        estado_base = "inalcanzable"

    estado_almacenamiento = almacenamiento.revisar_conexion()

    cuerpo = {
        "estado": "vivo",
        "entorno": ENTORNO,
        "motor_base_datos": "postgresql" if URL_BASE_DATOS.startswith("postgresql") else "sqlite",
        "base_datos": estado_base,
        "almacenamiento_s3": estado_almacenamiento,
    }
    almacenamiento_requerido_ok = (
        estado_almacenamiento == "ok" if ENTORNO != "desarrollo" else True
    )
    codigo = 200 if estado_base == "ok" and almacenamiento_requerido_ok else 503
    return JSONResponse(content=cuerpo, status_code=codigo)


@aplicacion.get("/salud/dependencias")
async def salud_dependencias():
    """Salud extendida: incluye el servicio de moderacion."""
    estado_moderador = await moderacion.revisar_conexion()
    codigo = 200 if estado_moderador == "ok" else 503
    return JSONResponse(content={"moderador": estado_moderador}, status_code=codigo)


# --- Registro e inicio de sesion ---------------------------------------------

@aplicacion.get("/registro", response_class=HTMLResponse)
def formulario_registro(peticion: Request):
    return _PLANTILLAS.TemplateResponse(peticion, "registro.html", {"error": ""})


@aplicacion.post("/registro")
def registrar(
    peticion: Request,
    correo: str = Form(...),
    nombre: str = Form(...),
    contrasena: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
):
    correo = correo.strip().lower()
    if len(contrasena) < 10:
        return _PLANTILLAS.TemplateResponse(
            peticion,
            "registro.html",
            {"error": "La contrasena debe tener al menos 10 caracteres."},
            status_code=400,
        )
    # Los correos de moderador estan RESERVADOS: se aprovisionan por via
    # administrativa (arranque), no por este formulario. Sin esto, quien
    # registrara primero un correo del allowlist obtendria acceso de moderador.
    if correo in MODERADORES:
        return _PLANTILLAS.TemplateResponse(
            peticion,
            "registro.html",
            {"error": "Ese correo esta reservado."},
            status_code=403,
        )
    usuario = Usuario(
        correo=correo,
        nombre=nombre.strip()[:80],
        credencial=derivar_credencial(contrasena),
    )
    sesion.add(usuario)
    try:
        sesion.commit()
    except IntegrityError:
        sesion.rollback()
        return _PLANTILLAS.TemplateResponse(
            peticion,
            "registro.html",
            {"error": "Ese correo ya esta registrado."},
            status_code=409,
        )
    return _redirigir("/entrar")


@aplicacion.get("/entrar", response_class=HTMLResponse)
def formulario_entrar(peticion: Request):
    return _PLANTILLAS.TemplateResponse(peticion, "entrar.html", {"error": ""})


@aplicacion.post("/entrar")
def entrar(
    peticion: Request,
    correo: str = Form(...),
    contrasena: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == correo.strip().lower()))
    # Mismo mensaje para correo inexistente y contrasena incorrecta: no se le
    # dice al atacante cuales correos existen en el foro.
    if usuario is None or not verificar_credencial(contrasena, usuario.credencial):
        return _PLANTILLAS.TemplateResponse(
            peticion,
            "entrar.html",
            {"error": "Correo o contrasena incorrectos."},
            status_code=401,
        )
    respuesta = _redirigir("/")
    respuesta.set_cookie(
        NOMBRE_COOKIE,
        crear_token_sesion(usuario.id),
        max_age=HORAS_SESION * 3600,
        httponly=True,       # el JavaScript de la pagina no puede leer la cookie
        samesite="lax",      # reduce CSRF en peticiones desde otros sitios
        secure=COOKIE_SEGURA,
    )
    return respuesta


@aplicacion.post("/salir")
def salir():
    respuesta = _redirigir("/")
    respuesta.delete_cookie(NOMBRE_COOKIE)
    return respuesta


# --- Listado de resenas -------------------------------------------------------

@aplicacion.get("/", response_class=HTMLResponse)
def portada(peticion: Request, sesion: Session = Depends(obtener_sesion)):
    hilos = sesion.scalars(
        select(Hilo).where(Hilo.estado == ESTADO_PUBLICADO).order_by(Hilo.creado_en.desc())
    ).all()
    promedio = sesion.scalar(
        select(func.avg(Hilo.calificacion)).where(Hilo.estado == ESTADO_PUBLICADO)
    )
    return _PLANTILLAS.TemplateResponse(
        peticion,
        "portada.html",
        {
            "hilos": hilos,
            "promedio": round(promedio, 2) if promedio else None,
            "usuario": usuario_actual(peticion, sesion),
        },
    )


@aplicacion.get("/hilos/{hilo_id}", response_class=HTMLResponse)
def ver_hilo(hilo_id: int, peticion: Request, sesion: Session = Depends(obtener_sesion)):
    hilo = sesion.get(Hilo, hilo_id)
    if hilo is None or hilo.estado != ESTADO_PUBLICADO:
        return _PLANTILLAS.TemplateResponse(
            peticion, "no_encontrado.html", {}, status_code=404
        )
    comentarios = sesion.scalars(
        select(Comentario)
        .where(Comentario.hilo_id == hilo.id, Comentario.estado == ESTADO_PUBLICADO)
        .order_by(Comentario.creado_en.asc())
    ).all()
    return _PLANTILLAS.TemplateResponse(
        peticion,
        "hilo.html",
        {
            "hilo": hilo,
            "comentarios": comentarios,
            "usuario": usuario_actual(peticion, sesion),
        },
    )


# --- Publicacion de resenas ---------------------------------------------------

@aplicacion.post("/hilos")
async def crear_hilo(
    peticion: Request,
    titulo: str = Form(...),
    cuerpo: str = Form(...),
    calificacion: int = Form(...),
    adjunto: UploadFile | None = File(None),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = _exigir_sesion(peticion, sesion)
    if usuario is None:
        return JSONResponse({"error": "Necesitas iniciar sesion."}, status_code=401)
    if not 1 <= calificacion <= 5:
        return JSONResponse({"error": "La calificacion debe ir de 1 a 5."}, status_code=400)

    contenido_adjunto = None
    extension_adjunto = None
    tipo_adjunto = None
    if adjunto is not None and adjunto.filename:
        # Lee como maximo un byte por encima del limite para no cargar en RAM
        # un archivo arbitrariamente grande antes de rechazarlo.
        contenido_adjunto = await adjunto.read(MAX_BYTES_ADJUNTO + 1)
        try:
            tipo_adjunto = adjunto.content_type or ""
            extension_adjunto = almacenamiento.validar_adjunto(
                adjunto.filename, tipo_adjunto, contenido_adjunto
            )
        except almacenamiento.AdjuntoInvalido as error:
            return JSONResponse({"error": str(error)}, status_code=400)

    try:
        veredicto = await moderacion.decidir_estado(cuerpo, titulo)
    except moderacion.ErrorDeModeracion as error:
        return JSONResponse({"error": str(error)}, status_code=503)

    clave_s3 = None
    if veredicto.estado == ESTADO_PUBLICADO and contenido_adjunto is not None:
        try:
            clave_s3 = almacenamiento.subir_adjunto(
                contenido_adjunto,
                extension_adjunto or "",
                tipo_adjunto or "application/octet-stream",
            )
        except almacenamiento.ErrorDeAlmacenamiento as error:
            return JSONResponse({"error": str(error)}, status_code=503)

    hilo = Hilo(
        autor_id=usuario.id,
        titulo=titulo.strip()[:160],
        cuerpo=cuerpo.strip(),
        calificacion=calificacion,
        estado=veredicto.estado,
        motivo_moderacion=veredicto.motivo,
        clave_s3=clave_s3,
    )
    sesion.add(hilo)
    try:
        sesion.commit()
    except SQLAlchemyError:
        sesion.rollback()
        if clave_s3:
            almacenamiento.eliminar_adjunto(clave_s3)
        return JSONResponse(
            {"error": "No se pudo guardar la publicacion."}, status_code=503
        )

    if veredicto.estado == ESTADO_RECHAZADO:
        return _redirigir("/mis-publicaciones")
    return _redirigir(f"/hilos/{hilo.id}")


@aplicacion.post("/hilos/{hilo_id}/comentarios")
async def comentar(
    hilo_id: int,
    peticion: Request,
    cuerpo: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = _exigir_sesion(peticion, sesion)
    if usuario is None:
        return JSONResponse({"error": "Necesitas iniciar sesion."}, status_code=401)

    hilo = sesion.get(Hilo, hilo_id)
    if hilo is None or hilo.estado != ESTADO_PUBLICADO:
        return JSONResponse({"error": "El hilo no existe."}, status_code=404)

    # Los comentarios pasan por la misma revision que las resenas: son la via
    # mas facil de meter contenido al foro. Si el moderador tarda, la peticion
    # falla con 503 (decidir_estado ya aplica su propio timeout); lo que no se
    # hace nunca es publicar sin revisar.
    try:
        veredicto = await moderacion.decidir_estado(cuerpo)
    except moderacion.ErrorDeModeracion as error:
        return JSONResponse({"error": str(error)}, status_code=503)

    comentario = Comentario(
        hilo_id=hilo.id,
        autor_id=usuario.id,
        cuerpo=cuerpo.strip(),
        estado=veredicto.estado,
        motivo_moderacion=veredicto.motivo,
    )
    sesion.add(comentario)
    sesion.commit()

    if veredicto.estado == ESTADO_RECHAZADO:
        return _redirigir("/mis-publicaciones")
    return _redirigir(f"/hilos/{hilo.id}")


# --- Vista previa enriquecida del moderador (Entrega Final, tema 4) -----------

@aplicacion.post("/moderacion/resenas/{resena_id}/vista-previa", response_class=HTMLResponse)
async def vista_previa_moderador(
    resena_id: int,
    peticion: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """
    Muestra al moderador una resena con formato enriquecido (negrita, saltos)
    para inspeccionarla. Solo para moderadores autorizados.

    La API es la frontera de autenticacion: comprueba que quien pide es
    moderador, carga la resena guardada (escrita por cualquier usuario) y pide el
    render al servicio de moderacion por la red interna. Asi el contenido de un
    atacante, ya almacenado, llega a la vista del moderador: es el vector real
    del defecto (XSS almacenado, CWE-79).
    """
    usuario = usuario_actual(peticion, sesion)
    if not _es_moderador(usuario):
        # 403 tanto para anonimo como para usuario comun: la vista del moderador
        # no la abre cualquiera con sesion.
        return JSONResponse(
            {"error": "Solo un moderador autorizado puede usar la vista previa."},
            status_code=403,
        )
    hilo = sesion.get(Hilo, resena_id)
    if hilo is None:
        return JSONResponse({"error": "La resena no existe."}, status_code=404)
    try:
        html_previa = await moderacion.render_vista_previa(hilo.cuerpo)
    except moderacion.ErrorDeModeracion as error:
        return JSONResponse({"error": str(error)}, status_code=503)
    return HTMLResponse(content=html_previa)


# --- Lo que no paso la moderacion --------------------------------------------

@aplicacion.get("/mis-publicaciones", response_class=HTMLResponse)
def mis_publicaciones(peticion: Request, sesion: Session = Depends(obtener_sesion)):
    """Cada autor ve sus propios rechazos y el motivo. Solo los suyos."""
    usuario = _exigir_sesion(peticion, sesion)
    if usuario is None:
        return _redirigir("/entrar")
    hilos = sesion.scalars(
        select(Hilo).where(Hilo.autor_id == usuario.id).order_by(Hilo.creado_en.desc())
    ).all()
    comentarios = sesion.scalars(
        select(Comentario)
        .where(Comentario.autor_id == usuario.id)
        .order_by(Comentario.creado_en.desc())
    ).all()
    return _PLANTILLAS.TemplateResponse(
        peticion,
        "mis_publicaciones.html",
        {"hilos": hilos, "comentarios": comentarios, "usuario": usuario},
    )


@aplicacion.get("/adjunto/{hilo_id}")
def ver_adjunto(hilo_id: int, peticion: Request, sesion: Session = Depends(obtener_sesion)):
    """Entrega el adjunto de S3 por URL prefirmada, solo a usuarios con sesion."""
    usuario = _exigir_sesion(peticion, sesion)
    if usuario is None:
        return JSONResponse({"error": "Necesitas iniciar sesion."}, status_code=401)
    hilo = sesion.get(Hilo, hilo_id)
    if hilo is None or not hilo.clave_s3 or hilo.estado != ESTADO_PUBLICADO:
        return JSONResponse({"error": "No hay adjunto."}, status_code=404)
    try:
        return _redirigir(almacenamiento.url_prefirmada(hilo.clave_s3))
    except almacenamiento.ErrorDeAlmacenamiento as error:
        return JSONResponse({"error": str(error)}, status_code=503)

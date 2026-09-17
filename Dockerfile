# Imagen de la API del foro.
#
# Endurecido segun los requisitos del Avance 2:
#   - Version fija de la imagen base (no :latest). El pin por digest exacto lo
#     aplica pipeline/fijar_imagen_base.sh con el digest real de TU docker pull:
#     esta linea queda como python:3.11-slim@sha256:<digest>.
#   - Proceso sin root (usuario 'foro', uid 10001).
#   - HEALTHCHECK real contra /salud.
#   - Sin secretos: toda credencial entra por variables de entorno en ejecucion.
FROM python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /aplicacion

# El digest fija el punto de partida, pero los repositorios de Debian pueden
# publicar correcciones despues. Se aplican en la construccion y se elimina el
# indice de apt para no conservar cache innecesaria en la imagen final.
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios: si alguien logra ejecutar codigo dentro del
# contenedor, no lo hace como root.
RUN groupadd --gid 10001 foro \
 && useradd --uid 10001 --gid foro --create-home --shell /usr/sbin/nologin foro

# Las dependencias se copian e instalan antes que el codigo para aprovechar la
# cache de capas: cambiar una linea de la app no reinstala todo.
COPY app/api/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade \
      pip==26.2.1 setuptools==84.0.0 wheel==0.48.0 \
 && python -m pip install --no-cache-dir -r requirements.txt

COPY app/api/ ./
RUN chown -R foro:foro /aplicacion

USER foro
EXPOSE 8000

# Usa python en vez de curl: la imagen slim no trae curl y agregarlo solo para
# el healthcheck seria superficie extra.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "main:aplicacion", "--host", "0.0.0.0", "--port", "8000"]

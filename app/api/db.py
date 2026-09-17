"""
Conexion a la base de datos (RDS PostgreSQL en el entregable).

Se usa SQLAlchemy con consultas parametrizadas en toda la app: el contenido de
un foro es texto que escribe cualquier usuario registrado, asi que concatenar
ese texto dentro de SQL es el camino directo a una inyeccion.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import URL_BASE_DATOS

_argumentos_conexion = {}
if URL_BASE_DATOS.startswith("sqlite"):
    _argumentos_conexion = {"check_same_thread": False}

motor = create_engine(
    URL_BASE_DATOS,
    pool_pre_ping=True,  # reconecta si RDS cerro la conexion por inactividad
    connect_args=_argumentos_conexion,
)

SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)
Base = declarative_base()


def obtener_sesion():
    """Dependencia de FastAPI: abre y cierra una sesion por peticion."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


def crear_tablas():
    import modelos  # noqa: F401  (registra los modelos en el metadata)

    Base.metadata.create_all(bind=motor)

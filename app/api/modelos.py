"""Modelos de datos del foro: usuarios, hilos (resenas) y comentarios."""
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db import Base

ESTADO_PUBLICADO = "publicado"
ESTADO_RECHAZADO = "rechazado"


def _ahora():
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    correo = Column(String(200), unique=True, nullable=False, index=True)
    nombre = Column(String(80), nullable=False)
    # Formato: scrypt$<sal_hex>$<derivado_hex>. Nunca la contrasena en claro.
    credencial = Column(String(300), nullable=False)
    creado_en = Column(DateTime(timezone=True), default=_ahora, nullable=False)

    hilos = relationship("Hilo", back_populates="autor")
    comentarios = relationship("Comentario", back_populates="autor")


class Hilo(Base):
    """Un hilo es una resena: titulo, cuerpo y calificacion de 1 a 5."""

    __tablename__ = "hilos"

    id = Column(Integer, primary_key=True)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String(160), nullable=False)
    cuerpo = Column(Text, nullable=False)
    calificacion = Column(Integer, nullable=False)
    # Lo asigna siempre el servicio de moderacion, nunca la ruta directamente.
    estado = Column(String(20), nullable=False, index=True)
    motivo_moderacion = Column(String(300), nullable=False, default="")
    # Solo la clave del objeto en S3; el contenido nunca se guarda en la base.
    clave_s3 = Column(String(300), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=_ahora, nullable=False)

    autor = relationship("Usuario", back_populates="hilos")
    comentarios = relationship(
        "Comentario", back_populates="hilo", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("calificacion >= 1 AND calificacion <= 5", name="ck_calificacion"),
    )


class Comentario(Base):
    __tablename__ = "comentarios"

    id = Column(Integer, primary_key=True)
    hilo_id = Column(Integer, ForeignKey("hilos.id"), nullable=False, index=True)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cuerpo = Column(Text, nullable=False)
    estado = Column(String(20), nullable=False, index=True)
    motivo_moderacion = Column(String(300), nullable=False, default="")
    creado_en = Column(DateTime(timezone=True), default=_ahora, nullable=False)

    hilo = relationship("Hilo", back_populates="comentarios")
    autor = relationship("Usuario", back_populates="comentarios")

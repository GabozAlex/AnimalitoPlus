from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Time, Date, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, date, time
import enum

from app.database import Base


class RolEnum(str, enum.Enum):
    user = "user"
    admin = "admin"


class EstadoApuestaEnum(str, enum.Enum):
    pendiente = "pendiente"
    ganada = "ganada"
    perdida = "perdida"
    pagada = "pagada"


class TipoTransaccionEnum(str, enum.Enum):
    recarga = "recarga"
    retiro = "retiro"
    apuesta = "apuesta"
    pago_premio = "pago_premio"
    ajuste_admin = "ajuste_admin"


class MetodoPagoEnum(str, enum.Enum):
    pago_movil = "pago_movil"
    cripto = "cripto"
    manual = "manual"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    correo = Column(String(255), unique=True, nullable=False, index=True)
    clave = Column(String(255), nullable=False)
    saldo = Column(Float, default=0.0)
    cedula = Column(String(20))
    telefono = Column(String(20))
    banco = Column(String(100))
    banco_codigo = Column(String(10))
    pago_movil_titular = Column(String(100))
    rol = Column(SAEnum(RolEnum), default=RolEnum.user)
    bloqueado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    apuestas = relationship("Apuesta", back_populates="usuario")
    transacciones = relationship("Transaccion", back_populates="usuario")


class Apuesta(Base):
    __tablename__ = "apuestas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    loteria = Column(String(50), nullable=False)
    total = Column(Float, nullable=False)
    fecha = Column(Date, default=date.today, nullable=False)
    horario = Column(Time, nullable=False)
    estado = Column(SAEnum(EstadoApuestaEnum), default=EstadoApuestaEnum.pendiente)
    created_at = Column(DateTime, default=datetime.now)

    usuario = relationship("Usuario", back_populates="apuestas")
    detalles = relationship("DetalleApuesta", back_populates="apuesta")


class DetalleApuesta(Base):
    __tablename__ = "detalle_apuesta"

    id = Column(Integer, primary_key=True, index=True)
    apuesta_id = Column(Integer, ForeignKey("apuestas.id"), nullable=False)
    animal_id = Column(String(3), nullable=False)  # '0', '00', '1'...'36'
    monto = Column(Float, nullable=False)

    apuesta = relationship("Apuesta", back_populates="detalles")


class Resultado(Base):
    __tablename__ = "resultados"

    id = Column(Integer, primary_key=True, index=True)
    loteria = Column(String(50), nullable=False)
    fecha = Column(Date, default=date.today, nullable=False)
    horario = Column(Time, nullable=False)
    animal_id = Column(String(3), nullable=False)
    numero = Column(String(2), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class Transaccion(Base):
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(SAEnum(TipoTransaccionEnum), nullable=False)
    monto = Column(Float, nullable=False)
    metodo = Column(SAEnum(MetodoPagoEnum))
    referencia = Column(String(255))
    estado = Column(String(20), default='pendiente')
    descripcion = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    usuario = relationship("Usuario", back_populates="transacciones")

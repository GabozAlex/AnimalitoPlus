from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Time, Date, Text, Enum as SAEnum, Numeric
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
    saldo = Column(Numeric(12, 2), default=0.0)
    cedula = Column(String(20))
    telefono = Column(String(20))
    banco = Column(String(100))
    banco_codigo = Column(String(10))
    pago_movil_titular = Column(String(100))
    rol = Column(SAEnum(RolEnum), default=RolEnum.user)
    bloqueado = Column(Boolean, default=False)
    codigo_referido = Column(String(20), unique=True, index=True)
    referido_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    bono_referido = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    apuestas = relationship("Apuesta", back_populates="usuario")
    transacciones = relationship("Transaccion", back_populates="usuario")
    referidos = relationship("Usuario", backref="referidor", remote_side=[id])


class Apuesta(Base):
    __tablename__ = "apuestas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    loteria = Column(String(50), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, default=date.today, nullable=False)
    horario = Column(Time, nullable=False)
    estado = Column(SAEnum(EstadoApuestaEnum), default=EstadoApuestaEnum.pendiente)
    folio = Column(String(20), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.now)

    usuario = relationship("Usuario", back_populates="apuestas")
    detalles = relationship("DetalleApuesta", back_populates="apuesta")


class DetalleApuesta(Base):
    __tablename__ = "detalle_apuesta"

    id = Column(Integer, primary_key=True, index=True)
    apuesta_id = Column(Integer, ForeignKey("apuestas.id"), nullable=False)
    animal_id = Column(String(3), nullable=False)  # '0', '00', '1'...'36'
    monto = Column(Numeric(12, 2), nullable=False)

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
    monto = Column(Numeric(12, 2), nullable=False)
    metodo = Column(SAEnum(MetodoPagoEnum))
    referencia = Column(String(255))
    estado = Column(String(20), default='pendiente')
    descripcion = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    usuario = relationship("Usuario", back_populates="transacciones")


class Cupo(Base):
    __tablename__ = "cupos"

    id = Column(Integer, primary_key=True, index=True)
    loteria = Column(String(50), nullable=False)
    horario = Column(Time, nullable=False)
    animal_id = Column(String(3), nullable=False)
    maximo = Column(Numeric(12, 2), nullable=False, default=0)
    activo = Column(Boolean, default=True)


class AcumuladoCupo(Base):
    __tablename__ = "acumulados_cupos"

    fecha = Column(Date, primary_key=True, default=date.today)
    loteria = Column(String(50), primary_key=True)
    horario = Column(Time, primary_key=True)
    animal_id = Column(String(3), primary_key=True)
    acumulado = Column(Numeric(12, 2), nullable=False, default=0)


class Animal(Base):
    __tablename__ = "animales"

    id = Column(String(3), primary_key=True)
    numero = Column(String(2), nullable=False)
    nombre = Column(String(50), nullable=False)
    icono = Column(String(30), nullable=False, default='fa-paw')


class Config(Base):
    __tablename__ = "config"

    clave = Column(String(50), primary_key=True)
    valor = Column(Text, nullable=False)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    accion = Column(String(50), nullable=False)
    descripcion = Column(Text)
    ip = Column(String(45))
    created_at = Column(DateTime, default=datetime.now)


class Aviso(Base):
    __tablename__ = "avisos"

    id = Column(Integer, primary_key=True, index=True)
    fuente = Column(String(20), nullable=False, default='manual')  # 'instagram' | 'manual'
    loteria = Column(String(50), nullable=True)  # null = todas
    titulo = Column(String(200), nullable=False)
    contenido = Column(Text, nullable=False)
    url_instagram = Column(String(500))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class TipoNotificacionEnum(str, enum.Enum):
    ganada = "ganada"
    perdida = "perdida"
    premio = "premio"
    sistema = "sistema"
    info = "info"


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(SAEnum(TipoNotificacionEnum), nullable=False)
    titulo = Column(String(200), nullable=False)
    contenido = Column(Text)
    referencia_id = Column(Integer, nullable=True)
    leida = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    usuario = relationship("Usuario", backref="notificaciones")

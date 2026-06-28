from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal
from datetime import date, time, datetime
import enum
import re


def normalize_phone(v: str) -> str:
    if v is None: return v
    limpio = re.sub(r'\D', '', v)
    if len(limpio) == 11 and limpio.startswith('0'):
        limpio = limpio[1:]
    if len(limpio) != 10:
        raise ValueError('El teléfono debe tener 10 dígitos')
    if not limpio.startswith(('412', '414', '416', '424', '426')) and not limpio.startswith('2'):
        raise ValueError('Teléfono inválido: debe ser un número venezolano')
    return limpio


# ===== ESQUEMAS DE USUARIO =====

class UsuarioCreate(BaseModel):
    nombre: str
    apellido: Optional[str] = None
    correo: EmailStr
    clave: str
    cedula: Optional[str] = Field(None, pattern=r'^[VE]\d{1,8}$', max_length=20)
    telefono: Optional[str] = Field(None, max_length=20)
    banco: Optional[str] = None
    banco_codigo: Optional[str] = None
    pago_movil_titular: Optional[str] = None
    codigo_referido: Optional[str] = None

    @field_validator('clave')
    @classmethod
    def validar_clave(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v):
        return normalize_phone(v)


class UsuarioLogin(BaseModel):
    correo: EmailStr
    clave: str


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    correo: str
    saldo: float
    cedula: Optional[str] = None
    telefono: Optional[str] = None
    banco: Optional[str] = None
    banco_codigo: Optional[str] = None
    pago_movil_titular: Optional[str] = None
    rol: str
    bloqueado: bool
    codigo_referido: Optional[str] = None
    referido_por: Optional[int] = None
    bono_referido: Optional[bool] = False

    class Config:
        from_attributes = True


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    cedula: Optional[str] = Field(None, pattern=r'^[VE]\d{1,8}$', max_length=20)
    telefono: Optional[str] = Field(None, max_length=20)
    banco: Optional[str] = None
    banco_codigo: Optional[str] = None
    pago_movil_titular: Optional[str] = None

    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v):
        return normalize_phone(v)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ===== ESQUEMAS DE APUESTA =====

class DetalleApuestaCreate(BaseModel):
    animal_id: str
    monto: float = Field(gt=0)


class ApuestaCreate(BaseModel):
    loteria: str
    horario: str  # "HH:MM"
    animales: List[DetalleApuestaCreate]


class DetalleApuestaOut(BaseModel):
    id: int
    animal_id: str
    monto: float

    class Config:
        from_attributes = True


class ApuestaOut(BaseModel):
    id: int
    loteria: str
    total: float
    fecha: str
    horario: str
    estado: str
    folio: Optional[str] = None
    created_at: str
    detalles: List[DetalleApuestaOut] = []

    class Config:
        from_attributes = True

    @field_validator('fecha', 'horario', 'created_at', mode='before')
    @classmethod
    def convert_dates(cls, v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        if isinstance(v, time):
            return v.strftime('%H:%M')
        return v


class ResultadoOut(BaseModel):
    id: int
    loteria: str
    fecha: str
    horario: str
    animal_id: str
    numero: str

    class Config:
        from_attributes = True

    @field_validator('fecha', mode='before')
    @classmethod
    def convert_date(cls, v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    @field_validator('horario', mode='before')
    @classmethod
    def convert_time(cls, v):
        if isinstance(v, time):
            return v.strftime('%H:%M')
        return v


# ===== ESQUEMAS DE RESULTADO =====

class ResultadoCreate(BaseModel):
    loteria: str
    fecha: Optional[str] = None
    horario: str
    animal_id: str
    numero: str


# ===== ESQUEMAS DE PAGO =====

class RecargaCreate(BaseModel):
    monto: float = Field(ge=10, le=10000)
    metodo: str
    referencia: Optional[str] = Field(None, pattern=r'^\d{4}$|^\d{6}$|^\d{12}$', max_length=12)
    banco_origen: Optional[str] = None
    movement_type: Optional[str] = None
    fecha: Optional[str] = None


class RetiroCreate(BaseModel):
    monto: float = Field(ge=10, le=10000)


class AdminPagoUpdate(BaseModel):
    estado: Literal["en_proceso", "completado", "cancelado"]


class TransaccionOut(BaseModel):
    id: int
    usuario_id: int
    tipo: str
    monto: float
    metodo: Optional[str] = None
    referencia: Optional[str] = None
    estado: Optional[str] = 'pendiente'
    descripcion: Optional[str] = None
    created_at: str
    usuario_nombre: Optional[str] = None
    usuario_cedula: Optional[str] = None
    usuario_telefono: Optional[str] = None
    usuario_banco: Optional[str] = None
    usuario_banco_codigo: Optional[str] = None
    usuario_titular: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator('created_at', mode='before')
    @classmethod
    def convert_dt(cls, v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v


# ===== ESQUEMAS DE ADMIN =====

class AdminUsuarioUpdate(BaseModel):
    saldo: Optional[float] = None
    bloqueado: Optional[bool] = None


class ResultadosResponse(BaseModel):
    source: str  # "db" | "scraped"
    count: int
    resultados: List[ResultadoOut]


class ReporteOut(BaseModel):
    fecha: str
    monto_jugado: float
    monto_premios: float
    ganancia_banca: float
    total_apuestas: int

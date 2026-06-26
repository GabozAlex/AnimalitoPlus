from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioLogin, UsuarioOut, UsuarioUpdate, Token
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(data: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.correo == data.correo).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    usuario = Usuario(
        nombre=data.nombre,
        apellido=data.apellido,
        correo=data.correo,
        clave=hash_password(data.clave),
        cedula=data.cedula,
        telefono=data.telefono,
        banco=data.banco,
        banco_codigo=data.banco_codigo,
        pago_movil_titular=data.pago_movil_titular,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = create_access_token({"sub": str(usuario.id)})
    return Token(access_token=token, usuario=usuario)


@router.post("/login", response_model=Token)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.correo == data.correo).first()
    if not usuario or not verify_password(data.clave, usuario.clave):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if usuario.bloqueado:
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    token = create_access_token({"sub": str(usuario.id)})
    return Token(access_token=token, usuario=usuario)


@router.get("/perfil", response_model=UsuarioOut)
def get_perfil(user: Usuario = Depends(get_current_user)):
    return user


@router.put("/perfil", response_model=UsuarioOut)
def update_perfil(data: UsuarioUpdate, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(user, campo, valor)
    db.commit()
    db.refresh(user)
    return user


@router.get("/balance")
def get_balance(user: Usuario = Depends(get_current_user)):
    return {"saldo": user.saldo}

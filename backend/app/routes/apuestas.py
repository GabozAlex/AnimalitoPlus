from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.database import get_db
from app.models import Usuario, Apuesta, DetalleApuesta, Transaccion
from app.schemas import ApuestaCreate, ApuestaOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/apuestas", tags=["apuestas"])


@router.post("", response_model=ApuestaOut)
def crear_apuesta(
    data: ApuestaCreate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.bloqueado:
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    total = sum(a.monto for a in data.animales)
    if total > user.saldo:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")

    if total <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    if not data.animales:
        raise HTTPException(status_code=400, detail="Debe apostar al menos 1 animal")

    # Validar horario
    try:
        horario = datetime.strptime(data.horario, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Horario inválido. Use HH:MM")

    # Descontar saldo
    user.saldo -= total

    # Crear apuesta
    apuesta = Apuesta(
        usuario_id=user.id,
        loteria=data.loteria,
        total=total,
        fecha=date.today(),
        horario=horario,
    )
    db.add(apuesta)
    db.flush()

    # Crear detalles
    for det in data.animales:
        db.add(DetalleApuesta(
            apuesta_id=apuesta.id,
            animal_id=str(det.animal_id),
            monto=det.monto,
        ))

    # Registrar transacción
    db.add(Transaccion(
        usuario_id=user.id,
        tipo="apuesta",
        monto=total,
        descripcion=f"Apuesta {data.loteria} - {data.horario}",
    ))

    db.commit()
    db.refresh(apuesta)
    return apuesta


@router.get("", response_model=list[ApuestaOut])
def listar_apuestas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 200,
    loteria: Optional[str] = None,
    fecha: Optional[str] = None,
):
    query = db.query(Apuesta).filter(Apuesta.usuario_id == user.id)
    if loteria:
        query = query.filter(Apuesta.loteria == loteria)
    if fecha:
        query = query.filter(Apuesta.fecha == date.fromisoformat(fecha))
    apuestas = (
        query
        .order_by(Apuesta.created_at.desc())
        .limit(limit)
        .all()
    )
    return apuestas


@router.get("/{apuesta_id}", response_model=ApuestaOut)
def detalle_apuesta(
    apuesta_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apuesta = db.query(Apuesta).filter(Apuesta.id == apuesta_id).first()
    if not apuesta:
        raise HTTPException(status_code=404, detail="Apuesta no encontrada")
    if apuesta.usuario_id != user.id and user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tienes acceso a esta apuesta")
    return apuesta

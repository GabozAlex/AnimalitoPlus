from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.models import Usuario, Transaccion
from app.schemas import RecargaCreate, RetiroCreate
from app.auth import get_current_user

router = APIRouter(prefix="/api/pagos", tags=["pagos"])


@router.post("/recarga")
def solicitar_recarga(
    data: RecargaCreate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.monto <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    tx = Transaccion(
        usuario_id=user.id,
        tipo="recarga",
        monto=data.monto,
        metodo=data.metodo,
        referencia=data.referencia,
        descripcion=f"Recarga solicitada vía {data.metodo}",
    )
    db.add(tx)
    db.commit()

    return {"mensaje": "Solicitud de recarga registrada", "id": tx.id}


@router.post("/retiro")
def solicitar_retiro(
    data: RetiroCreate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.monto <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")
    if data.monto > user.saldo:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")

    tx = Transaccion(
        usuario_id=user.id,
        tipo="retiro",
        monto=data.monto,
        descripcion="Solicitud de retiro",
    )
    db.add(tx)
    db.commit()

    return {"mensaje": "Solicitud de retiro registrada", "id": tx.id}


@router.get("/historial")
def historial_pagos(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    txs = (
        db.query(Transaccion)
        .filter(Transaccion.usuario_id == user.id)
        .order_by(Transaccion.created_at.desc())
        .limit(limit)
        .all()
    )
    return txs

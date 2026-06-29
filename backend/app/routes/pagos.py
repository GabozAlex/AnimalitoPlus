from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import date, datetime, time
import json

from app.database import get_db
from app.models import Usuario, Transaccion, Config
from app.schemas import RecargaCreate, RetiroCreate, TransaccionOut
from app.auth import get_current_user
from app.limiter import limiter

router = APIRouter(prefix="/api/pagos", tags=["pagos"])


def _validar_horario(db: Session, tipo: str):
    cfg = db.query(Config).filter(Config.clave == "horarios").first()
    if not cfg:
        return
    data = json.loads(cfg.valor)
    horario = data.get(tipo)
    if not horario:
        return
    ahora = datetime.now()
    dia_semana = ahora.isoweekday()
    dias = horario.get("dias", [])
    if dia_semana not in dias:
        raise HTTPException(
            status_code=400,
            detail=f"Los {tipo}s no están disponibles hoy. Días hábiles: {', '.join(map(str, dias))}",
        )
    inicio = time.fromisoformat(horario["inicio"])
    fin = time.fromisoformat(horario["fin"])
    ahora_hora = ahora.time()
    if not (inicio <= ahora_hora <= fin):
        raise HTTPException(
            status_code=400,
            detail=f"Los {tipo}s solo están disponibles de {horario['inicio']} a {horario['fin']}",
        )


@router.post("/recarga")
@limiter.limit("5/minute")
def solicitar_recarga(
    request: Request,
    data: RecargaCreate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validar_horario(db, "recarga")
    if data.monto <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    user = db.query(Usuario).filter(Usuario.id == user.id).with_for_update().first()

    extra = {}
    if data.banco_origen:
        extra["banco_origen"] = data.banco_origen
    if data.movement_type:
        extra["movement_type"] = data.movement_type
    if data.fecha:
        extra["fecha_pago"] = data.fecha

    tx = Transaccion(
        usuario_id=user.id,
        tipo="recarga",
        monto=data.monto,
        metodo=data.metodo,
        referencia=data.referencia,
        descripcion=json.dumps(extra) if extra else None,
        estado="pendiente",
    )
    db.add(tx)
    db.commit()

    return {"mensaje": "Solicitud de recarga registrada", "id": tx.id, "estado": "pendiente"}


@router.post("/retiro")
@limiter.limit("3/minute")
def solicitar_retiro(
    request: Request,
    data: RetiroCreate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validar_horario(db, "retiro")
    if data.monto <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    user = db.query(Usuario).filter(Usuario.id == user.id).with_for_update().first()
    if data.monto > user.saldo:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")

    tx = Transaccion(
        usuario_id=user.id,
        tipo="retiro",
        monto=data.monto,
        descripcion="Solicitud de retiro",
        estado="pendiente",
    )
    db.add(tx)
    db.commit()

    return {"mensaje": "Solicitud de retiro registrada", "id": tx.id, "estado": "pendiente"}


@router.get("/historial", response_model=list[TransaccionOut])
def historial_pagos(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    tipo: Optional[str] = None,
    limit: int = 50,
):
    query = db.query(Transaccion).filter(Transaccion.usuario_id == user.id)
    if tipo:
        query = query.filter(Transaccion.tipo == tipo)
    txs = query.order_by(Transaccion.created_at.desc()).limit(limit).all()

    result = []
    for tx in txs:
        extra = {}
        if tx.descripcion:
            try:
                extra = json.loads(tx.descripcion)
            except (json.JSONDecodeError, TypeError):
                extra = {"nota": tx.descripcion}
        u = db.query(Usuario).filter(Usuario.id == tx.usuario_id).first()
        result.append({
            "id": tx.id,
            "usuario_id": tx.usuario_id,
            "tipo": tx.tipo,
            "monto": tx.monto,
            "metodo": tx.metodo,
            "referencia": tx.referencia,
            "estado": tx.estado,
            "descripcion": tx.descripcion,
            "created_at": tx.created_at,
            "usuario_nombre": f"{u.nombre} {u.apellido}" if u else None,
            "usuario_cedula": u.cedula if u else None,
            "usuario_telefono": u.telefono if u else None,
            "usuario_banco": u.banco if u else None,
            "usuario_banco_codigo": u.banco_codigo if u else None,
            "usuario_titular": u.pago_movil_titular if u else None,
        })
    return result


@router.get("/config/casa")
def get_config_casa(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'casa').first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuración de casa no encontrada")
    return json.loads(cfg.valor)

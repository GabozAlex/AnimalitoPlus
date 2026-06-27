from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
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

    # Validar límites de apuesta
    from app.models import Config as ConfigModel
    import json
    cfg = db.query(ConfigModel).filter(ConfigModel.clave == 'limites').first()
    if cfg:
        try:
            limites = json.loads(cfg.valor)
            max_por_apuesta = float(limites.get('max_por_apuesta', 0) or 0)
            max_por_hora = float(limites.get('max_por_hora', 0) or 0)
            max_por_dia = float(limites.get('max_por_dia', 0) or 0)

            if max_por_apuesta > 0 and total > max_por_apuesta:
                raise HTTPException(status_code=400, detail=f"Máximo por apuesta: Bs {max_por_apuesta:.2f}")

            if max_por_hora > 0:
                hora_inicio = datetime.now().replace(minute=0, second=0, microsecond=0)
                gastado_hora = db.query(func.coalesce(func.sum(Apuesta.total), 0)).filter(
                    Apuesta.usuario_id == user.id,
                    Apuesta.created_at >= hora_inicio,
                ).scalar()
                if gastado_hora + total > max_por_hora:
                    raise HTTPException(status_code=400, detail=f"Máximo por hora: Bs {max_por_hora:.2f}")

            if max_por_dia > 0:
                hoy = date.today()
                gastado_dia = db.query(func.coalesce(func.sum(Apuesta.total), 0)).filter(
                    Apuesta.usuario_id == user.id,
                    Apuesta.fecha == hoy,
                ).scalar()
                if gastado_dia + total > max_por_dia:
                    raise HTTPException(status_code=400, detail=f"Máximo por día: Bs {max_por_dia:.2f}")
        except (json.JSONDecodeError, ValueError):
            pass

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


@router.get("/novedades")
def novedades_apuestas(
    desde: Optional[str] = Query(None, description="ISO datetime (ej: 2026-06-26T12:00:00)"),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Apuesta).filter(
        Apuesta.usuario_id == user.id,
        Apuesta.estado.in_(["ganada", "perdida"]),
    )
    if desde:
        try:
            dt = datetime.fromisoformat(desde)
            query = query.filter(Apuesta.created_at > dt)
        except ValueError:
            pass
    apuestas = query.order_by(Apuesta.created_at.desc()).limit(20).all()
    return [
        {
            "id": a.id,
            "loteria": a.loteria,
            "total": a.total,
            "horario": a.horario.strftime("%H:%M"),
            "fecha": a.fecha.isoformat(),
            "estado": a.estado,
            "premio": a.total * 30 if a.estado == "ganada" else 0,
        }
        for a in apuestas
    ]


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

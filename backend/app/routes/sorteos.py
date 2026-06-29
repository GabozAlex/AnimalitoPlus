from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.database import get_db
from app.models import Sorteo, Apuesta, Transaccion, Notificacion, Usuario
from app.schemas import SorteoOut, SorteoList, SorteoGenerar
from app.auth import require_admin

router = APIRouter(prefix="/api/sorteos", tags=["sorteos"])

HORARIOS_POR_LOTERIA = {
    "lotto_activo": [f"{h:02d}:00" for h in range(8, 20)],
    "la_granjita": [f"{h:02d}:00" for h in range(8, 20)],
    "selvaplus": [f"{h:02d}:00" for h in range(8, 20)],
}


def generar_fecha_sorteos(db: Session, fecha: date):
    """Crea sorteos pendientes para una fecha según el schedule."""
    creados = 0
    for loteria, horarios in HORARIOS_POR_LOTERIA.items():
        for h_str in horarios:
            h = datetime.strptime(h_str, "%H:%M").time()
            existe = db.query(Sorteo).filter(
                Sorteo.loteria == loteria,
                Sorteo.fecha == fecha,
                Sorteo.horario == h,
            ).first()
            if not existe:
                db.add(Sorteo(loteria=loteria, fecha=fecha, horario=h, estado="pendiente"))
                creados += 1
    db.commit()
    return creados


@router.get("", response_model=SorteoList)
def listar_sorteos(
    fecha: Optional[str] = None,
    loteria: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        target = date.fromisoformat(fecha) if fecha else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

    query = db.query(Sorteo).filter(Sorteo.fecha == target)
    if loteria:
        query = query.filter(Sorteo.loteria == loteria)
    sorteos = query.order_by(Sorteo.loteria, Sorteo.horario).all()
    return SorteoList(count=len(sorteos), sorteos=[
        SorteoOut(
            id=s.id,
            loteria=s.loteria,
            fecha=s.fecha.isoformat(),
            horario=s.horario.strftime("%H:%M"),
            estado=s.estado,
            created_at=s.created_at.isoformat() if s.created_at else None,
        )
        for s in sorteos
    ])


@router.post("/generar")
def generar_sorteos(
    data: SorteoGenerar,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    hoy = date.today()
    try:
        desde = date.fromisoformat(data.fecha_desde) if data.fecha_desde else hoy
        hasta = date.fromisoformat(data.fecha_hasta) if data.fecha_hasta else hoy + timedelta(days=7)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

    total = 0
    d = desde
    while d <= hasta:
        total += generar_fecha_sorteos(db, d)
        d += timedelta(days=1)
    return {"mensaje": f"Sorteos generados del {desde} al {hasta}", "creados": total}


@router.post("/{sorteo_id}/cancelar")
def cancelar_sorteo(
    sorteo_id: int,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sorteo = db.query(Sorteo).filter(Sorteo.id == sorteo_id).first()
    if not sorteo:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")
    if sorteo.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"No se puede cancelar un sorteo {sorteo.estado}")

    apuestas = (
        db.query(Apuesta)
        .filter(
            Apuesta.sorteo_id == sorteo_id,
            Apuesta.estado == "pendiente",
        )
        .all()
    )
    revertidas = 0
    for apuesta in apuestas:
        usuario = db.query(Usuario).filter(Usuario.id == apuesta.usuario_id).first()
        if usuario:
            usuario.saldo += apuesta.total
            db.add(Transaccion(
                usuario_id=usuario.id,
                tipo="ajuste_admin",
                monto=apuesta.total,
                descripcion=f"Reembolso sorteo cancelado {sorteo.loteria} {sorteo.horario.strftime('%H:%M')}",
            ))
        revertidas += 1

    sorteo.estado = "cancelado"
    db.commit()
    return {"mensaje": "Sorteo cancelado", "apuestas_reembolsadas": revertidas}

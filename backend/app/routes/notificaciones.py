from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Usuario, Notificacion
from app.auth import get_current_user

router = APIRouter(prefix="/api/notificaciones", tags=["notificaciones"])


@router.get("")
def listar_notificaciones(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    solo_no_leidas: bool = False,
    limit: int = 50,
):
    query = db.query(Notificacion).filter(Notificacion.usuario_id == user.id)
    if solo_no_leidas:
        query = query.filter(Notificacion.leida == False)
    notis = query.order_by(desc(Notificacion.created_at)).limit(limit).all()
    return [
        {
            "id": n.id,
            "tipo": n.tipo,
            "titulo": n.titulo,
            "contenido": n.contenido,
            "referencia_id": n.referencia_id,
            "leida": n.leida,
            "created_at": n.created_at.isoformat(),
        }
        for n in notis
    ]


@router.get("/no-leidas")
def contar_no_leidas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(Notificacion).filter(
        Notificacion.usuario_id == user.id,
        Notificacion.leida == False,
    ).count()
    return {"count": count}


@router.put("/{notificacion_id}/leer")
def marcar_leida(
    notificacion_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    noti = db.query(Notificacion).filter(
        Notificacion.id == notificacion_id,
        Notificacion.usuario_id == user.id,
    ).first()
    if not noti:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    noti.leida = True
    db.commit()
    return {"mensaje": "Marcada como leída"}


@router.put("/leer-todas")
def marcar_todas_leidas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notificacion).filter(
        Notificacion.usuario_id == user.id,
        Notificacion.leida == False,
    ).update({"leida": True})
    db.commit()
    return {"mensaje": "Todas marcadas como leídas"}

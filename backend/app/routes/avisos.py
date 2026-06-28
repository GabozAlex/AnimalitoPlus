from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from app.database import get_db
from app.models import Aviso

router = APIRouter(prefix="/api/avisos", tags=["avisos"])


@router.get("")
def listar_avisos(
    loteria: str = Query(None),
    activo: bool = Query(True),
    db: Session = Depends(get_db),
):
    query = db.query(Aviso).filter(Aviso.activo == activo).order_by(desc(Aviso.created_at))
    if loteria:
        query = query.filter(Aviso.loteria == loteria)
    avisos = query.limit(20).all()
    return [
        {
            "id": a.id,
            "fuente": a.fuente,
            "loteria": a.loteria,
            "titulo": a.titulo,
            "contenido": a.contenido,
            "url_instagram": a.url_instagram,
            "created_at": a.created_at.isoformat(),
        }
        for a in avisos
    ]

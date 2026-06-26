from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.database import get_db
from app.models import Resultado, Usuario
from app.schemas import ResultadoOut, ResultadoCreate
from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/resultados", tags=["resultados"])


@router.get("", response_model=list[ResultadoOut])
def listar_resultados(
    loteria: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Resultado)
    if loteria:
        query = query.filter(Resultado.loteria == loteria)
    if fecha:
        query = query.filter(Resultado.fecha == fecha)
    else:
        query = query.filter(Resultado.fecha == date.today())
    return query.order_by(Resultado.horario).all()


@router.post("", response_model=ResultadoOut)
def crear_resultado(
    data: ResultadoCreate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_date = date.fromisoformat(data.fecha) if data.fecha else date.today()
    horario = datetime.strptime(data.horario, "%H:%M").time()

    resultado = Resultado(
        loteria=data.loteria,
        fecha=target_date,
        horario=horario,
        animal_id=data.animal_id,
        numero=data.numero,
    )
    db.add(resultado)
    db.commit()
    db.refresh(resultado)
    return resultado

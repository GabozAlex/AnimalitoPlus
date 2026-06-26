from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.database import get_db
from app.models import Resultado, Usuario
from app.schemas import ResultadoOut, ResultadoCreate, ResultadosResponse
from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/resultados", tags=["resultados"])


@router.get("", response_model=ResultadosResponse)
def listar_resultados(
    loteria: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db),
):
    target_date = date.fromisoformat(fecha) if fecha else date.today()

    query = db.query(Resultado)
    if loteria:
        query = query.filter(Resultado.loteria == loteria)
    query = query.filter(Resultado.fecha == target_date)

    results = query.order_by(Resultado.horario).all()

    source = "db"
    if not results:
        from app.scraper import run_scraper_parallel
        fecha_str = target_date.isoformat()
        run_scraper_parallel(fecha_str, db)
        results = query.order_by(Resultado.horario).all()
        source = "scraped"

    return ResultadosResponse(
        source=source,
        count=len(results),
        resultados=results,
    )


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

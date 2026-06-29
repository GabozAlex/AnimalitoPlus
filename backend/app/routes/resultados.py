from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.database import get_db
from app.models import Resultado, Usuario, Sorteo
from app.schemas import ResultadoOut, ResultadoCreate, ResultadosResponse
from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/resultados", tags=["resultados"])


@router.get("", response_model=ResultadosResponse)
def listar_resultados(
    loteria: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        target_date = date.fromisoformat(fecha) if fecha else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

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
    try:
        target_date = date.fromisoformat(data.fecha) if data.fecha else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")
    horario = datetime.strptime(data.horario, "%H:%M").time()

    sorteo = db.query(Sorteo).filter(
        Sorteo.loteria == data.loteria,
        Sorteo.fecha == target_date,
        Sorteo.horario == horario,
    ).first()
    if not sorteo:
        sorteo = Sorteo(loteria=data.loteria, fecha=target_date, horario=horario, estado="pendiente")
        db.add(sorteo)
        db.flush()
    sorteo.estado = "realizado"

    resultado = Resultado(
        sorteo_id=sorteo.id,
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


@router.get("/ganadores")
def listar_ganadores_publico(
    loteria: Optional[str] = None,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import Apuesta, DetalleApuesta

    query = (
        db.query(
            Apuesta,
            DetalleApuesta,
            Usuario,
        )
        .join(DetalleApuesta, DetalleApuesta.apuesta_id == Apuesta.id)
        .join(Usuario, Usuario.id == Apuesta.usuario_id)
        .filter(Apuesta.estado == "ganada")
    )
    if loteria:
        query = query.filter(Apuesta.loteria == loteria)

    rows = query.order_by(Apuesta.created_at.desc()).limit(100).all()

    from app.routes.admin import get_multiplicador

    mult = get_multiplicador(db)

    return [
        {
            "usuario_nombre": f"{u.nombre} {u.apellido}".strip(),
            "loteria": a.loteria,
            "fecha": a.fecha.isoformat(),
            "horario": a.horario.strftime("%H:%M"),
            "animal_id": d.animal_id,
            "monto_apostado": d.monto,
            "premio": d.monto * mult,
        }
        for a, d, u in rows
    ]

from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime

from app.database import get_db
from app.models import Usuario, Apuesta, DetalleApuesta, Transaccion, Cupo, AcumuladoCupo, Animal, Resultado
from app.animales import ANIMALES_HARDCODE
from app.schemas import ApuestaCreate, ApuestaOut
from app.auth import get_current_user
from app.routes.admin import get_multiplicador
from app.limiter import limiter

router = APIRouter(prefix="/api/apuestas", tags=["apuestas"])


@router.post("", response_model=ApuestaOut)
@limiter.limit("30/minute")
def crear_apuesta(
    request: Request,
    data: ApuestaCreate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.bloqueado:
        raise HTTPException(status_code=403, detail="Usuario bloqueado")

    total = Decimal(str(sum(a.monto for a in data.animales)))
    db.refresh(user)
    user = db.query(Usuario).filter(Usuario.id == user.id).with_for_update().first()
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

    # Validar sorteo
    from app.models import Sorteo as SorteoModel
    sorteo = db.query(SorteoModel).filter(
        SorteoModel.loteria == data.loteria,
        SorteoModel.fecha == date.today(),
        SorteoModel.horario == horario,
    ).first()
    if not sorteo:
        sorteo = SorteoModel(loteria=data.loteria, fecha=date.today(), horario=horario, estado="pendiente")
        db.add(sorteo)
        db.flush()
    elif sorteo.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"El sorteo {data.loteria} {data.horario} está {sorteo.estado}")

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

    # Validar cupos por animal
    hoy = date.today()
    for det in data.animales:
        cupo = db.query(Cupo).filter(
            Cupo.loteria == data.loteria,
            Cupo.horario == horario,
            Cupo.animal_id == str(det.animal_id),
            Cupo.activo == True,
        ).first()
        if cupo and cupo.maximo > 0:
            ac = db.query(AcumuladoCupo).filter(
                AcumuladoCupo.fecha == hoy,
                AcumuladoCupo.loteria == data.loteria,
                AcumuladoCupo.horario == horario,
                AcumuladoCupo.animal_id == str(det.animal_id),
            ).with_for_update().first()
            if not ac:
                ac = AcumuladoCupo(
                    fecha=hoy,
                    loteria=data.loteria,
                    horario=horario,
                    animal_id=str(det.animal_id),
                    acumulado=0,
                )
                db.add(ac)
            nuevo_acumulado = float(ac.acumulado) + det.monto
            if nuevo_acumulado > float(cupo.maximo):
                animal_nombre = "?"
                try:
                    from app.models import Animal
                    animal_db = db.query(Animal).filter(Animal.id == str(det.animal_id)).first()
                    if animal_db:
                        animal_nombre = animal_db.nombre
                except Exception:
                    pass
                raise HTTPException(
                    status_code=400,
                    detail=f"Límite alcanzado para {animal_nombre} #{det.animal_id} en {data.loteria} {data.horario} (máx: Bs {float(cupo.maximo):.2f})",
                )
            ac.acumulado = nuevo_acumulado

    # Descontar saldo
    user.saldo -= total

    # Crear apuesta
    apuesta = Apuesta(
        usuario_id=user.id,
        sorteo_id=sorteo.id,
        loteria=data.loteria,
        total=total,
        fecha=date.today(),
        horario=horario,
    )
    db.add(apuesta)
    db.flush()

    # Generar folio único
    fecha_str = date.today().strftime("%y%m%d")
    PREFIJOS = {"lotto_activo": "LOT", "la_granjita": "GRA", "selvaplus": "SEL"}
    prefijo = PREFIJOS.get(data.loteria, data.loteria[:3].upper())
    apuesta.folio = f"{fecha_str}-{prefijo}-{apuesta.id}"
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
        try:
            query = query.filter(Apuesta.fecha == date.fromisoformat(fecha))
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida")
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
            raise HTTPException(status_code=400, detail="Fecha inválida")
    apuestas = query.order_by(Apuesta.created_at.desc()).limit(20).all()
    mult = get_multiplicador(db)
    return [
        {
            "id": a.id,
            "loteria": a.loteria,
            "total": a.total,
            "horario": a.horario.strftime("%H:%M"),
            "fecha": a.fecha.isoformat(),
            "estado": a.estado,
            "premio": a.total * mult if a.estado == "ganada" else 0,
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


@router.get("/{apuesta_id}/resumen")
def resumen_apuesta(
    apuesta_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apuesta = db.query(Apuesta).filter(Apuesta.id == apuesta_id).first()
    if not apuesta:
        raise HTTPException(status_code=404, detail="Apuesta no encontrada")
    if apuesta.usuario_id != user.id and user.rol != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    nombres = {}
    for a in db.query(Animal).all():
        nombres[a.id] = a.nombre
    for a in ANIMALES_HARDCODE:
        if a["id"] not in nombres:
            nombres[a["id"]] = a.get("nombre", "")

    mult = get_multiplicador(db)
    ganadores_ids = None
    if apuesta.estado == "ganada":
        resultados = db.query(Resultado).filter(
            Resultado.loteria == apuesta.loteria,
            Resultado.fecha == apuesta.fecha,
            Resultado.horario == apuesta.horario,
        ).all()
        ganadores_ids = {r.animal_id for r in resultados if r.animal_id}

    premio_total = Decimal(0)
    detalles = []
    for d in apuesta.detalles:
        es_ganador = ganadores_ids and d.animal_id in ganadores_ids
        if es_ganador:
            premio_total += Decimal(str(d.monto)) * mult
        detalles.append({
            "animal_id": d.animal_id,
            "nombre": nombres.get(d.animal_id, d.animal_id),
            "monto": float(d.monto),
            "ganador": es_ganador if apuesta.estado == "ganada" else None,
        })

    return {
        "id": apuesta.id,
        "folio": apuesta.folio,
        "fecha": apuesta.fecha.isoformat(),
        "horario": apuesta.horario.strftime("%H:%M"),
        "loteria": apuesta.loteria.replace("_", " ").title(),
        "total": float(apuesta.total),
        "estado": apuesta.estado,
        "detalles": detalles,
        "premio": float(premio_total) if premio_total > 0 else None,
    }


@router.get("/{apuesta_id}/ticket", response_class=HTMLResponse)
def ticket_apuesta(
    apuesta_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apuesta = db.query(Apuesta).filter(Apuesta.id == apuesta_id).first()
    if not apuesta:
        raise HTTPException(status_code=404, detail="Apuesta no encontrada")
    if apuesta.usuario_id != user.id and user.rol != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    loteria_nombre = apuesta.loteria.replace("_", " ").title()
    estado_class = {"pendiente": "Pendiente", "ganada": "Ganada", "perdida": "Perdida"}
    estado_txt = estado_class.get(apuesta.estado, apuesta.estado)

    mult = get_multiplicador(db)

    nombres = {}
    for a in db.query(Animal).all():
        nombres[a.id] = a.nombre
    for a in ANIMALES_HARDCODE:
        if a["id"] not in nombres:
            nombres[a["id"]] = a.get("nombre", "")

    ganadores_ids = None
    if apuesta.estado == "ganada":
        resultados = db.query(Resultado).filter(
            Resultado.loteria == apuesta.loteria,
            Resultado.fecha == apuesta.fecha,
            Resultado.horario == apuesta.horario,
        ).all()
        ganadores_ids = {r.animal_id for r in resultados if r.animal_id}

    detalles_html = ""
    premio_total = Decimal(0)
    for d in apuesta.detalles:
        nom = nombres.get(d.animal_id, d.animal_id)
        clase_estado = ""
        if ganadores_ids and d.animal_id in ganadores_ids:
            clase_estado = "ganador"
            premio_total += Decimal(str(d.monto)) * mult
        detalles_html += f"""
        <tr class="{clase_estado}">
            <td>{d.animal_id}</td>
            <td>{nom}</td>
            <td class="monto">Bs {float(d.monto):.2f}</td>
        </tr>"""

    premio_html = ""
    if premio_total > 0:
        premio_html = f"""
        <div class="premio">
            <strong>¡GANASTE!</strong> Premio: Bs {float(premio_total):.2f}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Ticket #{apuesta.folio or apuesta.id}</title>
<style>
    @page {{ margin: 10mm; size: 80mm 200mm; }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Courier New', monospace; font-size: 12px; width: 70mm; margin: auto; padding: 10px; }}
    h2 {{ text-align: center; font-size: 16px; margin-bottom: 4px; }}
    .folio {{ text-align: center; font-size: 10px; color: #666; margin-bottom: 12px; }}
    .info {{ width: 100%; margin-bottom: 10px; }}
    .info td {{ padding: 2px 4px; }}
    .info td:last-child {{ text-align: right; }}
    table.detalles {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
    table.detalles th {{ border-bottom: 1px dashed #333; padding: 4px; text-align: left; font-size: 11px; }}
    table.detalles td {{ padding: 4px; border-bottom: 1px dotted #ccc; }}
    .monto {{ text-align: right; }}
    .total {{ text-align: right; font-weight: bold; font-size: 14px; margin-bottom: 10px; }}
    .estado {{ text-align: center; font-weight: bold; font-size: 14px; padding: 6px; border: 1px solid #333; margin-bottom: 10px; }}
    .premio {{ text-align: center; font-weight: bold; font-size: 16px; color: #2e7d32; padding: 8px; border: 2px solid #2e7d32; margin-bottom: 10px; }}
    .footer {{ text-align: center; font-size: 9px; color: #999; margin-top: 10px; }}
    .ganador {{ background: #e8f5e9; }}
    .perdedor {{ background: #ffebee; }}
    @media print {{
        body {{ width: 100%; }}
        .no-print {{ display: none; }}
    }}
    .no-print {{ text-align: center; margin: 20px 0; }}
    .no-print button {{ padding: 8px 24px; font-size: 14px; cursor: pointer; }}
</style>
</head>
<body>
    <h2>🏆 AnimalitoPlus</h2>
    <div class="folio">Folio: {apuesta.folio or 'N/A'}</div>
    <table class="info">
        <tr><td>Fecha</td><td>{apuesta.fecha.isoformat()}</td></tr>
        <tr><td>Hora</td><td>{apuesta.horario.strftime('%H:%M')}</td></tr>
        <tr><td>Lotería</td><td>{loteria_nombre}</td></tr>
        <tr><td>Usuario</td><td>{user.nombre}</td></tr>
    </table>
    <table class="detalles">
        <thead><tr><th>#</th><th>Animal</th><th>Monto</th></tr></thead>
        <tbody>{detalles_html}</tbody>
    </table>
    <div class="total">Total: Bs {float(apuesta.total):.2f}</div>
    <div class="estado">{estado_txt}</div>
    {premio_html}
    <div class="footer">Ticket generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    <div class="no-print"><button onclick="window.print()">🖨️ Imprimir</button></div>
</body>
</html>"""
    return HTMLResponse(content=html)

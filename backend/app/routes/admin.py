import io, csv
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, timedelta, datetime, time as _time
from decimal import Decimal
import json

from app.database import get_db
from app.models import Usuario, Apuesta, DetalleApuesta, Transaccion, Resultado, Config, Auditoria, Notificacion, Cupo, AcumuladoCupo, Aviso, Animal, Sorteo
from app.schemas import AdminUsuarioUpdate, ApuestaOut, ReporteOut, ResultadoCreate, ResultadoUpdate, TransaccionOut, AdminPagoUpdate
from app.auth import require_admin, get_current_user



def registrar_auditoria(db: Session, usuario_id: int, accion: str, descripcion: str = None, ip: str = None):
    db.add(Auditoria(usuario_id=usuario_id, accion=accion, descripcion=descripcion, ip=ip))

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ===== USUARIOS =====

@router.get("/usuarios")
def listar_usuarios(admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).order_by(Usuario.created_at.desc()).all()
    return usuarios


@router.get("/usuarios/{usuario_id}")
def detalle_usuario(usuario_id: int, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.put("/usuarios/{usuario_id}")
def actualizar_usuario(
    usuario_id: int,
    data: AdminUsuarioUpdate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.saldo is not None:
        nuevo_saldo = Decimal(str(data.saldo))
        diferencia = nuevo_saldo - user.saldo
        user.saldo = nuevo_saldo
        db.add(Transaccion(
            usuario_id=user.id,
            tipo="ajuste_admin",
            monto=diferencia,
            descripcion=f"Ajuste admin: {diferencia:+.2f}",
        ))

    if data.bloqueado is not None:
        user.bloqueado = data.bloqueado

    db.commit()
    return user


# ===== APUESTAS GLOBALES =====

@router.get("/apuestas")
def listar_apuestas_admin(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    apuestas = (
        db.query(Apuesta)
        .order_by(Apuesta.created_at.desc())
        .limit(limit)
        .all()
    )
    # Cargar relaciones
    for a in apuestas:
        a.usuario_nombre = f"{a.usuario.nombre} {a.usuario.apellido}"
    return apuestas


# ===== REPORTES =====

@router.get("/reportes/diario")
def reporte_diario(
    fecha: str = None,
    formato: str = Query(None, pattern="^(csv|json)$"),
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        target = date.fromisoformat(fecha) if fecha else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")

    total_apuestas = db.query(func.sum(Apuesta.total)).filter(Apuesta.fecha == target).scalar() or 0
    count_apuestas = db.query(func.count(Apuesta.id)).filter(Apuesta.fecha == target).scalar() or 0
    total_premios = (
        db.query(func.sum(Transaccion.monto))
        .filter(
            Transaccion.tipo == "pago_premio",
            func.date(Transaccion.created_at) == target,
        )
        .scalar() or 0
    )
    ganancia = round(total_apuestas - total_premios, 2)

    if formato == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["fecha", "monto_jugado", "monto_premios", "ganancia_banca", "total_apuestas"])
        w.writerow([str(target), round(total_apuestas, 2), round(total_premios, 2), ganancia, count_apuestas])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=reporte_diario_{target}.csv"},
        )

    return {
        "fecha": str(target),
        "monto_jugado": round(total_apuestas, 2),
        "monto_premios": round(total_premios, 2),
        "ganancia_banca": ganancia,
        "total_apuestas": count_apuestas,
    }


@router.get("/reportes/semanal")
def reporte_semanal(
    formato: str = Query(None, pattern="^(csv|json)$"),
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    hoy = date.today()
    inicio = hoy - timedelta(days=6)
    reportes = []

    for i in range(7):
        dia = inicio + timedelta(days=i)
        jugado = db.query(func.sum(Apuesta.total)).filter(Apuesta.fecha == dia).scalar() or 0
        premios = (
            db.query(func.sum(Transaccion.monto))
            .filter(Transaccion.tipo == "pago_premio", func.date(Transaccion.created_at) == dia)
            .scalar() or 0
        )
        reportes.append({
            "fecha": str(dia),
            "monto_jugado": round(jugado, 2),
            "monto_premios": round(premios, 2),
            "ganancia_banca": round(jugado - premios, 2),
        })

    if formato == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["fecha", "monto_jugado", "monto_premios", "ganancia_banca"])
        for r in reportes:
            w.writerow([r["fecha"], r["monto_jugado"], r["monto_premios"], r["ganancia_banca"]])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=reporte_semanal_{inicio}_{hoy}.csv"},
        )

    return reportes


# ===== SORTEOS =====

@router.get("/auditoria")
def listar_auditoria(
    limit: int = 100,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = db.query(Auditoria).order_by(Auditoria.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "usuario_id": l.usuario_id,
            "accion": l.accion,
            "descripcion": l.descripcion,
            "ip": l.ip,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.post("/resultados")
def ingresar_resultado(
    data: ResultadoCreate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        fecha = date.fromisoformat(data.fecha) if data.fecha else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida")
    horario = datetime.strptime(data.horario, "%H:%M").time()

    sorteo = db.query(Sorteo).filter(
        Sorteo.loteria == data.loteria,
        Sorteo.fecha == fecha,
        Sorteo.horario == horario,
    ).first()
    if not sorteo:
        sorteo = Sorteo(loteria=data.loteria, fecha=fecha, horario=horario, estado="pendiente")
        db.add(sorteo)
        db.flush()
    sorteo.estado = "realizado"

    resultado = Resultado(
        sorteo_id=sorteo.id,
        loteria=data.loteria,
        fecha=fecha,
        horario=horario,
        animal_id=data.animal_id,
        numero=data.numero,
    )
    db.add(resultado)
    db.flush()

    ganadas = procesar_apuestas_por_resultado(db, resultado)
    db.commit()
    registrar_auditoria(db, admin.id, "resultado_manual",
        f"{data.loteria} {data.horario} → animal {data.animal_id} ({ganadas} ganadoras)")
    return {"mensaje": "Resultado registrado y apuestas procesadas", "ganadoras": ganadas}


@router.put("/resultados/{resultado_id}")
def editar_resultado(
    resultado_id: int,
    data: ResultadoUpdate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    resultado = db.query(Resultado).filter(Resultado.id == resultado_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")

    if not resultado.sorteo_id:
        sorteo = db.query(Sorteo).filter(
            Sorteo.loteria == resultado.loteria,
            Sorteo.fecha == resultado.fecha,
            Sorteo.horario == resultado.horario,
        ).first()
        if not sorteo:
            sorteo = Sorteo(loteria=resultado.loteria, fecha=resultado.fecha, horario=resultado.horario, estado="pendiente")
            db.add(sorteo)
            db.flush()
        resultado.sorteo_id = sorteo.id

    old_info = f"{resultado.animal_id} #{resultado.numero}"
    resultado.animal_id = data.animal_id
    resultado.numero = data.numero
    db.flush()

    ganadas = procesar_apuestas_por_resultado(db, resultado)
    db.commit()
    registrar_auditoria(db, admin.id, "resultado_editado",
        f"{resultado.loteria} {resultado.horario}: {old_info} → {data.animal_id} #{data.numero} ({ganadas} ganadoras)")
    return {"mensaje": "Resultado actualizado", "ganadoras": ganadas}


@router.delete("/resultados/{resultado_id}")
def eliminar_resultado(
    resultado_id: int,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    resultado = db.query(Resultado).filter(Resultado.id == resultado_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")

    loteria, fecha, horario = resultado.loteria, resultado.fecha, resultado.horario
    apuestas = (
        db.query(Apuesta)
        .filter(
            Apuesta.loteria == loteria,
            Apuesta.fecha == fecha,
            Apuesta.horario == horario,
            Apuesta.estado.in_(["ganada", "perdida"]),
        )
        .all()
    )
    revertidas = 0
    for apuesta in apuestas:
        if apuesta.estado == "ganada":
            detalles_ganadores = [d for d in apuesta.detalles if d.animal_id == resultado.animal_id]
            monto_base = sum(d.monto for d in detalles_ganadores)
            premio = monto_base * get_multiplicador(db)
            usuario = db.query(Usuario).filter(Usuario.id == apuesta.usuario_id).first()
            if usuario:
                usuario.saldo -= premio
                db.add(Transaccion(
                    usuario_id=usuario.id,
                    tipo="ajuste_admin",
                    monto=-premio,
                    descripcion=f"Reversión premio {loteria} {horario.strftime('%H:%M')} (eliminación resultado {resultado_id})",
                ))
            revertidas += 1
        apuesta.estado = "pendiente"

    db.delete(resultado)
    db.commit()
    info = f"{loteria} {horario.strftime('%H:%M')} → {resultado.animal_id} ({revertidas} apuestas revertidas)"
    registrar_auditoria(db, admin.id, "resultado_eliminado", info)
    return {"mensaje": "Resultado eliminado", "apuestas_revertidas": revertidas}


@router.get("/ganadores")
def listar_ganadores(
    loteria: Optional[str] = None,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
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
    mult = get_multiplicador(db)

    return [
        {
            "usuario_nombre": f"{u.nombre} {u.apellido}".strip(),
            "apuesta_id": a.id,
            "loteria": a.loteria,
            "fecha": a.fecha.isoformat(),
            "horario": a.horario.strftime("%H:%M"),
            "animal_id": d.animal_id,
            "monto_apostado": d.monto,
            "premio": d.monto * mult,
        }
        for a, d, u in rows
    ]


def get_multiplicador(db: Session) -> int:
    cfg = db.query(Config).filter(Config.clave == "config_general").first()
    if cfg:
        return int(json.loads(cfg.valor).get("multiplicador", 30))
    return 30


def procesar_apuestas_por_resultado(db: Session, resultado: Resultado):
    """Marca apuestas pendientes como ganadas/perdidas según un resultado."""
    apuestas = (
        db.query(Apuesta)
        .filter(
            Apuesta.loteria == resultado.loteria,
            Apuesta.fecha == resultado.fecha,
            Apuesta.horario == resultado.horario,
            Apuesta.estado == "pendiente",
        )
        .all()
    )
    ganadas = 0
    for apuesta in apuestas:
        detalles_ganadores = [d for d in apuesta.detalles if d.animal_id == resultado.animal_id]
        if detalles_ganadores:
            monto_base = sum(d.monto for d in detalles_ganadores)
            premio = monto_base * get_multiplicador(db)
            usuario = db.query(Usuario).filter(Usuario.id == apuesta.usuario_id).first()
            if usuario:
                usuario.saldo += premio
                db.add(Transaccion(
                    usuario_id=usuario.id,
                    tipo="pago_premio",
                    monto=premio,
                    descripcion=f"Premio {resultado.loteria} {resultado.horario.strftime('%H:%M')}",
                ))
                db.add(Notificacion(
                    usuario_id=usuario.id,
                    tipo="ganada",
                    titulo="🎉 ¡Ganaste!",
                    contenido=f"Tu apuesta en {resultado.loteria} ({resultado.horario.strftime('%H:%M')}) — animal {resultado.animal_id} — ganó Bs {premio:.2f}",
                    referencia_id=apuesta.id,
                ))
            apuesta.estado = "ganada"
            ganadas += 1
        else:
            apuesta.estado = "perdida"
            db.add(Notificacion(
                usuario_id=apuesta.usuario_id,
                tipo="perdida",
                titulo="😢 No ganaste",
                contenido=f"Tu apuesta en {resultado.loteria} ({resultado.horario.strftime('%H:%M')}) no resultó ganadora. ¡Sigue intentando!",
                referencia_id=apuesta.id,
            ))
    return ganadas


@router.post("/scraper")
def trigger_scraper(
    fecha: Optional[str] = None,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.scraper import run_scraper_parallel

    scrape_results = run_scraper_parallel(fecha, db)
    total_ganadas = 0
    for loteria, info in scrape_results["loterias"].items():
        resultados = (
            db.query(Resultado)
            .filter(
                Resultado.loteria == loteria,
                Resultado.fecha == scrape_results["fecha"],
            )
            .all()
        )
        for r in resultados:
            total_ganadas += procesar_apuestas_por_resultado(db, r)
    db.commit()
    registrar_auditoria(db, admin.id, "scraper",
        f"Fecha {scrape_results['fecha']}: {scrape_results['total']} resultados, {total_ganadas} apuestas procesadas")
    scrape_results["apuestas_procesadas"] = total_ganadas
    return scrape_results


# ===== PAGOS / RECARGAS / RETIROS =====

@router.get("/pagos", response_model=list[TransaccionOut])
def listar_pagos(
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Transaccion)
    if tipo:
        query = query.filter(Transaccion.tipo == tipo)
    if estado:
        query = query.filter(Transaccion.estado == estado)
    pagos = query.order_by(Transaccion.created_at.desc()).limit(100).all()

    result = []
    for p in pagos:
        u = db.query(Usuario).filter(Usuario.id == p.usuario_id).first()
        result.append({
            "id": p.id,
            "usuario_id": p.usuario_id,
            "tipo": p.tipo,
            "monto": p.monto,
            "metodo": p.metodo,
            "referencia": p.referencia,
            "estado": p.estado,
            "descripcion": p.descripcion,
            "created_at": p.created_at,
            "usuario_nombre": f"{u.nombre} {u.apellido}" if u else None,
            "usuario_cedula": u.cedula if u else None,
            "usuario_telefono": u.telefono if u else None,
            "usuario_banco": u.banco if u else None,
            "usuario_banco_codigo": u.banco_codigo if u else None,
            "usuario_titular": u.pago_movil_titular if u else None,
        })
    return result


TRANSICIONES_PAGO = {
    "pendiente": ["en_proceso", "completado", "cancelado"],
    "en_proceso": ["completado", "cancelado"],
    "completado": [],
    "cancelado": [],
}

@router.post("/pagos/{pago_id}/estado")
def cambiar_estado_pago(
    pago_id: int,
    data: AdminPagoUpdate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    pago = db.query(Transaccion).filter(Transaccion.id == pago_id).with_for_update().first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    if data.estado not in TRANSICIONES_PAGO.get(pago.estado, []):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cambiar de '{pago.estado}' a '{data.estado}'",
        )

    # Revertir saldo si se sale de completado
    if pago.estado == "completado":
        user = db.query(Usuario).filter(Usuario.id == pago.usuario_id).with_for_update().first()
        if pago.tipo == "recarga":
            user.saldo -= pago.monto
        elif pago.tipo == "retiro":
            user.saldo += pago.monto

    if data.estado == "completado":
        user = db.query(Usuario).filter(Usuario.id == pago.usuario_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if pago.tipo == "recarga":
            user.saldo += pago.monto
            if user.referido_por and not user.bono_referido:
                referidor = db.query(Usuario).filter(Usuario.id == user.referido_por).with_for_update().first()
                if referidor:
                    bono = round(pago.monto * 0.05, 2)
                    referidor.saldo += bono
                    db.add(Transaccion(
                        usuario_id=referidor.id,
                        tipo="ajuste_admin",
                        monto=bono,
                        descripcion=f"Bono referido {user.correo} ({pago.monto:.2f})",
                    ))
                    user.bono_referido = True
        elif pago.tipo == "retiro":
            if pago.monto > user.saldo:
                raise HTTPException(status_code=400, detail="Saldo insuficiente")
            user.saldo -= pago.monto
        else:
            raise HTTPException(status_code=400, detail="Tipo de pago no soportado")

    pago.estado = data.estado
    db.commit()
    return {"mensaje": f"Pago marcado como {data.estado}", "tipo": pago.tipo, "monto": pago.monto}


# ===== CONFIGURACION DE CASA =====

@router.get("/config/casa")
def get_config_casa(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'casa').first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuración de casa no encontrada")
    return json.loads(cfg.valor)


@router.put("/config/casa")
def update_config_casa(
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'casa').first()
    if not cfg:
        cfg = Config(clave='casa', valor=json.dumps(data))
        db.add(cfg)
    else:
        cfg.valor = json.dumps(data)
    db.commit()
    return {"mensaje": "Configuración de casa actualizada"}


# ===== CONFIGURACION SCHEDULER =====

@router.get("/config/scheduler")
def get_config_scheduler(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'scheduler').first()
    if not cfg:
        return {"habilitado": True, "intervalo_minutos": 60}
    return json.loads(cfg.valor)


@router.put("/config/scheduler")
def update_config_scheduler(
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'scheduler').first()
    if not cfg:
        cfg = Config(clave='scheduler', valor=json.dumps(data))
        db.add(cfg)
    else:
        cfg.valor = json.dumps(data)
    db.commit()
    return {"mensaje": "Configuración del scheduler actualizada"}


# ===== CONFIGURACION DE HORARIOS (recarga/retiro) =====

@router.get("/config/horarios")
def get_config_horarios(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'horarios').first()
    if not cfg:
        return {
            "recarga": {"inicio": "06:00", "fin": "22:00", "dias": [1, 2, 3, 4, 5, 6, 7]},
            "retiro": {"inicio": "08:00", "fin": "16:00", "dias": [1, 2, 3, 4, 5]},
        }
    return json.loads(cfg.valor)


@router.put("/config/horarios")
def update_config_horarios(
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'horarios').first()
    if not cfg:
        cfg = Config(clave='horarios', valor=json.dumps(data))
        db.add(cfg)
    else:
        cfg.valor = json.dumps(data)
    db.commit()
    return {"mensaje": "Horarios actualizados"}


# ===== CONFIGURACION GENERAL (multiplicador, etc.) =====

@router.get("/config/general")
def get_config_general(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'config_general').first()
    if not cfg:
        return {"multiplicador": 30}
    return json.loads(cfg.valor)


@router.put("/config/general")
def update_config_general(
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'config_general').first()
    if not cfg:
        cfg = Config(clave='config_general', valor=json.dumps(data))
        db.add(cfg)
    else:
        cfg.valor = json.dumps(data)
    db.commit()
    return {"mensaje": "Configuración general actualizada"}


# ===== CONFIGURACION DE LIMITES =====

@router.get("/config/limites")
def get_config_limites(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'limites').first()
    if not cfg:
        return {"max_por_apuesta": 0, "max_por_hora": 0, "max_por_dia": 0}
    return json.loads(cfg.valor)


@router.put("/config/limites")
def update_config_limites(
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(Config).filter(Config.clave == 'limites').first()
    if not cfg:
        cfg = Config(clave='limites', valor=json.dumps(data))
        db.add(cfg)
    else:
        cfg.valor = json.dumps(data)
    db.commit()
    return {"mensaje": "Límites actualizados"}


# ===== AVISOS =====

@router.get("/avisos")
def listar_avisos_admin(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    avisos = db.query(Aviso).order_by(desc(Aviso.created_at)).limit(50).all()
    return [
        {
            "id": a.id,
            "fuente": a.fuente,
            "loteria": a.loteria,
            "titulo": a.titulo,
            "contenido": a.contenido,
            "url_instagram": a.url_instagram,
            "activo": a.activo,
            "created_at": a.created_at.isoformat(),
        }
        for a in avisos
    ]


@router.post("/avisos")
def crear_aviso(
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    aviso = Aviso(
        fuente="manual",
        loteria=data.get("loteria"),
        titulo=data.get("titulo", "Aviso"),
        contenido=data.get("contenido", ""),
        activo=data.get("activo", True),
    )
    db.add(aviso)
    db.commit()
    registrar_auditoria(db, admin.id, "aviso_creado", f"Aviso: {aviso.titulo}")
    return {"mensaje": "Aviso creado", "id": aviso.id}


@router.put("/avisos/{aviso_id}")
def actualizar_aviso(
    aviso_id: int,
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    aviso = db.query(Aviso).filter(Aviso.id == aviso_id).first()
    if not aviso:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    if "titulo" in data:
        aviso.titulo = data["titulo"]
    if "contenido" in data:
        aviso.contenido = data["contenido"]
    if "loteria" in data:
        aviso.loteria = data["loteria"]
    if "activo" in data:
        aviso.activo = data["activo"]
    db.commit()
    registrar_auditoria(db, admin.id, "aviso_editado", f"Aviso #{aviso_id}")
    return {"mensaje": "Aviso actualizado"}


# ===== ANIMALES (admin) =====

@router.get("/animales")
def listar_animales_admin(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    animales = db.query(Animal).order_by(Animal.id).all()
    return [
        {"id": a.id, "numero": a.numero, "nombre": a.nombre, "icono": a.icono}
        for a in animales
    ]


@router.put("/animales/{animal_id}")
def actualizar_animal(
    animal_id: str,
    data: dict,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal no encontrado")
    if "nombre" in data:
        animal.nombre = data["nombre"].upper()
    if "icono" in data:
        animal.icono = data["icono"]
    db.commit()
    registrar_auditoria(db, admin.id, "animal_editado",
        f"Animal #{animal_id}: nombre={animal.nombre}")
    return {"mensaje": "Animal actualizado"}


# ===== CUPOS (riesgo por animal + horario) =====

@router.get("/cupos")
def listar_cupos(
    loteria: Optional[str] = None,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):


    query = db.query(Cupo)
    if loteria:
        query = query.filter(Cupo.loteria == loteria)
    cupos = query.order_by(Cupo.loteria, Cupo.horario, Cupo.animal_id).all()
    return [
        {
            "id": c.id,
            "loteria": c.loteria,
            "horario": c.horario.strftime("%H:%M"),
            "animal_id": c.animal_id,
            "maximo": float(c.maximo),
            "activo": c.activo,
        }
        for c in cupos
    ]


@router.put("/cupos/batch")
def actualizar_cupos(
    data: list[dict],
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):


    for item in data:
        if item.get("id"):
            cupo = db.query(Cupo).filter(Cupo.id == item["id"]).first()
            if cupo:
                if "maximo" in item:
                    cupo.maximo = item["maximo"]
                if "activo" in item:
                    cupo.activo = item["activo"]
        else:
            existente = db.query(Cupo).filter(
                Cupo.loteria == item["loteria"],
                Cupo.horario == _time.fromisoformat(item["horario"]),
                Cupo.animal_id == str(item["animal_id"]),
            ).first()
            if not existente:
                db.add(Cupo(
                    loteria=item["loteria"],
                    horario=_time.fromisoformat(item["horario"]),
                    animal_id=str(item["animal_id"]),
                    maximo=item.get("maximo", 0),
                    activo=item.get("activo", True),
                ))
    db.commit()
    registrar_auditoria(db, admin.id, "cupos_actualizados", f"{len(data)} cupos")
    return {"mensaje": f"{len(data)} cupos actualizados"}


@router.post("/cupos/generar")
def generar_cupos_default(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):



    existentes = db.query(Cupo).count()
    if existentes > 0:
        return {"mensaje": f"Ya existen {existentes} cupos", "generados": 0}
    loterias = ["lotto_activo", "la_granjita", "selvaplus"]
    horarios = [f"{h}:00" for h in range(8, 20)]
    count = 0
    for loteria in loterias:
        for h in horarios:
            for animal in ANIMALES_HARDCODE:
                db.add(Cupo(
                    loteria=loteria,
                    horario=_time.fromisoformat(h),
                    animal_id=str(animal["id"]),
                    maximo=0,
                    activo=False,
                ))
                count += 1
    db.commit()
    registrar_auditoria(db, admin.id, "cupos_generados", f"{count} cupos creados")
    return {"mensaje": f"{count} cupos generados", "generados": count}


@router.get("/cupos/acumulados")
def listar_acumulados(
    fecha: Optional[str] = None,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    today = date.today()
    q = db.query(AcumuladoCupo)
    if fecha:
        try:
            q = q.filter(AcumuladoCupo.fecha == date.fromisoformat(fecha))
        except ValueError:
            q = q.filter(AcumuladoCupo.fecha == today)
    else:
        q = q.filter(AcumuladoCupo.fecha == today)
    rows = q.order_by(AcumuladoCupo.loteria, AcumuladoCupo.horario, AcumuladoCupo.animal_id).all()
    return [
        {
            "fecha": r.fecha.isoformat(),
            "loteria": r.loteria,
            "horario": r.horario.strftime("%H:%M"),
            "animal_id": r.animal_id,
            "acumulado": float(r.acumulado),
        }
        for r in rows
    ]


@router.post("/cupos/reset-acumulados")
def reset_acumulados(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):


    count = db.query(AcumuladoCupo).delete()
    db.commit()
    registrar_auditoria(db, admin.id, "acumulados_reset", f"{count} registros eliminados")
    return {"mensaje": f"{count} acumulados eliminados"}


@router.delete("/avisos/{aviso_id}")
def eliminar_aviso(
    aviso_id: int,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):

    aviso = db.query(Aviso).filter(Aviso.id == aviso_id).first()
    if not aviso:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    db.delete(aviso)
    db.commit()
    registrar_auditoria(db, admin.id, "aviso_eliminado", f"Aviso #{aviso_id}")
    return {"mensaje": "Aviso eliminado"}

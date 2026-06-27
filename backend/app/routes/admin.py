from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime
import json

from app.database import get_db
from app.models import Usuario, Apuesta, DetalleApuesta, Transaccion, Resultado, Config, Auditoria
from app.schemas import AdminUsuarioUpdate, ApuestaOut, ReporteOut, ResultadoCreate, TransaccionOut, AdminPagoUpdate
from app.auth import require_admin, get_current_user


def registrar_auditoria(db: Session, usuario_id: int, accion: str, descripcion: str = None, ip: str = None):
    db.add(Auditoria(usuario_id=usuario_id, accion=accion, descripcion=descripcion, ip=ip))
    db.commit()

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
        diferencia = data.saldo - user.saldo
        user.saldo = data.saldo
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
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = date.fromisoformat(fecha) if fecha else date.today()

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

    return {
        "fecha": str(target),
        "monto_jugado": round(total_apuestas, 2),
        "monto_premios": round(total_premios, 2),
        "ganancia_banca": round(total_apuestas - total_premios, 2),
        "total_apuestas": count_apuestas,
    }


@router.get("/reportes/semanal")
def reporte_semanal(admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
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
    fecha = date.fromisoformat(data.fecha) if data.fecha else date.today()
    horario = datetime.strptime(data.horario, "%H:%M").time()

    resultado = Resultado(
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


@router.get("/ganadores")
def listar_ganadores(
    loteria: Optional[str] = None,
    usuario: Usuario = Depends(get_current_user),
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

    return [
        {
            "usuario_id": u.id,
            "usuario_nombre": f"{u.nombre} {u.apellido}".strip(),
            "usuario_correo": u.correo,
            "apuesta_id": a.id,
            "loteria": a.loteria,
            "fecha": a.fecha.isoformat(),
            "horario": a.horario.strftime("%H:%M"),
            "animal_id": d.animal_id,
            "monto_apostado": d.monto,
            "premio": d.monto * 30,
        }
        for a, d, u in rows
    ]


MULTIPLICADOR = 30


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
        ganadora = any(d.animal_id == resultado.animal_id for d in apuesta.detalles)
        if ganadora:
            premio = apuesta.total * MULTIPLICADOR
            usuario = db.query(Usuario).filter(Usuario.id == apuesta.usuario_id).first()
            if usuario:
                usuario.saldo += premio
                db.add(Transaccion(
                    usuario_id=usuario.id,
                    tipo="pago_premio",
                    monto=premio,
                    descripcion=f"Premio {resultado.loteria} {resultado.horario.strftime('%H:%M')}",
                ))
            apuesta.estado = "ganada"
            ganadas += 1
        else:
            apuesta.estado = "perdida"
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


@router.post("/pagos/{pago_id}/estado")
def cambiar_estado_pago(
    pago_id: int,
    data: AdminPagoUpdate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    pago = db.query(Transaccion).filter(Transaccion.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pago.estado == "completado":
        raise HTTPException(status_code=400, detail="El pago ya fue completado")

    if data.estado == "completado":
        user = db.query(Usuario).filter(Usuario.id == pago.usuario_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if pago.tipo == "recarga":
            user.saldo += pago.monto
            # Bono de referido (5% de la primera recarga)
            if user.referido_por and not user.bono_referido:
                referidor = db.query(Usuario).filter(Usuario.id == user.referido_por).first()
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
        return CASA_DEFAULT
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


CASA_DEFAULT = {
    "nombre": "Gabriel Alejandro Rosas Rosas",
    "banco": "Banco Mercantil",
    "banco_codigo": "0105",
    "cedula": "27650586",
    "telefono": "4123656230",
}


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

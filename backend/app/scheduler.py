import json, traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()


def job_scraper():
    from app.database import SessionLocal
    from app.scraper import run_scraper_parallel
    from app.models import Resultado, Auditoria
    from app.routes.admin import procesar_apuestas_por_resultado

    db = SessionLocal()
    try:
        results = run_scraper_parallel(None, db)
        total_ganadas = 0
        for loteria in results.get("loterias", {}):
            res_list = db.query(Resultado).filter(
                Resultado.loteria == loteria,
                Resultado.fecha == results["fecha"],
            ).all()
            for r in res_list:
                total_ganadas += procesar_apuestas_por_resultado(db, r)
        db.commit()
        db.add(Auditoria(
            usuario_id=None, accion="scheduler_scraper",
            descripcion=f"Auto: {results.get('total', 0)} resultados, {total_ganadas} apuestas",
        ))
        db.commit()
    except Exception:
        db.rollback()
        db.add(Auditoria(
            usuario_id=None, accion="scheduler_scraper",
            descripcion=f"Error: {traceback.format_exc()[:500]}",
        ))
        db.commit()
    finally:
        db.close()


def job_instagram_avisos():
    from app.database import SessionLocal
    from app.instagram_scraper import scrape_avisos_instagram

    db = SessionLocal()
    try:
        resultados = scrape_avisos_instagram(db)
        if resultados:
            print(f"[instagram] {len(resultados)} avisos nuevos")
    except Exception:
        print(f"[instagram] Error: {traceback.format_exc()[:300]}")
    finally:
        db.close()


def job_reset_cupos():
    from app.database import SessionLocal
    from app.models import AcumuladoCupo

    db = SessionLocal()
    try:
        count = db.query(AcumuladoCupo).delete()
        db.commit()
        print(f"[cupos] {count} acumulados reseteados a las 00:00")
    except Exception:
        db.rollback()
        print(f"[cupos] Error reset: {traceback.format_exc()[:300]}")
    finally:
        db.close()


def start_scheduler():
    from app.database import SessionLocal
    from app.models import Config

    db = SessionLocal()
    try:
        cfg = db.query(Config).filter(Config.clave == "scheduler").first()
        data = json.loads(cfg.valor) if cfg else {}
        intervalo = int(data.get("intervalo_minutos", 60))
        habilitado = data.get("habilitado", True)
    except Exception:
        intervalo, habilitado = 60, True
    finally:
        db.close()

    if not habilitado:
        return

    scheduler.add_job(
        job_scraper,
        IntervalTrigger(minutes=intervalo),
        id="scraper_auto",
        replace_existing=True,
    )
    scheduler.add_job(
        job_instagram_avisos,
        IntervalTrigger(minutes=intervalo),
        id="instagram_avisos",
        replace_existing=True,
    )
    scheduler.add_job(
        job_reset_cupos,
        CronTrigger(hour=0, minute=0),
        id="reset_cupos_diario",
        replace_existing=True,
    )
    scheduler.start()

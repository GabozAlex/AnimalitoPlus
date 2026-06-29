import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Resultado, Sorteo

logger = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

LOTTERIES = {
    "lotto_activo": {
        "url": "https://www.loteriadehoy.com/animalito/lottoactivo/resultados/",
        "name": "Lotto Activo",
    },
    "la_granjita": {
        "url": "https://www.loteriadehoy.com/animalito/lagranjita/resultados/",
        "name": "La Granjita",
    },
    "selvaplus": {
        "url": "https://www.loteriadehoy.com/animalito/selvaplus/resultados/",
        "name": "Selva Plus",
    },
}

HORA_MAP = {
    "08:00 AM": "08:00:00", "09:00 AM": "09:00:00",
    "10:00 AM": "10:00:00", "11:00 AM": "11:00:00",
    "12:00 PM": "12:00:00", "01:00 PM": "13:00:00",
    "02:00 PM": "14:00:00", "03:00 PM": "15:00:00",
    "04:00 PM": "16:00:00", "05:00 PM": "17:00:00",
    "06:00 PM": "18:00:00", "07:00 PM": "19:00:00",
    "08:30 AM": "08:30:00", "09:30 AM": "09:30:00",
    "10:30 AM": "10:30:00", "11:30 AM": "11:30:00",
    "12:30 PM": "12:30:00", "01:30 PM": "13:30:00",
    "02:30 PM": "14:30:00", "03:30 PM": "15:30:00",
    "04:30 PM": "16:30:00", "05:30 PM": "17:30:00",
    "06:30 PM": "18:30:00", "07:30 PM": "19:30:00",
}


ANIMAL_NOMBRE_A_ID = {
    "DELFIN": "0",
    "BALLENA": "00",
    "CARNERO": "1", "TORO": "2", "CIEMPIES": "3", "ALACRAN": "4",
    "LEON": "5", "RANA": "6", "PERICO": "7", "RATON": "8",
    "AGUILA": "9", "TIGRE": "10", "GATO": "11", "CABALLO": "12",
    "MONO": "13", "PALOMA": "14", "ZORRO": "15", "OSO": "16",
    "PAVO": "17", "BURRO": "18", "CHIVO": "19", "COCHINO": "20",
    "GALLO": "21", "CAMELLO": "22", "CEBRA": "23", "IGUANA": "24",
    "GALLINA": "25", "VACA": "26", "PERRO": "27", "ZAMURO": "28",
    "ELEFANTE": "29", "CAIMAN": "30", "LAPA": "31", "ARDILLA": "32",
    "PESCADO": "33", "VENADO": "34", "JIRAFA": "35", "CULEBRA": "36",
}


def scrape_lottery(url: str, loteria: str, fecha: str) -> list[dict]:
    records = []
    try:
        resp = requests.post(url, data={"fecha": fecha}, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"[{loteria}] Error fetching {fecha}: {e}")
        return records

    soup = BeautifulSoup(resp.text, "lxml")
    items = soup.select("div.row.text-center.js-con > div")
    if not items:
        logger.warning(f"[{loteria}] No results for {fecha}")
        return records

    prefixes = []
    for k, v in LOTTERIES.items():
        if k == loteria:
            prefixes = [v["name"], v["name"].replace(" ", "")]
            break

    for item in items:
        h4 = item.select_one("h4")
        h5 = item.select_one("h5")
        if not h4 or not h5:
            continue
        text = h4.get_text(strip=True)
        time_text = h5.get_text(strip=True)
        for p in prefixes:
            if time_text.startswith(p):
                time_text = time_text[len(p):].strip()
                break
        parts = text.split(" ", 1)
        if len(parts) != 2:
            continue
        num_str, animal = parts
        try:
            numero = int(num_str)
        except ValueError:
            logger.warning(f"[{loteria}] Bad number '{num_str}' on {fecha}")
            continue
        hour_24 = HORA_MAP.get(time_text)
        if not hour_24:
            logger.warning(f"[{loteria}] Unknown time '{time_text}' on {fecha}")
            continue
        animal_id = ANIMAL_NOMBRE_A_ID.get(animal.upper(), str(numero))
        records.append({
            "fecha": fecha,
            "loteria": loteria,
            "numero": num_str,
            "animal": animal.upper(),
            "animal_id": animal_id,
            "horario": hour_24,
        })

    logger.info(f"[{loteria}] {fecha}: {len(records)} records")
    return records


def save_results(db: Session, records: list[dict]) -> int:
    saved = 0
    for r in records:
        exists = (
            db.query(Resultado)
            .filter(
                Resultado.fecha == r["fecha"],
                Resultado.loteria == r["loteria"],
                Resultado.horario == r["horario"],
                Resultado.animal_id == r["animal_id"],
            )
            .first()
        )
        if exists:
            continue
        from datetime import datetime as _dt
        horario_time = _dt.strptime(r["horario"], "%H:%M:%S").time()
        sorteo = db.query(Sorteo).filter(
            Sorteo.loteria == r["loteria"],
            Sorteo.fecha == r["fecha"],
            Sorteo.horario == horario_time,
        ).first()
        if not sorteo:
            sorteo = Sorteo(loteria=r["loteria"], fecha=r["fecha"], horario=horario_time, estado="pendiente")
            db.add(sorteo)
            db.flush()
        sorteo.estado = "realizado"
        db.add(Resultado(
            sorteo_id=sorteo.id,
            fecha=r["fecha"],
            loteria=r["loteria"],
            horario=horario_time,
            animal_id=r["animal_id"],
            numero=r["numero"],
        ))
        saved += 1
    db.commit()
    return saved


def run_scraper(fecha: Optional[str] = None) -> dict:
    if fecha is None:
        fecha = date.today().isoformat()
    results = {"fecha": fecha, "total": 0, "loterias": {}}
    for loteria, info in LOTTERIES.items():
        records = scrape_lottery(info["url"], loteria, fecha)
        results["loterias"][loteria] = {"scraped": len(records)}
    return results


def run_scraper_save(fecha: Optional[str] = None, db: Optional[Session] = None) -> dict:
    if fecha is None:
        fecha = date.today().isoformat()
    close_db = db is None
    if db is None:
        db = SessionLocal()
    try:
        total_saved = 0
        results = {"fecha": fecha, "total": 0, "loterias": {}}
        for loteria, info in LOTTERIES.items():
            records = scrape_lottery(info["url"], loteria, fecha)
            saved = save_results(db, records)
            total_saved += saved
            results["loterias"][loteria] = {"scraped": len(records), "saved": saved}
        results["total"] = total_saved
        return results
    finally:
        if close_db:
            db.close()


def scrape_one(loteria: str, info: dict, fecha: str) -> tuple:
    records = scrape_lottery(info["url"], loteria, fecha)
    return (loteria, records)


def run_scraper_parallel(fecha: Optional[str] = None, db: Optional[Session] = None) -> dict:
    if fecha is None:
        fecha = date.today().isoformat()
    close_db = db is None
    if db is None:
        db = SessionLocal()
    try:
        scraped_per_loteria = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(scrape_one, loteria, info, fecha): loteria
                for loteria, info in LOTTERIES.items()
            }
            for future in as_completed(futures):
                loteria, records = future.result()
                scraped_per_loteria[loteria] = records

        total_saved = 0
        results = {"fecha": fecha, "total": 0, "loterias": {}}
        for loteria, records in scraped_per_loteria.items():
            saved = save_results(db, records)
            total_saved += saved
            results["loterias"][loteria] = {"scraped": len(records), "saved": saved}
        results["total"] = total_saved
        return results
    finally:
        if close_db:
            db.close()

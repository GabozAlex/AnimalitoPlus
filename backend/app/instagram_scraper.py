import json, traceback, re
from datetime import datetime

CUENTAS = {
    "lotto_activo": "lottoactivovzla",
    "la_granjita": "lagranjitaofic",
    "selvaplus": "selvaplus",
}

def scrape_avisos_instagram(db):
    resultados = []
    try:
        from instagram_posts_scraper.instagram_posts_scraper import InstaPeriodScraper
        scraper = InstaPeriodScraper()
    except ImportError:
        from app.models import Auditoria
        db.add(Auditoria(usuario_id=None, accion="instagram_scraper",
            descripcion="Error: instagram-posts-scraper no instalado"))
        db.commit()
        return resultados

    from app.models import Aviso, Auditoria

    for loteria, username in CUENTAS.items():
        try:
            posts = scraper.get_posts({"username": username, "days_limit": 2})
            if not posts or not isinstance(posts, list):
                continue
            for post in posts[:3]:
                texto = post.get("texto") or post.get("caption") or post.get("text", "")
                post_id = post.get("id") or post.get("shortcode") or post.get("code", "")
                if not post_id or not texto:
                    continue
                existe = db.query(Aviso).filter(Aviso.url_instagram.like(f"%{post_id}%")).first()
                if existe:
                    continue
                corto = texto[:300]
                titulo = extraer_titulo(corto, loteria)
                aviso = Aviso(
                    fuente="instagram",
                    loteria=loteria,
                    titulo=titulo,
                    contenido=corto,
                    url_instagram=f"https://instagram.com/p/{post_id}",
                    activo=True,
                )
                db.add(aviso)
                resultados.append({"loteria": loteria, "titulo": titulo})
        except Exception as e:
            db.add(Auditoria(usuario_id=None, accion="instagram_scraper",
                descripcion=f"Error con @{username}: {str(e)[:200]}"))
            db.commit()

    if resultados:
        db.add(Auditoria(usuario_id=None, accion="instagram_scraper",
            descripcion=f"{len(resultados)} avisos nuevos de Instagram"))
        db.commit()

    return resultados


def extraer_titulo(texto: str, loteria: str) -> str:
    texto_l = texto.lower()
    if any(p in texto_l for p in ["no hay sorteo", "suspendido", "cancelado", "no se realiza"]):
        return "Sorteo suspendido"
    if any(p in texto_l for p in ["comunicado", "informamos", "noticia"]):
        return "Comunicado importante"
    nombres = {"lotto_activo": "Lotto Activo", "la_granjita": "La Granjita", "selvaplus": "SelvaPlus"}
    return f"Aviso de {nombres.get(loteria, loteria)}"

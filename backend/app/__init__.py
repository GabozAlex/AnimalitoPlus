from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter

app = FastAPI(
    title="AnimalitoPlus API",
    description="Backend de plataforma de lotería de animalitos",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

import os

_DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:3000,https://animalito-plus.vercel.app,https://animalitoplus-production.up.railway.app"
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


from app.routes import auth, apuestas, resultados, pagos, admin, avisos, animales, notificaciones
app.include_router(auth.router)
app.include_router(apuestas.router)
app.include_router(resultados.router)
app.include_router(pagos.router)
app.include_router(admin.router)
app.include_router(avisos.router)
app.include_router(animales.router)
app.include_router(notificaciones.router)

from app.scheduler import start_scheduler


def seed_config_defaults():
    from app.database import SessionLocal
    from app.models import Config

    db = SessionLocal()
    try:
        DEFAULTS = {
            "casa": {
                "nombre": "Gabriel Alejandro Rosas Rosas",
                "banco": "Banco Mercantil",
                "banco_codigo": "0105",
                "cedula": "27650586",
                "telefono": "4123656230",
            },
            "config_general": {"multiplicador": 30},
            "scheduler": {"habilitado": True, "intervalo_minutos": 60},
            "limites": {"max_por_apuesta": 0, "max_por_hora": 0, "max_por_dia": 0},
            "horarios": {
                "recarga": {"inicio": "06:00", "fin": "22:00", "dias": [1, 2, 3, 4, 5, 6, 7]},
                "retiro": {"inicio": "08:00", "fin": "16:00", "dias": [1, 2, 3, 4, 5]},
            },
        }
        import json
        for clave, valor in DEFAULTS.items():
            existe = db.query(Config).filter(Config.clave == clave).first()
            if not existe:
                db.add(Config(clave=clave, valor=json.dumps(valor)))
        db.commit()
    except Exception as e:
        print(f"[config] Error al sembrar defaults: {e}")
        db.rollback()
    finally:
        db.close()


def seed_animales():
    from app.database import SessionLocal
    from app.models import Animal
    from app.animales import ANIMALES_HARDCODE

    db = SessionLocal()
    try:
        count = db.query(Animal).count()
        if count == 0:
            for a in ANIMALES_HARDCODE:
                db.add(Animal(id=str(a["id"]), numero=a["numero"], nombre=a["nombre"], icono=a["icono"]))
            db.commit()
            print(f"[animales] Sembrados {len(ANIMALES_HARDCODE)} animales")
    except Exception as e:
        print(f"[animales] Error: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    try:
        seed_config_defaults()
        seed_animales()
        start_scheduler()
    except Exception as e:
        print(f"[startup] Error: {e}")

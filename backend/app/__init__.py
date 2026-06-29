from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import traceback

from app.limiter import limiter

app = FastAPI(
    title="AnimalitoPlus API",
    description="Backend de plataforma de lotería de animalitos",
    version="1.0.2",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(f"[global_exception] {request.method} {request.url.path}: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno: {type(exc).__name__}: {str(exc)}"},
    )


import os
import threading

_DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:3000,http://localhost:8000,http://127.0.0.1:5173,http://127.0.0.1:3000,http://127.0.0.1:8000,https://animalito-plus.vercel.app,https://animalitoplus-api.onrender.com"
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.2"}


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


from app.routes import auth, apuestas, resultados, pagos, admin, avisos, animales, notificaciones, sorteos
app.include_router(auth.router)
app.include_router(apuestas.router)
app.include_router(resultados.router)
app.include_router(pagos.router)
app.include_router(admin.router)
app.include_router(avisos.router)
app.include_router(animales.router)
app.include_router(notificaciones.router)
app.include_router(sorteos.router)

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


def seed_initial_users():
    from app.database import SessionLocal
    from app.models import Usuario, RolEnum

    db = SessionLocal()
    try:
        admin_exists = db.query(Usuario).filter(Usuario.rol == "admin").first()
        if admin_exists:
            print(f"[users] Admin ya existe: {admin_exists.correo}")
        else:
            import os
            from passlib.hash import bcrypt

            admin_email = os.environ.get("ADMIN_EMAIL", "admin@animalitoplus.com")
            admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
            test_email = os.environ.get("TEST_EMAIL", "test@animalitoplus.com")
            test_pass = os.environ.get("TEST_PASSWORD", "test123")

            users = [
                ("Admin", "Principal", admin_email, bcrypt.hash(admin_pass), "admin"),
                ("Test", "Usuario", test_email, bcrypt.hash(test_pass), "user"),
            ]
            for nombre, apellido, correo, clave, rol in users:
                existe = db.query(Usuario).filter(Usuario.correo == correo).first()
                if not existe:
                    db.add(Usuario(nombre=nombre, apellido=apellido, correo=correo, clave=clave, rol=rol))
                    print(f"[users] Creado {correo} como {rol}")
            db.commit()
    except Exception as e:
        print(f"[users] Error al sembrar usuarios: {e}")
        db.rollback()
    finally:
        db.close()


def _run_seeds():
    try:
        seed_config_defaults()
        seed_animales()
        seed_initial_users()
        start_scheduler()
    except Exception as e:
        traceback.print_exc()
        print(f"[seeds] Error: {e}")


@app.on_event("startup")
def startup():
    try:
        from app.database import engine, Base
        Base.metadata.create_all(bind=engine)
        threading.Thread(target=_run_seeds, daemon=True).start()
    except Exception as e:
        traceback.print_exc()
        print(f"[startup] Error: {e}")

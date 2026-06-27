from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AnimalitoPlus API",
    description="Backend de plataforma de lotería de animalitos",
    version="1.0.0",
)

origins = [
    "https://animalito-plus.vercel.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


from app.routes import auth, apuestas, resultados, pagos, admin
app.include_router(auth.router)
app.include_router(apuestas.router)
app.include_router(resultados.router)
app.include_router(pagos.router)
app.include_router(admin.router)

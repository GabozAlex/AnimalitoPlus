from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AnimalitoPlus API",
    description="Backend de plataforma de lotería de animalitos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

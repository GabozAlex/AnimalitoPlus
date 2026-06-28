from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Animal

router = APIRouter(prefix="/api/animales", tags=["animales"])


@router.get("")
def listar_animales(db: Session = Depends(get_db)):
    animales = db.query(Animal).order_by(Animal.id).all()
    return [
        {
            "id": a.id,
            "numero": a.numero,
            "nombre": a.nombre,
            "icono": a.icono,
        }
        for a in animales
    ]

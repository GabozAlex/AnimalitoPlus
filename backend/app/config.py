from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


CASA_DEFAULT = {
    "nombre": "Gabriel Alejandro Rosas Rosas",
    "banco": "Banco Mercantil",
    "banco_codigo": "0105",
    "cedula": "27650586",
    "telefono": "4123656230",
}

@lru_cache()
def get_settings() -> Settings:
    return Settings()

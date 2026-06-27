# AnimalitoPlus 🐾

Plataforma de lotería de animalitos — apuestas en **lotto_activo**, **la_granjita** y **selvaplus** con 38 animales cada una. Pago Móvil (Mercantil), retiros, panel admin, referidos y más.

## Stack

- **Backend:** FastAPI + PostgreSQL (desplegado en Railway)
- **Frontend:** HTML / CSS / JS puro + Bootstrap 5 + Font Awesome 6 + SweetAlert2 (desplegado en Vercel)
- **Auth:** JWT + bcrypt
- **Pagos:** Pago Móvil manual (Mercantil) — admin confirma la transferencia
- **PWA:** Instalable en dispositivos móviles

## Características

- **Registro** con código de referido — el referidor recibe 5% de bono en la primera recarga
- **Recargas** por Pago Móvil (el usuario ingresa referencia, el admin confirma)
- **Retiros** con validación de saldo disponible
- **Apuestas** con selección múltiple de animales, 3 loterías y 3 horarios
- **Resultados automáticos** vía scraper de loteriadehoy.com
- **Notificaciones** de resultados de apuestas al cargar el dashboard
- **Límites de apuesta** configurables por admin (máximo por apuesta/hora/día)
- **Panel admin:** gestión de pagos, resultados (manual + scraper), configuración, referidos, auditoría
- **PWA** con manifest.json y service worker

## URLs

| Recurso | URL |
|---|---|
| Frontend | https://animalito-plus.vercel.app |
| Backend (API) | https://animalitoplus-production.up.railway.app |
| Admin login | admin@animalitoplus.com / admin123 |
| Usuario test | test@test.com / 123456 |

## Despliegue

### Backend (Railway)

El backend está en `backend/`. Railway se configura con `railway.toml`:

```toml
[build]
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn main:application --host 0.0.0.0 --port $PORT"

[service]
rootDirectory = "backend"
```

La variable de entorno `DATABASE_URL` es provista por el add-on PostgreSQL de Railway.

### Frontend (Vercel)

El frontend está en la raíz del repositorio. Vercel se configura como static export apuntando a `index.html`.

La URL del backend se define en `js/app.js` como `API_BASE` (auto-detecta localhost vs producción).

## Desarrollo local

```bash
# Clonar
git clone https://github.com/GabozAlex/AnimalitoPlus.git
cd AnimalitoPlus

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar base de datos local
cp .env.example .env  # editar DATABASE_URL
createdb animalitoplus
psql -d animalitoplus -f schema.sql  # migración inicial

# Ejecutar servidor
uvicorn main:application --reload --port 8000

# Frontend (otra terminal)
cd ..
# Abrir index.html en navegador o usar live-server
npx live-server .
```

## Estructura del proyecto

```
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App FastAPI + CORS
│   │   ├── config.py            # Settings (DB, JWT)
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py            # Modelos: Usuario, Apuesta, etc.
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── auth.py              # JWT helpers
│   │   └── routes/
│   │       ├── auth.py          # Login / Register / Perfil
│   │       ├── apuestas.py      # CRUD apuestas + novedades
│   │       ├── resultados.py    # Resultados + scraper
│   │       ├── pagos.py         # Recargas / Retiros
│   │       └── admin.py         # Admin: pagos, resultados, config, referidos, auditoría
│   ├── main.py                  # Punto de entrada uvicorn
│   ├── schema.sql               # Migración inicial de DB
│   └── requirements.txt
├── css/
│   ├── bootstrap.min.css
│   └── style.css                # Estilos personalizados
├── js/
│   ├── app.js                   # Utilidades globales, API fetch, PWA
│   ├── auth.js                  # Login / Register
│   ├── dashboard.js             # Dashboard principal, apuestas
│   └── admin.js                 # Panel admin
├── img/
│   ├── animales/                # Fotos de animales (114 archivos)
│   │   ├── lotto_activo/
│   │   ├── la_granjita/
│   │   └── selvaplus/
│   ├── loterias/                # Logos de loterías (3 archivos)
│   ├── icon-192.svg
│   └── icon-512.svg
├── manifest.json                # PWA manifest
├── service-worker.js            # Service worker
├── *.html                       # Páginas: index, login, register, dashboard, admin, etc.
└── README.md
```

## API endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/login` | Iniciar sesión |
| POST | `/api/auth/register` | Registrarse (con `codigo_referido` opcional) |
| GET | `/api/auth/perfil` | Obtener perfil (token requerido) |
| PUT | `/api/auth/perfil` | Actualizar perfil |
| GET | `/api/auth/balance` | Obtener saldo |
| POST | `/api/apuestas` | Crear apuesta |
| GET | `/api/apuestas?loteria=&fecha=` | Historial de apuestas |
| GET | `/api/apuestas/novedades` | Resultados recientes no vistos |
| GET | `/api/resultados?loteria=&fecha=` | Resultados por lotería |
| GET | `/api/pagos/historial?tipo=` | Historial de recargas/retiros |
| POST | `/api/pagos/recarga` | Solicitar recarga |
| POST | `/api/pagos/retiro` | Solicitar retiro |
| GET | `/api/admin/pagos` | Listar pagos (admin) |
| PUT | `/api/admin/pagos/{id}/estado` | Cambiar estado de pago (admin) |
| POST | `/api/admin/resultados` | Ingresar resultado manual (admin) |
| POST | `/api/admin/scraper` | Ejecutar scraper (admin) |
| GET | `/api/admin/config/limites` | Ver límites (admin) |
| PUT | `/api/admin/config/limites` | Actualizar límites (admin) |
| GET | `/api/admin/config/casa` | Ver datos de CASA (admin) |
| PUT | `/api/admin/config/casa` | Actualizar datos de CASA (admin) |
| GET | `/api/admin/referidos` | Listar referidos (admin) |
| GET | `/api/admin/auditoria` | Ver auditoría (admin) |
| GET | `/api/health` | Health check |

## Animals

38 animales por lotería (ids: `0`=DELFIN, `00`=BALLENA, 1–36). Cada lotería tiene su propio set de ilustraciones en `img/animales/{loteria}/`.

## Licencia

Proyecto privado — uso personal.

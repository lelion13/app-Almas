# app-Almas

Proyecto full stack con:
- Frontend: React + Vite + Tailwind CSS (`frontend/`)
- Backend: FastAPI + Pydantic (`backend/`)
- Base de datos: PostgreSQL

## Requisitos

- Node.js 18+ y npm
- Python 3.11+ (recomendado)
- PostgreSQL en ejecución

## Inicializacion del backend

Desde la raiz del proyecto:

```bash
cd backend
python -m venv .venv
```

Activar entorno virtual:

- PowerShell:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- CMD:
  ```cmd
  .\.venv\Scripts\activate.bat
  ```
- Linux/macOS:
  ```bash
  source .venv/bin/activate
  ```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar variables de entorno:

```bash
copy .env.example .env
```

Ajusta en `backend/.env` al menos:
- `DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS`

Ejecutar API en desarrollo:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Healthcheck:
- `http://127.0.0.1:8000/health`

## Inicializacion del frontend

Desde la raiz del proyecto:

```bash
cd frontend
npm install
```

Configurar variables de entorno:

```bash
copy .env.example .env
```

Por defecto el frontend usa proxy de Vite hacia:
- `VITE_PROXY_TARGET=http://127.0.0.1:8000`

Levantar frontend en desarrollo:

```bash
npm run dev
```

Build de produccion:

```bash
npm run build
```

Preview local del build:

```bash
npm run preview
```

## Flujo recomendado de desarrollo

1. Levantar backend en `127.0.0.1:8000`
2. Levantar frontend en `localhost:5173`
3. Verificar que `GET /health` responda `{"status":"ok"}`

## Notas de seguridad

- No commitear archivos `.env`.
- No subir secretos, tokens ni credenciales.
- Usar solo archivos `*.env.example` para compartir configuraciones.

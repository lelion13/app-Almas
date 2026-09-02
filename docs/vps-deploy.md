# Deploy VPS — almas.lionapp.cloud

Stack: Traefik → frontend (Nginx) → backend (FastAPI) + Postgres en Docker.

## Prerrequisitos VPS

- Traefik ya corriendo (mismo patrón que otras apps `*.lionapp.cloud`)
- DNS `almas.lionapp.cloud` → IP del VPS
- Acceso GHCR (`ghcr.io/lelion13/...`)
- Carpeta: `/docker/app-almas/`

## 1. Imágenes

Push a `main` (o `workflow_dispatch`) construye:

- `ghcr.io/lelion13/app-almas-backend:<sha|main>`
- `ghcr.io/lelion13/app-almas-frontend:<sha|main>`

- Preferí tag por SHA en `.env.prod` (evitar depender solo de `:main` a largo plazo).
- Postgres en compose: **`postgres:18-alpine`** (alineado a dumps hechos con PostgreSQL 18 local). Si el dump viene de otra major, igualá la imagen a esa versión.
- Volumen PG 18+: montar en `/var/lib/postgresql` (no `/var/lib/postgresql/data`).

## 2. Archivos en el VPS

```bash
mkdir -p /docker/app-almas
cd /docker/app-almas
# copiar docker-compose.prod.yml y .env.prod (desde .env.prod.example)
chmod 600 .env.prod
```

Ajustá en `.env.prod`:

- `POSTGRES_PASSWORD` / `DATABASE_URL` (misma clave)
- `JWT_SECRET` (largo y aleatorio; **si restaurás dump, podés reusar el JWT local** para no invalidar sesiones, o rotarlo y pedir re-login)
- `BACKEND_IMAGE` / `FRONTEND_IMAGE`
- `TRAEFIK_CERT_RESOLVER` / `TRAEFIK_ENTRYPOINT` (igual que tus otras apps)
- Conciliación MP (si habilitás OAuth): `MP_CLIENT_ID`, `MP_CLIENT_SECRET`, `MP_REDIRECT_URI=https://almas.lionapp.cloud/api/v1/mp/oauth/callback`, `MP_OAUTH_FRONTEND_REDIRECT=https://almas.lionapp.cloud/conciliacion`, `MP_TOKEN_ENCRYPTION_KEY` (Fernet). Registrá la redirect URI en el panel de la app Mercado Pago. Si perdés la encryption key, hay que reconectar cuentas.

## 3. Migración de datos locales (obligatoria)

### 3.1 En tu PC — chequear revisión Alembic

Antes del dump, en la DB local:

```sql
SELECT version_num FROM alembic_version;
```

El código de producto llega hasta **`014`** (`005` studio ops + `006` maps_url + `007`–`010` salones/horarios/espacio compartido + `011` activity↔rooms + `012` system backups + `013` instructor↔activities + `014` align instructor emails).

- Si ves **`001`–`014`** alineado con el repo: OK (en dump viejo, el entrypoint sube a head).
- Si ves **`009`** y `\d studio_rooms` no tiene `shares_space_with_room_id`: la revisión 009 se reescribió; el entrypoint con imagen que incluye `010`/`011` lo corrige.
- Si ves un **`003` huérfano** de la feature MP de reconciliación **descartada** (tablas `income_reconciliations` / `mp_income_lines` / `mp_import_batches` y sin el `003_mp_accounts` actual): limpiá antes del dump:

```sql
DROP TABLE IF EXISTS income_reconciliations CASCADE;
DROP TABLE IF EXISTS mp_income_lines CASCADE;
DROP TABLE IF EXISTS mp_import_batches CASCADE;
DROP TABLE IF EXISTS mp_accounts CASCADE;
UPDATE alembic_version SET version_num = '002';
```

Lecciones OAuth / Movimientos MP: `docs/mp-conciliation-lessons.md`.

Nota: la consulta de Movimientos puede demorar hasta ~2 min (reporte async); Nginx proxy usa `proxy_read_timeout 180s`.

### 3.2 Dump local (Windows / PowerShell)

Con PostgreSQL en el PATH (o ruta completa a `pg_dump`):

```powershell
cd c:\Users\llion\Documents\apps\app-Almas
# Ajustá user/db/host/port según backend\.env
$env:PGPASSWORD = "TU_PASSWORD_LOCAL"
pg_dump -h localhost -p 5432 -U postgres -d almas -Fc -f almas_local.dump
```

Formato custom (`-Fc`) permite restore flexible.

### 3.3 Subir dump al VPS

```powershell
scp almas_local.dump root@TU_VPS:/docker/app-almas/almas_local.dump
```

### 3.4 Restaurar en Docker (orden importante)

```bash
cd /docker/app-almas

# 1) Solo base (volumen vacío la primera vez)
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d db

# 2) Esperar healthy
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

# 3) Restore (usuario/db según .env.prod)
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl \
  < almas_local.dump

# Si pg_restore se queja de ownership/roles, alternativa:
# docker compose ... exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < almas.sql
# (en ese caso exportá con pg_dump -Fp en lugar de -Fc)

# 4) Levantar backend/frontend
# Tras restore con schema, el entrypoint corre alembic hasta head (hoy **014**).
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

Si el restore trae schema completo y querés evitar migrate al primer start:

```bash
# temporal en .env.prod
SKIP_DB_MIGRATE=1
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
# después sacar SKIP_DB_MIGRATE o dejarlo en 0
```

### 3.5 Verificar datos

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec db \
  psql -U almas -d almas -c "SELECT count(*) FROM users;"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec db \
  psql -U almas -d almas -c "SELECT version_num FROM alembic_version;"
```

Login en https://almas.lionapp.cloud con un usuario que ya existía en local.

## 4. Deploy cotidiano (sin re-migrar DB)

```bash
cd /docker/app-almas
# actualizar tags en .env.prod si hace falta
docker compose --env-file .env.prod -f docker-compose.prod.yml pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

El volumen `almas_pgdata` **no** se borra con `up -d`. Evitá `down -v` salvo destrucción deliberada.

## 5. Checks post-deploy

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://almas.lionapp.cloud/health   # 200
curl -sS -o /dev/null -w "%{http_code}\n" https://almas.lionapp.cloud/docs     # 404 en prod
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T db \
  psql -U almas -d almas -c "SELECT version_num FROM alembic_version;"   # 014
```

Si `alembic_version` es `009` y `\d studio_rooms` muestra `space_id` y **no** `shares_space_with_room_id`, la revisión 009 se reescribió en el repo. Aplicá `010`/`011` (o el `ALTER` de `docs/studio-ops-lessons.md`) antes de usar Salones.

## 6. Notas de seguridad

- No publicar `5432` al host.
- Docs OpenAPI desactivados con `APP_ENV=production`.
- Solo el frontend tiene labels Traefik; `/api` va por Nginx interno.
- Healthchecks cada 60s (menos carga en `dockerd`).

# Mercado Pago Conciliación — lecciones y fuera de alcance

Documento operativo (V1 OAuth + V2 Movimientos Account Money).  
Specs: `openspec/specs/mercado-pago/spec.md` · change activo: `openspec/changes/mp-movements-v1/`.

## Qué quedó FUERA (sigue vigente)

| Tema | Estado |
|------|--------|
| Vincular movimientos MP ↔ SigueFit / cierres | Fuera |
| Auto-match | Fuera |
| Webhooks / sync en tiempo real | Fuera |
| Persistir filas de movimientos/reportes en DB | Fuera (solo se muestran) |
| Acceso **staff** a Conciliación | Fuera — solo **admin** |
| Pegar Access Token a mano | Fuera — solo OAuth |

## Fuente de datos actual (mp-movements-v1)

Conciliación → **Movimientos** usa el **Account Money Report** de Mercado Pago (`/v1/account/settlement_report*`):

1. Asegura config de columnas (+ `include_withdraw`)
2. Genera reporte para el rango (≤ 60 días)
3. Espera hasta `processed` + `file_name`
4. Descarga CSV, parsea, devuelve DTOs (sin persistir)

| `TRANSACTION_TYPE` | UI (tipo) | Grupo |
|--------------------|-----------|-------|
| `SETTLEMENT` | Cobro | Ingreso |
| `REFUND` | Devolución | Egreso |
| `CHARGEBACK` | Contracargo | Egreso |
| `WITHDRAWAL` | Retiro bancario | Egreso |
| `PAYOUT` | Extracción de efectivo | Egreso |
| `DISPUTE` | Reclamo | Otro |
| `WITHDRAWAL_CANCEL` | Retiro cancelado | Otro |

Filtros UI: Todos | Ingresos | Egresos + tipo + moneda + texto.  
UX: spinner + “Generando reporte en Mercado Pago…” (request bloqueante).

Env extra: `MP_REPORT_POLL_INTERVAL_SECONDS` (default 2), `MP_REPORT_POLL_TIMEOUT_SECONDS` (default 120).

> Nota histórica V1: antes se usaba `/v1/payments/search` (solo cobros). Ese path se eliminó del producto.

## Errores que nos pasaron (y cómo no repetirlos)

### 1. App MP “no está preparada para conectarse”
- **Síntoma:** pantalla MP antes de autorizar.
- **Causas típicas:** redirect URI mal formada (`https://https://...`), app sin modelo OAuth/Connect, datos de app incompletos, PKCE desalineado.
- **Fix:** URI exacta `https://almas.lionapp.cloud/api/v1/mp/oauth/callback`; PKCE = **Sí**; usar app apta para vincular vendedores.

### 2. Credenciales equivocadas
- **Usar:** `Client ID` → `MP_CLIENT_ID`, `Client Secret` → `MP_CLIENT_SECRET` (producción).
- **No usar** para OAuth de Almas: Public Key ni Access Token de esa pantalla.

### 3. `oauth_failed` después de autorizar
- **Causa:** `scopes` > 512 chars → truncación.
- **Fix:** columna `scopes` como **TEXT** (migración `004`).

### 4. Postgres 18 + volumen Docker
- Volumen: `/var/lib/postgresql` (no `/.../data`).
- Dump local PG18 ↔ imagen `postgres:18-alpine`.

### 5. Nginx + `cap_drop: ALL`
- Frontend Nginx no debe usar `cap_drop: ALL`.

### 6. Dump local con Alembic huérfano `003` (reconcilación vieja)
- Limpiar tablas MP viejas y stamp a revisión conocida.

### 7. Reportes Account Money (nuevo)
- Generación **async**: timeout configurable; si falla permisos, reconectar OAuth.
- Cuentas de prueba MP pueden devolver reportes vacíos (limitación documentada por MP).
- CSV puede usar `;` o `,` — el parser detecta ambos.

## Checklist ops OAuth + Movimientos (prod)

1. App MP: redirect URI exacta + PKCE Sí  
2. `.env.prod`: `MP_CLIENT_ID`, `MP_CLIENT_SECRET`, `MP_REDIRECT_URI`, `MP_OAUTH_FRONTEND_REDIRECT`, `MP_TOKEN_ENCRYPTION_KEY`, poll timeouts  
3. Compose pasa `MP_*` al backend  
4. Alembic head ≥ `004`  
5. Probar Conectar cuenta + Movimientos ≤ 60 días (spinner → tabla con ingresos/egresos)

Generar Fernet:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

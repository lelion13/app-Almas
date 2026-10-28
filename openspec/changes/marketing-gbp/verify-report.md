# Verify: marketing-gbp

Date: 2026-10-27

## Checks
- `pytest tests/test_marketing_gbp.py` (+ aranceles smoke): **7 passed**
- `frontend npm run build`: **ok**
- Alembic head documented as **018**
- Router `/api/v1/marketing/*` wired; Settings GBP connect UI present
- Setup doc: `docs/marketing-gbp-setup.md`

## Remaining (ops, not code)
- Configure Telegram webhook + allowlist
- Configure GBP OAuth client + Pub/Sub push audience
- Run `alembic upgrade head` in each env
- Connect Google from Admin → Configuración

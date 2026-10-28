# Marketing GBP — setup breve

Specs: change `marketing-gbp`. Alembic **018**.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/marketing/telegram-webhook` | `X-Telegram-Bot-Api-Secret-Token` |
| POST | `/api/v1/marketing/google-pubsub-webhook` | Bearer OIDC Pub/Sub |
| POST | `/api/v1/marketing/gbp/oauth/start` | Admin JWT |
| GET | `/api/v1/marketing/gbp/oauth/callback` | público (OAuth) |
| GET | `/api/v1/marketing/gbp/status` | Admin JWT |
| DELETE | `/api/v1/marketing/gbp/connection` | Admin JWT |

## Telegram

1. Crear bot con BotFather; copiar token → `TELEGRAM_BOT_TOKEN`.
2. `TELEGRAM_ALLOWED_USER_IDS` = ids numéricos (comma-separated).
3. `TELEGRAM_ADMIN_CHAT_ID` = chat donde llegan alertas.
4. Set webhook:
   ```bash
   curl "https://api.telegram.org/bot$TOKEN/setWebhook" \
     -d "url=https://almas.lionapp.cloud/api/v1/marketing/telegram-webhook" \
     -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
   ```
5. Usuarios allowlist: foto+caption o texto → post GBP; botón Responder → texto → reply.

## Google OAuth + GBP

1. Google Cloud project: OAuth client (web) con redirect `…/marketing/gbp/oauth/callback`.
2. Pedir acceso a Business Profile APIs si el proyecto aún no lo tiene.
3. `GBP_ACCOUNT_ID` / `GBP_LOCATION_ID` (ids o resource names).
4. En Almas → Configuración → Conectar Google.

## Pub/Sub (reseñas)

1. En Google Cloud: topic de notificaciones de Business Profile (según doc actual de Google para review notifications).
2. Push subscription → `https://almas.lionapp.cloud/api/v1/marketing/google-pubsub-webhook`.
3. `GBP_PUBSUB_AUDIENCE` = esa URL (OIDC).
4. Prod: `GBP_PUBSUB_SKIP_AUTH=false`.

## Dependencias

- `google-auth` (verify OIDC push)
- Telegram/GBP vía `httpx` (sin PTB event loop)

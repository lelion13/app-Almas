# Exploration: marketing-gbp

**Change**: `marketing-gbp`  
**Date**: 2026-10-27  
**Status**: Survey CLOSED — ready for proposal

## Intent

Operate Google Business Profile (GBP) from Telegram: publish local posts and handle reviews (Pub/Sub alerts, auto-reply for 5★ empty text, manual reply via bot). Admin connects GBP via OAuth in Almas; day-to-day stays in Telegram.

## Prompt source / notes

Gemini prompt proposed landing + Telegram posts + Pub/Sub reviews. Survey narrowed scope. Frontend is React (Vite), not a Node app. GBP API auth is OAuth (`business.manage`), not service-account-as-merchant. Landing deferred.

## Survey (CLOSED)

| Q | Decision |
|---|----------|
| Q1 | **B** Reseñas + posts GBP desde Telegram (landing OUT) |
| Q2 | **A** Pub/Sub push → webhook FastAPI |
| Q3 | **A** Una sola Location GBP (env) |
| Q4 | **A** Allowlist `telegram_user_id` en env |
| Q5 | **A** Auto-reply solo 5★ sin texto; resto alerta + manual |
| Q6 | **A** Alertas a `TELEGRAM_ADMIN_CHAT_ID` fijo |
| Q7 | **B** OAuth admin GBP (tokens cifrados, estilo MP) |
| Q8 | **A** Botón Responder → pedir texto → `reviews.reply` |
| Q9 | **A** Persistir reseñas en Postgres (estado + idempotencia) |
| Q10 | **C** OAuth GBP en admin web; operación diaria en Telegram |
| Q11 | **B** Post: foto+caption **o** texto solo |
| Q12 | **A** Frases de agradecimiento fijas en código/config |
| Q13 | **A** Out of scope confirmado (landing, multi-location, UI reseñas, editar/borrar posts, auto &lt;5★) |

## Open risks (design)

- GBP API access is application-gated (request access with Google).
- Pub/Sub “NEW_REVIEW” product wiring must match current Google notifications docs during design/apply.
- Telegram webhook + Pub/Sub push must be publicly reachable on `almas.lionapp.cloud` with signature/token validation.

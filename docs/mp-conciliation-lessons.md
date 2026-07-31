# Mercado Pago Conciliación — lecciones y fuera de alcance

Specs: `openspec/specs/mercado-pago/spec.md` · change: `openspec/changes/mp-movements-v1/`.

## Decisión de velocidad (importante)

| Fuente MP | Velocidad | Qué trae |
|-----------|-----------|----------|
| **`/v1/payments/search`** (actual) | Segundos | Cobros + estados (devolución, contracargo, etc.) |
| **Account Money Report** (CSV async) | 1–varios minutos | También retiros a banco (`WITHDRAWAL`/`PAYOUT`) |

**Sacamos el reporte Account Money de la consulta principal** porque 5 días ~2 min y un mes no terminaba: es el diseño de MP (generar CSV), no un bug de Almas.

### Qué muestra hoy
- **Ingresos:** cobros (`approved` → Cobro)
- **Egresos (filtro):** devoluciones / contracargos (`refunded` / `charged_back`)
- **No incluye:** retiros a cuenta bancaria ni extracciones de efectivo (solo estaban en el reporte lento)

Si más adelante hacen falta retiros, debe ser un flujo **aparte** (opcional / lento), no el botón Consultar.

## Fuera de alcance
- Match SigueFit / cierres, webhooks, staff, pegar Access Token, persistir filas

## Errores históricos (OAuth / deploy)
Ver secciones previas en git history si hace falta: Client ID/Secret, PKCE, redirect exacta, `scopes` TEXT, PG18 volume, Nginx sin `cap_drop: ALL`.

# Mercado Pago Conciliación — lecciones y fuera de alcance

Specs: `openspec/specs/mercado-pago/spec.md`.  
Archives: `2026-07-31-mp-conciliation-v1`, `2026-07-31-mp-movements-v1`.

## Decisión de velocidad (mp-movements-v1)

| Fuente MP | Velocidad | Qué trae |
|-----------|-----------|----------|
| **`/v1/payments/search`** (actual / shipped) | Segundos | Cobros + devoluciones/contracargos + payer/medio cuando MP los manda |
| **Account Money Report** (CSV async) | Minutos / timeouts | Ledger completo incl. retiros bancarios |

**Sacamos Account Money del Consultar principal** tras medir en prod (~2 min / 5 días; mes no terminaba). Chunking y paralelismo no alcanzaron.

### Qué muestra hoy
- **Ingresos:** cobros (`approved`)
- **Egresos (filtro):** devoluciones / contracargos
- **Columnas conciliación:** Documento (DNI/CUIT/CUIL), Email, Medio — "—" si MP no envía
- **No incluye:** retiros a banco / extracciones (solo en reporte lento, no usado)

Mejor ancla para match futuro con el sistema: `external_reference` al cobrar + documento cuando exista.

## Fuera de alcance
- Match automático SigueFit / cierres, webhooks, staff, pegar Access Token, persistir filas
- Consultar primario vía Account Money

## Errores históricos (OAuth / deploy)
Client ID/Secret (no Public Key/Access Token); PKCE Sí; redirect URI exacta; `scopes` TEXT (mig 004); PG18 volume `/var/lib/postgresql`; Nginx sin `cap_drop: ALL`.

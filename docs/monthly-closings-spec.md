# Especificación: cierres de mes (SigueFit + gastos manuales)

## Mapeo Excel → base de datos

Export típico SigueFit (`Pagos_Detalles_*.xlsx`):

| Columna Excel (fila cabecera) | Campo persistido | Notas |
|-------------------------------|------------------|--------|
| Fecha | `payment_date` | Serial Excel → `date` (zona `America/Argentina/Buenos_Aires` para interpretación de negocio; almacenamiento como fecha civil). |
| Cliente | `client_name` | Texto. |
| DNI | `dni` | Texto; puede estar vacío. |
| Categoría de Pago | `payment_category` | Clave de agrupación; normalizar espacios y Unicode NFC para totales. |
| Mes / Año | — | Opcional; no requerido para agregación si hay `Fecha`. |
| Vencimiento | — | Opcional; puede persistirse en `raw_row` si hace falta. |
| Importe | `amount` | `Decimal`; incluye negativos (p. ej. `Deuda`). |
| Divisa | `currency` | P. ej. `ARS`. |
| Método de Pago | `payment_method` | Clave de agrupación. |
| Actividad | `activity` | Texto libre. |
| Detalle | `detail` | Texto libre. |
| Fecha de Registro | `registered_at` | Serial/datetime → `timestamptz` UTC. |
| Usuario | `registered_by_user` | Quien registró en SigueFit. |

Filas 1–3 del archivo: metadatos (`Desde`, `Hasta` en serial Excel, `Actvidad`). Se guardan en `siguefit_import_batches` (`source_from`, `source_to`, `activity_filter`).

Cada fila de datos se guarda también en `raw_row` (JSON) para auditoría.

## Ingesta

1. Localizar fila de cabecera escaneando las primeras filas hasta encontrar, tras normalización, las columnas `Categoría de Pago`, `Método de Pago` e `Importe`.
2. Normalización de texto para agrupación en consultas: `trim`, espacios múltiples a uno, `unicodedata.normalize("NFC", s)`.
3. Tamaño máximo de archivo: 10 MB (configurable).
4. Dedup: `file_sha256` por batch; si ya existe para el mismo cierre, la API responde `409` con mensaje genérico de duplicado.

## Estados de cierre (`monthly_closings.status`)

- `draft`: se permiten importaciones, altas/edición/baja de gastos manuales, PATCH del cierre, **eliminación de lotes de importación Excel**.
- `finalized`: no se permiten nuevas importaciones ni mutaciones de líneas importadas; gastos manuales no editables/borrables (solo lectura). PATCH de `status` de vuelta a `draft` solo rol `admin` (opcional; implementado como regla en servicio).

## Eliminación de importaciones (lotes Excel)

**Objetivo:** permitir corregir un archivo equivocado o “reemplazar” datos SigueFit sin borrar todo el cierre ni los gastos manuales.

**Unidad de borrado:** un registro `siguefit_import_batches` y **todas** sus `imported_payment_lines` (la FK en BD usa `ON DELETE CASCADE`).

**Reglas de negocio:**

1. Solo si `monthly_closings.status === draft`. En `finalized` → `400` (mismo criterio que nuevas importaciones).
2. El lote debe pertenecer al `closing_id` indicado en la URL → si no, `404`.
3. Roles: `admin` y `staff` (igual que importar y ver resúmenes).
4. Efecto en agregados: los totales por categoría/método/overview se recalculan al excluir las líneas de ese lote; los **gastos manuales** del cierre no se tocan.
5. Tras borrar, el mismo archivo puede volver a subirse (el `file_sha256` deja de existir para ese cierre).

**API:** `DELETE /api/v1/closings/{closing_id}/imports/{batch_id}` → `204 No Content`.

**UX (frontend):** listado de importaciones del cierre (nombre de archivo, fecha de subida) con acción “Eliminar” y confirmación; deshabilitado si el cierre está finalizado.

## Agregación

Por `closing_id`, sobre todas las `imported_payment_lines` de todos los batches del cierre:

- `SUM(amount)`, `COUNT(*)` agrupado por `payment_category`.
- `SUM(amount)`, `COUNT(*)` agrupado por `payment_method`.
- Overview: suma total de importes, suma de líneas con `amount >= 0` y con `amount < 0`, `COUNT(DISTINCT client_name)` opcional en overview.

### Ingreso atribuido a Yoga (SigueFit)

Sobre las mismas `imported_payment_lines` del cierre, el backend aplica reglas por **categoría de pago** (texto normalizado igual que al importar). Solo las líneas cuya categoría coincide exactamente con una categoría configurada entran en el desglose; cada fila muestra importe original, etiqueta de regla y monto atribuido a Yoga (2 decimales). El total es la suma de esos montos.

**API:** `GET /api/v1/closings/{closing_id}/summary/yoga-attribution` — respuesta `items` (línea a línea) + `total_yoga`.

Categorías y fórmulas están definidas en `app/services/yoga_income.py` (incluye alias de texto para variantes de export). Si una categoría del Excel no coincide con ninguna regla, esa línea no aparece en este resumen (no es error).

### Gastos importados desde Excel (separado de ingresos)

Los ingresos SigueFit viven en `siguefit_import_batches` / `imported_payment_lines`. Los **gastos importados** usan tablas propias: `expense_import_batches` e `imported_expense_lines`. No modifican los agregados de categoría, método de pago ni overview de ingresos.

**Columnas requeridas en el Excel:** fila de cabecera con **Importe** y **Método de Pago** o **Medio de pago** (detección por nombre normalizado, como SigueFit). Las primeras filas pueden repetir metadatos `Desde` / `Hasta` / actividad; se guardan en el batch como en SigueFit.

**Medios de pago permitidos** (tras normalizar espacios y comparar sin distinguir mayúsculas):

- Efectivo  
- Transferencia Irene  
- Transferencia Lea  
- Transferencia Mercedes  
- Transferencia Raquel  

Filas con importe numérico y medio no permitido **no** se persisten; la API puede devolver advertencias en `row_errors`. Filas sin importe se omiten (`rows_skipped`). Si no queda ninguna fila válida → `422`.

**Dedup:** `file_sha256` único por cierre **solo entre lotes de gastos** (`ix_expense_import_batch_closing_sha`). Un mismo archivo puede existir como ingreso SigueFit y como gasto importado si se sube por ambos flujos (responsabilidad de negocio evitar duplicar conceptos).

**Eliminación en borrador:** `DELETE /api/v1/closings/{closing_id}/expense-imports/{batch_id}` → `204`. Mismas reglas de estado que los lotes SigueFit.

**API adicional:**

- `POST /api/v1/closings/{closing_id}/expense-imports` — multipart `file` (.xlsx). Respuesta alineada a `ImportResultResponse`.
- `GET /api/v1/closings/{closing_id}/expense-imports` — lista de lotes.
- `GET /api/v1/closings/{closing_id}/summary/imported-expense-methods` — `SUM(amount)`, `COUNT(*)` por `payment_method` canónico sobre todas las `imported_expense_lines` del cierre.

## Gastos manuales (Pydantic)

- `expense_type`: `service` | `teacher_hours`.
- `amount`: obligatorio, > 0, máximo 2 decimales.
- `service`: requiere `vendor_or_teacher_name` (proveedor/concepto), `expense_date`, `description` opcional.
- `teacher_hours`: requiere `teacher_id` (UUID), `hours` > 0, `hourly_rate` > 0; validación: `abs(hours * hourly_rate - amount) <= 0.02` (tolerancia centavos).

## Ejemplos de payload

### POST `/api/v1/closings`

```json
{ "year": 2026, "month": 3 }
```

### POST `/api/v1/closings/{id}/expenses` (servicio)

```json
{
  "expense_type": "service",
  "amount": "15000.00",
  "expense_date": "2026-03-15",
  "vendor_or_teacher_name": "EDENOR",
  "description": "Luz marzo"
}
```

### POST `/api/v1/closings/{id}/expenses` (horas docente)

```json
{
  "expense_type": "teacher_hours",
  "amount": "80000.00",
  "expense_date": "2026-03-31",
  "teacher_id": "550e8400-e29b-41d4-a716-446655440000",
  "hours": "10.0",
  "hourly_rate": "8000.00"
}
```

### POST `/api/v1/auth/login`

```json
{ "email": "admin@local.test", "password": "********" }
```

Respuesta (sin incluir secretos en logs):

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

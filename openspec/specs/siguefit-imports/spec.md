# SigueFit Imports

## Purpose
Ingest SigueFit payment Excel exports into a monthly closing as income lines, with batch listing, deduplication, and draft-only deletion.

## Requirements

### Requirement: Upload Excel into a draft closing

`POST /api/v1/closings/{closing_id}/imports` MUST accept multipart `.xlsx` (max size per `max_upload_bytes`, default 10 MB) for StaffOrAdmin when the closing is `draft`.

The importer MUST locate the header row (scan early rows) requiring columns equivalent to **Categoría de Pago**, **Método de Pago**, and **Importe**. Metadata rows (`Desde` / `Hasta` / activity) SHOULD populate batch fields `source_from`, `source_to`, `activity_filter`.

Each data row MUST persist mapped fields plus `raw_row` JSON for audit. Negative amounts MUST be allowed.

#### Scenario: Successful import
- **Given** a draft closing and a valid SigueFit workbook
- **When** the file is uploaded
- **Then** a `siguefit_import_batches` row and related `imported_payment_lines` MUST be created

#### Scenario: Reject when finalized
- **Given** a finalized closing
- **When** upload is attempted
- **Then** the response MUST be `400`

### Requirement: Deduplicate by file hash

The system MUST compute `file_sha256` per batch and enforce uniqueness per closing. A duplicate upload MUST return `409` with a generic duplicate message.

### Requirement: List and delete batches

- `GET /api/v1/closings/{id}/imports` MUST list batches for the closing
- `DELETE /api/v1/closings/{id}/imports/{batch_id}` MUST delete the batch and cascade its lines when status is `draft`
- Deleting MUST NOT remove manual expenses
- After delete, the same file SHA MAY be uploaded again

#### Scenario: Delete wrong import in draft
- **Given** a draft closing with an import batch
- **When** staff deletes that batch
- **Then** response MUST be `204` and income summaries MUST exclude those lines

### Requirement: Batch and line inspection APIs

The system SHOULD expose:
- `GET /api/v1/imports/{batch_id}`
- `GET /api/v1/imports/{batch_id}/lines` (pagination / filters)

A dedicated line-browser UI is OUT OF SCOPE; closing detail MUST support upload, list, and delete.

### Requirement: Frontend

Closing detail MUST provide upload, list of imports (filename, upload time), and confirmed delete disabled when finalized.

## Related
- Detailed column mapping: `docs/monthly-closings-spec.md`
- Aggregations: `monthly-closings` domain

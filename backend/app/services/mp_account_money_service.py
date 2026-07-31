from __future__ import annotations

import csv
import io
import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import mp_account_repo
from app.schemas.mercado_pago import MovementBucket, MovementDto
from app.services import mp_oauth_service

logger = logging.getLogger(__name__)

MAX_RANGE_DAYS = 60

REQUIRED_COLUMNS = [
    "SOURCE_ID",
    "TRANSACTION_TYPE",
    "TRANSACTION_DATE",
    "TRANSACTION_AMOUNT",
    "TRANSACTION_CURRENCY",
    "SETTLEMENT_NET_AMOUNT",
    "EXTERNAL_REFERENCE",
    "DESCRIPTION",
    "FEE_AMOUNT",
    "REAL_AMOUNT",
]

TYPE_LABELS_ES: dict[str, str] = {
    "SETTLEMENT": "Cobro",
    "REFUND": "Devolución",
    "CHARGEBACK": "Contracargo",
    "DISPUTE": "Reclamo",
    "WITHDRAWAL": "Retiro bancario",
    "WITHDRAWAL_CANCEL": "Retiro cancelado",
    "PAYOUT": "Extracción de efectivo",
}

INGRESO_TYPES = frozenset({"SETTLEMENT"})
EGRESO_TYPES = frozenset({"REFUND", "CHARGEBACK", "WITHDRAWAL", "PAYOUT"})


def _validate_range(from_dt: datetime, to_dt: datetime) -> None:
    if to_dt <= from_dt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rango de fechas inválido.")
    delta = to_dt - from_dt
    if delta.total_seconds() > MAX_RANGE_DAYS * 24 * 3600:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El rango no puede superar {MAX_RANGE_DAYS} días.",
        )


def _as_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_range_chunks(
    from_dt: datetime,
    to_dt: datetime,
    *,
    chunk_days: int,
) -> Iterator[tuple[datetime, datetime]]:
    """Split [from, to] into contiguous windows of at most chunk_days (keeps MP reports small)."""
    days = max(1, int(chunk_days))
    cursor = from_dt
    while cursor < to_dt:
        nxt = min(cursor + timedelta(days=days), to_dt)
        yield cursor, nxt
        cursor = nxt


def _movement_dedupe_key(m: MovementDto) -> tuple:
    return (
        m.source_id,
        m.transaction_type,
        m.transaction_date.isoformat() if m.transaction_date else "",
        str(m.amount),
        m.currency,
        m.external_reference or "",
    )


def bucket_for_type(transaction_type: str) -> MovementBucket:
    t = (transaction_type or "").strip().upper()
    if t in INGRESO_TYPES:
        return "ingreso"
    if t in EGRESO_TYPES:
        return "egreso"
    return "otro"


def label_for_type(transaction_type: str) -> str:
    t = (transaction_type or "").strip().upper()
    return TYPE_LABELS_ES.get(t, t or "Desconocido")


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _norm_header(h: str) -> str:
    return h.strip().strip('"').upper()


def parse_settlement_csv(content: str) -> list[MovementDto]:
    text = content.lstrip("\ufeff")
    if not text.strip():
        return []
    sample = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        return []
    # Normalize fieldnames
    field_map = {_norm_header(f): f for f in reader.fieldnames if f}
    items: list[MovementDto] = []
    for row in reader:
        def cell(key: str) -> str | None:
            src = field_map.get(key)
            if src is None:
                return None
            val = row.get(src)
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        tx_type = (cell("TRANSACTION_TYPE") or "").upper()
        amount = (
            _parse_decimal(cell("SETTLEMENT_NET_AMOUNT"))
            or _parse_decimal(cell("REAL_AMOUNT"))
            or _parse_decimal(cell("TRANSACTION_AMOUNT"))
            or Decimal("0")
        )
        source_id = cell("SOURCE_ID") or ""
        items.append(
            MovementDto(
                source_id=source_id,
                transaction_date=_parse_datetime(cell("TRANSACTION_DATE")),
                transaction_type=tx_type or "UNKNOWN",
                transaction_type_label=label_for_type(tx_type),
                bucket=bucket_for_type(tx_type),
                amount=amount,
                currency=cell("TRANSACTION_CURRENCY") or cell("SETTLEMENT_CURRENCY") or "",
                description=cell("DESCRIPTION"),
                external_reference=cell("EXTERNAL_REFERENCE"),
                fee_amount=_parse_decimal(cell("FEE_AMOUNT")),
            )
        )
    return items


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}


def _mp_error(detail: str, code: int = status.HTTP_502_BAD_GATEWAY) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def ensure_report_config(client: httpx.Client, token: str) -> None:
    base = settings.mp_api_base_url.rstrip("/")
    url = f"{base}/v1/account/settlement_report/config"
    body: dict[str, Any] = {
        "file_name_prefix": "almas-settlement-report",
        "include_withdraw": True,
        "show_fee_prevision": False,
        "show_chargeback_cancel": True,
        "coupon_detailed": False,
        "shipping_detail": False,
        "refund_detailed": True,
        "display_timezone": "GMT-03",
        "header_language": "es",
        "frequency": {"hour": 0, "type": "monthly", "value": 1},
        "columns": [{"key": k} for k in REQUIRED_COLUMNS],
    }
    get_resp = client.get(url, headers=_auth_headers(token))
    if get_resp.status_code == 401:
        raise _mp_error("Token de Mercado Pago inválido al configurar reportes.")
    if get_resp.status_code < 400:
        existing = get_resp.json()
        keys = {
            (c.get("key") if isinstance(c, dict) else None)
            for c in (existing.get("columns") or [])
        }
        if keys.issuperset(REQUIRED_COLUMNS) and existing.get("include_withdraw") is True:
            return
        put = client.put(url, headers=_auth_headers(token), json={**existing, **body})
        if put.status_code >= 400:
            logger.warning("MP settlement_report config PUT status=%s", put.status_code)
            raise _mp_error("No se pudo actualizar la configuración del reporte de dinero.")
        return
    # No config yet
    post = client.post(url, headers=_auth_headers(token), json=body)
    if post.status_code >= 400:
        logger.warning("MP settlement_report config POST status=%s", post.status_code)
        raise _mp_error("No se pudo crear la configuración del reporte de dinero.")


def _find_report_by_id(entries: list[dict], report_id: Any) -> dict | None:
    if report_id is None:
        return None
    for e in entries:
        if not isinstance(e, dict):
            continue
        if e.get("id") == report_id or e.get("report_id") == report_id:
            return e
    return None


def _list_reports(client: httpx.Client, token: str) -> list[dict]:
    base = settings.mp_api_base_url.rstrip("/")
    resp = client.get(f"{base}/v1/account/settlement_report/list", headers=_auth_headers(token))
    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Mercado Pago inválido al listar reportes.",
        )
    if resp.status_code >= 400:
        logger.warning("MP settlement_report list status=%s", resp.status_code)
        raise _mp_error("Error al listar reportes de Mercado Pago.")
    payload = resp.json()
    entries = payload if isinstance(payload, list) else (payload.get("results") or [])
    return [e for e in entries if isinstance(e, dict)]


def _create_report(client: httpx.Client, token: str, *, begin: str, end: str) -> dict[str, Any]:
    base = settings.mp_api_base_url.rstrip("/")
    gen = client.post(
        f"{base}/v1/account/settlement_report",
        headers=_auth_headers(token),
        json={"begin_date": begin, "end_date": end},
    )
    if gen.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Mercado Pago inválido al generar reporte.",
        )
    if gen.status_code >= 400:
        logger.warning("MP settlement_report create status=%s begin=%s end=%s", gen.status_code, begin, end)
        raise _mp_error(
            "Mercado Pago rechazó la generación del reporte. "
            "Verificá permisos de la cuenta o reconectá OAuth."
        )
    return gen.json() if gen.content else {}


def wait_for_many_report_files(
    client: httpx.Client,
    token: str,
    *,
    jobs: list[dict[str, Any]],
) -> None:
    """Poll until every job has file_name. Mutates jobs in place (sets file_name)."""
    pending = [j for j in jobs if not j.get("file_name")]
    if not pending:
        return

    deadline = time.monotonic() + float(settings.mp_report_poll_timeout_seconds)
    interval = max(0.5, float(settings.mp_report_poll_interval_seconds))
    last_statuses: dict[Any, str | None] = {j.get("report_id"): None for j in pending}

    while pending and time.monotonic() < deadline:
        entries = _list_reports(client, token)
        still: list[dict[str, Any]] = []
        for job in pending:
            found = _find_report_by_id(entries, job.get("report_id"))
            if not found:
                still.append(job)
                continue
            st = found.get("status")
            last_statuses[job.get("report_id")] = str(st) if st is not None else None
            file_name = found.get("file_name")
            if st in {"processed", "available", "ready"} and file_name:
                job["file_name"] = str(file_name)
                continue
            if st in {"failed", "error", "cancelled"}:
                raise _mp_error("Mercado Pago falló al generar el reporte de movimientos.")
            still.append(job)
        pending = still
        if pending:
            time.sleep(interval)

    if pending:
        detail_bits = ", ".join(
            f"{rid}:{last_statuses.get(rid) or 'desconocido'}" for rid in (j.get("report_id") for j in pending)
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout esperando reportes de Mercado Pago ({detail_bits}).",
        )


def download_report_csv(client: httpx.Client, token: str, file_name: str) -> str:
    base = settings.mp_api_base_url.rstrip("/")
    url = f"{base}/v1/account/settlement_report/{file_name}"
    resp = client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "*/*"})
    if resp.status_code >= 400:
        logger.warning("MP settlement_report download status=%s", resp.status_code)
        raise _mp_error("No se pudo descargar el reporte de movimientos.")
    return resp.text


def search_movements(
    db: Session,
    *,
    account_id: UUID,
    from_datetime: datetime,
    to_datetime: datetime,
) -> list[MovementDto]:
    _validate_range(from_datetime, to_datetime)
    account = mp_account_repo.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta Mercado Pago no encontrada.")
    if not account.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cuenta está desactivada.")

    token = mp_oauth_service.ensure_access_token(db, account)
    chunk_days = max(1, int(settings.mp_report_chunk_days))
    chunks = list(iter_range_chunks(from_datetime, to_datetime, chunk_days=chunk_days))
    # Parallel pipeline: wall ≈ one slow report, not sum of chunks
    wall = float(settings.mp_report_poll_timeout_seconds) + 90.0
    timeout = httpx.Timeout(max(120.0, float(settings.mp_api_timeout_seconds), wall))

    with httpx.Client(timeout=timeout) as client:
        ensure_report_config(client, token)

        def start_all(tok: str) -> list[dict[str, Any]]:
            jobs: list[dict[str, Any]] = []
            for idx, (chunk_from, chunk_to) in enumerate(chunks, start=1):
                begin = _as_utc_iso(chunk_from)
                end = _as_utc_iso(chunk_to)
                logger.info(
                    "MP movements start chunk %s/%s account=%s begin=%s end=%s",
                    idx,
                    len(chunks),
                    account_id,
                    begin,
                    end,
                )
                created = _create_report(client, tok, begin=begin, end=end)
                report_id = created.get("id") or created.get("report_id")
                file_name = None
                if created.get("file_name") and created.get("status") in {"processed", "available", "ready"}:
                    file_name = str(created["file_name"])
                jobs.append(
                    {
                        "report_id": report_id,
                        "begin": begin,
                        "end": end,
                        "file_name": file_name,
                    }
                )
            return jobs

        try:
            jobs = start_all(token)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_401_UNAUTHORIZED:
                raise
            token = mp_oauth_service.ensure_access_token(db, account)
            ensure_report_config(client, token)
            jobs = start_all(token)

        try:
            wait_for_many_report_files(client, token, jobs=jobs)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_401_UNAUTHORIZED:
                raise
            token = mp_oauth_service.ensure_access_token(db, account)
            wait_for_many_report_files(client, token, jobs=jobs)

        items: list[MovementDto] = []
        seen: set[tuple] = set()
        for job in jobs:
            file_name = job.get("file_name")
            if not file_name:
                raise _mp_error("Reporte de Mercado Pago sin archivo para descargar.")
            csv_text = download_report_csv(client, token, str(file_name))
            for m in parse_settlement_csv(csv_text):
                key = _movement_dedupe_key(m)
                if key in seen:
                    continue
                seen.add(key)
                items.append(m)

    items.sort(
        key=lambda m: m.transaction_date or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items

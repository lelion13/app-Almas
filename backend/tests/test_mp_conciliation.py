from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.services import mp_crypto
from app.services.mp_account_money_service import (
    MAX_RANGE_DAYS,
    _validate_range,
    bucket_for_type,
    label_for_type,
    map_payment_to_movement,
)


def test_fernet_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.services.mp_crypto.settings.mp_token_encryption_key", key)
    plain = "APP_USR-secret-token-value"
    enc = mp_crypto.encrypt_secret(plain)
    assert enc != plain
    assert mp_crypto.decrypt_secret(enc) == plain
    assert mp_crypto.token_last4(plain) == plain[-4:]


def test_range_rejects_over_60_days() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=MAX_RANGE_DAYS, seconds=1)
    with pytest.raises(HTTPException) as exc:
        _validate_range(start, end)
    assert exc.value.status_code == 422


def test_range_allows_60_days() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=MAX_RANGE_DAYS)
    _validate_range(start, end)


def test_bucket_and_labels() -> None:
    assert bucket_for_type("SETTLEMENT") == "ingreso"
    assert bucket_for_type("REFUND") == "egreso"
    assert bucket_for_type("CHARGEBACK") == "egreso"
    assert label_for_type("SETTLEMENT") == "Cobro"
    assert label_for_type("REFUND") == "Devolución"


def test_map_payment_approved_and_refunded() -> None:
    cobro = map_payment_to_movement(
        {
            "id": 123,
            "date_created": "2026-01-01T10:00:00.000-03:00",
            "date_approved": "2026-01-02T11:00:00.000-03:00",
            "transaction_amount": 1500.5,
            "currency_id": "ARS",
            "status": "approved",
            "description": "Cuota",
            "external_reference": "SF-1",
            "fee_details": [{"amount": 50}],
        }
    )
    assert cobro.source_id == "123"
    assert cobro.bucket == "ingreso"
    assert cobro.transaction_type == "SETTLEMENT"
    assert cobro.amount == Decimal("1500.5")
    assert cobro.fee_amount == Decimal("50")
    assert cobro.external_reference == "SF-1"
    assert cobro.transaction_date is not None
    assert cobro.transaction_date.day == 2

    devol = map_payment_to_movement(
        {
            "id": 456,
            "date_created": "2026-01-03T10:00:00.000-03:00",
            "transaction_amount": 200,
            "currency_id": "ARS",
            "status": "refunded",
            "description": "Dev",
        }
    )
    assert devol.bucket == "egreso"
    assert devol.transaction_type == "REFUND"
    assert devol.transaction_type_label == "Devolución"

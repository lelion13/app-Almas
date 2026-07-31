from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.services import mp_crypto
from app.services.mp_payments_service import MAX_RANGE_DAYS, _map_payment, _validate_range


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


def test_map_payment_prefers_date_approved() -> None:
    dto = _map_payment(
        {
            "id": 123,
            "date_created": "2026-01-01T10:00:00.000-03:00",
            "date_approved": "2026-01-02T11:00:00.000-03:00",
            "transaction_amount": 1500.5,
            "currency_id": "ARS",
            "status": "approved",
            "description": "Cuota",
            "payer": {"email": "a@b.com"},
        }
    )
    assert dto.id == "123"
    assert dto.amount == Decimal("1500.5")
    assert dto.currency == "ARS"
    assert dto.status == "approved"
    assert dto.description == "Cuota"
    assert dto.payer_reference == "a@b.com"
    assert dto.date is not None
    assert dto.date.day == 2

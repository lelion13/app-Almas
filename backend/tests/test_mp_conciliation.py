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
    parse_settlement_csv,
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
    assert bucket_for_type("WITHDRAWAL") == "egreso"
    assert bucket_for_type("PAYOUT") == "egreso"
    assert bucket_for_type("REFUND") == "egreso"
    assert bucket_for_type("DISPUTE") == "otro"
    assert label_for_type("SETTLEMENT") == "Cobro"
    assert label_for_type("WITHDRAWAL") == "Retiro bancario"


def test_parse_settlement_csv_semicolon() -> None:
    csv_text = (
        "SOURCE_ID;TRANSACTION_TYPE;TRANSACTION_DATE;TRANSACTION_AMOUNT;"
        "TRANSACTION_CURRENCY;SETTLEMENT_NET_AMOUNT;EXTERNAL_REFERENCE;DESCRIPTION;FEE_AMOUNT\n"
        "123;SETTLEMENT;2026-01-02T10:00:00Z;1000;ARS;950;ref1;Cuota;50\n"
        "456;WITHDRAWAL;2026-01-03T12:00:00Z;500;ARS;500;;Retiro;0\n"
    )
    items = parse_settlement_csv(csv_text)
    assert len(items) == 2
    assert items[0].source_id == "123"
    assert items[0].bucket == "ingreso"
    assert items[0].amount == Decimal("950")
    assert items[0].transaction_type_label == "Cobro"
    assert items[0].external_reference == "ref1"
    assert items[1].bucket == "egreso"
    assert items[1].transaction_type_label == "Retiro bancario"

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook

from app.services.siguefit_excel import json_safe_cell_value, normalize_group_key, parse_workbook


def test_normalize_group_key_collapses_spaces() -> None:
    assert normalize_group_key("  a   b  ") == "a b"


def test_json_safe_cell_value_roundtrip() -> None:
    d = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "d": json_safe_cell_value(d),
        "t": json_safe_cell_value(date(2026, 4, 1)),
        "dec": json_safe_cell_value(Decimal("10.5")),
        "n": json_safe_cell_value(42),
    }
    json.dumps(payload)


def test_parse_minimal_xlsx() -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["Desde:", 44927, "Hasta:", 44987, ""])
    ws.append(["Actvidad:", "Todos", " ", ""])
    ws.append([])
    ws.append(
        [
            "Fecha",
            "Cliente",
            "DNI",
            "Categoría de Pago",
            "Mes",
            "Año",
            "Vencimiento",
            "Importe",
            "Divisa",
            "Método de Pago",
            "Actividad",
            "Detalle",
            "Fecha de Registro",
            "Usuario",
        ]
    )
    ws.append(
        [
            44950,
            "Test Cliente",
            "123",
            "1 vez Yoga",
            0,
            0,
            None,
            10000,
            "ARS",
            "Efectivo",
            "Yoga",
            "",
            44950.5,
            "Admin",
        ]
    )
    buf = BytesIO()
    wb.save(buf)
    content = buf.getvalue()

    result = parse_workbook(content)
    assert not result.row_errors
    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.payment_category == "1 vez Yoga"
    assert line.payment_method == "Efectivo"
    assert line.amount == Decimal("10000")
    assert line.client_name == "Test Cliente"


def test_parse_skips_row_without_amount() -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["Fecha", "Cliente", "DNI", "Categoría de Pago", "Importe", "Método de Pago"])
    ws.append([None, "X", None, "Cat", None, "Efectivo"])
    buf = BytesIO()
    wb.save(buf)
    result = parse_workbook(buf.getvalue())
    assert result.lines == []
    assert result.rows_skipped >= 1

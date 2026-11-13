from decimal import Decimal

import pytest

from servicos.moeda import converter_para_brl, cotacao_brl, valor_em_brl


def test_converter_multiplies_by_the_brl_rate_per_unit() -> None:
    assert converter_para_brl(Decimal("100"), Decimal("5.12345678")) == Decimal("512.35")


def test_converter_rejects_a_non_positive_rate() -> None:
    with pytest.raises(ValueError, match="positiva"):
        converter_para_brl(Decimal("10"), Decimal("0"))


def test_cotacao_is_brl_per_unit_of_foreign_currency() -> None:
    assert cotacao_brl(Decimal("3.4")) == Decimal("0.29411765")


def test_value_in_brl_divides_by_rate() -> None:
    assert valor_em_brl(Decimal("340"), Decimal("3.4")) == Decimal("100.00")


def test_value_in_brl_rounds_half_up_to_cents() -> None:
    assert valor_em_brl(Decimal("0.125"), Decimal("1")) == Decimal("0.13")


def test_rate_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positiva"):
        valor_em_brl(Decimal("10"), Decimal("0"))
    with pytest.raises(ValueError, match="positiva"):
        cotacao_brl(Decimal("-1"))

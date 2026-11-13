from datetime import date
from decimal import Decimal

import pytest

from servicos import importacao_antiga

HOJE = date(2026, 11, 13)


def test_frozen_trip_becomes_stand_by() -> None:
    assert importacao_antiga.estado_da_viagem(True, date(2028, 1, 12), HOJE) == "stand_by"


def test_trip_that_ended_before_today_becomes_completed() -> None:
    assert importacao_antiga.estado_da_viagem(False, date(2026, 11, 1), HOJE) == "concluida"


def test_trip_ending_today_stays_in_planning() -> None:
    assert importacao_antiga.estado_da_viagem(False, HOJE, HOJE) == "planejamento"


def test_destination_maps_to_country_and_city() -> None:
    assert importacao_antiga.destino_da_viagem("Cape Town (South Africa)") == ("ZA", "Cape Town")


def test_destination_without_city_keeps_empty_city() -> None:
    assert importacao_antiga.destino_da_viagem("Japão") == ("JP", "")


def test_trip_name_is_not_used_as_the_city() -> None:
    assert importacao_antiga.destino_da_viagem("Floripa - Natal") == ("BR", "Florianópolis")


def test_unknown_destination_is_rejected() -> None:
    with pytest.raises(ValueError, match="sem mapeamento"):
        importacao_antiga.destino_da_viagem("Lisboa")


def test_expense_statuses_map_to_portuguese_situations() -> None:
    assert importacao_antiga.situacao_da_despesa("actual") == "realizada"
    assert importacao_antiga.situacao_da_despesa("planned") == "planejada"


def test_unknown_expense_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="desconhecido"):
        importacao_antiga.situacao_da_despesa("refunded")


def test_home_currency_always_has_rate_one() -> None:
    assert importacao_antiga.taxa_da_despesa("BRL", "actual", None, None) == Decimal(1)


def test_realized_expense_keeps_its_own_rate() -> None:
    taxa = importacao_antiga.taxa_da_despesa("ZAR", "actual", Decimal("3.4"), Decimal("2.9"))
    assert taxa == Decimal("3.4")


def test_planned_expense_uses_the_shared_trip_rate() -> None:
    taxa = importacao_antiga.taxa_da_despesa("ZAR", "planned", None, Decimal("2.9"))
    assert taxa == Decimal("2.9")


def test_realized_expense_without_rate_is_rejected() -> None:
    with pytest.raises(ValueError, match="sem taxa de câmbio"):
        importacao_antiga.taxa_da_despesa("ZAR", "actual", None, Decimal("2.9"))


def test_planned_expense_without_shared_rate_is_rejected() -> None:
    with pytest.raises(ValueError, match="sem taxa compartilhada"):
        importacao_antiga.taxa_da_despesa("ZAR", "planned", None, None)

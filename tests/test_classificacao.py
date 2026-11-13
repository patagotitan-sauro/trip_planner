import pytest

from servicos.classificacao import classificar_viagem


def test_trip_with_only_brazilian_destinations_is_national() -> None:
    assert classificar_viagem(["BR"]) == "nacional"


def test_trip_to_japan_is_international() -> None:
    assert classificar_viagem(["JP"]) == "internacional"


def test_trip_with_mixed_destinations_is_international() -> None:
    assert classificar_viagem(["BR", "AR"]) == "internacional"


def test_trip_without_destinations_cannot_be_classified() -> None:
    with pytest.raises(ValueError, match="sem destinos"):
        classificar_viagem([])

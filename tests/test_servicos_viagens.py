from dataclasses import dataclass
from datetime import date

import pytest

from servicos import viagens


@dataclass
class ViagemFalsa:
    nome: str
    estado: str
    data_fim: date | None = None


def test_groups_trips_by_state_and_completed_by_end_year_newest_first():
    stand_by = ViagemFalsa("Japão", "stand_by")
    planejada = ViagemFalsa("Argentina", "planejamento", date(2027, 3, 1))
    velha = ViagemFalsa("Manaus", "concluida", date(2023, 5, 1))
    recente_a = ViagemFalsa("Floripa", "concluida", date(2025, 1, 10))
    recente_b = ViagemFalsa("Porto Alegre", "concluida", date(2025, 7, 20))

    grupos = viagens.agrupar_viagens([velha, stand_by, recente_a, planejada, recente_b])

    assert grupos.stand_by == [stand_by]
    assert grupos.planejamento == [planejada]
    assert list(grupos.concluidas_por_ano) == [2025, 2023]
    assert grupos.concluidas_por_ano[2025] == [recente_a, recente_b]
    assert grupos.concluidas_por_ano[2023] == [velha]


def test_grouping_an_empty_list_gives_empty_groups():
    grupos = viagens.agrupar_viagens([])

    assert (grupos.stand_by, grupos.planejamento, grupos.concluidas_por_ano) == ([], [], {})


def test_year_is_the_end_date_year_even_when_the_trip_starts_earlier():
    virada = ViagemFalsa("Réveillon", "concluida", date(2025, 1, 2))

    assert list(viagens.agrupar_viagens([virada]).concluidas_por_ano) == [2025]


def test_completed_trip_without_end_date_is_rejected():
    with pytest.raises(ValueError, match="sem data de fim"):
        viagens.agrupar_viagens([ViagemFalsa("X", "concluida")])


def test_unknown_state_is_rejected():
    with pytest.raises(ValueError, match="desconhecido"):
        viagens.agrupar_viagens([ViagemFalsa("X", "cancelada")])


def test_stand_by_trip_may_have_no_dates():
    assert viagens.validar_datas_da_viagem("stand_by", None, None) == {}


def test_planning_trip_requires_both_dates():
    erros = viagens.validar_datas_da_viagem("planejamento", None, None)

    assert set(erros) == {"data_inicio", "data_fim"}


def test_end_date_before_start_date_is_rejected():
    erros = viagens.validar_datas_da_viagem("planejamento", date(2026, 5, 10), date(2026, 5, 9))

    assert set(erros) == {"data_fim"}


def test_one_day_trip_is_valid():
    assert (
        viagens.validar_datas_da_viagem("planejamento", date(2026, 5, 10), date(2026, 5, 10)) == {}
    )


def test_stand_by_trip_with_reversed_dates_is_rejected():
    erros = viagens.validar_datas_da_viagem("stand_by", date(2026, 5, 10), date(2026, 5, 1))

    assert set(erros) == {"data_fim"}


def test_stand_by_activity_needs_a_day_number_of_one_or_more():
    assert set(viagens.validar_posicao_da_atividade("stand_by", None, None)) == {"dia"}
    assert set(viagens.validar_posicao_da_atividade("stand_by", None, 0)) == {"dia"}
    assert viagens.validar_posicao_da_atividade("stand_by", None, 1) == {}


def test_activity_in_other_states_needs_a_date():
    assert set(viagens.validar_posicao_da_atividade("planejamento", None, 2)) == {"data"}
    assert viagens.validar_posicao_da_atividade("concluida", date(2026, 1, 1), None) == {}

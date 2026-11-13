from dataclasses import dataclass
from datetime import date, time

import pytest

from servicos import viagens


@dataclass
class AtividadeFalsa:
    nome: str
    data: date | None = None
    dia: int | None = None
    hora: time | None = None


def _nomes(grupo):
    return [atividade.nome for atividade in grupo.atividades]


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


def test_only_planning_and_stand_by_trips_can_be_deleted():
    assert viagens.pode_excluir_viagem("planejamento")
    assert viagens.pode_excluir_viagem("stand_by")
    assert not viagens.pode_excluir_viagem("concluida")


def test_itinerary_is_grouped_by_date_in_ascending_order():
    tarde = AtividadeFalsa("Jantar", data=date(2027, 1, 2), hora=time(20, 0))
    manha = AtividadeFalsa("Café", data=date(2027, 1, 2), hora=time(8, 30))
    outro_dia = AtividadeFalsa("Praia", data=date(2027, 1, 1))

    grupos = viagens.agrupar_roteiro([tarde, outro_dia, manha], "planejamento")

    assert [grupo.chave for grupo in grupos] == [date(2027, 1, 1), date(2027, 1, 2)]
    assert _nomes(grupos[1]) == ["Café", "Jantar"]


def test_stand_by_itinerary_is_grouped_by_day_number_not_by_date():
    dia_2 = AtividadeFalsa("B", data=date(2020, 1, 1), dia=2)
    dia_1 = AtividadeFalsa("A", data=date(2030, 1, 1), dia=1)

    grupos = viagens.agrupar_roteiro([dia_2, dia_1], "stand_by")

    assert [grupo.chave for grupo in grupos] == [1, 2]


def test_activities_without_time_come_after_timed_ones_in_input_order():
    sem_hora_a = AtividadeFalsa("A", dia=1)
    com_hora = AtividadeFalsa("B", dia=1, hora=time(23, 0))
    sem_hora_c = AtividadeFalsa("C", dia=1)

    grupos = viagens.agrupar_roteiro([sem_hora_a, com_hora, sem_hora_c], "stand_by")

    assert _nomes(grupos[0]) == ["B", "A", "C"]


def test_midnight_activity_is_sorted_before_untimed_ones():
    meia_noite = AtividadeFalsa("Virada", dia=1, hora=time(0, 0))
    sem_hora = AtividadeFalsa("Livre", dia=1)

    grupos = viagens.agrupar_roteiro([sem_hora, meia_noite], "stand_by")

    assert _nomes(grupos[0]) == ["Virada", "Livre"]


def test_activities_missing_the_day_or_date_form_a_last_group():
    sem_data = AtividadeFalsa("Solta")
    com_data = AtividadeFalsa("Certa", data=date(2027, 1, 1))

    grupos = viagens.agrupar_roteiro([sem_data, com_data], "planejamento")

    assert [grupo.chave for grupo in grupos] == [date(2027, 1, 1), None]


def test_empty_itinerary_has_no_groups():
    assert viagens.agrupar_roteiro([], "planejamento") == []


def test_allowed_state_changes():
    assert viagens.estados_de_destino("stand_by") == ("planejamento",)
    assert viagens.estados_de_destino("planejamento") == ("stand_by", "concluida")
    assert viagens.estados_de_destino("concluida") == ("planejamento",)


def test_stand_by_trip_cannot_be_completed_directly():
    assert "concluida" not in viagens.estados_de_destino("stand_by")


def test_unknown_state_has_no_destinations():
    assert viagens.estados_de_destino("cancelada") == ()


INICIO = date(2027, 3, 10)


def test_date_becomes_day_number_when_going_to_stand_by():
    assert viagens.nova_posicao_da_atividade("stand_by", date(2027, 3, 10), None, INICIO) == (
        None,
        1,
    )
    assert viagens.nova_posicao_da_atividade("stand_by", date(2027, 3, 14), None, INICIO) == (
        None,
        5,
    )


def test_activity_before_the_start_date_keeps_its_date_in_stand_by():
    posicao = viagens.nova_posicao_da_atividade("stand_by", date(2027, 3, 9), None, INICIO)

    assert posicao == (date(2027, 3, 9), None)


def test_day_number_becomes_date_when_going_back_to_planning():
    novo_inicio = date(2028, 1, 30)

    assert viagens.nova_posicao_da_atividade("planejamento", None, 1, novo_inicio) == (
        novo_inicio,
        None,
    )
    assert viagens.nova_posicao_da_atividade("planejamento", None, 4, novo_inicio) == (
        date(2028, 2, 2),
        None,
    )


def test_activity_with_only_a_date_keeps_it_when_going_back_to_planning():
    antiga = date(2099, 1, 1)

    assert viagens.nova_posicao_da_atividade("planejamento", antiga, None, INICIO) == (antiga, None)


def test_activities_stay_as_they_are_when_the_trip_has_no_start_date():
    assert viagens.nova_posicao_da_atividade("stand_by", date(2027, 3, 14), None, None) == (
        date(2027, 3, 14),
        None,
    )


def test_going_to_stand_by_and_back_restores_the_same_date():
    em_stand_by = viagens.nova_posicao_da_atividade("stand_by", date(2027, 3, 12), None, INICIO)

    volta = viagens.nova_posicao_da_atividade("planejamento", *em_stand_by, INICIO)

    assert volta == (date(2027, 3, 12), None)

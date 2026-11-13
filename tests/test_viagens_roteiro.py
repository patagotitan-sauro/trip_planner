from datetime import date, time
from decimal import Decimal

from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, EstadoViagem, Viagem


def _planejada(nome="Sul"):
    return Viagem.objects.create(
        nome=nome,
        estado=EstadoViagem.PLANEJAMENTO,
        data_inicio=date(2027, 1, 1),
        data_fim=date(2027, 1, 10),
    )


def _stand_by(nome="Japão"):
    return Viagem.objects.create(nome=nome, estado=EstadoViagem.STAND_BY)


def _detalhe(client, viagem):
    return client.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()


def test_detail_without_activities_says_so_and_links_to_add_one(logado):
    viagem = _planejada()

    html = _detalhe(logado, viagem)

    assert "Nenhuma atividade ainda." in html
    assert reverse("viagens:criar_atividade", args=[viagem.pk]) in html


def test_planning_trip_form_asks_for_a_date_and_not_a_day_number(logado):
    viagem = _planejada()

    html = logado.get(reverse("viagens:criar_atividade", args=[viagem.pk])).content.decode()

    assert 'name="data"' in html
    assert 'name="dia"' not in html


def test_stand_by_trip_form_asks_for_a_day_number_and_not_a_date(logado):
    viagem = _stand_by()

    html = logado.get(reverse("viagens:criar_atividade", args=[viagem.pk])).content.decode()

    assert 'name="dia"' in html
    assert 'name="data"' not in html


def test_create_activity_on_a_planning_trip(logado):
    viagem = _planejada()
    dados = {
        "data": "2027-01-03",
        "hora": "09:30",
        "atividade": "Passeio de barco",
        "local": "Porto",
        "observacoes": "Levar protetor",
    }

    response = logado.post(reverse("viagens:criar_atividade", args=[viagem.pk]), dados)

    assert response.status_code == 302
    atividade = viagem.atividades.get()
    assert (atividade.data, atividade.hora, atividade.dia) == (date(2027, 1, 3), time(9, 30), None)
    assert (atividade.atividade, atividade.local) == ("Passeio de barco", "Porto")


def test_planning_activity_without_date_shows_error_and_saves_nothing(logado):
    viagem = _planejada()

    response = logado.post(
        reverse("viagens:criar_atividade", args=[viagem.pk]), {"data": "", "atividade": "X"}
    )

    assert response.status_code == 200
    assert "Informe a data." in response.content.decode()
    assert not viagem.atividades.exists()


def test_invalid_date_shows_a_single_error_message(logado):
    viagem = _planejada()

    response = logado.post(
        reverse("viagens:criar_atividade", args=[viagem.pk]),
        {"data": "99/99/9999", "atividade": "X"},
    )

    html = response.content.decode()
    assert "Informe a data." not in html
    assert not viagem.atividades.exists()


def test_activity_name_is_required(logado):
    viagem = _planejada()

    response = logado.post(
        reverse("viagens:criar_atividade", args=[viagem.pk]),
        {"data": "2027-01-03", "atividade": ""},
    )

    assert response.status_code == 200
    assert not viagem.atividades.exists()


def test_activity_date_may_fall_outside_the_trip_dates(logado):
    viagem = _planejada()

    logado.post(
        reverse("viagens:criar_atividade", args=[viagem.pk]),
        {"data": "2030-05-05", "atividade": "Fora do período"},
    )

    assert viagem.atividades.count() == 1


def test_create_activity_on_a_stand_by_trip_uses_the_day_number(logado):
    viagem = _stand_by()

    logado.post(
        reverse("viagens:criar_atividade", args=[viagem.pk]), {"dia": "2", "atividade": "Templo"}
    )

    atividade = viagem.atividades.get()
    assert (atividade.dia, atividade.data) == (2, None)
    assert "Dia 2" in _detalhe(logado, viagem)


def test_stand_by_activity_needs_a_day_of_one_or_more(logado):
    viagem = _stand_by()
    url = reverse("viagens:criar_atividade", args=[viagem.pk])

    sem_dia = logado.post(url, {"dia": "", "atividade": "X"})
    dia_zero = logado.post(url, {"dia": "0", "atividade": "X"})

    assert "Informe o número do dia." in sem_dia.content.decode()
    assert "1 ou maior" in dia_zero.content.decode()
    assert not viagem.atividades.exists()


def test_detail_lists_the_itinerary_by_date_with_activities_in_time_order(logado):
    viagem = _planejada()
    AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 1, 5), hora=time(20, 0), atividade="Jantar"
    )
    AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 1, 5), hora=time(8, 0), atividade="Café"
    )
    AtividadeRoteiro.objects.create(viagem=viagem, data=date(2027, 1, 2), atividade="Chegada")

    html = _detalhe(logado, viagem)

    assert html.index("02/01/2027") < html.index("05/01/2027")
    assert html.index("Café") < html.index("Jantar")
    assert "08:00" in html


def test_imported_stand_by_activity_without_day_goes_to_a_last_group(logado):
    viagem = _stand_by()
    AtividadeRoteiro.objects.create(viagem=viagem, dia=1, atividade="Primeira")
    AtividadeRoteiro.objects.create(viagem=viagem, data=date(2099, 1, 1), atividade="Antiga")

    html = _detalhe(logado, viagem)

    assert html.index("Dia 1") < html.index("Sem dia")
    assert "Antiga" in html


def test_edit_activity_changes_it(logado):
    viagem = _planejada()
    atividade = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 1, 2), atividade="Velha"
    )

    response = logado.post(
        reverse("viagens:editar_atividade", args=[viagem.pk, atividade.pk]),
        {"data": "2027-01-04", "atividade": "Nova"},
    )

    assert response.status_code == 302
    atividade.refresh_from_db()
    assert (atividade.atividade, atividade.data) == ("Nova", date(2027, 1, 4))


def test_edit_form_shows_the_current_values(logado):
    viagem = _planejada()
    atividade = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 1, 2), hora=time(7, 5), atividade="Trilha"
    )

    html = logado.get(
        reverse("viagens:editar_atividade", args=[viagem.pk, atividade.pk])
    ).content.decode()

    assert 'value="Trilha"' in html
    assert 'value="2027-01-02"' in html
    assert 'value="07:05"' in html


def test_cannot_edit_an_activity_through_another_trip(logado):
    dona = _planejada("Dona")
    outra = _planejada("Outra")
    atividade = AtividadeRoteiro.objects.create(
        viagem=dona, data=date(2027, 1, 2), atividade="Trilha"
    )

    response = logado.get(reverse("viagens:editar_atividade", args=[outra.pk, atividade.pk]))

    assert response.status_code == 404


def test_remove_activity_requires_post_and_deletes_only_that_one(logado):
    viagem = _planejada()
    alvo = AtividadeRoteiro.objects.create(viagem=viagem, data=date(2027, 1, 2), atividade="A")
    AtividadeRoteiro.objects.create(viagem=viagem, data=date(2027, 1, 3), atividade="B")
    url = reverse("viagens:remover_atividade", args=[viagem.pk, alvo.pk])

    assert logado.get(url).status_code == 405
    assert viagem.atividades.count() == 2

    assert logado.post(url).status_code == 302
    assert [a.atividade for a in viagem.atividades.all()] == ["B"]


def test_cannot_remove_an_activity_through_another_trip(logado):
    dona = _planejada("Dona")
    outra = _planejada("Outra")
    atividade = AtividadeRoteiro.objects.create(viagem=dona, data=date(2027, 1, 2), atividade="A")

    response = logado.post(reverse("viagens:remover_atividade", args=[outra.pk, atividade.pk]))

    assert response.status_code == 404
    assert dona.atividades.exists()


def test_removing_an_activity_keeps_its_linked_expense(logado):
    viagem = _planejada()
    atividade = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 1, 2), atividade="Passeio"
    )
    despesa = Despesa.objects.create(
        viagem=viagem,
        atividade=atividade,
        categoria=Categoria.objects.create(nome="Passeios"),
        descricao="Ingresso",
        valor_original=Decimal("50.00"),
        moeda="BRL",
    )

    logado.post(reverse("viagens:remover_atividade", args=[viagem.pk, atividade.pk]))

    despesa.refresh_from_db()
    assert despesa.atividade is None

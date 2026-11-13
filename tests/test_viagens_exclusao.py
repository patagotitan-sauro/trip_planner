from datetime import date
from decimal import Decimal

from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, Destino, EstadoViagem, Viagem


def _viagem(estado=EstadoViagem.PLANEJAMENTO, nome="Sul"):
    datas = {} if estado == EstadoViagem.STAND_BY else {"data_inicio": date(2027, 1, 1)}
    if datas:
        datas["data_fim"] = date(2027, 1, 5)
    return Viagem.objects.create(nome=nome, estado=estado, **datas)


def test_detail_shows_delete_button_for_planning_and_stand_by(logado):
    for estado in (EstadoViagem.PLANEJAMENTO, EstadoViagem.STAND_BY):
        viagem = _viagem(estado, nome=f"V {estado}")

        html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

        assert reverse("viagens:excluir", args=[viagem.pk]) in html


def test_detail_hides_delete_button_for_completed_trip(logado):
    viagem = _viagem(EstadoViagem.CONCLUIDA)

    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert reverse("viagens:excluir", args=[viagem.pk]) not in html


def test_confirmation_page_counts_what_will_be_deleted(logado):
    viagem = _viagem()
    Destino.objects.create(viagem=viagem, pais="BR", cidade="Natal")
    atividade = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 1, 2), atividade="Praia"
    )
    categoria = Categoria.objects.create(nome="Hospedagem")
    Despesa.objects.create(
        viagem=viagem,
        atividade=atividade,
        categoria=categoria,
        descricao="Hotel",
        valor_original=Decimal("100.00"),
        moeda="BRL",
    )

    html = logado.get(reverse("viagens:excluir", args=[viagem.pk])).content.decode()

    assert "1 destino(s), 1 atividade(s) do roteiro e 1 despesa(s)" in html
    assert Viagem.objects.filter(pk=viagem.pk).exists()


def test_confirming_deletes_the_trip_and_its_related_data(logado):
    viagem = _viagem()
    Destino.objects.create(viagem=viagem, pais="BR", cidade="Natal")
    categoria = Categoria.objects.create(nome="Hospedagem")
    Despesa.objects.create(
        viagem=viagem,
        categoria=categoria,
        descricao="Hotel",
        valor_original=Decimal("100.00"),
        moeda="BRL",
    )

    response = logado.post(reverse("viagens:excluir", args=[viagem.pk]))

    assert response.status_code == 302
    assert response.url == reverse("viagens:inicio")
    assert not Viagem.objects.exists()
    assert not Destino.objects.exists()
    assert not Despesa.objects.exists()
    assert Categoria.objects.exists()


def test_stand_by_trip_can_be_deleted(logado):
    viagem = _viagem(EstadoViagem.STAND_BY)

    logado.post(reverse("viagens:excluir", args=[viagem.pk]))

    assert not Viagem.objects.exists()


def test_completed_trip_cannot_be_deleted(logado):
    viagem = _viagem(EstadoViagem.CONCLUIDA)

    get = logado.get(reverse("viagens:excluir", args=[viagem.pk]))
    post = logado.post(reverse("viagens:excluir", args=[viagem.pk]))

    assert get.status_code == post.status_code == 302
    assert post.url == reverse("viagens:detalhe", args=[viagem.pk])
    assert Viagem.objects.filter(pk=viagem.pk).exists()


def test_delete_of_unknown_trip_returns_404(logado):
    assert logado.post(reverse("viagens:excluir", args=[999])).status_code == 404

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa, MovimentoSaldo
from apps.saldos.models import Saldo
from apps.viagens.models import EstadoViagem, Viagem


@pytest.fixture
def viagem(db):
    return Viagem.objects.create(
        nome="Nova York",
        estado=EstadoViagem.PLANEJAMENTO,
        data_inicio=date(2027, 3, 10),
        data_fim=date(2027, 3, 20),
    )


def _comprar(client, viagem, **extra):
    dados = {"tipo": "dinheiro", "moeda": "USD", "valor": "100,00", "cotacao": "5,00"}
    dados.update(extra)
    return client.post(reverse("saldos:comprar", args=[viagem.pk]), dados)


def _gastar(client, viagem, saldo, valor):
    categoria, _ = Categoria.objects.get_or_create(nome="Passeios")
    return client.post(
        reverse("despesas:criar", args=[viagem.pk]),
        {
            "descricao": "Museu",
            "categoria": categoria.pk,
            "moeda": saldo.moeda,
            "valor_original": valor,
            "saldo": saldo.pk,
        },
    )


def _concluir(client, viagem):
    return client.post(reverse("viagens:mudar_estado", args=[viagem.pk, "concluida"]))


def test_confirmation_page_lists_the_balances_and_changes_nothing(logado, viagem):
    _comprar(logado, viagem)

    resposta = logado.get(reverse("viagens:mudar_estado", args=[viagem.pk, "concluida"]))

    html = resposta.content.decode()
    assert "Dinheiro em USD" in html
    assert "500,00" in html
    assert Saldo.objects.get().encerrado is False
    assert Despesa.objects.count() == 1


def test_confirmation_page_without_balances_has_no_balance_notice(logado, viagem):
    html = logado.get(reverse("viagens:mudar_estado", args=[viagem.pk, "concluida"])).content
    assert b"saldos que sobraram" not in html


def test_completing_the_trip_posts_the_leftover_and_closes_the_balance(logado, viagem):
    _comprar(logado, viagem)
    saldo = Saldo.objects.get()
    _gastar(logado, viagem, saldo, "20,00")

    resposta = _concluir(logado, viagem)

    assert resposta.status_code == 302
    viagem.refresh_from_db()
    assert viagem.estado == EstadoViagem.CONCLUIDA
    saldo.refresh_from_db()
    assert saldo.encerrado is True
    assert (saldo.valor_restante, saldo.custo_restante) == (Decimal("0"), Decimal("0"))
    sobra = Despesa.objects.get(movimento_saldo=MovimentoSaldo.ENCERRAMENTO)
    assert sobra.valor_original == Decimal("80.00")
    assert sobra.valor_brl == Decimal("400.00")
    assert sobra.data == date(2027, 3, 20)
    assert sobra.categoria.nome == "Outros gastos com dinheiro"


def test_total_equals_the_cost_of_the_purchase(logado, viagem):
    _comprar(logado, viagem)
    _gastar(logado, viagem, Saldo.objects.get(), "20,00")
    _concluir(logado, viagem)

    resposta = logado.get(reverse("despesas:lista", args=[viagem.pk]))

    assert resposta.context["total"] == Decimal("500.00")


def test_each_balance_type_goes_to_its_own_category(logado, viagem):
    _comprar(logado, viagem)
    _comprar(logado, viagem, tipo="cartao_pre_pago", moeda="EUR", cotacao="6,00")

    _concluir(logado, viagem)

    categorias = set(
        Despesa.objects.filter(movimento_saldo=MovimentoSaldo.ENCERRAMENTO).values_list(
            "categoria__nome", flat=True
        )
    )
    assert categorias == {"Outros gastos com dinheiro", "Outros gastos de cartão pré-pago"}


def test_fully_spent_balance_closes_without_a_leftover_expense(logado, viagem):
    _comprar(logado, viagem)
    _gastar(logado, viagem, Saldo.objects.get(), "100,00")

    _concluir(logado, viagem)

    assert Saldo.objects.get().encerrado is True
    assert not Despesa.objects.filter(movimento_saldo=MovimentoSaldo.ENCERRAMENTO).exists()


def test_completing_a_trip_without_balances_still_works(logado, viagem):
    _concluir(logado, viagem)

    viagem.refresh_from_db()
    assert viagem.estado == EstadoViagem.CONCLUIDA
    assert not Despesa.objects.exists()


def test_moving_to_stand_by_keeps_the_balances_open(logado, viagem):
    _comprar(logado, viagem)

    logado.post(reverse("viagens:mudar_estado", args=[viagem.pk, "stand_by"]))

    assert Saldo.objects.get().encerrado is False
    assert Despesa.objects.count() == 1


def test_reopening_the_trip_keeps_the_balances_closed(logado, viagem):
    _comprar(logado, viagem)
    _concluir(logado, viagem)

    logado.post(reverse("viagens:mudar_estado", args=[viagem.pk, "planejamento"]))

    assert Saldo.objects.get().encerrado is True
    assert Despesa.objects.filter(movimento_saldo=MovimentoSaldo.ENCERRAMENTO).count() == 1


def test_closing_rows_cannot_be_edited_or_deleted(logado, viagem):
    _comprar(logado, viagem)
    _concluir(logado, viagem)
    sobra = Despesa.objects.get(movimento_saldo=MovimentoSaldo.ENCERRAMENTO)

    editar = logado.get(reverse("despesas:editar", args=[viagem.pk, sobra.pk]))
    excluir = logado.post(reverse("despesas:excluir", args=[viagem.pk, sobra.pk]))

    assert editar.status_code == 302
    assert excluir.status_code == 302
    assert Despesa.objects.filter(pk=sobra.pk).exists()

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, EstadoViagem, Viagem
from servicos.integracoes.cotacao import CotacaoIndisponivel


@pytest.fixture
def viagem(db):
    return Viagem.objects.create(
        nome="Sul",
        estado=EstadoViagem.PLANEJAMENTO,
        data_inicio=date(2027, 3, 10),
        data_fim=date(2027, 3, 20),
    )


@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nome="Teste de categoria")


def _dados(categoria, **extra):
    dados = {
        "descricao": "Jantar",
        "categoria": categoria.pk,
        "moeda": "BRL",
        "valor_original": "100,00",
        "forma_pagamento": "pix",
    }
    dados.update(extra)
    return dados


def _criar(client, viagem, dados):
    return client.post(reverse("despesas:criar", args=[viagem.pk]), dados)


def test_form_asks_for_brl_by_default_and_has_no_situation_or_iof_fields(logado, viagem):
    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert 'value="BRL"' in html
    assert "Novo gasto" in html
    for campo in ("situacao", "cancelavel", "IOF"):
        assert campo not in html


def test_form_lists_only_activities_of_this_trip(logado, viagem):
    outra = Viagem.objects.create(nome="Outra", estado=EstadoViagem.STAND_BY)
    AtividadeRoteiro.objects.create(viagem=viagem, data=date(2027, 3, 11), atividade="Daqui")
    AtividadeRoteiro.objects.create(viagem=outra, dia=1, atividade="De fora")

    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert "Daqui" in html
    assert "De fora" not in html


def test_brl_expense_is_saved_with_rate_one(logado, viagem, categoria):
    response = _criar(logado, viagem, _dados(categoria))

    assert response.status_code == 302
    assert response.url == reverse("despesas:lista", args=[viagem.pk])
    despesa = Despesa.objects.get()
    assert despesa.viagem == viagem
    assert (despesa.cotacao, despesa.valor_brl) == (Decimal(1), Decimal("100.00"))


def test_brl_expense_may_have_no_payment_method_and_ignores_a_given_rate(logado, viagem, categoria):
    _criar(logado, viagem, _dados(categoria, forma_pagamento="", cotacao="9"))

    despesa = Despesa.objects.get()
    assert despesa.cotacao == Decimal(1)


def test_credit_card_expense_in_foreign_currency_is_converted(logado, viagem, categoria):
    dados = _dados(
        categoria,
        moeda="USD",
        valor_original="100,00",
        cotacao="5,12345678",
        forma_pagamento="cartao_credito",
    )

    _criar(logado, viagem, dados)

    despesa = Despesa.objects.get()
    assert despesa.cotacao == Decimal("5.12345678")
    assert despesa.valor_brl == Decimal("512.35")


def test_foreign_expense_without_balance_must_be_paid_by_credit_card(logado, viagem, categoria):
    dados = _dados(categoria, moeda="USD", cotacao="5", forma_pagamento="dinheiro")

    response = _criar(logado, viagem, dados)

    assert response.status_code == 200
    assert "só pode ser pago no cartão de crédito" in response.content.decode()
    assert not Despesa.objects.exists()


@pytest.mark.parametrize("forma", ["pix", "cartao_debito"])
def test_debit_and_pix_are_refused_for_foreign_currency(logado, viagem, categoria, forma):
    dados = _dados(categoria, moeda="USD", cotacao="5", forma_pagamento=forma)

    response = _criar(logado, viagem, dados)

    assert "só valem em reais" in response.content.decode()
    assert not Despesa.objects.exists()


def test_foreign_currency_needs_a_rate_and_a_payment_method(logado, viagem, categoria):
    sem_cotacao = _criar(
        logado, viagem, _dados(categoria, moeda="USD", forma_pagamento="cartao_credito")
    )
    sem_forma = _criar(
        logado, viagem, _dados(categoria, moeda="USD", cotacao="5", forma_pagamento="")
    )

    assert "Informe a cotação da moeda estrangeira." in sem_cotacao.content.decode()
    assert "Informe a forma de pagamento" in sem_forma.content.decode()
    assert not Despesa.objects.exists()


def test_currency_code_is_normalized_to_upper_case(logado, viagem, categoria):
    dados = _dados(categoria, moeda=" usd ", cotacao="5", forma_pagamento="cartao_credito")

    _criar(logado, viagem, dados)

    assert Despesa.objects.get().moeda == "USD"


@pytest.mark.parametrize("moeda", ["US", "12A", "USDX", ""])
def test_invalid_currency_codes_are_rejected(logado, viagem, categoria, moeda):
    response = _criar(logado, viagem, _dados(categoria, moeda=moeda))

    assert response.status_code == 200
    assert not Despesa.objects.exists()


def test_negative_amount_and_non_positive_rate_are_rejected(logado, viagem, categoria):
    negativo = _criar(logado, viagem, _dados(categoria, valor_original="-1"))
    cotacao_zero = _criar(
        logado,
        viagem,
        _dados(categoria, moeda="USD", cotacao="0", forma_pagamento="cartao_credito"),
    )

    assert "O valor não pode ser negativo." in negativo.content.decode()
    assert "A cotação precisa ser positiva." in cotacao_zero.content.decode()
    assert not Despesa.objects.exists()


def test_zero_amount_is_accepted(logado, viagem, categoria):
    _criar(logado, viagem, _dados(categoria, valor_original="0"))

    assert Despesa.objects.get().valor_brl == Decimal("0.00")


def test_expense_may_be_dated_before_the_trip_starts(logado, viagem, categoria):
    _criar(logado, viagem, _dados(categoria, data="2027-01-05"))

    assert Despesa.objects.get().data == date(2027, 1, 5)


def test_expense_can_be_linked_to_an_activity_of_the_same_trip(logado, viagem, categoria):
    atividade = AtividadeRoteiro.objects.create(
        viagem=viagem, data=date(2027, 3, 11), atividade="Jantar fora"
    )

    _criar(logado, viagem, _dados(categoria, atividade=atividade.pk))

    assert Despesa.objects.get().atividade == atividade


def test_activity_of_another_trip_is_rejected(logado, viagem, categoria):
    outra = Viagem.objects.create(nome="Outra", estado=EstadoViagem.STAND_BY)
    atividade = AtividadeRoteiro.objects.create(viagem=outra, dia=1, atividade="De fora")

    response = _criar(logado, viagem, _dados(categoria, atividade=atividade.pk))

    assert response.status_code == 200
    assert not Despesa.objects.exists()


def test_category_is_required(logado, viagem, categoria):
    response = _criar(logado, viagem, {**_dados(categoria), "categoria": ""})

    assert response.status_code == 200
    assert not Despesa.objects.exists()


def test_stand_by_trip_accepts_expenses(logado, categoria):
    viagem = Viagem.objects.create(nome="Japão", estado=EstadoViagem.STAND_BY)

    _criar(logado, viagem, _dados(categoria))

    assert Despesa.objects.get().viagem == viagem


def test_create_for_unknown_trip_returns_404(logado):
    assert logado.get(reverse("despesas:criar", args=[999])).status_code == 404


def _despesa_em_dolar(logado, viagem, categoria):
    dados = _dados(
        categoria, moeda="USD", cotacao="5", valor_original="100", forma_pagamento="cartao_credito"
    )
    _criar(logado, viagem, dados)
    return Despesa.objects.get()


def test_edit_form_shows_the_saved_values(logado, viagem, categoria):
    despesa = _despesa_em_dolar(logado, viagem, categoria)

    html = logado.get(reverse("despesas:editar", args=[viagem.pk, despesa.pk])).content.decode()

    assert 'value="Jantar"' in html
    assert 'value="USD"' in html
    assert 'value="100,00"' in html
    assert 'value="5,00000000"' in html


def test_editing_an_expense_recalculates_the_brl_amount(logado, viagem, categoria):
    despesa = _despesa_em_dolar(logado, viagem, categoria)
    dados = _dados(
        categoria,
        moeda="USD",
        cotacao="5",
        valor_original="200",
        forma_pagamento="cartao_credito",
        descricao="Jantar 2",
    )

    logado.post(reverse("despesas:editar", args=[viagem.pk, despesa.pk]), dados)

    despesa.refresh_from_db()
    assert despesa.descricao == "Jantar 2"
    assert despesa.valor_brl == Decimal("1000.00")


def test_changing_the_currency_to_brl_resets_the_rate(logado, viagem, categoria):
    despesa = _despesa_em_dolar(logado, viagem, categoria)

    logado.post(
        reverse("despesas:editar", args=[viagem.pk, despesa.pk]),
        _dados(categoria, moeda="BRL", valor_original="100", forma_pagamento="pix"),
    )

    despesa.refresh_from_db()
    assert (despesa.cotacao, despesa.valor_brl) == (Decimal(1), Decimal("100.00"))


def test_cannot_edit_an_expense_through_another_trip(logado, viagem, categoria):
    despesa = _despesa_em_dolar(logado, viagem, categoria)
    outra = Viagem.objects.create(nome="Outra", estado=EstadoViagem.STAND_BY)

    response = logado.get(reverse("despesas:editar", args=[outra.pk, despesa.pk]))

    assert response.status_code == 404


def test_delete_asks_for_confirmation_before_removing(logado, viagem, categoria):
    despesa = _despesa_em_dolar(logado, viagem, categoria)
    url = reverse("despesas:excluir", args=[viagem.pk, despesa.pk])

    pagina = logado.get(url)

    assert pagina.status_code == 200
    assert "Jantar" in pagina.content.decode()
    assert Despesa.objects.exists()

    resposta = logado.post(url)

    assert resposta.status_code == 302
    assert not Despesa.objects.exists()


def test_cannot_delete_an_expense_through_another_trip(logado, viagem, categoria):
    despesa = _despesa_em_dolar(logado, viagem, categoria)
    outra = Viagem.objects.create(nome="Outra", estado=EstadoViagem.STAND_BY)

    response = logado.post(reverse("despesas:excluir", args=[outra.pk, despesa.pk]))

    assert response.status_code == 404
    assert Despesa.objects.exists()


def test_trip_page_offers_the_new_expense_entry(logado, viagem):
    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert reverse("despesas:criar", args=[viagem.pk]) in html
    assert "?situacao=" not in html


def _sugerir(client, viagem, dados, url=None):
    url = url or reverse("despesas:criar", args=[viagem.pk])
    return client.post(url, {**dados, "sugerir_cotacao": "1"})


def test_suggest_button_fills_the_rate_and_keeps_the_other_fields(
    logado, viagem, categoria, provedor_de_cotacao
):
    dados = _dados(categoria, moeda="usd", forma_pagamento="cartao_credito", data="2026-03-12")

    response = _sugerir(logado, viagem, dados)

    form = response.context["form"]
    assert response.status_code == 200
    assert form["cotacao"].value() == "5,6628"
    assert form["descricao"].value() == "Jantar"
    assert form["valor_original"].value() == "100,00"
    assert form["moeda"].value() == "usd"
    assert not form.errors
    assert not Despesa.objects.exists()
    assert "Cotação sugerida de 13/11/2026: R$ 5,6628 por USD" in response.content.decode()


def test_suggestion_uses_the_expense_date_unless_it_is_missing_or_in_the_future(
    logado, viagem, categoria, provedor_de_cotacao
):
    for data in ("2026-03-12", "", "2999-01-01"):
        _sugerir(logado, viagem, _dados(categoria, moeda="USD", data=data))

    assert provedor_de_cotacao.chamadas == [
        ("USD", date(2026, 3, 12)),
        ("USD", None),
        ("USD", None),
    ]


def test_failed_suggestion_shows_the_message_and_keeps_what_was_typed(
    logado, viagem, categoria, provedor_de_cotacao
):
    provedor_de_cotacao.erro = CotacaoIndisponivel(
        "Serviço fora do ar. Digite a cotação manualmente."
    )

    response = _sugerir(logado, viagem, _dados(categoria, moeda="USD", cotacao="9,10"))

    assert response.context["form"]["cotacao"].value() == "9,10"
    assert "Serviço fora do ar" in response.content.decode()


def test_suggestion_for_reais_says_no_rate_is_needed(
    logado, viagem, categoria, provedor_de_cotacao
):
    response = _sugerir(logado, viagem, _dados(categoria, moeda="BRL"))

    assert "Reais não precisam de cotação." in response.content.decode()
    assert provedor_de_cotacao.chamadas == []


def test_the_rate_the_user_edits_after_the_suggestion_is_the_one_stored(
    logado, viagem, categoria, provedor_de_cotacao
):
    dados = _dados(categoria, moeda="USD", forma_pagamento="cartao_credito")
    _sugerir(logado, viagem, dados)

    _criar(logado, viagem, {**dados, "cotacao": "5,7000"})

    assert Despesa.objects.get().cotacao == Decimal("5.70000000")


def test_suggesting_on_the_edit_page_changes_nothing_in_the_database(
    logado, viagem, categoria, provedor_de_cotacao
):
    _criar(
        logado,
        viagem,
        _dados(categoria, moeda="USD", forma_pagamento="cartao_credito", cotacao="5"),
    )
    despesa = Despesa.objects.get()
    url = reverse("despesas:editar", args=[viagem.pk, despesa.pk])

    response = _sugerir(
        logado,
        viagem,
        _dados(categoria, moeda="USD", forma_pagamento="cartao_credito", descricao="Outro"),
        url,
    )

    assert response.context["form"]["descricao"].value() == "Outro"
    despesa.refresh_from_db()
    assert (despesa.descricao, despesa.cotacao) == ("Jantar", Decimal("5"))


def test_suggest_button_comes_after_save_so_enter_still_saves(logado, viagem):
    html = logado.get(reverse("despesas:criar", args=[viagem.pk])).content.decode()

    assert html.index(">Salvar<") < html.index('name="sugerir_cotacao"')

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import EstadoViagem, Viagem
from servicos import despesas as regras


@pytest.mark.django_db
def test_trip_gets_the_default_iof_rates_from_rn_10():
    viagem = Viagem.objects.create(nome="Teste", estado=EstadoViagem.STAND_BY)

    assert viagem.aliquota_iof_credito == regras.ALIQUOTA_CREDITO_PADRAO
    assert viagem.aliquota_iof_pre_pago_dinheiro == regras.ALIQUOTA_PRE_PAGO_DINHEIRO_PADRAO


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["aliquota_iof_credito", "aliquota_iof_pre_pago_dinheiro"])
@pytest.mark.parametrize("valor", [Decimal("-0.0001"), Decimal("1.0001")])
def test_iof_rate_outside_zero_and_one_is_rejected_by_the_database(campo, valor):
    with pytest.raises(IntegrityError), transaction.atomic():
        Viagem.objects.create(nome="Teste", estado=EstadoViagem.STAND_BY, **{campo: valor})


@pytest.mark.django_db
def test_iof_rate_of_zero_and_one_are_accepted():
    Viagem.objects.create(
        nome="Teste",
        estado=EstadoViagem.STAND_BY,
        aliquota_iof_credito=Decimal("0"),
        aliquota_iof_pre_pago_dinheiro=Decimal("1"),
    )


@pytest.mark.django_db
def test_expense_date_is_optional():
    viagem = Viagem.objects.create(nome="Teste", estado=EstadoViagem.STAND_BY)
    categoria = Categoria.objects.create(nome="Teste")

    despesa = Despesa.objects.create(
        viagem=viagem,
        categoria=categoria,
        descricao="Hotel",
        valor_original=Decimal("1.00"),
        moeda="BRL",
    )

    assert despesa.data is None


@pytest.mark.django_db
def test_additional_categories_exist_after_migrating():
    nomes = set(Categoria.objects.values_list("nome", flat=True))

    assert {"Alimentação", "Compras", "Seguro", "Outros"} <= nomes

from decimal import Decimal

import pytest

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import EstadoViagem, Viagem


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

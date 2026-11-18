from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, EstadoViagem, Viagem


@pytest.fixture
def viagem() -> Viagem:
    return Viagem.objects.create(nome="Porto Alegre", estado=EstadoViagem.STAND_BY)


@pytest.fixture
def categoria() -> Categoria:
    return Categoria.objects.create(nome="Hospedagem")


def criar_despesa(viagem: Viagem, categoria: Categoria, **campos: object) -> Despesa:
    dados: dict[str, object] = {
        "viagem": viagem,
        "categoria": categoria,
        "descricao": "Hotel",
        "valor_original": Decimal("350.00"),
        "moeda": "BRL",
    }
    dados.update(campos)
    return Despesa.objects.create(**dados)


@pytest.mark.django_db
def test_one_activity_can_have_several_expenses(viagem: Viagem, categoria: Categoria) -> None:
    atividade = AtividadeRoteiro.objects.create(viagem=viagem, dia=1, atividade="Jantar")

    criar_despesa(viagem, categoria, atividade=atividade, descricao="Jantar")
    criar_despesa(viagem, categoria, atividade=atividade, descricao="Vinho")

    assert atividade.despesas.count() == 2


@pytest.mark.django_db
def test_deleting_activity_keeps_its_expenses(viagem: Viagem, categoria: Categoria) -> None:
    atividade = AtividadeRoteiro.objects.create(viagem=viagem, dia=1, atividade="Jantar")
    despesa = criar_despesa(viagem, categoria, atividade=atividade)

    atividade.delete()
    despesa.refresh_from_db()

    assert despesa.atividade is None


@pytest.mark.django_db
def test_activity_from_another_trip_is_rejected(viagem: Viagem, categoria: Categoria) -> None:
    outra_viagem = Viagem.objects.create(nome="Manaus", estado=EstadoViagem.STAND_BY)
    atividade = AtividadeRoteiro.objects.create(viagem=outra_viagem, dia=1, atividade="Barco")
    despesa = Despesa(
        viagem=viagem,
        categoria=categoria,
        descricao="Barco",
        valor_original=Decimal("80.00"),
        moeda="BRL",
        atividade=atividade,
    )

    with pytest.raises(ValidationError, match="mesma viagem"):
        despesa.clean()


@pytest.mark.django_db
def test_negative_amount_is_rejected(viagem: Viagem, categoria: Categoria) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(viagem, categoria, valor_original=Decimal("-10.00"))


@pytest.mark.django_db
def test_category_in_use_cannot_be_deleted(viagem: Viagem, categoria: Categoria) -> None:
    criar_despesa(viagem, categoria)

    with pytest.raises(ProtectedError):
        categoria.delete()


@pytest.mark.django_db
def test_rate_keeps_eight_decimal_places(viagem: Viagem, categoria: Categoria) -> None:
    despesa = criar_despesa(viagem, categoria, moeda="USD", cotacao=Decimal("5.12345678"))

    despesa.refresh_from_db()

    assert despesa.cotacao == Decimal("5.12345678")

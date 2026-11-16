from datetime import date
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


@pytest.mark.django_db
def test_planned_cost_can_be_cancelable_with_a_deadline(
    viagem: Viagem, categoria: Categoria
) -> None:
    despesa = criar_despesa(
        viagem,
        categoria,
        situacao="planejada",
        cancelavel=True,
        data_limite_cancelamento=date(2027, 1, 5),
    )

    despesa.refresh_from_db()

    assert despesa.cancelavel
    assert despesa.data_limite_cancelamento == date(2027, 1, 5)


@pytest.mark.django_db
def test_expense_is_not_cancelable_by_default(viagem: Viagem, categoria: Categoria) -> None:
    despesa = criar_despesa(viagem, categoria)

    assert despesa.cancelavel is False
    assert despesa.data_limite_cancelamento is None


@pytest.mark.django_db
def test_cancelable_without_deadline_is_rejected(viagem: Viagem, categoria: Categoria) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(viagem, categoria, situacao="planejada", cancelavel=True)


@pytest.mark.django_db
def test_deadline_without_cancelable_mark_is_rejected(viagem: Viagem, categoria: Categoria) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(viagem, categoria, data_limite_cancelamento=date(2027, 1, 5))


@pytest.mark.django_db
def test_realized_expense_cannot_be_cancelable(viagem: Viagem, categoria: Categoria) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(
            viagem,
            categoria,
            situacao="realizada",
            cancelavel=True,
            data_limite_cancelamento=date(2027, 1, 5),
        )

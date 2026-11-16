from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import RestrictedError

from apps.despesas.models import Categoria, Despesa, MovimentoSaldo, SituacaoDespesa
from apps.saldos.models import Saldo, TipoSaldo
from apps.viagens.models import EstadoViagem, Viagem


@pytest.fixture
def viagem() -> Viagem:
    return Viagem.objects.create(nome="Nova York", estado=EstadoViagem.STAND_BY)


@pytest.fixture
def categoria() -> Categoria:
    return Categoria.objects.create(nome="Passeios")


def criar_saldo(viagem: Viagem, **campos: object) -> Saldo:
    dados: dict[str, object] = {
        "viagem": viagem,
        "tipo": TipoSaldo.DINHEIRO,
        "moeda": "USD",
        "valor_restante": Decimal("100.00"),
        "custo_restante": Decimal("505.50"),
    }
    dados.update(campos)
    return Saldo.objects.create(**dados)


def criar_despesa(viagem: Viagem, categoria: Categoria, **campos: object) -> Despesa:
    dados: dict[str, object] = {
        "viagem": viagem,
        "categoria": categoria,
        "descricao": "Compra",
        "valor_original": Decimal("10.00"),
        "moeda": "USD",
        "situacao": SituacaoDespesa.REALIZADA,
    }
    dados.update(campos)
    return Despesa.objects.create(**dados)


@pytest.mark.django_db
def test_balance_is_unique_per_trip_type_and_currency(viagem: Viagem) -> None:
    criar_saldo(viagem)

    with pytest.raises(IntegrityError), transaction.atomic():
        criar_saldo(viagem)

    criar_saldo(viagem, moeda="EUR")
    criar_saldo(viagem, tipo=TipoSaldo.CARTAO_PRE_PAGO)


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["valor_restante", "custo_restante"])
def test_balance_cannot_be_negative(viagem: Viagem, campo: str) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_saldo(viagem, **{campo: Decimal("-0.01")})


@pytest.mark.django_db
def test_balance_can_reach_zero(viagem: Viagem) -> None:
    saldo = criar_saldo(viagem, valor_restante=Decimal("0"), custo_restante=Decimal("0"))

    assert saldo.encerrado is False


@pytest.mark.django_db
def test_expense_without_balance_has_no_movement(viagem: Viagem, categoria: Categoria) -> None:
    despesa = criar_despesa(viagem, categoria)

    assert despesa.saldo is None
    assert despesa.movimento_saldo == ""


@pytest.mark.django_db
def test_balance_and_movement_must_come_together(viagem: Viagem, categoria: Categoria) -> None:
    saldo = criar_saldo(viagem)

    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(viagem, categoria, saldo=saldo)
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(viagem, categoria, movimento_saldo=MovimentoSaldo.USO)


@pytest.mark.django_db
@pytest.mark.parametrize("movimento", [MovimentoSaldo.COMPRA, MovimentoSaldo.ENCERRAMENTO])
def test_purchase_and_closing_must_be_realized(
    viagem: Viagem, categoria: Categoria, movimento: str
) -> None:
    saldo = criar_saldo(viagem)

    with pytest.raises(IntegrityError), transaction.atomic():
        criar_despesa(
            viagem,
            categoria,
            saldo=saldo,
            movimento_saldo=movimento,
            situacao=SituacaoDespesa.PLANEJADA,
        )

    criar_despesa(viagem, categoria, saldo=saldo, movimento_saldo=movimento)


@pytest.mark.django_db
def test_planned_cost_can_reserve_a_balance(viagem: Viagem, categoria: Categoria) -> None:
    saldo = criar_saldo(viagem)

    despesa = criar_despesa(
        viagem,
        categoria,
        saldo=saldo,
        movimento_saldo=MovimentoSaldo.USO,
        situacao=SituacaoDespesa.PLANEJADA,
    )

    assert list(saldo.despesas.all()) == [despesa]


@pytest.mark.django_db
def test_balance_with_expenses_cannot_be_deleted_alone(
    viagem: Viagem, categoria: Categoria
) -> None:
    saldo = criar_saldo(viagem)
    criar_despesa(viagem, categoria, saldo=saldo, movimento_saldo=MovimentoSaldo.COMPRA)

    with pytest.raises(RestrictedError):
        saldo.delete()


@pytest.mark.django_db
def test_deleting_the_trip_removes_balances_and_their_expenses(
    viagem: Viagem, categoria: Categoria
) -> None:
    saldo = criar_saldo(viagem)
    criar_despesa(viagem, categoria, saldo=saldo, movimento_saldo=MovimentoSaldo.COMPRA)

    viagem.delete()

    assert Saldo.objects.count() == 0
    assert Despesa.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("nome", ["Outros gastos de cartão pré-pago", "Outros gastos com dinheiro"])
def test_closing_categories_exist_after_migrating(nome: str) -> None:
    assert Categoria.objects.filter(nome=nome).exists()

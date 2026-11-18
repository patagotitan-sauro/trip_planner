from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

ANTES = [
    ("despesas", "0008_titulo_compra_nao_alocada"),
    ("saldos", "0001_initial"),
    ("viagens", "0002_viagem_aliquota_iof_credito_and_more"),
]


@pytest.fixture
def migrar(transactional_db):
    """Moves the schema back to the last migration with IOF and planned costs, then forward."""
    executor = MigrationExecutor(connection)
    folhas = list(executor.loader.graph.leaf_nodes())
    executor.migrate(ANTES)
    estado_antigo = executor.loader.project_state(ANTES).apps

    def avancar():
        depois = MigrationExecutor(connection)
        depois.migrate(folhas)
        return depois.loader.project_state(folhas).apps

    try:
        yield estado_antigo, avancar
    finally:
        MigrationExecutor(connection).migrate(folhas)


def _lancar(Despesa, viagem, categoria, saldo, movimento, situacao, valor, brl, iof="0"):
    return Despesa.objects.create(
        viagem=viagem,
        categoria=categoria,
        descricao=movimento,
        situacao=situacao,
        valor_original=Decimal(valor),
        moeda="USD",
        cotacao=Decimal("5"),
        valor_brl=Decimal(brl),
        valor_iof=Decimal(iof),
        saldo=saldo,
        movimento_saldo=movimento,
    )


def test_balances_are_rebuilt_without_iof_and_reservations_become_uses(migrar):
    antigo, avancar = migrar
    Viagem, Categoria = (
        antigo.get_model("viagens", "Viagem"),
        antigo.get_model("despesas", "Categoria"),
    )
    Despesa, Saldo = antigo.get_model("despesas", "Despesa"), antigo.get_model("saldos", "Saldo")
    viagem = Viagem.objects.create(nome="Nova York", estado="stand_by")
    categoria = Categoria.objects.create(nome="Passeios")
    aberto = Saldo.objects.create(
        viagem=viagem,
        tipo="dinheiro",
        moeda="USD",
        valor_restante=Decimal("60"),
        custo_restante=Decimal("303.30"),
    )
    # The use has a lower id than the purchase that covers it, as in real data.
    uso = _lancar(Despesa, viagem, categoria, aberto, "uso", "realizada", "20", "101.10")
    compra = _lancar(
        Despesa, viagem, categoria, aberto, "compra", "realizada", "100", "500", "5.50"
    )
    reserva = _lancar(Despesa, viagem, categoria, aberto, "uso", "planejada", "20", "101.10")
    sem_saldo = _lancar(Despesa, viagem, categoria, None, "", "planejada", "10", "50", "1.75")
    encerrado = Saldo.objects.create(
        viagem=viagem,
        tipo="cartao_pre_pago",
        moeda="USD",
        valor_restante=Decimal("0"),
        custo_restante=Decimal("0"),
        encerrado=True,
    )
    _lancar(Despesa, viagem, categoria, encerrado, "compra", "realizada", "50", "250", "2.75")
    reserva_encerrada = _lancar(
        Despesa, viagem, categoria, encerrado, "uso", "planejada", "5", "25.27"
    )
    sobra = _lancar(
        Despesa, viagem, categoria, encerrado, "encerramento", "realizada", "50", "252.75"
    )

    novo = avancar()

    Despesa, Saldo = novo.get_model("despesas", "Despesa"), novo.get_model("saldos", "Saldo")
    saldo = Saldo.objects.get(pk=aberto.pk)
    assert (saldo.valor_restante, saldo.custo_restante) == (Decimal("60.00"), Decimal("300.00"))
    assert Despesa.objects.get(pk=compra.pk).valor_brl == Decimal("500.00")
    for lancamento in (uso, reserva):
        assert Despesa.objects.get(pk=lancamento.pk).valor_brl == Decimal("100.00")
        assert Despesa.objects.get(pk=lancamento.pk).movimento_saldo == "uso"
    assert Despesa.objects.get(pk=sem_saldo.pk).valor_brl == Decimal("50.00")
    assert not Despesa.objects.filter(pk=reserva_encerrada.pk).exists()
    fechado = Saldo.objects.get(pk=encerrado.pk)
    assert (fechado.valor_restante, fechado.custo_restante) == (Decimal("0"), Decimal("0"))
    assert Despesa.objects.get(pk=sobra.pk).valor_brl == Decimal("250.00")

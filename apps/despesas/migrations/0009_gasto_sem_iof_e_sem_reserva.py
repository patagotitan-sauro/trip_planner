from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations

CENTAVO = Decimal("0.01")
CASAS_COTACAO = Decimal("0.00000001")


def _custo_do_uso(valor_restante: Decimal, custo_restante: Decimal, valor: Decimal) -> Decimal:
    if valor == valor_restante:
        return custo_restante
    return (custo_restante * valor / valor_restante).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _custo_medio(valor_restante: Decimal, custo_restante: Decimal) -> Decimal:
    return (custo_restante / valor_restante).quantize(CASAS_COTACAO, rounding=ROUND_HALF_UP)


def refazer_saldos_sem_iof(apps, schema_editor):
    """Replays each balance without IOF and without planned reservations.

    A planned reservation on an open balance becomes a real use; on a closed balance it was already
    inside the closing, so it is deleted. A use waits until a purchase covers it (ids are not
    always chronological); one that never fits becomes a plain expense.
    """
    Saldo = apps.get_model("saldos", "Saldo")
    Despesa = apps.get_model("despesas", "Despesa")
    for saldo in Saldo.objects.order_by("id"):
        valor = custo = Decimal(0)
        pendentes = []

        def aplicar_usos(lancamentos):
            nonlocal valor, custo
            for lancamento in lancamentos:
                gasto = _custo_do_uso(valor, custo, lancamento.valor_original)
                lancamento.cotacao = _custo_medio(valor, custo) if valor else None
                lancamento.valor_brl = gasto
                lancamento.save()
                valor -= lancamento.valor_original
                custo -= gasto

        def usos_que_cabem():
            cabem = []
            restante = valor
            for lancamento in list(pendentes):
                if lancamento.valor_original <= restante:
                    restante -= lancamento.valor_original
                    cabem.append(lancamento)
                    pendentes.remove(lancamento)
            return cabem

        for lancamento in Despesa.objects.filter(saldo=saldo).order_by("id"):
            movimento = lancamento.movimento_saldo
            if movimento == "compra":
                valor += lancamento.valor_original
                custo += lancamento.valor_brl
                aplicar_usos(usos_que_cabem())
            elif movimento == "uso":
                if lancamento.situacao == "planejada" and saldo.encerrado:
                    lancamento.delete()
                else:
                    pendentes.append(lancamento)
                    aplicar_usos(usos_que_cabem())
            elif movimento == "encerramento":
                lancamento.valor_original = valor
                lancamento.valor_brl = custo
                lancamento.cotacao = _custo_medio(valor, custo) if valor else None
                lancamento.save()
                valor = custo = Decimal(0)
        for lancamento in pendentes:
            lancamento.saldo = None
            lancamento.movimento_saldo = ""
            lancamento.save()
        saldo.valor_restante = valor
        saldo.custo_restante = custo
        saldo.save()


class Migration(migrations.Migration):
    dependencies = [
        ("despesas", "0008_titulo_compra_nao_alocada"),
        ("saldos", "0001_initial"),
    ]

    operations = [
        # Not reversible: the IOF and the reservations are dropped by the next migration.
        migrations.RunPython(refazer_saldos_sem_iof, migrations.RunPython.noop),
    ]

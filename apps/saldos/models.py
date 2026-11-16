from decimal import Decimal

from django.db import models
from django.db.models import Q

from apps.despesas.models import moeda_iso
from apps.viagens.models import Viagem
from servicos.saldos import EstadoDoSaldo, custo_medio


class TipoSaldo(models.TextChoices):
    CARTAO_PRE_PAGO = "cartao_pre_pago", "Cartão pré-pago"
    DINHEIRO = "dinheiro", "Dinheiro"


class Saldo(models.Model):
    """RN-17: what is left of the prepaid or cash balance of one currency in one trip."""

    viagem = models.ForeignKey(Viagem, on_delete=models.CASCADE, related_name="saldos")
    tipo = models.CharField(max_length=20, choices=TipoSaldo.choices)
    moeda = models.CharField(max_length=3, validators=[moeda_iso])
    valor_restante = models.DecimalField(max_digits=14, decimal_places=2)
    custo_restante = models.DecimalField(max_digits=14, decimal_places=2)  # BRL, IOF included
    encerrado = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "saldos"
        constraints = [
            models.UniqueConstraint(
                fields=["viagem", "tipo", "moeda"], name="saldo_unico_por_viagem_tipo_moeda"
            ),
            models.CheckConstraint(
                condition=Q(valor_restante__gte=0), name="saldo_valor_nao_negativo"
            ),
            models.CheckConstraint(
                condition=Q(custo_restante__gte=0), name="saldo_custo_nao_negativo"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} em {self.moeda}"

    @property
    def estado(self) -> EstadoDoSaldo:
        return EstadoDoSaldo(self.valor_restante, self.custo_restante)

    @property
    def custo_medio(self) -> Decimal | None:
        return custo_medio(self.estado) if self.valor_restante > 0 else None

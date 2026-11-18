from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from apps.viagens.models import AtividadeRoteiro, Viagem

moeda_iso = RegexValidator(r"^[A-Z]{3}$", "Use o código ISO 4217 de três letras.")


class FormaPagamento(models.TextChoices):
    CARTAO_CREDITO = "cartao_credito", "Cartão de crédito"
    CARTAO_DEBITO = "cartao_debito", "Cartão de débito"
    CARTAO_PRE_PAGO = "cartao_pre_pago", "Cartão pré-pago"
    DINHEIRO = "dinheiro", "Dinheiro"
    PIX = "pix", "Pix"


class MovimentoSaldo(models.TextChoices):
    COMPRA = "compra", "Compra ou carga"
    USO = "uso", "Uso do saldo"
    ENCERRAMENTO = "encerramento", "Encerramento do saldo"


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "categorias"

    def __str__(self) -> str:
        return self.nome


class Despesa(models.Model):
    viagem = models.ForeignKey(Viagem, on_delete=models.CASCADE, related_name="despesas")
    atividade = models.ForeignKey(
        AtividadeRoteiro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="despesas",
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="despesas")
    descricao = models.CharField(max_length=100)
    data = models.DateField(null=True, blank=True)
    valor_original = models.DecimalField(max_digits=14, decimal_places=2)
    moeda = models.CharField(max_length=3, validators=[moeda_iso])
    cotacao = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    valor_brl = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, blank=True)
    # RESTRICT lets the trip delete cascade to both, but blocks deleting a balance alone.
    saldo = models.ForeignKey(
        "saldos.Saldo",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="despesas",
    )
    movimento_saldo = models.CharField(
        max_length=20, choices=MovimentoSaldo.choices, blank=True, default=""
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(valor_original__gte=0), name="despesa_valor_nao_negativo"
            ),
            models.CheckConstraint(
                condition=Q(saldo__isnull=True, movimento_saldo="")
                | (Q(saldo__isnull=False) & ~Q(movimento_saldo="")),
                name="despesa_saldo_e_movimento_juntos",
            ),
        ]

    def __str__(self) -> str:
        return self.descricao

    @property
    def travada_por_saldo(self) -> bool:
        """Posted balance movements (purchases, uses, closings) stay as recorded."""
        return bool(self.saldo_id)

    def clean(self) -> None:
        if self.atividade_id and self.atividade.viagem_id != self.viagem_id:
            raise ValidationError({"atividade": "A atividade precisa ser da mesma viagem."})

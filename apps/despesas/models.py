from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from apps.viagens.models import AtividadeRoteiro, Viagem

moeda_iso = RegexValidator(r"^[A-Z]{3}$", "Use o código ISO 4217 de três letras.")


class SituacaoDespesa(models.TextChoices):
    PLANEJADA = "planejada", "Planejada"
    REALIZADA = "realizada", "Realizada"


class FormaPagamento(models.TextChoices):
    CARTAO_CREDITO = "cartao_credito", "Cartão de crédito"
    CARTAO_DEBITO = "cartao_debito", "Cartão de débito"
    CARTAO_PRE_PAGO = "cartao_pre_pago", "Cartão pré-pago"
    DINHEIRO = "dinheiro", "Dinheiro"
    PIX = "pix", "Pix"


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
    situacao = models.CharField(
        max_length=20, choices=SituacaoDespesa.choices, default=SituacaoDespesa.PLANEJADA
    )
    valor_original = models.DecimalField(max_digits=14, decimal_places=2)
    moeda = models.CharField(max_length=3, validators=[moeda_iso])
    cotacao = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    valor_brl = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, blank=True)
    taxa_iof = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0"))
    valor_iof = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(valor_original__gte=0), name="despesa_valor_nao_negativo"
            ),
            models.CheckConstraint(condition=Q(valor_iof__gte=0), name="despesa_iof_nao_negativo"),
        ]

    def __str__(self) -> str:
        return self.descricao

    def clean(self) -> None:
        if self.atividade_id and self.atividade.viagem_id != self.viagem_id:
            raise ValidationError({"atividade": "A atividade precisa ser da mesma viagem."})

from decimal import Decimal

from django import forms
from django.db import transaction

from apps.despesas.forms import MoedaField, campo_decimal
from apps.despesas.models import Categoria, Despesa, MovimentoSaldo, SituacaoDespesa, moeda_iso
from apps.viagens.forms import CamposInvalidosMixin
from apps.viagens.models import Viagem
from servicos.despesas import calcular_despesa, moeda_estrangeira
from servicos.saldos import categoria_de_encerramento, registrar_compra

from .models import Saldo, TipoSaldo


class CompraDeSaldoForm(CamposInvalidosMixin, forms.Form):
    tipo = forms.ChoiceField(label="Tipo de saldo", choices=TipoSaldo.choices)
    moeda = MoedaField(
        label="Moeda (código ISO, por exemplo USD)",
        min_length=3,
        max_length=3,
        validators=[moeda_iso],
    )
    valor = campo_decimal(
        "Valor comprado ou carregado",
        minimo=Decimal("0.01"),
        mensagem="O valor precisa ser positivo.",
        max_digits=14,
        decimal_places=2,
    )
    cotacao = campo_decimal(
        "Cotação (R$ por unidade da moeda)",
        minimo=Decimal("0.00000001"),
        mensagem="A cotação precisa ser positiva.",
        max_digits=18,
        decimal_places=8,
    )
    data = forms.DateField(
        label="Data (opcional)",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, viagem: Viagem, **kwargs):
        super().__init__(*args, **kwargs)
        self.viagem = viagem
        self._resultado = None

    def clean_moeda(self):
        moeda = self.cleaned_data["moeda"]
        if not moeda_estrangeira(moeda):
            raise forms.ValidationError("Informe uma moeda estrangeira; reais não têm saldo.")
        return moeda

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        saldo = Saldo.objects.filter(
            viagem=self.viagem, tipo=dados["tipo"], moeda=dados["moeda"]
        ).first()
        if saldo and saldo.encerrado:
            raise forms.ValidationError("Esse saldo já foi encerrado e não recebe novas compras.")
        # RN-13: the IOF is charged when the balance is bought or loaded.
        self._resultado = calcular_despesa(
            dados["valor"],
            dados["moeda"],
            dados["cotacao"],
            dados["tipo"],
            self.viagem.aliquota_iof_credito,
            self.viagem.aliquota_iof_pre_pago_dinheiro,
        )
        return dados

    @transaction.atomic
    def save(self) -> Saldo:
        dados = self.cleaned_data
        resultado = self._resultado
        saldo, _ = Saldo.objects.get_or_create(
            viagem=self.viagem,
            tipo=dados["tipo"],
            moeda=dados["moeda"],
            defaults={"valor_restante": Decimal(0), "custo_restante": Decimal(0)},
        )
        novo = registrar_compra(saldo.estado, dados["valor"], resultado.total_brl)
        saldo.valor_restante, saldo.custo_restante = novo.valor_restante, novo.custo_restante
        saldo.save()

        categoria, _ = Categoria.objects.get_or_create(nome=categoria_de_encerramento(saldo.tipo))
        Despesa.objects.create(
            viagem=self.viagem,
            categoria=categoria,
            descricao=f"Compra ou carga: {saldo}",
            data=dados["data"],
            situacao=SituacaoDespesa.REALIZADA,
            valor_original=dados["valor"],
            moeda=dados["moeda"],
            cotacao=resultado.cotacao,
            valor_brl=resultado.valor_brl,
            forma_pagamento=dados["tipo"],
            taxa_iof=resultado.taxa_iof,
            valor_iof=resultado.valor_iof,
            saldo=saldo,
            movimento_saldo=MovimentoSaldo.COMPRA,
        )
        return saldo

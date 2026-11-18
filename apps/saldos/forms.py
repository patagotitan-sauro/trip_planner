from decimal import Decimal

from django import forms
from django.db import transaction

from apps.despesas.forms import MoedaField, campo_decimal
from apps.despesas.models import Categoria, Despesa, MovimentoSaldo, moeda_iso
from apps.viagens.forms import CamposInvalidosMixin
from apps.viagens.models import Viagem
from servicos.despesas import calcular_despesa, moeda_estrangeira
from servicos.saldos import categoria_de_encerramento, registrar_compra

from .compras import motivo_de_bloqueio, refazer_saldo
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

    def __init__(self, *args, viagem: Viagem, compra: Despesa | None = None, **kwargs):
        if compra is not None:
            atual = {
                "tipo": compra.forma_pagamento,
                "moeda": compra.moeda,
                "valor": compra.valor_original,
                "cotacao": compra.cotacao,
                "data": compra.data,
            }
            kwargs["initial"] = {**atual, **(kwargs.get("initial") or {})}
        super().__init__(*args, **kwargs)
        self.viagem = viagem
        self.compra = compra
        self._resultado = None
        if compra is not None:
            # Type and currency identify the balance, so they stay as bought; only the rest changes.
            for nome in ("tipo", "moeda"):
                self.fields[nome].widget = forms.HiddenInput()
                self.fields[nome].required = False

    def clean_tipo(self):
        return self.compra.forma_pagamento if self.compra else self.cleaned_data["tipo"]

    def clean_moeda(self):
        if self.compra:
            return self.compra.moeda
        moeda = self.cleaned_data["moeda"]
        if not moeda_estrangeira(moeda):
            raise forms.ValidationError("Informe uma moeda estrangeira; reais não têm saldo.")
        return moeda

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        if self.compra is None:
            saldo = Saldo.objects.filter(
                viagem=self.viagem, tipo=dados["tipo"], moeda=dados["moeda"]
            ).first()
            if saldo and saldo.encerrado:
                raise forms.ValidationError(
                    "Esse saldo já foi encerrado e não recebe novas compras."
                )
        self._resultado = calcular_despesa(dados["valor"], dados["moeda"], dados["cotacao"])
        if self.compra:
            motivo = motivo_de_bloqueio(self.compra)
            if motivo:
                raise forms.ValidationError(motivo)
        return dados

    @transaction.atomic
    def save(self) -> Saldo:
        return self._alterar() if self.compra else self._criar()

    def _alterar(self) -> Saldo:
        compra, resultado = self.compra, self._resultado
        compra.data = self.cleaned_data["data"]
        compra.valor_original = self.cleaned_data["valor"]
        compra.cotacao = resultado.cotacao
        compra.valor_brl = resultado.valor_brl
        compra.save()
        refazer_saldo(compra.saldo)
        return compra.saldo

    def _criar(self) -> Saldo:
        dados = self.cleaned_data
        resultado = self._resultado
        saldo, _ = Saldo.objects.get_or_create(
            viagem=self.viagem,
            tipo=dados["tipo"],
            moeda=dados["moeda"],
            defaults={"valor_restante": Decimal(0), "custo_restante": Decimal(0)},
        )
        novo = registrar_compra(saldo.estado, dados["valor"], resultado.valor_brl)
        saldo.valor_restante, saldo.custo_restante = novo.valor_restante, novo.custo_restante
        saldo.save()

        categoria, _ = Categoria.objects.get_or_create(nome=categoria_de_encerramento(saldo.tipo))
        Despesa.objects.create(
            viagem=self.viagem,
            categoria=categoria,
            descricao="Compra de moeda estrangeira não alocada",
            data=dados["data"],
            valor_original=dados["valor"],
            moeda=dados["moeda"],
            cotacao=resultado.cotacao,
            valor_brl=resultado.valor_brl,
            forma_pagamento=dados["tipo"],
            saldo=saldo,
            movimento_saldo=MovimentoSaldo.COMPRA,
        )
        return saldo

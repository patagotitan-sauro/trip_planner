from decimal import Decimal

from django import forms

from apps.viagens.forms import CamposInvalidosMixin
from apps.viagens.models import Viagem
from servicos.despesas import calcular_despesa, moeda_estrangeira, validar_forma_de_pagamento
from servicos.moeda import MOEDA_CASA

from .models import Despesa, moeda_iso


class MoedaField(forms.CharField):
    """ISO 4217 code, typed in any case."""

    def to_python(self, value):
        valor = super().to_python(value)
        return valor.strip().upper() if valor else valor


def _campo_decimal(rotulo: str, *, minimo: Decimal, mensagem: str, **extra) -> forms.DecimalField:
    return forms.DecimalField(
        label=rotulo,
        min_value=minimo,
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        error_messages={"min_value": mensagem},
        **extra,
    )


class DespesaForm(CamposInvalidosMixin, forms.ModelForm):
    moeda = MoedaField(
        label="Moeda (código ISO, por exemplo USD)",
        min_length=3,
        max_length=3,
        validators=[moeda_iso],
        initial=MOEDA_CASA,
    )
    valor_original = _campo_decimal(
        "Valor na moeda original",
        minimo=Decimal(0),
        mensagem="O valor não pode ser negativo.",
        max_digits=14,
        decimal_places=2,
    )
    cotacao = _campo_decimal(
        "Cotação (R$ por unidade da moeda; só para moeda estrangeira)",
        minimo=Decimal("0.00000001"),
        mensagem="A cotação precisa ser positiva.",
        required=False,
        max_digits=18,
        decimal_places=8,
    )

    class Meta:
        model = Despesa
        fields = [
            "situacao",
            "descricao",
            "categoria",
            "atividade",
            "data",
            "moeda",
            "valor_original",
            "cotacao",
            "forma_pagamento",
        ]
        labels = {
            "situacao": "Situação",
            "descricao": "Descrição",
            "categoria": "Categoria",
            "atividade": "Atividade do roteiro (opcional)",
            "data": "Data (opcional)",
            "forma_pagamento": "Forma de pagamento",
        }
        widgets = {"data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, viagem: Viagem, **kwargs):
        super().__init__(*args, **kwargs)
        self.viagem = viagem
        self.instance.viagem = viagem
        self.fields["atividade"].queryset = viagem.atividades.all()
        self.fields["atividade"].required = False
        self._resultado = None

    def clean(self):
        dados = super().clean()
        situacao = dados.get("situacao")
        moeda = dados.get("moeda")
        valor = dados.get("valor_original")
        if not (situacao and moeda and valor is not None):
            return dados
        forma = dados.get("forma_pagamento", "")
        cotacao = dados.get("cotacao")

        if moeda_estrangeira(moeda) and cotacao is None and "cotacao" not in self.errors:
            self.add_error("cotacao", "Informe a cotação da moeda estrangeira.")
        mensagem = validar_forma_de_pagamento(situacao, moeda, forma)
        if mensagem:
            self.add_error("forma_pagamento", mensagem)
        if self.errors:
            return dados

        # RN-12: an unchanged expense keeps the rate stored when it was recorded.
        inalterada = (
            self.instance.pk
            and moeda == self.initial.get("moeda")
            and forma == self.initial.get("forma_pagamento")
        )
        self._resultado = calcular_despesa(
            valor,
            moeda,
            cotacao,
            forma,
            self.viagem.aliquota_iof_credito,
            self.viagem.aliquota_iof_pre_pago_dinheiro,
            taxa_iof_gravada=self.instance.taxa_iof if inalterada else None,
        )
        return dados

    def save(self, commit=True):
        resultado = self._resultado
        self.instance.cotacao = resultado.cotacao
        self.instance.valor_brl = resultado.valor_brl
        self.instance.taxa_iof = resultado.taxa_iof
        self.instance.valor_iof = resultado.valor_iof
        return super().save(commit=commit)

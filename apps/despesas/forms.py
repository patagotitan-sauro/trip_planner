from decimal import Decimal

from django import forms
from django.db import transaction
from django.db.models import Q, Sum

from apps.saldos.models import Saldo
from apps.viagens.forms import CamposInvalidosMixin
from apps.viagens.models import Viagem
from servicos.despesas import calcular_despesa, moeda_estrangeira, validar_forma_de_pagamento
from servicos.moeda import MOEDA_CASA
from servicos.planejamento import validar_cancelamento
from servicos.saldos import calcular_despesa_com_saldo, disponivel, registrar_uso

from .models import Despesa, MovimentoSaldo, SituacaoDespesa, moeda_iso


class MoedaField(forms.CharField):
    """ISO 4217 code, typed in any case."""

    def to_python(self, value):
        valor = super().to_python(value)
        return valor.strip().upper() if valor else valor


def campo_decimal(rotulo: str, *, minimo: Decimal, mensagem: str, **extra) -> forms.DecimalField:
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
    valor_original = campo_decimal(
        "Valor na moeda original",
        minimo=Decimal(0),
        mensagem="O valor não pode ser negativo.",
        max_digits=14,
        decimal_places=2,
    )
    cotacao = campo_decimal(
        "Cotação (R$ por unidade da moeda; só para moeda estrangeira)",
        minimo=Decimal("0.00000001"),
        mensagem="A cotação precisa ser positiva.",
        required=False,
        max_digits=18,
        decimal_places=8,
    )
    # RN-16: only offered when the trip has a balance to pay with.
    saldo = forms.ModelChoiceField(
        label="Pagar com saldo",
        queryset=Saldo.objects.none(),
        required=False,
        empty_label="Não, usar outra forma de pagamento",
        help_text=(
            "Pago com saldo, o custo é o custo médio do saldo, sem novo IOF. "
            "Em um custo planejado, reserva o valor no saldo."
        ),
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
            "cancelavel",
            "data_limite_cancelamento",
        ]
        labels = {
            "situacao": "Situação",
            "descricao": "Descrição",
            "categoria": "Categoria",
            "atividade": "Atividade do roteiro (opcional)",
            "data": "Data (opcional)",
            "forma_pagamento": "Forma de pagamento",
            "cancelavel": "Custo cancelável (só para custo planejado)",
            "data_limite_cancelamento": "Data limite de cancelamento",
        }
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_limite_cancelamento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, viagem: Viagem, **kwargs):
        super().__init__(*args, **kwargs)
        self.viagem = viagem
        self.instance.viagem = viagem
        self.fields["atividade"].queryset = viagem.atividades.all()
        self.fields["atividade"].required = False
        self._configurar_saldo(viagem)
        self._resultado = None

    def _configurar_saldo(self, viagem: Viagem) -> None:
        abertos = Q(encerrado=False, valor_restante__gt=0) | Q(pk=self.instance.saldo_id)
        saldos = viagem.saldos.filter(abertos)
        if not saldos:
            del self.fields["saldo"]
            return
        campo = self.fields["saldo"]
        campo.queryset = saldos
        campo.label_from_instance = lambda s: f"{s} (restam {s.valor_restante:.2f} {s.moeda})"
        if self.instance.pk and self.instance.saldo_id:
            campo.initial = self.instance.saldo_id

    def _reservado_por_outros(self, saldo: Saldo) -> Decimal:
        reservas = saldo.despesas.filter(
            situacao=SituacaoDespesa.PLANEJADA, movimento_saldo=MovimentoSaldo.USO
        ).exclude(pk=self.instance.pk)
        return reservas.aggregate(total=Sum("valor_original"))["total"] or Decimal(0)

    def _calcular_com_saldo(self, saldo: Saldo, moeda: str, valor: Decimal):
        if saldo.encerrado:
            self.add_error("saldo", "Esse saldo já foi encerrado.")
        elif saldo.moeda != moeda:
            self.add_error(
                "saldo", f"Esse saldo é em {saldo.moeda}; a despesa precisa ser na mesma moeda."
            )
        elif valor > disponivel(saldo.estado, self._reservado_por_outros(saldo)):
            self.add_error("saldo", "O saldo disponível não cobre esse valor.")
        else:
            try:
                return calcular_despesa_com_saldo(saldo.estado, valor)
            except ValueError as erro:
                self.add_error("valor_original", str(erro))
        return None

    def _limpar_cancelamento(self, dados: dict, situacao: str | None) -> None:
        if situacao == SituacaoDespesa.REALIZADA:
            # Turning a planned cost into an expense drops the cancellation mark (RN-20).
            dados["cancelavel"] = False
            dados["data_limite_cancelamento"] = None
        elif situacao:
            erros = validar_cancelamento(
                situacao, dados.get("cancelavel", False), dados.get("data_limite_cancelamento")
            )
            for campo, mensagem in erros.items():
                self.add_error(campo, mensagem)

    def clean(self):
        dados = super().clean()
        situacao = dados.get("situacao")
        self._limpar_cancelamento(dados, situacao)
        moeda = dados.get("moeda")
        valor = dados.get("valor_original")
        if not (situacao and moeda and valor is not None):
            return dados
        forma = dados.get("forma_pagamento", "")
        cotacao = dados.get("cotacao")
        saldo = dados.get("saldo")
        if saldo:
            # The balance decides the payment method (RN-14).
            forma = dados["forma_pagamento"] = saldo.tipo

        if not saldo and moeda_estrangeira(moeda) and cotacao is None:
            if "cotacao" not in self.errors:
                self.add_error("cotacao", "Informe a cotação da moeda estrangeira.")
        mensagem = validar_forma_de_pagamento(situacao, moeda, forma, com_saldo=bool(saldo))
        if mensagem:
            self.add_error("forma_pagamento", mensagem)
        if self.errors:
            return dados

        if saldo:
            self._resultado = self._calcular_com_saldo(saldo, moeda, valor)
            return dados

        # RN-12: an unchanged expense keeps the rate stored when it was recorded.
        # A reservation that leaves its balance starts over with the trip's rates.
        inalterada = (
            self.instance.pk
            and not self.instance.saldo_id
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
        saldo = self.cleaned_data.get("saldo")
        self.instance.cotacao = resultado.cotacao
        self.instance.valor_brl = resultado.valor_brl
        self.instance.taxa_iof = resultado.taxa_iof
        self.instance.valor_iof = resultado.valor_iof
        self.instance.saldo = saldo
        self.instance.movimento_saldo = MovimentoSaldo.USO if saldo else ""
        with transaction.atomic():
            # A planned cost only reserves the balance; a realized one consumes it (RN-14, RN-22).
            if saldo and self.cleaned_data["situacao"] == SituacaoDespesa.REALIZADA:
                novo, _ = registrar_uso(saldo.estado, self.cleaned_data["valor_original"])
                saldo.valor_restante, saldo.custo_restante = (
                    novo.valor_restante,
                    novo.custo_restante,
                )
                saldo.save(update_fields=["valor_restante", "custo_restante"])
            return super().save(commit=commit)

from django import forms
from django.db import transaction

from servicos.viagens import (
    PLANEJAMENTO,
    STAND_BY,
    validar_datas_da_viagem,
    validar_posicao_da_atividade,
)

from .models import AtividadeRoteiro, Destino, EstadoViagem, Viagem

PAIS_PADRAO = "BR"

ESTADOS_NA_CRIACAO = [
    (EstadoViagem.PLANEJAMENTO, EstadoViagem.PLANEJAMENTO.label),
    (EstadoViagem.STAND_BY, EstadoViagem.STAND_BY.label),
]


class CamposInvalidosMixin:
    """Lets Pico style the fields that failed validation."""

    def full_clean(self):
        super().full_clean()
        for nome in self.errors:
            if nome in self.fields:
                self.fields[nome].widget.attrs["aria-invalid"] = "true"


class DestinoForm(CamposInvalidosMixin, forms.ModelForm):
    class Meta:
        model = Destino
        fields = ["pais", "cidade"]
        labels = {"pais": "País", "cidade": "Cidade"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pais"].initial = PAIS_PADRAO
        # The model keeps city optional for old imported data; new destinations always need one.
        self.fields["cidade"].required = True
        self.fields["cidade"].error_messages["required"] = "Informe a cidade."


class ViagemForm(CamposInvalidosMixin, forms.ModelForm):
    # First destination, asked only when creating; more are added on the trip page.
    pais = Destino._meta.get_field("pais").formfield(label="País", initial=PAIS_PADRAO)
    cidade = forms.CharField(
        label="Cidade",
        max_length=100,
        error_messages={"required": "Informe a cidade."},
    )
    orcamento = forms.DecimalField(
        label="Orçamento (R$)",
        required=False,
        min_value=0,
        max_digits=14,
        decimal_places=2,
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        error_messages={"min_value": "O orçamento não pode ser negativo."},
    )

    class Meta:
        model = Viagem
        fields = ["nome", "estado", "data_inicio", "data_fim", "orcamento"]
        labels = {
            "nome": "Nome",
            "estado": "Situação",
            "data_inicio": "Data de início",
            "data_fim": "Data de fim",
        }
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    field_order = ["nome", "estado", "pais", "cidade", "data_inicio", "data_fim", "orcamento"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Changing the state of an existing trip has its own screen (RF-08);
        # destinations of an existing trip are managed on its page.
        if self.instance.pk:
            del self.fields["estado"], self.fields["pais"], self.fields["cidade"]
        else:
            self.fields["estado"].choices = ESTADOS_NA_CRIACAO
            self.fields["estado"].initial = PLANEJAMENTO

    def save(self, commit=True):
        with transaction.atomic():
            viagem = super().save(commit=commit)
            if commit and "pais" in self.fields:
                Destino.objects.create(
                    viagem=viagem,
                    pais=self.cleaned_data["pais"],
                    cidade=self.cleaned_data["cidade"],
                )
        return viagem

    def clean(self):
        dados = super().clean()
        estado = self.instance.estado if self.instance.pk else dados.get("estado", STAND_BY)
        erros = validar_datas_da_viagem(estado, dados.get("data_inicio"), dados.get("data_fim"))
        for campo, mensagem in erros.items():
            self.add_error(campo, mensagem)
        return dados


class AtividadeForm(CamposInvalidosMixin, forms.ModelForm):
    class Meta:
        model = AtividadeRoteiro
        fields = ["data", "dia", "hora", "atividade", "local", "observacoes"]
        labels = {
            "data": "Data",
            "dia": "Dia (número)",
            "hora": "Hora (opcional)",
            "atividade": "Atividade",
            "local": "Local (opcional)",
            "observacoes": "Observações (opcional)",
        }
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "dia": forms.NumberInput(attrs={"min": 1}),
            "hora": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, viagem, **kwargs):
        super().__init__(*args, **kwargs)
        self.viagem = viagem
        # Stand-by trips use numbered days; the others use dates (RN-18).
        del self.fields["dia" if viagem.estado != STAND_BY else "data"]

    def clean(self):
        dados = super().clean()
        erros = validar_posicao_da_atividade(
            self.viagem.estado, dados.get("data"), dados.get("dia")
        )
        for campo, mensagem in erros.items():
            if campo not in self.errors:
                self.add_error(campo, mensagem)
        return dados

    def save(self, commit=True):
        self.instance.viagem = self.viagem
        return super().save(commit=commit)


class DatasDoPlanejamentoForm(CamposInvalidosMixin, forms.Form):
    """Dates asked when a stand-by trip goes back to planning (RN-03)."""

    data_inicio = forms.DateField(
        label="Data de início",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    data_fim = forms.DateField(
        label="Data de fim",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def clean(self):
        dados = super().clean()
        erros = validar_datas_da_viagem(
            PLANEJAMENTO, dados.get("data_inicio"), dados.get("data_fim")
        )
        for campo, mensagem in erros.items():
            if campo not in self.errors:
                self.add_error(campo, mensagem)
        return dados

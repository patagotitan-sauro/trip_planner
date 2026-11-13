from django import forms
from django.db import transaction

from servicos.viagens import PLANEJAMENTO, STAND_BY, validar_datas_da_viagem

from .models import Destino, EstadoViagem, Viagem

PAIS_PADRAO = "BR"

ESTADOS_NA_CRIACAO = [
    (EstadoViagem.PLANEJAMENTO, EstadoViagem.PLANEJAMENTO.label),
    (EstadoViagem.STAND_BY, EstadoViagem.STAND_BY.label),
]


class DestinoForm(forms.ModelForm):
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

    def full_clean(self):
        super().full_clean()
        for nome in self.errors:
            if nome in self.fields:
                self.fields[nome].widget.attrs["aria-invalid"] = "true"


class ViagemForm(forms.ModelForm):
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

    def full_clean(self):
        super().full_clean()
        for nome in self.errors:
            if nome in self.fields:
                self.fields[nome].widget.attrs["aria-invalid"] = "true"

from django.db import models
from django.db.models import F, Q
from django_countries.fields import CountryField


class EstadoViagem(models.TextChoices):
    STAND_BY = "stand_by", "Stand-by"
    PLANEJAMENTO = "planejamento", "Em planejamento"
    CONCLUIDA = "concluida", "Concluída"


class Viagem(models.Model):
    nome = models.CharField(max_length=100)
    estado = models.CharField(
        max_length=20, choices=EstadoViagem.choices, default=EstadoViagem.PLANEJAMENTO
    )
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    orcamento = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["data_fim", "nome"]
        constraints = [
            models.CheckConstraint(
                condition=Q(estado=EstadoViagem.STAND_BY)
                | Q(data_inicio__isnull=False, data_fim__isnull=False),
                name="viagem_datas_obrigatorias_fora_do_stand_by",
            ),
            models.CheckConstraint(
                condition=Q(data_inicio__isnull=True)
                | Q(data_fim__isnull=True)
                | Q(data_fim__gte=F("data_inicio")),
                name="viagem_fim_nao_antes_do_inicio",
            ),
            models.CheckConstraint(
                condition=Q(orcamento__isnull=True) | Q(orcamento__gte=0),
                name="viagem_orcamento_nao_negativo",
            ),
        ]

    def __str__(self) -> str:
        return self.nome


class Destino(models.Model):
    viagem = models.ForeignKey(Viagem, on_delete=models.CASCADE, related_name="destinos")
    pais = CountryField()
    cidade = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return self.cidade or str(self.pais)


class AtividadeRoteiro(models.Model):
    viagem = models.ForeignKey(Viagem, on_delete=models.CASCADE, related_name="atividades")
    data = models.DateField(null=True, blank=True)
    dia = models.PositiveSmallIntegerField(null=True, blank=True)  # numerado, usado em stand-by
    hora = models.TimeField(null=True, blank=True)
    atividade = models.CharField(max_length=200)
    local = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["data", "dia", "hora"]

    def __str__(self) -> str:
        return self.atividade

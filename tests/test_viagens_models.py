from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.viagens.models import Destino, EstadoViagem, Viagem


@pytest.mark.django_db
def test_stand_by_trip_can_be_saved_without_dates() -> None:
    viagem = Viagem.objects.create(nome="Japão", estado=EstadoViagem.STAND_BY)

    assert viagem.data_inicio is None
    assert viagem.data_fim is None


@pytest.mark.django_db
def test_planned_trip_requires_start_and_end_dates() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Viagem.objects.create(nome="Manaus", estado=EstadoViagem.PLANEJAMENTO)


@pytest.mark.django_db
def test_end_date_before_start_date_is_rejected() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Viagem.objects.create(
            nome="Manaus",
            data_inicio=date(2027, 1, 14),
            data_fim=date(2027, 1, 4),
        )


@pytest.mark.django_db
def test_budget_cannot_be_negative() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Viagem.objects.create(
            nome="Cape Town",
            estado=EstadoViagem.STAND_BY,
            orcamento=Decimal("-1.00"),
        )


@pytest.mark.django_db
def test_destination_stores_country_code_and_optional_city() -> None:
    viagem = Viagem.objects.create(nome="Argentina", estado=EstadoViagem.STAND_BY)

    com_cidade = Destino.objects.create(viagem=viagem, pais="AR", cidade="Buenos Aires")
    sem_cidade = Destino.objects.create(viagem=viagem, pais="BR")

    assert com_cidade.pais.code == "AR"
    assert sem_cidade.cidade == ""

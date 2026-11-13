from django.urls import reverse

from apps.viagens.models import Destino, EstadoViagem, Viagem


def _viagem(nome="Sul", **extra):
    return Viagem.objects.create(nome=nome, estado=EstadoViagem.STAND_BY, **extra)


def test_detail_shows_trip_and_destinations_with_country_names(logado):
    viagem = _viagem()
    Destino.objects.create(viagem=viagem, pais="AR", cidade="Buenos Aires")
    Destino.objects.create(viagem=viagem, pais="JP")

    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert "Sul" in html
    assert "Buenos Aires, Argentina" in html
    assert "Japão" in html
    assert "<mark>Internacional</mark>" in html


def test_detail_without_destinations_says_so_and_has_no_label(logado):
    viagem = _viagem()

    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert "Nenhum destino ainda." in html
    assert "<mark>" not in html


def test_detail_of_unknown_trip_returns_404(logado):
    assert logado.get(reverse("viagens:detalhe", args=[999])).status_code == 404


def test_add_destination_with_country_and_city(logado):
    viagem = _viagem()

    response = logado.post(
        reverse("viagens:detalhe", args=[viagem.pk]), {"pais": "PT", "cidade": "Lisboa"}
    )

    assert response.status_code == 302
    destino = viagem.destinos.get()
    assert (destino.pais.code, destino.cidade) == ("PT", "Lisboa")


def test_add_destination_without_city(logado):
    viagem = _viagem()

    logado.post(reverse("viagens:detalhe", args=[viagem.pk]), {"pais": "JP", "cidade": ""})

    assert viagem.destinos.get().cidade == ""


def test_add_destination_without_country_shows_error_and_saves_nothing(logado):
    viagem = _viagem()

    response = logado.post(
        reverse("viagens:detalhe", args=[viagem.pk]), {"pais": "", "cidade": "X"}
    )

    assert response.status_code == 200
    assert "obrigatório" in response.content.decode()
    assert not viagem.destinos.exists()


def test_add_destination_with_invalid_country_code_is_rejected(logado):
    viagem = _viagem()

    response = logado.post(reverse("viagens:detalhe", args=[viagem.pk]), {"pais": "XX"})

    assert response.status_code == 200
    assert not viagem.destinos.exists()


def test_country_options_are_in_portuguese(logado):
    viagem = _viagem()

    html = logado.get(reverse("viagens:detalhe", args=[viagem.pk])).content.decode()

    assert ">Brasil<" in html
    assert ">África do Sul<" in html


def test_remove_destination_deletes_only_that_one(logado):
    viagem = _viagem()
    alvo = Destino.objects.create(viagem=viagem, pais="AR")
    Destino.objects.create(viagem=viagem, pais="JP")

    response = logado.post(reverse("viagens:remover_destino", args=[viagem.pk, alvo.pk]))

    assert response.status_code == 302
    assert [destino.pais.code for destino in viagem.destinos.all()] == ["JP"]


def test_remove_destination_requires_post(logado):
    viagem = _viagem()
    destino = Destino.objects.create(viagem=viagem, pais="AR")

    response = logado.get(reverse("viagens:remover_destino", args=[viagem.pk, destino.pk]))

    assert response.status_code == 405
    assert viagem.destinos.exists()


def test_cannot_remove_a_destination_through_another_trip(logado):
    dono = _viagem("Dono")
    outra = _viagem("Outra")
    destino = Destino.objects.create(viagem=dono, pais="AR")

    response = logado.post(reverse("viagens:remover_destino", args=[outra.pk, destino.pk]))

    assert response.status_code == 404
    assert dono.destinos.exists()


def test_trip_card_links_to_the_detail_page(logado):
    viagem = _viagem()

    html = logado.get(reverse("viagens:inicio")).content.decode()

    assert reverse("viagens:detalhe", args=[viagem.pk]) in html

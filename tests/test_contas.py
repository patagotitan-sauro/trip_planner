from collections.abc import Iterator

import pytest
from django.contrib.auth import get_user_model
from django.urls import URLPattern, URLResolver, get_resolver, reverse

LOGIN_URL = "/contas/entrar/"
PUBLIC_ROUTES = {"contas/entrar/"}


def _routes(patterns: list, prefix: str = "") -> Iterator[tuple[str, URLPattern]]:
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            # The admin has its own login page.
            if route != "admin/":
                yield from _routes(pattern.url_patterns, route)
        else:
            yield route, pattern


def test_only_the_login_page_is_public():
    routes = list(_routes(get_resolver().url_patterns))
    public = {
        route
        for route, pattern in routes
        if getattr(pattern.callback, "login_required", True) is False
    }

    assert public == PUBLIC_ROUTES


@pytest.mark.django_db
def test_every_url_without_login_redirects_to_login(client):
    urls = [
        "/" + route
        for route, _ in _routes(get_resolver().url_patterns)
        if "<" not in route and route not in PUBLIC_ROUTES
    ]

    assert urls
    for url in urls:
        response = client.get(url)
        assert response.status_code == 302, url
        assert response.url == f"{LOGIN_URL}?next={url}", url


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("ana", password="senha-forte-123")  # noqa: S106


def test_login_page_renders_in_portuguese(client):
    response = client.get(reverse("contas:login"))

    assert response.status_code == 200
    assert "Entrar" in response.content.decode()


def test_login_with_valid_credentials_opens_the_home_page(client, user):
    response = client.post(
        reverse("contas:login"), {"username": "ana", "password": "senha-forte-123"}
    )

    assert response.status_code == 302
    assert response.url == reverse("viagens:inicio")
    assert client.get(reverse("viagens:inicio")).status_code == 200


def test_login_with_wrong_password_shows_an_error_and_stays_logged_out(client, user):
    response = client.post(reverse("contas:login"), {"username": "ana", "password": "errada"})

    assert response.status_code == 200
    assert "Usuário ou senha incorretos" in response.content.decode()
    assert client.get(reverse("viagens:inicio")).status_code == 302


def test_logout_requires_post_and_ends_the_session(client, user):
    client.force_login(user)

    assert client.get(reverse("contas:logout")).status_code == 405

    response = client.post(reverse("contas:logout"))

    assert response.status_code == 302
    assert response.url == reverse("contas:login")
    assert client.get(reverse("viagens:inicio")).status_code == 302

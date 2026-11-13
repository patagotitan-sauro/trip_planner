import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def logado(client, db):
    usuario = get_user_model().objects.create_user("ana", password="senha-forte-123")  # noqa: S106
    client.force_login(usuario)
    return client


@pytest.fixture(autouse=True)
def _plain_static_storage(settings):
    # The manifest storage needs collectstatic output, which tests do not run.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

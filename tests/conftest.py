from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from servicos.integracoes.cotacao import CotacaoSugerida


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


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    def bloqueado(*args, **kwargs):
        raise AssertionError("Tests must not call the network; inject a fake opener or provider.")

    monkeypatch.setattr("urllib.request.urlopen", bloqueado)


class ProvedorDeCotacaoFalso:
    def __init__(self):
        self.valor = Decimal("5.6628")
        self.dia = date(2026, 11, 13)
        self.erro: Exception | None = None
        self.chamadas: list[tuple[str, date | None]] = []

    def cotacao_em_brl(self, moeda, data):
        self.chamadas.append((moeda, data))
        if self.erro:
            raise self.erro
        return CotacaoSugerida(self.valor, self.dia)


@pytest.fixture
def provedor_de_cotacao(monkeypatch):
    provedor = ProvedorDeCotacaoFalso()
    monkeypatch.setattr("apps.viagens.cotacao.provedor_de_cotacao", lambda: provedor)
    return provedor

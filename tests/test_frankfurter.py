import json
from datetime import date
from decimal import Decimal
from urllib.error import HTTPError, URLError

import pytest

from servicos.integracoes.cotacao import CotacaoIndisponivel
from servicos.integracoes.frankfurter import ClienteFrankfurter


class RespostaFalsa:
    def __init__(self, corpo: bytes):
        self.corpo = corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limite: int = -1) -> bytes:
        return self.corpo[:limite]


class AberturaFalsa:
    def __init__(self, corpo: bytes | None = None, erro: Exception | None = None):
        self.corpo = corpo
        self.erro = erro
        self.pedidos: list[tuple[str, float]] = []

    def __call__(self, pedido, timeout):
        self.pedidos.append((pedido.full_url, timeout))
        if self.erro:
            raise self.erro
        return RespostaFalsa(self.corpo)


def _corpo(rate, dia="2026-11-16"):
    return json.dumps({"date": dia, "base": "USD", "quote": "BRL", "rate": rate}).encode()


def _cliente(abertura, **extra):
    return ClienteFrankfurter(abrir=abertura, **extra)


def _http(codigo):
    return HTTPError("https://api.frankfurter.dev", codigo, "erro", {}, None)


def test_latest_rate_is_requested_without_a_date():
    abertura = AberturaFalsa(_corpo(5.6628))

    sugestao = _cliente(abertura).cotacao_em_brl("USD", None)

    assert abertura.pedidos == [("https://api.frankfurter.dev/v2/rate/usd/brl", 5.0)]
    assert sugestao.valor == Decimal("5.6628")
    assert sugestao.data == date(2026, 11, 16)


def test_dated_rate_is_requested_with_the_date_and_reports_the_provider_day():
    abertura = AberturaFalsa(_corpo(5.6385, dia="2026-11-13"))

    sugestao = _cliente(abertura).cotacao_em_brl("EUR", date(2026, 11, 14))

    assert abertura.pedidos[0][0] == "https://api.frankfurter.dev/v2/rate/eur/brl?date=2026-11-14"
    assert sugestao.data == date(2026, 11, 13)


def test_rate_is_read_as_decimal_and_rounded_half_up_to_eight_places():
    abertura = AberturaFalsa(b'{"date":"2026-11-16","rate":0.123456785}')

    sugestao = _cliente(abertura).cotacao_em_brl("ARS", None)

    assert sugestao.valor == Decimal("0.12345679")
    assert isinstance(sugestao.valor, Decimal)


def test_integer_rate_is_accepted():
    abertura = AberturaFalsa(b'{"date":"2026-11-16","rate":6}')

    assert _cliente(abertura).cotacao_em_brl("CHF", None).valor == Decimal(6)


def test_timeout_is_configurable():
    abertura = AberturaFalsa(_corpo(5.6))

    _cliente(abertura, timeout=2.5).cotacao_em_brl("USD", None)

    assert abertura.pedidos[0][1] == 2.5


@pytest.mark.parametrize(
    ("erro", "trecho"),
    [
        (_http(404), "não tem cotação"),
        (_http(422), "não reconhece essa moeda"),
        (_http(400), "não reconhece essa moeda"),
        (_http(500), "indisponível"),
        (URLError("sem rede"), "Não foi possível consultar"),
        (TimeoutError(), "Não foi possível consultar"),
    ],
)
def test_service_failures_become_a_message_for_the_user(erro, trecho):
    with pytest.raises(CotacaoIndisponivel, match=trecho) as capturado:
        _cliente(AberturaFalsa(erro=erro)).cotacao_em_brl("USD", None)

    assert "manualmente" in str(capturado.value)


@pytest.mark.parametrize(
    "corpo",
    [
        b"nao e json",
        b"[]",
        b'{"date":"2026-11-16"}',
        b'{"rate":5.6}',
        b'{"date":"ontem","rate":5.6}',
        b'{"date":"2026-11-16","rate":"5.6"}',
        b'{"date":"2026-11-16","rate":true}',
        b'{"date":"2026-11-16","rate":null}',
        b'{"date":"2026-11-16","rate":0}',
        b'{"date":"2026-11-16","rate":-1.5}',
        b'{"date":"2026-11-16","rate":0.000000001}',
    ],
)
def test_unexpected_responses_are_refused(corpo):
    with pytest.raises(CotacaoIndisponivel, match="Resposta inesperada"):
        _cliente(AberturaFalsa(corpo)).cotacao_em_brl("USD", None)


@pytest.mark.parametrize("moeda", ["", "US", "usd", "USD/../x", "U$D"])
def test_currency_code_is_validated_before_building_the_url(moeda):
    abertura = AberturaFalsa(_corpo(5.6))

    with pytest.raises(CotacaoIndisponivel):
        _cliente(abertura).cotacao_em_brl(moeda, None)

    assert abertura.pedidos == []


@pytest.mark.parametrize("url", ["http://api.frankfurter.dev", "file:///etc/passwd", ""])
def test_base_url_must_use_https(url):
    with pytest.raises(ValueError, match="https"):
        ClienteFrankfurter(url_base=url)


def test_tests_cannot_reach_the_real_network():
    with pytest.raises(AssertionError, match="network"):
        ClienteFrankfurter().cotacao_em_brl("USD", None)

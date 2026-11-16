from datetime import date
from decimal import Decimal

import pytest

from servicos import cotacao
from servicos.integracoes.cotacao import CotacaoIndisponivel, CotacaoSugerida

HOJE = date(2026, 11, 16)


class ProvedorFalso:
    def __init__(self, valor: Decimal = Decimal("5.6628"), erro: Exception | None = None):
        self.valor = valor
        self.erro = erro
        self.chamadas: list[tuple[str, date | None]] = []

    def cotacao_em_brl(self, moeda: str, data: date | None) -> CotacaoSugerida:
        self.chamadas.append((moeda, data))
        if self.erro:
            raise self.erro
        return CotacaoSugerida(self.valor, data or HOJE)


@pytest.mark.parametrize(
    ("data", "esperada"),
    [
        (None, None),
        (date(2026, 11, 15), date(2026, 11, 15)),
        (HOJE, HOJE),
        (date(2026, 11, 17), None),
    ],
)
def test_query_date_is_the_expense_day_unless_missing_or_in_the_future(data, esperada):
    assert cotacao.data_da_consulta(data, HOJE) == esperada


def test_suggestion_asks_the_provider_for_the_expense_day():
    provedor = ProvedorFalso()

    sugestao = cotacao.sugerir_cotacao(provedor, "USD", date(2026, 11, 10), HOJE)

    assert provedor.chamadas == [("USD", date(2026, 11, 10))]
    assert sugestao.valor == Decimal("5.6628")


def test_suggestion_for_a_future_date_asks_for_the_latest_rate():
    provedor = ProvedorFalso()

    cotacao.sugerir_cotacao(provedor, "USD", date(2027, 1, 1), HOJE)

    assert provedor.chamadas == [("USD", None)]


def test_currency_code_is_normalized_to_upper_case():
    provedor = ProvedorFalso()

    cotacao.sugerir_cotacao(provedor, " usd ", None, HOJE)

    assert provedor.chamadas == [("USD", None)]


@pytest.mark.parametrize("moeda", [None, "", "US", "USDX", "12A", "U$D"])
def test_invalid_currency_code_is_refused_without_calling_the_provider(moeda):
    provedor = ProvedorFalso()

    with pytest.raises(CotacaoIndisponivel, match="três letras"):
        cotacao.sugerir_cotacao(provedor, moeda, None, HOJE)

    assert provedor.chamadas == []


def test_reais_need_no_rate_and_the_provider_is_not_called():
    provedor = ProvedorFalso()

    with pytest.raises(CotacaoIndisponivel, match="Reais"):
        cotacao.sugerir_cotacao(provedor, "brl", None, HOJE)

    assert provedor.chamadas == []


def test_provider_failure_reaches_the_caller():
    provedor = ProvedorFalso(erro=CotacaoIndisponivel("Serviço fora do ar."))

    with pytest.raises(CotacaoIndisponivel, match="fora do ar"):
        cotacao.sugerir_cotacao(provedor, "USD", None, HOJE)

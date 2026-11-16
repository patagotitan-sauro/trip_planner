from datetime import date

from servicos.despesas import moeda_estrangeira
from servicos.integracoes.cotacao import (
    CODIGO_ISO,
    CotacaoIndisponivel,
    CotacaoSugerida,
    ProvedorDeCotacao,
)


def data_da_consulta(data: date | None, hoje: date) -> date | None:
    """RN-08: the rate of the expense day; a missing or future date asks for the latest."""
    return data if data is not None and data <= hoje else None


def sugerir_cotacao(
    provedor: ProvedorDeCotacao, moeda: str | None, data: date | None, hoje: date
) -> CotacaoSugerida:
    """RN-08: suggests the BRL rate of a foreign currency; the user may still change it."""
    codigo = (moeda or "").strip().upper()
    if not CODIGO_ISO.fullmatch(codigo):
        raise CotacaoIndisponivel("Informe a moeda com o código ISO de três letras.")
    if not moeda_estrangeira(codigo):
        raise CotacaoIndisponivel("Reais não precisam de cotação.")
    return provedor.cotacao_em_brl(codigo, data_da_consulta(data, hoje))

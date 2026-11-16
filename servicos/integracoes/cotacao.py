from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class CotacaoSugerida:
    valor: Decimal  # BRL per unit of the foreign currency
    data: date  # day the provider's rate refers to


class CotacaoIndisponivel(Exception):
    """A rate cannot be suggested; the message is meant for the user."""


class ProvedorDeCotacao(Protocol):
    def cotacao_em_brl(self, moeda: str, data: date | None) -> CotacaoSugerida:
        """Rate for `moeda` on `data`, or the latest one when `data` is None."""
        ...

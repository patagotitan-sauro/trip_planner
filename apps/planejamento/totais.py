from dataclasses import dataclass
from decimal import Decimal

from apps.despesas.models import SituacaoDespesa
from apps.viagens.models import EstadoViagem, Viagem
from servicos.planejamento import total_da_viagem, valor_restante


def total_planejado(viagem: Viagem) -> Decimal:
    """Planned total in BRL; prefetch `despesas` when calling this for many trips."""
    return total_da_viagem(
        d for d in viagem.despesas.all() if d.situacao == SituacaoDespesa.PLANEJADA
    )


def total_realizado(viagem: Viagem) -> Decimal:
    """Realized total in BRL; prefetch `despesas` when calling this for many trips."""
    return total_da_viagem(
        d for d in viagem.despesas.all() if d.situacao == SituacaoDespesa.REALIZADA
    )


def total_global(viagem: Viagem) -> Decimal:
    """Realized plus planned total in BRL; purchases and loads stay out of both (RN-14)."""
    return total_realizado(viagem) + total_planejado(viagem)


@dataclass(frozen=True)
class Orcamento:
    planejado: Decimal
    restante: Decimal | None  # None when the trip has no budget (RN-19)

    @property
    def excesso(self) -> Decimal | None:
        return -self.restante if self.restante is not None and self.restante < 0 else None


def orcamento_da_viagem(viagem: Viagem) -> Orcamento:
    planejado = total_planejado(viagem)
    return Orcamento(planejado, valor_restante(viagem.orcamento, planejado))


def orcamento_a_mostrar(viagem: Viagem) -> Orcamento | None:
    """RN-19: only trips with a budget; a completed trip no longer plans against it."""
    if viagem.orcamento is None or viagem.estado == EstadoViagem.CONCLUIDA:
        return None
    return orcamento_da_viagem(viagem)

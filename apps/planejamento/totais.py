from decimal import Decimal

from apps.despesas.models import SituacaoDespesa
from apps.viagens.models import Viagem
from servicos.planejamento import total_da_viagem


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

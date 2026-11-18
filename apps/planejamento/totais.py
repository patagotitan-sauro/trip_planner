from decimal import Decimal

from apps.viagens.models import Viagem
from servicos.planejamento import total_da_viagem


def total_gasto(viagem: Viagem) -> Decimal:
    """Total in BRL, each balance purchase counted once (RN-14); prefetch `despesas` for many."""
    return total_da_viagem(list(viagem.despesas.all()))

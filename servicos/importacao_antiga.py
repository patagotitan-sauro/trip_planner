from datetime import date
from decimal import Decimal

MOEDA_CASA = "BRL"

DESTINOS: dict[str, tuple[str, str]] = {
    "Cape Town (South Africa)": ("ZA", "Cape Town"),
    "Buenos Aires (Argentina)": ("AR", "Buenos Aires"),
    "Porto Alegre (Brasil)": ("BR", "Porto Alegre"),
    "Manaus (Rio Negro)": ("BR", "Manaus"),
    "Japão": ("JP", ""),
    "Floripa - Natal": ("BR", "Florianópolis"),
}


def estado_da_viagem(congelada: bool, data_fim: date, hoje: date) -> str:
    if congelada:
        return "stand_by"
    if data_fim < hoje:
        return "concluida"
    return "planejamento"


def destino_da_viagem(texto: str) -> tuple[str, str]:
    if texto not in DESTINOS:
        raise ValueError(f"Destino sem mapeamento de país e cidade: {texto}")
    return DESTINOS[texto]


def taxa_da_despesa(
    moeda: str,
    status_antigo: str,
    taxa_antiga: Decimal | None,
    taxa_planejada: Decimal | None,
) -> Decimal:
    if moeda == MOEDA_CASA:
        return Decimal(1)
    if status_antigo == "actual":
        if taxa_antiga is None:
            raise ValueError(f"Despesa realizada em {moeda} sem taxa de câmbio.")
        return taxa_antiga
    if taxa_planejada is None:
        raise ValueError(f"Despesa planejada em {moeda} sem taxa compartilhada.")
    return taxa_planejada

from datetime import date

DESTINOS: dict[str, tuple[str, str]] = {
    "Cape Town (South Africa)": ("ZA", "Cape Town"),
    "Buenos Aires (Argentina)": ("AR", "Buenos Aires"),
    "Porto Alegre (Brasil)": ("BR", "Porto Alegre"),
    "Manaus (Rio Negro)": ("BR", "Manaus"),
    "Japão": ("JP", ""),
    "Floripa - Natal": ("BR", "Floripa - Natal"),
}

SITUACOES_DESPESA = {"actual": "realizada", "planned": "planejada"}


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


def situacao_da_despesa(status_antigo: str) -> str:
    if status_antigo not in SITUACOES_DESPESA:
        raise ValueError(f"Status de despesa desconhecido: {status_antigo}")
    return SITUACOES_DESPESA[status_antigo]

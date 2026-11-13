from collections.abc import Iterable

PAIS_CASA = "BR"


def classificar_viagem(codigos_paises: Iterable[str]) -> str:
    """Regra RN-02: internacional se algum destino não for do Brasil."""
    codigos = list(codigos_paises)
    if not codigos:
        raise ValueError("Viagem sem destinos não pode ser classificada.")
    return "internacional" if any(codigo != PAIS_CASA for codigo in codigos) else "nacional"

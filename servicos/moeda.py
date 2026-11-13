from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
CASAS_COTACAO = Decimal("0.00000001")


def cotacao_brl(unidades_por_real: Decimal) -> Decimal:
    """Converte unidades da moeda por 1 BRL (taxa antiga) em BRL por unidade (cotação)."""
    _exige_taxa_positiva(unidades_por_real)
    return (Decimal(1) / unidades_por_real).quantize(CASAS_COTACAO, rounding=ROUND_HALF_UP)


def valor_em_brl(valor: Decimal, unidades_por_real: Decimal) -> Decimal:
    _exige_taxa_positiva(unidades_por_real)
    return (valor / unidades_por_real).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _exige_taxa_positiva(taxa: Decimal) -> None:
    if taxa <= 0:
        raise ValueError("A taxa de câmbio precisa ser positiva.")

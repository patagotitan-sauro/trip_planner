from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

STAND_BY = "stand_by"
PLANEJAMENTO = "planejamento"
CONCLUIDA = "concluida"


class ComEstadoEFim(Protocol):
    estado: str
    data_fim: date | None


@dataclass
class GruposDeViagens[T]:
    stand_by: list[T] = field(default_factory=list)
    planejamento: list[T] = field(default_factory=list)
    concluidas_por_ano: dict[int, list[T]] = field(default_factory=dict)


def agrupar_viagens[T: ComEstadoEFim](viagens: list[T]) -> GruposDeViagens[T]:
    """RN-18 e RN-23: concluídas agrupadas pelo ano da data de fim, anos recentes primeiro."""
    grupos: GruposDeViagens[T] = GruposDeViagens()
    por_ano: dict[int, list[T]] = {}
    for viagem in viagens:
        if viagem.estado == STAND_BY:
            grupos.stand_by.append(viagem)
        elif viagem.estado == PLANEJAMENTO:
            grupos.planejamento.append(viagem)
        elif viagem.estado == CONCLUIDA:
            if viagem.data_fim is None:
                raise ValueError("Viagem concluída sem data de fim não pode ser agrupada por ano.")
            por_ano.setdefault(viagem.data_fim.year, []).append(viagem)
        else:
            raise ValueError(f"Estado de viagem desconhecido: {viagem.estado}")
    grupos.concluidas_por_ano = dict(sorted(por_ano.items(), reverse=True))
    return grupos


def validar_datas_da_viagem(
    estado: str, data_inicio: date | None, data_fim: date | None
) -> dict[str, str]:
    """RN-03: datas obrigatórias fora do stand-by; o fim não pode ser anterior ao início."""
    erros: dict[str, str] = {}
    if estado != STAND_BY:
        if data_inicio is None:
            erros["data_inicio"] = "Informe a data de início."
        if data_fim is None:
            erros["data_fim"] = "Informe a data de fim."
    if data_inicio and data_fim and data_fim < data_inicio:
        erros["data_fim"] = "A data de fim não pode ser anterior à data de início."
    return erros


def validar_posicao_da_atividade(estado: str, data: date | None, dia: int | None) -> dict[str, str]:
    """RN-18: o roteiro usa dia numerado em stand-by e data nos demais estados."""
    if estado == STAND_BY:
        if dia is None:
            return {"dia": "Informe o número do dia."}
        if dia < 1:
            return {"dia": "O número do dia deve ser 1 ou maior."}
    elif data is None:
        return {"data": "Informe a data."}
    return {}

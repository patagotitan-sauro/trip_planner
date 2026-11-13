from dataclasses import dataclass, field
from datetime import date, time
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
    """RN-18, RN-23: completed trips grouped by end-date year, newest year first."""
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
    """RN-03: dates are required outside stand-by; the end cannot precede the start."""
    erros: dict[str, str] = {}
    if estado != STAND_BY:
        if data_inicio is None:
            erros["data_inicio"] = "Informe a data de início."
        if data_fim is None:
            erros["data_fim"] = "Informe a data de fim."
    if data_inicio and data_fim and data_fim < data_inicio:
        erros["data_fim"] = "A data de fim não pode ser anterior à data de início."
    return erros


def pode_excluir_viagem(estado: str) -> bool:
    """RN-06: completed trips stay in the history; the others can be deleted."""
    return estado in (STAND_BY, PLANEJAMENTO)


def validar_posicao_da_atividade(estado: str, data: date | None, dia: int | None) -> dict[str, str]:
    """RN-18: the itinerary uses a numbered day in stand-by and a date otherwise."""
    if estado == STAND_BY:
        if dia is None:
            return {"dia": "Informe o número do dia."}
        if dia < 1:
            return {"dia": "O número do dia deve ser 1 ou maior."}
    elif data is None:
        return {"data": "Informe a data."}
    return {}


class ComPosicaoNoRoteiro(Protocol):
    data: date | None
    dia: int | None
    hora: time | None


@dataclass
class GrupoDoRoteiro[T]:
    chave: date | int | None  # date, or day number in stand-by; None when missing
    atividades: list[T]


def agrupar_roteiro[T: ComPosicaoNoRoteiro](
    atividades: list[T], estado: str
) -> list[GrupoDoRoteiro[T]]:
    """RN-18: group by day number in stand-by and by date otherwise; items without it go last."""
    por_chave: dict[date | int | None, list[T]] = {}
    for atividade in atividades:
        chave = atividade.dia if estado == STAND_BY else atividade.data
        por_chave.setdefault(chave, []).append(atividade)

    chaves = sorted(chave for chave in por_chave if chave is not None)
    if None in por_chave:
        chaves.append(None)
    return [
        GrupoDoRoteiro(
            chave,
            # sorted() is stable, so activities at the same time keep their input order.
            sorted(por_chave[chave], key=lambda a: (a.hora is None, a.hora or time.min)),
        )
        for chave in chaves
    ]

import sqlite3
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.despesas.models import Categoria, Despesa
from apps.viagens.models import AtividadeRoteiro, Destino, Viagem
from servicos import importacao_antiga
from servicos.moeda import cotacao_brl, valor_em_brl

# Despesa sem moeda própria usa a moeda da viagem.
CONSULTA_DESPESAS = """
    SELECT e.id, e.trip_id, e.category_id, e.description, e.amount, e.status,
           e.rate_to_home, COALESCE(moeda_despesa.code, moeda_viagem.code)
    FROM expenses_expense e
    JOIN trips_trip t ON t.id = e.trip_id
    JOIN currencies_currency moeda_viagem ON moeda_viagem.id = t.currency_id
    LEFT JOIN currencies_currency moeda_despesa ON moeda_despesa.id = e.currency_id
    ORDER BY e.id
"""


class Command(BaseCommand):
    help = "Importa o db.sqlite3 antigo (somente leitura) para os modelos novos."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("origem", type=Path, help="Caminho do db.sqlite3 antigo.")

    def handle(self, *args: Any, **options: Any) -> None:
        origem: Path = options["origem"]
        if not origem.is_file():
            raise CommandError(f"Arquivo não encontrado: {origem}")
        if Viagem.objects.exists():
            raise CommandError("O banco de destino já tem viagens. Importação cancelada.")

        conexao = sqlite3.connect(f"{origem.resolve().as_uri()}?mode=ro", uri=True)
        try:
            with transaction.atomic():
                contagens = _importar(conexao, timezone.localdate())
        except ValueError as erro:
            raise CommandError(str(erro)) from erro
        finally:
            conexao.close()

        self.stdout.write(
            f"Importado: {contagens['viagens']} viagens, {contagens['despesas']} despesas, "
            f"{contagens['atividades']} atividades e {contagens['categorias']} categorias."
        )


def _importar(conexao: sqlite3.Connection, hoje: date) -> dict[str, int]:
    viagens = _importar_viagens(conexao, hoje)
    categorias = _importar_categorias(conexao)
    despesas = _importar_despesas(conexao, viagens, categorias)
    atividades = _importar_atividades(conexao, viagens, despesas)
    return {
        "viagens": len(viagens),
        "categorias": len(categorias),
        "despesas": len(despesas),
        "atividades": atividades,
    }


def _importar_viagens(conexao: sqlite3.Connection, hoje: date) -> dict[int, Viagem]:
    viagens: dict[int, Viagem] = {}
    linhas = conexao.execute(
        "SELECT id, destination, start_date, end_date, is_frozen FROM trips_trip ORDER BY id"
    ).fetchall()
    for id_antigo, destino, inicio, fim, congelada in linhas:
        pais, cidade = importacao_antiga.destino_da_viagem(destino)
        data_fim = date.fromisoformat(fim)
        viagem = Viagem.objects.create(
            nome=destino,
            estado=importacao_antiga.estado_da_viagem(bool(congelada), data_fim, hoje),
            data_inicio=date.fromisoformat(inicio) if inicio else None,
            data_fim=data_fim,
        )
        Destino.objects.create(viagem=viagem, pais=pais, cidade=cidade)
        viagens[id_antigo] = viagem
    return viagens


def _importar_categorias(conexao: sqlite3.Connection) -> dict[int, Categoria]:
    linhas = conexao.execute("SELECT id, name FROM expenses_category ORDER BY id").fetchall()
    return {id_antigo: Categoria.objects.create(nome=nome) for id_antigo, nome in linhas}


def _importar_despesas(
    conexao: sqlite3.Connection,
    viagens: dict[int, Viagem],
    categorias: dict[int, Categoria],
) -> dict[int, Despesa]:
    taxas_planejadas = _taxas_planejadas(conexao)
    despesas: dict[int, Despesa] = {}
    for (
        id_antigo,
        id_viagem,
        id_categoria,
        descricao,
        valor,
        status,
        taxa_antiga,
        moeda,
    ) in conexao.execute(CONSULTA_DESPESAS).fetchall():
        valor_original = Decimal(str(valor))
        taxa_antiga_decimal = None if taxa_antiga is None else Decimal(str(taxa_antiga))
        try:
            taxa = importacao_antiga.taxa_da_despesa(
                moeda, status, taxa_antiga_decimal, taxas_planejadas.get((id_viagem, moeda))
            )
        except ValueError as erro:
            raise ValueError(f"{erro} Viagem {id_viagem} no banco antigo.") from erro
        despesas[id_antigo] = Despesa.objects.create(
            viagem=viagens[id_viagem],
            categoria=categorias[id_categoria],
            descricao=descricao,
            situacao=importacao_antiga.situacao_da_despesa(status),
            valor_original=valor_original,
            moeda=moeda,
            cotacao=cotacao_brl(taxa),
            valor_brl=valor_em_brl(valor_original, taxa),
        )
    return despesas


def _taxas_planejadas(conexao: sqlite3.Connection) -> dict[tuple[int, str], Decimal]:
    linhas = conexao.execute(
        """
        SELECT p.trip_id, c.code, p.rate_to_home
        FROM expenses_plannedrate p
        JOIN currencies_currency c ON c.id = p.currency_id
        """
    ).fetchall()
    return {(id_viagem, codigo): Decimal(str(taxa)) for id_viagem, codigo, taxa in linhas}


def _importar_atividades(
    conexao: sqlite3.Connection,
    viagens: dict[int, Viagem],
    despesas: dict[int, Despesa],
) -> int:
    linhas = conexao.execute(
        """
        SELECT trip_id, date, time, activity, location, notes, expense_id
        FROM itinerary_itineraryitem
        ORDER BY id
        """
    ).fetchall()
    for id_viagem, data, hora, atividade, local, notas, id_despesa in linhas:
        nova = AtividadeRoteiro.objects.create(
            viagem=viagens[id_viagem],
            data=date.fromisoformat(data),
            hora=time.fromisoformat(hora) if hora else None,
            atividade=atividade,
            local=local,
            observacoes=notas,
        )
        if id_despesa is not None:
            despesa = despesas[id_despesa]
            despesa.atividade = nova
            despesa.save(update_fields=["atividade"])
    return len(linhas)

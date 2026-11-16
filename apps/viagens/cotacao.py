from datetime import date

from django.contrib import messages
from django.http import HttpRequest
from django.utils import formats, timezone

from servicos.cotacao import sugerir_cotacao
from servicos.integracoes.cotacao import CotacaoIndisponivel, ProvedorDeCotacao
from servicos.integracoes.frankfurter import ClienteFrankfurter

PEDIDO_DE_SUGESTAO = "sugerir_cotacao"


def provedor_de_cotacao() -> ProvedorDeCotacao:
    return ClienteFrankfurter()


def pediu_sugestao(request: HttpRequest) -> bool:
    return request.method == "POST" and PEDIDO_DE_SUGESTAO in request.POST


def sugerir_no_formulario(request: HttpRequest) -> dict[str, str]:
    """RN-08: the posted values with the suggested rate filled in, to show the form again.

    Nothing is validated or saved; on failure the user's typed rate stays as it was.
    """
    dados = request.POST.dict()
    try:
        sugestao = sugerir_cotacao(
            provedor_de_cotacao(),
            dados.get("moeda"),
            _data(dados.get("data")),
            timezone.localdate(),
        )
    except CotacaoIndisponivel as erro:
        messages.error(request, str(erro))
        return dados

    texto = formats.number_format(sugestao.valor.normalize(), use_l10n=True)
    dados["cotacao"] = texto
    messages.success(
        request,
        f"Cotação sugerida de {sugestao.data:%d/%m/%Y}: R$ {texto} por {dados['moeda'].upper()}. "
        "Confira, edite se precisar e salve.",
    )
    return dados


def _data(texto: str | None) -> date | None:
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return None

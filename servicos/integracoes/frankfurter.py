import json
import urllib.request
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.error import HTTPError, URLError

from servicos.integracoes.cotacao import CODIGO_ISO, CotacaoIndisponivel, CotacaoSugerida
from servicos.moeda import CASAS_COTACAO

URL_PADRAO = "https://api.frankfurter.dev"
LIMITE_DA_RESPOSTA = 65_536

MANUAL = "Digite a cotação manualmente."


class ClienteFrankfurter:
    """Rate suggestions from api.frankfurter.dev (no key needed)."""

    def __init__(self, url_base: str = URL_PADRAO, timeout: float = 5.0, abrir=None):
        if not url_base.startswith("https://"):
            raise ValueError("O serviço de cotações precisa usar https.")
        self._url_base = url_base.rstrip("/")
        self._timeout = timeout
        self._abrir = abrir

    def cotacao_em_brl(self, moeda: str, data: date | None) -> CotacaoSugerida:
        if not CODIGO_ISO.fullmatch(moeda):
            raise CotacaoIndisponivel("Informe a moeda com o código ISO de três letras.")
        url = f"{self._url_base}/v2/rate/{moeda.lower()}/brl"
        if data is not None:
            url += f"?date={data.isoformat()}"
        return _ler_cotacao(self._baixar(url))

    def _baixar(self, url: str) -> bytes:
        pedido = urllib.request.Request(  # noqa: S310 - the constructor only allows https
            url, headers={"Accept": "application/json"}
        )
        abrir = self._abrir or urllib.request.urlopen
        try:
            with abrir(pedido, timeout=self._timeout) as resposta:
                return resposta.read(LIMITE_DA_RESPOSTA)
        except HTTPError as erro:
            raise CotacaoIndisponivel(_mensagem_do_erro_http(erro.code)) from erro
        except (URLError, OSError) as erro:
            raise CotacaoIndisponivel(
                f"Não foi possível consultar o serviço de cotações. {MANUAL}"
            ) from erro


def _mensagem_do_erro_http(codigo: int) -> str:
    if codigo == 404:
        return f"O serviço não tem cotação para essa moeda nessa data. {MANUAL}"
    if codigo in (400, 422):
        return f"O serviço de cotações não reconhece essa moeda. {MANUAL}"
    return f"O serviço de cotações está indisponível. {MANUAL}"


def _ler_cotacao(corpo: bytes) -> CotacaoSugerida:
    resposta_invalida = CotacaoIndisponivel(f"Resposta inesperada do serviço de cotações. {MANUAL}")
    try:
        # Decimals straight from the JSON text: money never goes through float.
        dados = json.loads(corpo, parse_float=Decimal)
        taxa = dados["rate"]
        if isinstance(taxa, bool) or not isinstance(taxa, int | Decimal):
            raise resposta_invalida
        valor = Decimal(taxa).quantize(CASAS_COTACAO, rounding=ROUND_HALF_UP)
        dia = date.fromisoformat(dados["date"])
    except (ValueError, KeyError, TypeError, InvalidOperation) as erro:
        raise resposta_invalida from erro
    if valor <= 0:
        raise resposta_invalida
    return CotacaoSugerida(valor, dia)

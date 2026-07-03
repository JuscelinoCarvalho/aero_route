"""Cartas aeronáuticas (DECEA / AISWEB).

Lista as cartas de um aeródromo brasileiro — em especial as IAC (cartas de
aproximação por instrumentos) — e faz proxy do PDF oficial para o navegador.

Fonte primária: **web scraping da página pública** de cartas do AISWEB
(https://aisweb.decea.mil.br/?i=cartas). Essa página é HTML estático (ColdFusion),
o filtro é um POST por ICAO/tipo e cada linha já traz o link direto do PDF com a
apikey pública de download que o próprio site usa — ou seja, não exige a
apiKey/apiPass da API oficial (que o DECEA só libera a instituições).

Fallback: se o scraping falhar e as credenciais da API oficial estiverem
configuradas (env AISWEB_API_KEY/AISWEB_API_PASS), consulta a API XML.

Princípios:
- NÃO re-hospedamos cartas: o PDF é sempre buscado ao vivo do DECEA (sempre na
  emenda/AIRAC vigente). O proxy só faz passthrough do arquivo atual.
- O cliente nunca vê a URL/credenciais do DECEA — referencia cada carta por um
  token opaco.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict

# Página pública de cartas (fonte primária, via scraping).
PUBLIC_PAGE = "https://aisweb.decea.mil.br/?i=cartas"
# API oficial credenciada (fallback).
API_BASE = "https://aisweb.decea.mil.br/api/"
# Hosts permitidos no proxy de PDF (evita uso como proxy aberto / SSRF).
ALLOWED_HOSTS = ("aisweb.decea.mil.br", "aisweb.decea.gov.br", "geoaisweb.decea.mil.br")
_UA = "Mozilla/5.0 (JussaAero/1.0; +https://aero.jussa.com.br)"

# Tipos de carta mais comuns (rótulo amigável -> código AISWEB).
CHART_TYPES = [
    ("IAC", "Aproximação por instrumentos (IAC)"),
    ("VAC", "Aproximação visual (VAC)"),
    ("ADC", "Aeródromo (ADC)"),
    ("SID", "Saída por instrumentos (SID)"),
    ("STAR", "Chegada por instrumentos (STAR)"),
    ("AOC", "Obstáculos (AOC)"),
]

# token opaco -> URL real do PDF no DECEA (mantém apikey/URL fora do cliente).
_CHART_URLS: "OrderedDict[str, str]" = OrderedDict()
_CACHE_MAX = 8000


def configured() -> bool:
    """A feature de cartas está sempre disponível (scraping não exige credenciais)."""
    return True


def api_configured() -> bool:
    """As credenciais da API oficial (fallback) estão presentes?"""
    return bool(os.environ.get("AISWEB_API_KEY") and os.environ.get("AISWEB_API_PASS"))


def _remember(url: str) -> str:
    token = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    if token not in _CHART_URLS:
        _CHART_URLS[token] = url
        if len(_CHART_URLS) > _CACHE_MAX:
            _CHART_URLS.popitem(last=False)  # descarta o mais antigo
    return token


def url_for_token(token: str) -> str | None:
    return _CHART_URLS.get(token)


def host_allowed(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


# --------------------------------------------------------------------------- #
# Fonte primária: scraping da página pública
# --------------------------------------------------------------------------- #

_TAG_RE = re.compile(r"<[^>]+>")
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_A_RE = re.compile(r"<a\b.*?</a>", re.S | re.I)
_BUSCA_RE = re.compile(r'name="busca"\s+value="([^"]+)"', re.I)
_HREF_ARQ_RE = re.compile(r'href="([^"]*arquivo=[^"]+)"', re.I)


def _clean(html: str) -> str:
    """Remove tags e normaliza espaços de um fragmento HTML."""
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", html)).strip()


def _opener() -> urllib.request.OpenerDirector:
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _parse_rows(html: str) -> list[dict]:
    """Extrai as cartas da tabela de resultados da página pública.

    Colunas esperadas: [checkbox, ICAO, tipo, nome(+badge), emenda, data, uso, download].
    """
    out: list[dict] = []
    for row in _TR_RE.findall(html):
        if "arquivo=" not in row:
            continue
        cells = _TD_RE.findall(row)
        if len(cells) < 8:
            continue
        m = _HREF_ARQ_RE.search(cells[-1])
        if not m:
            continue
        link = m.group(1).replace("&amp;", "&")
        if not host_allowed(link):
            continue
        # A célula do nome pode conter um <a> (código índice da carta) — removê-lo.
        nome_cell = _A_RE.sub("", cells[3])
        out.append(
            {
                "nome": _clean(nome_cell) or "Carta",
                "tipo": _clean(cells[2]).upper(),
                "amdt": _clean(cells[4]),
                "dt": _clean(cells[5]),
                "token": _remember(link),
            }
        )
    return out


def _scrape_cartas(icao: str, tipo: str = "") -> list[dict]:
    """Consulta a página pública: GET (cookie + token) -> POST (filtro) -> parse."""
    opener = _opener()

    # 1. GET para obter cookie de sessão + token oculto 'busca'.
    req = urllib.request.Request(PUBLIC_PAGE, headers={"User-Agent": _UA})
    with opener.open(req, timeout=15) as resp:
        page = resp.read().decode("utf-8", "replace")
    m = _BUSCA_RE.search(page)
    busca = m.group(1) if m else ""

    # 2. POST com o filtro por ICAO/tipo.
    tipo_val = tipo.upper() if tipo and tipo.upper() != "ALL" else "0"
    data = urllib.parse.urlencode(
        {
            "icaocode": icao.upper(),
            "tipo": tipo_val,
            "carta": "",
            "pe": "0",
            "amdt": "0",
            "uso": "0",
            "busca": busca,
        }
    ).encode()
    req = urllib.request.Request(
        PUBLIC_PAGE,
        data=data,
        headers={
            "User-Agent": _UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": PUBLIC_PAGE,
        },
    )
    with opener.open(req, timeout=20) as resp:
        result = resp.read().decode("utf-8", "replace")
    return _parse_rows(result)


# --------------------------------------------------------------------------- #
# Fallback: API oficial credenciada (XML)
# --------------------------------------------------------------------------- #


def _carta_to_dict(carta: ET.Element) -> dict:
    """Extrai campos de um nó <carta>, tolerante a variações de nomes/caixa."""
    d: dict[str, str] = {}
    for child in carta:
        tag = child.tag.split("}")[-1].lower()  # remove namespace, se houver
        if child.text and child.text.strip():
            d[tag] = child.text.strip()
    for k, v in carta.attrib.items():
        d.setdefault(k.lower(), v)

    nome = d.get("nome") or d.get("name") or d.get("titulo") or "Carta"
    tipo = (d.get("tipo") or d.get("type") or "").upper()
    link = d.get("link") or d.get("url") or d.get("arquivo") or d.get("pdf") or ""
    amdt = d.get("amdt") or d.get("emenda") or ""
    dt = d.get("dt") or d.get("data") or d.get("dctmd") or ""
    return {"nome": nome, "tipo": tipo, "link": link, "amdt": amdt, "dt": dt}


def _fetch_cartas_api(icao: str, tipo: str = "") -> list[dict]:
    """Consulta a API XML credenciada do AISWEB (fallback)."""
    params = {
        "apiKey": os.environ["AISWEB_API_KEY"],
        "apiPass": os.environ["AISWEB_API_PASS"],
        "area": "cartas",
        "icaoCode": icao.upper(),
    }
    if tipo and tipo.upper() != "ALL":
        params["tipo"] = tipo.upper()

    url = API_BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Falha ao consultar a API do AISWEB: {exc}") from exc

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RuntimeError("Resposta inválida da API do AISWEB.") from exc

    out: list[dict] = []
    for carta in root.iter():
        if carta.tag.split("}")[-1].lower() != "carta":
            continue
        info = _carta_to_dict(carta)
        if not info["link"] or not host_allowed(info["link"]):
            continue
        out.append(
            {
                "nome": info["nome"],
                "tipo": info["tipo"],
                "amdt": info["amdt"],
                "dt": info["dt"],
                "token": _remember(info["link"]),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Ponto de entrada
# --------------------------------------------------------------------------- #


def fetch_cartas(icao: str, tipo: str = "") -> list[dict]:
    """Lista cartas de um aeródromo. Devolve dicts com token opaco do PDF.

    Tenta o scraping da página pública; se falhar (ou vier vazio) e a API oficial
    estiver configurada, cai para ela. Lança RuntimeError com mensagem amigável.
    """
    try:
        rows = _scrape_cartas(icao, tipo)
    except Exception as exc:  # noqa: BLE001 — rede/HTML: tenta fallback
        if api_configured():
            return _fetch_cartas_api(icao, tipo)
        raise RuntimeError(f"Falha ao consultar as cartas do AISWEB: {exc}") from exc

    # Vazio pode ser legítimo (aeródromo sem cartas do tipo) ou quebra do parser.
    # Só vale a pena tentar a API se ela estiver configurada.
    if not rows and api_configured():
        return _fetch_cartas_api(icao, tipo)
    return rows


def fetch_pdf(url: str) -> tuple[bytes, str]:
    """Baixa o PDF da carta direto do DECEA (passthrough). Retorna (bytes, content_type)."""
    if not host_allowed(url):
        raise RuntimeError("URL de carta não permitida.")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "application/pdf")
    return data, ctype

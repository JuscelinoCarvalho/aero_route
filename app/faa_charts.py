"""Cartas terminais dos EUA (FAA d-TPP) — domínio público.

A FAA publica o *Digital Terminal Procedures Publication* (d-TPP) — cartas de
aproximação por instrumentos (IAP), saídas (DP/SID), chegadas (STAR), diagrama
de aeródromo (APD) e mínimos (MIN) — em **domínio público**, sem credenciais.
Diferente do DECEA (que exige uma consulta por ICAO a cada busca), a FAA publica
um único *metafile* XML por ciclo AIRAC (28 dias) que mapeia cada aeroporto às
suas cartas; o PDF de cada carta fica em
``https://aeronav.faa.gov/d-tpp/{ciclo}/{pdf_name}``.

Estratégia: baixamos o metafile do ciclo vigente uma vez (~16 MB), indexamos por
ICAO em memória e servimos as buscas localmente. O PDF continua sendo buscado ao
vivo (proxy passthrough em ``/api/carta``), então nunca re-hospedamos nada — o
usuário sempre recebe a emenda vigente e nunca vê a URL de origem.

O ciclo AIRAC é calculado a partir de uma âncora fixa (o intervalo de 28 dias é
estável há décadas); em caso de falha o código recua um ciclo automaticamente.
"""

from __future__ import annotations

import datetime
import io
import threading
import urllib.request
import xml.etree.ElementTree as ET

from . import cartas as cartas_mod

_UA = "Mozilla/5.0 (JussaAero/1.0; +https://aero.jussa.com.br)"
_METAFILE = "https://aeronav.faa.gov/d-tpp/{cycle}/xml_data/d-tpp_Metafile.xml"
_PDF_BASE = "https://aeronav.faa.gov/d-tpp/{cycle}/{pdf_name}"

# Âncora AIRAC: o ciclo 2607 entra em vigor em 2026-07-09. Os ciclos têm 28 dias
# fixos (calendário AIRAC), então dá para derivar o ciclo vigente de qualquer data
# sem depender da rede. `_ANCHOR_G` é o índice global do ciclo (ano*13 + número).
_ANCHOR_DATE = datetime.date(2026, 7, 9)
_ANCHOR_G = 26 * 13 + 7

# Rótulo amigável (dropdown do site) -> chart_code(s) da FAA.
# Códigos do d-TPP: IAP (aproximação), DP/ODP (saídas), STR (STAR/chegada),
# APD (diagrama), MIN (mínimos decolagem/alternativa), HOT (hot spots),
# LAH (land-and-hold-short), DAU (diverse vector area).
_TYPE_MAP = {
    "IAC": ("IAP",),          # aproximação por instrumentos
    "ADC": ("APD",),          # diagrama de aeródromo
    "SID": ("DP", "ODP"),     # saídas (gráficas + textuais por obstáculo)
    "STAR": ("STR",),         # chegada por instrumentos
    "AOC": ("MIN",),          # mínimos (o mais próximo de "obstáculos" na FAA)
    # VAC não existe no d-TPP (a FAA não publica carta de aproximação visual).
}
# Rótulo exibido por chart_code (para o campo "tipo" de cada carta na lista).
_CODE_LABEL = {
    "IAP": "IAC", "APD": "ADC", "DP": "SID", "ODP": "SID", "STR": "STAR",
    "MIN": "MIN", "HOT": "HOT", "LAH": "LAHSO", "DAU": "DAU",
}

# Índice em memória: {ICAO: [(chart_code, chart_name, pdf_name), ...]}.
_index: dict[str, list[tuple[str, str, str]]] = {}
_index_cycle: str = ""
_lock = threading.Lock()


def configured() -> bool:
    """A feature está sempre disponível (fonte pública, sem credenciais)."""
    return True


def current_cycle(today: datetime.date | None = None) -> str:
    """Ciclo AIRAC vigente (ex.: '2606') calculado a partir da âncora fixa."""
    today = today or datetime.date.today()
    steps = (today - _ANCHOR_DATE).days // 28
    g = _ANCHOR_G + steps
    cycle_num = ((g - 1) % 13) + 1
    year2 = (g - cycle_num) // 13
    return f"{year2:02d}{cycle_num:02d}"


def _download_metafile(cycle: str) -> bytes:
    url = _METAFILE.format(cycle=cycle)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _build_index(cycle: str) -> dict[str, list[tuple[str, str, str]]]:
    """Baixa e parseia o metafile do ciclo, indexando as cartas por ICAO."""
    raw = _download_metafile(cycle)
    idx: dict[str, list[tuple[str, str, str]]] = {}
    # iterparse mantém o uso de memória baixo mesmo com ~16 MB de XML.
    icao = ""
    code = name = pdf = ""
    for event, elem in ET.iterparse(io.BytesIO(raw), events=("start", "end")):
        tag = elem.tag
        if event == "start" and tag == "airport_name":
            icao = (elem.get("icao_ident") or "").upper()
        elif event == "end":
            if tag == "chart_code":
                code = (elem.text or "").strip().upper()
            elif tag == "chart_name":
                name = (elem.text or "").strip()
            elif tag == "pdf_name":
                pdf = (elem.text or "").strip()
            elif tag == "record":
                if icao and pdf:
                    idx.setdefault(icao, []).append((code, name, pdf))
                code = name = pdf = ""
                elem.clear()
            elif tag == "airport_name":
                icao = ""
                elem.clear()
    return idx


def _ensure_index() -> str:
    """Garante que o índice reflete o ciclo vigente. Retorna o ciclo carregado."""
    global _index, _index_cycle
    cycle = current_cycle()
    if _index_cycle == cycle and _index:
        return cycle
    with _lock:
        if _index_cycle == cycle and _index:  # outra thread já carregou
            return cycle
        try:
            idx = _build_index(cycle)
        except Exception:  # noqa: BLE001 — ciclo pode ainda não estar publicado
            prev = current_cycle(datetime.date.today() - datetime.timedelta(days=28))
            idx = _build_index(prev)
            cycle = prev
        _index = idx
        _index_cycle = cycle
        return cycle


def fetch_cartas(icao: str, tipo: str = "") -> list[dict]:
    """Lista as cartas FAA de um aeroporto dos EUA. Mesmo formato do módulo DECEA.

    Devolve dicts com token opaco do PDF (reaproveita o cofre de tokens e o proxy
    de ``cartas.py``, então ``/api/carta`` serve os dois países sem mudanças).
    """
    cycle = _ensure_index()
    records = _index.get(icao.upper(), [])
    if not records:
        return []

    tipo = (tipo or "ALL").upper()
    wanted = None if tipo == "ALL" else set(_TYPE_MAP.get(tipo, ()))

    out: list[dict] = []
    for code, name, pdf in records:
        if wanted is not None and code not in wanted:
            continue
        url = _PDF_BASE.format(cycle=cycle, pdf_name=pdf)
        out.append(
            {
                "nome": name or code or "Carta",
                "tipo": _CODE_LABEL.get(code, code),
                "amdt": "",
                "dt": "",
                "token": cartas_mod.remember_url(url),
            }
        )
    return out

"""Cartas do Japão (AIS Japan / JCAB) via espelho público **NagoDede/AIPJapan**.

O portal oficial (``aisjapan.mlit.go.jp``) **exige registro/login** para ver as
cartas — não dá para embutir nem deep-linkar direto. O projeto comunitário
*NagoDede/AIPJapan* (GitHub Pages) reprocessa o eAIP oficial e publica, por
aeródromo, dois PDFs abertos, com URL determinística por ICAO:

- ``documents/{ICAO}_chart.pdf`` — todas as cartas do aeródromo (AD 2) num PDF;
- ``documents/{ICAO}_full.pdf``  — a seção AD 2 completa (texto + cartas).

Um ``documents/info.json`` traz a data de vigência (``EffectiveDate``) e a lista
de aeródromos. Indexamos ambos uma vez (com TTL) e servimos as buscas localmente;
o PDF continua sendo buscado ao vivo pelo proxy ``/api/carta`` (passthrough), então
nunca re-hospedamos nada.

Cuidados desta fonte (diferente de FAA/DECEA, que são oficiais e sempre no ciclo
vigente):
- É um **espelho não oficial** e pode ficar defasado do ciclo AIRAC atual — por
  isso expomos a ``EffectiveDate`` em cada carta (campo ``dt``), para o piloto
  julgar a validade.
- Só o Japão. Se o ICAO não estiver no índice, ``fetch_cartas`` devolve ``[]`` e o
  chamador cai no deep-link do portal oficial (``eaip``).
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.request

from . import cartas as cartas_mod

_BASE = "https://nagodede.github.io/aip/japan/"
_INDEX_URL = _BASE + "index.html"
_INFO_URL = _BASE + "documents/info.json"
_CHART_URL = _BASE + "documents/{icao}_chart.pdf"
_FULL_URL = _BASE + "documents/{icao}_full.pdf"

_UA = "Mozilla/5.0 (JussaAero/1.0; +https://aero.jussa.com.br)"

# Host do espelho — liberado no proxy de PDF (ver ALLOWED_HOSTS em cartas.py).
HOST = "nagodede.github.io"

# Índice em memória: quais ICAOs têm chart/full + data de vigência. Recarrega a
# cada _TTL segundos (o espelho publica ~a cada ciclo AIRAC; não precisa ser ao vivo).
_TTL = 6 * 3600
_chart_icaos: frozenset[str] = frozenset()
_full_icaos: frozenset[str] = frozenset()
_effective: str = ""
_loaded_at: float = 0.0
_lock = threading.Lock()

_HREF_CHART_RE = re.compile(r"/aip/japan/documents/([A-Z]{4})_chart\.pdf", re.I)
_HREF_FULL_RE = re.compile(r"/aip/japan/documents/([A-Z]{4})_full\.pdf", re.I)


def configured() -> bool:
    """Fonte pública, sem credenciais — sempre disponível."""
    return True


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _load_index() -> None:
    """Baixa o index.html (disponibilidade por ICAO) e o info.json (vigência)."""
    global _chart_icaos, _full_icaos, _effective, _loaded_at
    html = _get(_INDEX_URL).decode("utf-8", "replace")
    chart = frozenset(ic.upper() for ic in _HREF_CHART_RE.findall(html))
    full = frozenset(ic.upper() for ic in _HREF_FULL_RE.findall(html))

    effective = ""
    try:
        info = json.loads(_get(_INFO_URL).decode("utf-8", "replace"))
        # EffectiveDate vem como ISO ("2026-03-01T00:00:00Z"); guardamos só a data.
        effective = (info.get("EffectiveDate") or "")[:10]
    except Exception:  # noqa: BLE001 — vigência é opcional; sem ela seguimos sem rótulo
        effective = ""

    _chart_icaos, _full_icaos, _effective = chart, full, effective
    _loaded_at = time.time()


def _ensure_index() -> None:
    if _chart_icaos and (time.time() - _loaded_at) < _TTL:
        return
    with _lock:
        if _chart_icaos and (time.time() - _loaded_at) < _TTL:
            return
        _load_index()


def effective_date() -> str:
    """Data de vigência (YYYY-MM-DD) do espelho, ou '' se desconhecida."""
    try:
        _ensure_index()
    except Exception:  # noqa: BLE001
        return _effective
    return _effective


def fetch_cartas(icao: str, tipo: str = "") -> list[dict]:
    """Lista as cartas do aeródromo japonês. Mesmo formato do módulo DECEA/FAA.

    Devolve as cartas do aeródromo (AD 2) e a seção AIP completa como entradas com
    token opaco do PDF (reaproveita o cofre de tokens e o proxy de ``cartas.py``).
    ``tipo`` é ignorado: o espelho publica um único PDF combinado por aeródromo
    (não há como filtrar por IAC/SID/STAR na origem). Vazio se o ICAO não existir
    — ou se o espelho estiver fora do ar, para o chamador cair no deep-link oficial.
    """
    try:
        _ensure_index()
    except Exception:  # noqa: BLE001 — espelho indisponível: degrada p/ portal oficial
        return []
    icao = icao.upper()
    if icao not in _chart_icaos and icao not in _full_icaos:
        return []

    dt = f"Vigência {_effective}" if _effective else ""
    out: list[dict] = []
    if icao in _chart_icaos:
        out.append(
            {
                "nome": "Cartas do aeródromo (AD 2) — todas",
                "tipo": "AD 2",
                "amdt": "",
                "dt": dt,
                "token": cartas_mod.remember_url(_CHART_URL.format(icao=icao)),
            }
        )
    if icao in _full_icaos:
        out.append(
            {
                "nome": "AIP completo (AD 2 — texto + cartas)",
                "tipo": "AIP",
                "amdt": "",
                "dt": dt,
                "token": cartas_mod.remember_url(_FULL_URL.format(icao=icao)),
            }
        )
    return out

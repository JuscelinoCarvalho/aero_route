"""Cliente da REDEMET (DECEA) — METAR e TAF oficiais do Brasil.

API gratuita do DECEA (mesma casa do AISWEB já usado em cartas.py). Requer uma
chave gratuita, configurada por variável de ambiente:

    REDEMET_API_KEY   chave obtida em https://api-redemet.decea.mil.br

Sem a chave, configured() devolve False e os endpoints respondem 503 (igual ao
fluxo das cartas). O decodificador (app/metar.py) é independente desta camada.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

API_BASE = "https://api-redemet.decea.mil.br"
_UA = "JussaAero/1.0 (+https://aero.jussa.com.br)"


def configured() -> bool:
    return bool(os.environ.get("REDEMET_API_KEY"))


def _get(path: str) -> dict:
    if not configured():
        raise RuntimeError("Chave da REDEMET não configurada no servidor (REDEMET_API_KEY).")
    sep = "&" if "?" in path else "?"
    url = f"{API_BASE}{path}{sep}" + urllib.parse.urlencode({"api_key": os.environ["REDEMET_API_KEY"]})
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Falha ao consultar a REDEMET: {exc}") from exc
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Resposta inválida da REDEMET.") from exc


def _extract_message(data: dict) -> str | None:
    """Pega a mensagem crua (METAR/TAF) da resposta, tolerante a variações de formato."""
    node = data.get("data", data)
    # Formatos vistos: {"data": {"data": [{"mens": "..."}]}} ou {"data": [...]}.
    if isinstance(node, dict):
        node = node.get("data", node)
    if isinstance(node, list) and node:
        first = node[0]
        if isinstance(first, dict):
            for key in ("mens", "metar", "taf", "mensagem", "txt"):
                if first.get(key):
                    return str(first[key]).strip()
        elif isinstance(first, str):
            return first.strip()
    if isinstance(node, str):
        return node.strip()
    return None


def fetch_metar(icao: str) -> str:
    """METAR mais recente de um aeródromo (mensagem crua). Lança RuntimeError em falha."""
    data = _get(f"/mensagens/metar/{icao.upper()}")
    msg = _extract_message(data)
    if not msg:
        raise RuntimeError(f"METAR não disponível para {icao.upper()}.")
    return msg


def list_stations(country_substr: str = "BRAS") -> list[str]:
    """Lista os códigos ICAO dos aeródromos de um país conhecidos pela REDEMET."""
    data = _get("/aerodromos/")
    rows = data.get("data") or []
    out = {
        (a.get("cod") or "").upper()
        for a in rows
        if isinstance(a, dict) and country_substr in (a.get("pais") or "").upper() and a.get("cod")
    }
    return sorted(out)


def fetch_metar_batch(icaos: list[str]) -> dict[str, str]:
    """METAR mais recente de várias estações numa só requisição (vírgula-separadas).

    Retorna {ICAO: mensagem_crua}. Estações sem METAR atual simplesmente não
    aparecem no resultado.
    """
    if not icaos:
        return {}
    data = _get("/mensagens/metar/" + ",".join(i.upper() for i in icaos))
    node = data.get("data", {})
    rows = node.get("data", []) if isinstance(node, dict) else (node if isinstance(node, list) else [])
    out: dict[str, str] = {}
    for r in rows:
        if isinstance(r, dict) and r.get("mens"):
            loc = (r.get("id_localidade") or "").upper()
            if loc:
                out[loc] = str(r["mens"]).strip()
    return out


def fetch_taf(icao: str) -> str:
    """TAF mais recente de um aeródromo (mensagem crua). Lança RuntimeError em falha."""
    data = _get(f"/mensagens/taf/{icao.upper()}")
    msg = _extract_message(data)
    if not msg:
        raise RuntimeError(f"TAF não disponível para {icao.upper()}.")
    return msg


def fetch_taf_batch(icaos: list[str]) -> dict[str, str]:
    """TAF mais recente de várias estações numa só requisição. {ICAO: mensagem}."""
    if not icaos:
        return {}
    data = _get("/mensagens/taf/" + ",".join(i.upper() for i in icaos))
    node = data.get("data", {})
    rows = node.get("data", []) if isinstance(node, dict) else (node if isinstance(node, list) else [])
    out: dict[str, str] = {}
    for r in rows:
        if isinstance(r, dict) and r.get("mens"):
            loc = (r.get("id_localidade") or "").upper()
            if loc:
                out[loc] = str(r["mens"]).strip()
    return out

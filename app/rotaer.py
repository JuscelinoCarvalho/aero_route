"""Ficha do aeródromo — ROTAER (AISWEB, área ``rotaer``).

Dados oficiais do aeródromo: identificação, elevação, fuso, FIR, pistas e
auxílios de navegação (NAV). Os campos de cabeçalho são filhos diretos da raiz
``<aisweb>``; pistas vêm em ``<runway>`` e auxílios em ``<service type="NAV">``.
"""

from __future__ import annotations

import re
import time

from . import aisweb
from . import calc
from . import magvar


def configured() -> bool:
    return aisweb.configured()


# Cache em memória do ROTAER. A ficha muda só por AIRAC (ciclo de 28 dias), então
# um TTL de horas é seguro e evita marteler a API do DECEA nos crawls das páginas
# SEO por aeródromo (/aerodromo/{icao}). Só sucessos entram no cache.
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 12 * 3600  # 12 h


def fetch_rotaer_cached(icao: str, ttl: float = _CACHE_TTL,
                        fb_lat: float | None = None, fb_lon: float | None = None) -> dict:
    """Como ``fetch_rotaer``, mas memoiza o resultado por ``ttl`` segundos."""
    key = icao.upper()
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    data = fetch_rotaer(key, fb_lat, fb_lon)
    _CACHE[key] = (now, data)
    return data


def _float(v: str) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _dms_to_deg(v: str) -> float | None:
    """'S 23 26 03' / 'W 046 28 57' -> grau decimal com sinal. None se inválido."""
    parts = (v or "").strip().replace("°", " ").replace("'", " ").split()
    if len(parts) < 2:
        return None
    hemi = parts[0].upper()
    if hemi not in ("N", "S", "E", "W"):
        return None
    try:
        nums = [float(x.replace(",", ".")) for x in parts[1:4]]
    except ValueError:
        return None
    deg = nums[0] + (nums[1] / 60 if len(nums) > 1 else 0) + (nums[2] / 3600 if len(nums) > 2 else 0)
    return -deg if hemi in ("S", "W") else deg


def _rmkdist(root) -> dict[str, dict]:
    """Bloco rmkDistDeclared por cabeceira: {cabeceira -> {coords, tora, toda, asda, lda}}.

    Fonte das coordenadas de cabeceira (p/ rumo geométrico) e das distâncias
    declaradas oficiais (p/ o contexto de altitude-densidade). Nem todo aeródromo
    publica este bloco.
    """
    out: dict[str, dict] = {}
    for rd in aisweb.iter_tag(root, "rmkDist"):
        d = aisweb.to_dict(rd)
        rwy = (d.get("rwy") or "").upper().strip()
        if not rwy:
            continue
        lat, lon = _dms_to_deg(d.get("lat", "")), _dms_to_deg(d.get("lng", ""))
        out[rwy] = {
            "coords": (lat, lon) if (lat is not None and lon is not None) else None,
            "tora": d.get("tora", ""),
            "toda": d.get("toda", ""),
            "asda": d.get("asda", ""),
            "lda": d.get("lda", ""),
        }
    return out


def _end_heading(end: str, rmk: dict, other: str, ap_lat, ap_lon) -> dict | None:
    """Rumo VERDADEIRO de uma cabeceira. Geometria (thr→thr) se houver coords das
    duas pontas; senão ident×10 (magnético) + declinação. ``end`` ex.: '10L'."""
    m = re.match(r"(\d{1,2})", end)
    if not m:
        return None
    a = rmk.get(end, {}).get("coords")
    b = rmk.get(other, {}).get("coords")
    if a and b:
        hdg = calc.initial_bearing_deg(calc.Point(*a), calc.Point(*b))
        return {"ident": end, "heading": round(hdg), "source": "geo"}
    # Fallback: número da pista = rumo magnético; converte para verdadeiro.
    mag = (int(m.group(1)) * 10) % 360
    if ap_lat is None or ap_lon is None:
        return {"ident": end, "heading": mag, "source": "mag"}  # sem lat/lon: fica magnético
    true = (mag + magvar.declination(ap_lat, ap_lon) + 360) % 360
    return {"ident": end, "heading": round(true), "source": "wmm"}


def _runways(root, ap_lat=None, ap_lon=None) -> list[dict]:
    rmk = _rmkdist(root)
    out: list[dict] = []
    for rw in aisweb.iter_tag(root, "runway"):
        d = aisweb.to_dict(rw)
        ident = d.get("ident", "")
        # 'ident' vem como par de cabeceiras "10L/28R"; separa e acha o rumo de cada.
        ends = [e.strip().upper() for e in ident.split("/") if e.strip()]
        cabeceiras = []
        if len(ends) == 2:
            for end, other in ((ends[0], ends[1]), (ends[1], ends[0])):
                h = _end_heading(end, rmk, other, ap_lat, ap_lon)
                if h:
                    dist = rmk.get(end, {})
                    for k in ("tora", "toda", "asda", "lda"):  # distâncias declaradas
                        if dist.get(k):
                            h[k] = dist[k]
                    cabeceiras.append(h)
        out.append(
            {
                "ident": ident,
                "piso": d.get("surface", ""),
                "comprimento_m": d.get("length", ""),
                "largura_m": d.get("width", ""),
                "pcn": d.get("surface_c", ""),
                "cabeceiras": cabeceiras,
            }
        )
    return out


def _navaids(root) -> list[dict]:
    """Auxílios de navegação (ILS/VOR/DME/NDB…) de ``<service type="NAV">``."""
    out: list[dict] = []
    for svc in aisweb.iter_tag(root, "service"):
        if (svc.get("type") or "").upper() != "NAV":
            continue
        # No <service type="NAV"> o filho <type> (ex.: "ILS/DME") vence o atributo.
        d = aisweb.to_dict(svc)
        out.append(
            {
                "tipo": d.get("type", ""),
                "ident": d.get("ident", ""),
                "freq": d.get("freq", ""),
                "cabeceira": d.get("thr", ""),
            }
        )
    return out


def fetch_rotaer(icao: str, fb_lat: float | None = None, fb_lon: float | None = None) -> dict:
    """Ficha ROTAER do aeródromo. Lança ``RuntimeError`` com mensagem amigável.

    ``fb_lat``/``fb_lon`` são coordenadas de fallback (ex.: da base OurAirports)
    usadas só para a declinação magnética quando o ROTAER vier sem lat/lng — alguns
    aeródromos (ex.: SBKP) devolvem o cabeçalho vazio, mas com pistas válidas.
    """
    root = aisweb.fetch("rotaer", icaoCode=icao.upper())

    d = aisweb.to_dict(root)  # campos de cabeçalho (filhos diretos com texto)
    has_rwy = next(aisweb.iter_tag(root, "runway"), None) is not None
    if not d.get("aerocode") and not d.get("name") and not d.get("status") and not has_rwy:
        raise RuntimeError(f"Aeródromo não encontrado no ROTAER: {icao.upper()}")

    ap_lat = _float(d.get("lat", ""))
    ap_lon = _float(d.get("lng", ""))
    if ap_lat is None or ap_lon is None:  # cabeçalho esparso: usa o fallback local
        ap_lat, ap_lon = fb_lat, fb_lon

    return {
        "codigo": d.get("aerocode", icao.upper()),
        "nome": d.get("name", ""),
        "cidade": d.get("city", ""),
        "uf": d.get("uf", ""),
        "status": d.get("status", ""),
        "tipo": d.get("type", ""),
        "utilizacao": d.get("typeutil", ""),
        "operacao": d.get("typeopr", ""),
        "categoria": d.get("cat", ""),
        "utc": d.get("utc", ""),
        "alt_m": d.get("altm", ""),
        "alt_ft": d.get("altft", ""),
        "fir": d.get("fir", ""),
        "lat": _float(d.get("lat", "")),
        "lng": _float(d.get("lng", "")),
        "lat_dms": d.get("latrotaer", ""),
        "lng_dms": d.get("lngrotaer", ""),
        "distancia_cidade": d.get("distance", ""),
        "pistas": _runways(root, ap_lat, ap_lon),
        "navaids": _navaids(root),
    }

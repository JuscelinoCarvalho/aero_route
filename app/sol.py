"""Nascer e pôr do sol de um aeródromo (AISWEB, área ``sol``).

Útil para a janela VFR diurna. A API devolve os horários em **UTC**; aqui também
convertemos para a hora local a partir do fuso do aeródromo (``utc_offset``,
padrão -3 para o Brasil).
"""

from __future__ import annotations

from . import aisweb


def configured() -> bool:
    return aisweb.configured()


def _shift_hhmm(hhmm: str, offset_h: int) -> str:
    """Desloca ``"HH:MM"`` por ``offset_h`` horas (envolve em 24h). Vazio se inválido."""
    try:
        h, m = (int(x) for x in hhmm.split(":"))
    except (ValueError, AttributeError):
        return ""
    return f"{(h + offset_h) % 24:02d}:{m:02d}"


def fetch_sol(icao: str, utc_offset: int = -3, date: str = "") -> dict:
    """Nascer/pôr do sol do aeródromo. ``date`` opcional (AAAA-MM-DD) consulta outro dia.

    Devolve horários em UTC e locais (pelo ``utc_offset``). Lança ``RuntimeError``
    com mensagem amigável em caso de falha.
    """
    root = aisweb.fetch("sol", icaoCode=icao.upper(), date=date)

    day = next(aisweb.iter_tag(root, "day"), None)
    if day is None:
        raise RuntimeError("Aeródromo sem dados de nascer/pôr do sol.")
    d = aisweb.to_dict(day)

    sr, ss = d.get("sunrise", ""), d.get("sunset", "")
    lat = lng = None
    if d.get("geo") and "," in d["geo"]:
        try:
            lat, lng = (float(x) for x in d["geo"].split(",", 1))
        except ValueError:
            lat = lng = None

    return {
        "aero": d.get("aero", icao.upper()),
        "date": d.get("date", date),
        "utc_offset": utc_offset,
        "sunrise_utc": sr,
        "sunset_utc": ss,
        "sunrise_local": _shift_hhmm(sr, utc_offset),
        "sunset_local": _shift_hhmm(ss, utc_offset),
        "lat": lat,
        "lng": lng,
    }

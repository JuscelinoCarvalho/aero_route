"""NOTAMs de um aeródromo (AISWEB, área ``notam``).

NOTAM = aviso operacional temporário (obstáculo, auxílio fora do ar, pista
interditada…). São **de apoio** — não substituem o briefing oficial.

A API devolve cada NOTAM num nó ``<item>`` no formato ICAO cru: campo ``e`` é o
texto, ``b``/``c`` são início/fim no formato ``AAMMDDHHMM`` (UTC), ``n`` é o
número (ex.: ``F2934/26``). Aqui decodificamos as datas e expomos um subconjunto
útil ao piloto, preservando o texto original.
"""

from __future__ import annotations

from . import aisweb


def configured() -> bool:
    return aisweb.configured()


def _fmt_dt(v: str) -> str:
    """``"2606022027"`` (AAMMDDHHMM, UTC) -> ``"2026-06-02 20:27Z"``.

    Valores não-numéricos (ex.: ``PERM``, ``EST``) voltam como estão; vazio -> ``""``.
    """
    v = (v or "").strip()
    if len(v) == 10 and v.isdigit():
        yy, mm, dd, hh, mi = v[0:2], v[2:4], v[4:6], v[6:8], v[8:10]
        return f"20{yy}-{mm}-{dd} {hh}:{mi}Z"
    return v


def fetch_notam(icao: str) -> list[dict]:
    """Lista os NOTAMs ativos de um aeródromo. Lança ``RuntimeError`` em falha."""
    root = aisweb.fetch("notam", icaoCode=icao.upper())

    out: list[dict] = []
    for item in aisweb.iter_tag(root, "item"):
        d = aisweb.to_dict(item)
        out.append(
            {
                "numero": d.get("n", ""),
                "texto": d.get("e", ""),
                "cod": d.get("cod", ""),          # Q-code (natureza)
                "categoria": d.get("cat", ""),
                "status": d.get("status") or d.get("state", ""),
                "inicio": _fmt_dt(d.get("b", "")),
                "fim": _fmt_dt(d.get("c", "")),
                "loc": d.get("loc", icao.upper()),
                "lower": d.get("lower", ""),
                "upper": d.get("upper", ""),
                "geo_url": d.get("geo_url", ""),
            }
        )
    return out

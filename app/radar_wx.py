"""Nowcast de precipitação por ponto (RainViewer), para a "janela de voo".

Amostra o pixel do aeródromo nos tiles de radar do RainViewer (grátis, sem chave)
no quadro atual e nos quadros de previsão (nowcast, ~próxima hora). Devolve a
intensidade da chuva sobre o ponto agora e quando deve chegar/cessar.

É uma aproximação de apoio (resolução do tile), não medição pontual exata.
"""

from __future__ import annotations

import io
import json
import math
import time
import urllib.request

from PIL import Image

_MAPS_URL = "https://api.rainviewer.com/public/weather-maps.json"
_UA = "JussaAero/1.0 (+https://aero.jussa.com.br)"
_ZOOM = 7

_cache: dict = {"t": 0.0, "data": None}
_LABEL = {0: "sem chuva", 1: "fraca", 2: "moderada", 3: "forte"}

# Rótulos e frases do nowcast por idioma (o texto vai em summary_pt).
_LABEL_I18N = {
    0: {"pt": "sem chuva", "en": "no rain", "es": "sin lluvia"},
    1: {"pt": "fraca", "en": "light", "es": "débil"},
    2: {"pt": "moderada", "en": "moderate", "es": "moderada"},
    3: {"pt": "forte", "en": "heavy", "es": "fuerte"},
}
_NC = {
    "extra_up": {"pt": " e intensificando", "en": " and intensifying", "es": " e intensificándose"},
    "extra_down": {"pt": " e diminuindo", "en": " and easing", "es": " y disminuyendo"},
    "now": {"pt": "Chuva {lvl} sobre o aeródromo agora{extra} (radar).",
            "en": "{lvl} rain over the airport now{extra} (radar).",
            "es": "Lluvia {lvl} sobre el aeródromo ahora{extra} (radar)."},
    "soon": {"pt": "Sem chuva agora; radar prevê chuva {lvl} em ~{min} min.",
             "en": "No rain now; radar forecasts {lvl} rain in ~{min} min.",
             "es": "Sin lluvia ahora; el radar prevé lluvia {lvl} en ~{min} min."},
    "ceasing": {"pt": "Chuva cessando; sem chuva sobre o aeródromo agora (radar).",
                "en": "Rain ending; no rain over the airport now (radar).",
                "es": "Lluvia cesando; sin lluvia sobre el aeródromo ahora (radar)."},
    "none": {"pt": "Sem chuva no radar sobre o aeródromo.",
             "en": "No rain on radar over the airport.",
             "es": "Sin lluvia en el radar sobre el aeródromo."},
}


def _lbl(level: int, lang: str) -> str:
    e = _LABEL_I18N[level]
    return e.get(lang) or e["pt"]


def _nc(key: str, lang: str, **kw) -> str:
    return _NC[key].get(lang, _NC[key]["pt"]).format(**kw)


def _maps() -> dict:
    now = time.time()
    if _cache["data"] and now - _cache["t"] < 240:
        return _cache["data"]
    req = urllib.request.Request(_MAPS_URL, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    _cache.update(t=now, data=data)
    return data


def _tile_rgba(host: str, path: str, lat: float, lon: float, z: int = _ZOOM):
    n = 2 ** z
    latr = math.radians(lat)
    xf = (lon + 180.0) / 360.0 * n
    yf = (1.0 - math.asinh(math.tan(latr)) / math.pi) / 2.0 * n
    xt, yt = int(xf), int(yf)
    px = min(255, int((xf - xt) * 256))
    py = min(255, int((yf - yt) * 256))
    url = f"{host}{path}/256/{z}/{xt}/{yt}/4/1_1.png"  # color 4, suave+neve
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=10) as resp:
        im = Image.open(io.BytesIO(resp.read())).convert("RGBA")
    return im.getpixel((px, py))


def _level(rgba) -> int:
    """0 sem chuva, 1 fraca, 2 moderada, 3 forte (heurística pela cor RainViewer)."""
    r, g, b, a = rgba
    if a < 25:
        return 0
    if r >= 180 and g < 120:       # vermelho/rosa/laranja → forte
        return 3
    if r >= 150 and g >= 150:      # amarelo → moderada
        return 2
    return 1                       # azul/verde → fraca


def precip_at(lat: float, lon: float, frames: int = 4, lang: str = "pt") -> dict:
    """Chuva sobre o ponto: agora + tendência recente + nowcast (se houver).

    O nowcast do RainViewer (free) é intermitente; quando vazio, usamos a
    tendência dos últimos quadros observados. Lança RuntimeError em falha.
    """
    try:
        m = _maps()
        host = m["host"]
        past = m["radar"]["past"]
        nowcast = m["radar"].get("nowcast", [])
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Radar indisponível: {exc}") from exc

    base_t = past[-1]["time"]
    now_level = _level(_tile_rgba(host, past[-1]["path"], lat, lon))

    # Tendência recente (~20–30 min atrás).
    trend = None
    if len(past) >= 3:
        prev = _level(_tile_rgba(host, past[-3]["path"], lat, lon))
        trend = "subindo" if now_level > prev else "caindo" if now_level < prev else "estável"

    # Nowcast (próximos quadros), quando disponível.
    fc: list[dict] = []
    for f in nowcast[:frames]:
        try:
            lvl = _level(_tile_rgba(host, f["path"], lat, lon))
        except Exception:  # noqa: BLE001
            continue
        fc.append({"minutes": max(0, round((f["time"] - base_t) / 60)), "level": lvl,
                   "label": _lbl(lvl, lang)})

    if now_level > 0:
        extra = {"subindo": _nc("extra_up", lang), "caindo": _nc("extra_down", lang)}.get(trend or "", "")
        summary = _nc("now", lang, lvl=_lbl(now_level, lang), extra=extra)
    else:
        nxt = next((x for x in fc if x["level"] > 0), None)
        if nxt:
            summary = _nc("soon", lang, lvl=nxt["label"], min=nxt["minutes"])
        elif trend == "caindo":
            summary = _nc("ceasing", lang)
        else:
            summary = _nc("none", lang)

    return {"now_level": now_level, "now_label": _lbl(now_level, lang), "trend": trend,
            "nowcast": fc, "summary_pt": summary}

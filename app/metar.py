"""Decodificador de METAR e classificação VFR/IFR (semáforo).

Recebe a mensagem METAR crua (ICAO) e devolve uma estrutura legível + um resumo
em português + a categoria de voo (VFR/MVFR/IFR/LIFR). É **função pura**: não
depende de rede, então pode ser testada offline e reaproveitada pelo histórico
e pelo preditivo.

Referência das categorias (teto = camada BKN/OVC mais baixa, ou VV):
  VFR   teto > 3000 ft  e  visibilidade > 8 km
  MVFR  teto 1000–3000 ft  ou  vis 5–8 km
  IFR   teto 500–1000 ft  ou  vis 1.6–5 km
  LIFR  teto < 500 ft  ou  vis < 1.6 km
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Dicionários de tradução (pt/en/es) ---------------------------------- #
# O texto decodificado é gerado no idioma pedido em decode(raw, lang); os campos
# estruturados (vento, vis, teto, categoria) são neutros. A chave do resumo no
# dict continua "summary_pt" por compatibilidade, mas traz o idioma escolhido.
_LANGS = ("pt", "en", "es")

_CLOUD = {
    "FEW": {"pt": "poucas nuvens (1–2/8)", "en": "few clouds (1–2/8)", "es": "pocas nubes (1–2/8)"},
    "SCT": {"pt": "nuvens esparsas (3–4/8)", "en": "scattered clouds (3–4/8)", "es": "nubes dispersas (3–4/8)"},
    "BKN": {"pt": "nublado (5–7/8)", "en": "broken clouds (5–7/8)", "es": "nublado (5–7/8)"},
    "OVC": {"pt": "encoberto (8/8)", "en": "overcast (8/8)", "es": "cubierto (8/8)"},
}
_CLOUD_SHORT = {"FEW": "FEW", "SCT": "SCT", "BKN": "BKN", "OVC": "OVC"}

# Fenômenos significativos (intensidade + descritor + precipitação/obscuração).
_INTENS = {
    "-": {"pt": "fraco", "en": "light", "es": "débil"},
    "+": {"pt": "forte", "en": "heavy", "es": "fuerte"},
    "": {"pt": "moderado", "en": "moderate", "es": "moderado"},
    "VC": {"pt": "nas proximidades", "en": "in the vicinity", "es": "en las proximidades"},
}
_DESC = {
    "MI": {"pt": "raso", "en": "shallow", "es": "bajo"},
    "BC": {"pt": "bancos", "en": "patches", "es": "bancos"},
    "PR": {"pt": "parcial", "en": "partial", "es": "parcial"},
    "DR": {"pt": "baixo arrasto", "en": "low drifting", "es": "arrastre bajo"},
    "BL": {"pt": "soprando", "en": "blowing", "es": "ventisca"},
    "SH": {"pt": "pancadas", "en": "showers", "es": "chubascos"},
    "TS": {"pt": "trovoada", "en": "thunderstorm", "es": "tormenta"},
    "FZ": {"pt": "congelante", "en": "freezing", "es": "engelante"},
}
_PHEN = {
    "DZ": {"pt": "chuvisco", "en": "drizzle", "es": "llovizna"},
    "RA": {"pt": "chuva", "en": "rain", "es": "lluvia"},
    "SN": {"pt": "neve", "en": "snow", "es": "nieve"},
    "SG": {"pt": "grãos de neve", "en": "snow grains", "es": "granos de nieve"},
    "IC": {"pt": "cristais de gelo", "en": "ice crystals", "es": "cristales de hielo"},
    "PL": {"pt": "pelotas de gelo", "en": "ice pellets", "es": "gránulos de hielo"},
    "GR": {"pt": "granizo", "en": "hail", "es": "granizo"},
    "GS": {"pt": "granizo pequeno", "en": "small hail", "es": "granizo pequeño"},
    "UP": {"pt": "precipitação desconhecida", "en": "unknown precipitation", "es": "precipitación desconocida"},
    "BR": {"pt": "névoa úmida", "en": "mist", "es": "neblina"},
    "FG": {"pt": "nevoeiro", "en": "fog", "es": "niebla"},
    "FU": {"pt": "fumaça", "en": "smoke", "es": "humo"},
    "VA": {"pt": "cinza vulcânica", "en": "volcanic ash", "es": "ceniza volcánica"},
    "DU": {"pt": "poeira", "en": "dust", "es": "polvo"},
    "SA": {"pt": "areia", "en": "sand", "es": "arena"},
    "HZ": {"pt": "névoa seca", "en": "haze", "es": "calima"},
    "PY": {"pt": "borrifo", "en": "spray", "es": "rocío marino"},
    "PO": {"pt": "redemoinhos de poeira", "en": "dust whirls", "es": "remolinos de polvo"},
    "SQ": {"pt": "tempestade de vento", "en": "squall", "es": "turbonada"},
    "FC": {"pt": "nuvem funil/tornado", "en": "funnel cloud/tornado", "es": "nube embudo/tornado"},
    "SS": {"pt": "tempestade de areia", "en": "sandstorm", "es": "tormenta de arena"},
    "DS": {"pt": "tempestade de poeira", "en": "duststorm", "es": "tormenta de polvo"},
}


def _tr(dic: dict, key: str, lang: str) -> str:
    """Tradução de uma entrada lang-keyed, com fallback pt e, por fim, a própria chave."""
    e = dic.get(key)
    if not e:
        return key
    return e.get(lang) or e.get("pt") or key


_WIND_DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _compass(deg: int) -> str:
    return _WIND_DIRS[round(deg / 45) % 8]


@dataclass
class Cloud:
    cover: str          # FEW/SCT/BKN/OVC
    base_ft: int | None  # altura da base em pés
    cb: bool = False     # cumulonimbus / torre


@dataclass
class Metar:
    raw: str
    station: str | None = None
    day: int | None = None               # dia do mês da observação (DD)
    time_utc: str | None = None          # "1800" (HHMM, UTC)
    wind: dict | None = None             # {dir, speed_kt, gust_kt, vrb, var_from, var_to}
    visibility_m: int | None = None      # metros (9999 => >=10km)
    cavok: bool = False
    weather: list[tuple] = field(default_factory=list)  # (intens, [desc], [phen]) por fenômeno
    clouds: list[Cloud] = field(default_factory=list)
    vert_vis_ft: int | None = None
    temp_c: int | None = None
    dewpoint_c: int | None = None
    qnh_hpa: int | None = None
    trend: str | None = None
    category: str = "UNKNOWN"            # VFR/MVFR/IFR/LIFR
    ceiling_ft: int | None = None
    summary_pt: str = ""


def _parse_wind(tok: str) -> dict | None:
    m = re.fullmatch(r"(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?(KT|MPS)", tok)
    if not m:
        return None
    d, spd, gust, unit = m.groups()
    f = 1.94384 if unit == "MPS" else 1.0  # m/s -> kt
    return {
        "dir": None if d == "VRB" else int(d),
        "vrb": d == "VRB",
        "speed_kt": round(int(spd) * f),
        "gust_kt": round(int(gust) * f) if gust else None,
        "var_from": None,
        "var_to": None,
    }


def parse(raw: str) -> Metar:
    """Decodifica uma mensagem METAR/SPECI crua."""
    s = raw.strip().rstrip("=").strip()
    met = Metar(raw=s)
    toks = s.split()
    if not toks:
        return met

    i = 0
    if toks[0] in ("METAR", "SPECI"):
        i = 1
    if i < len(toks) and re.fullmatch(r"[A-Z]{4}", toks[i]):
        met.station = toks[i]
        i += 1
    if i < len(toks) and re.fullmatch(r"\d{6}Z", toks[i]):
        met.day = int(toks[i][0:2])
        met.time_utc = toks[i][2:6]  # DDHHMMZ -> HHMM
        i += 1
    if i < len(toks) and toks[i] in ("AUTO", "COR", "NIL"):
        i += 1

    while i < len(toks):
        t = toks[i]

        # Vento
        w = _parse_wind(t)
        if w and met.wind is None:
            met.wind = w
            # variação de direção logo a seguir? (ex.: 090V150)
            if i + 1 < len(toks) and re.fullmatch(r"\d{3}V\d{3}", toks[i + 1]):
                a, b = toks[i + 1].split("V")
                met.wind["var_from"], met.wind["var_to"] = int(a), int(b)
                i += 1
            i += 1
            continue

        if t == "CAVOK":
            met.cavok = True
            met.visibility_m = 9999
            i += 1
            continue

        # Visibilidade em metros (4 dígitos) — opcional sufixo de direção (NDV/letras)
        mvis = re.fullmatch(r"(\d{4})(NDV|[NSEW]{1,2})?", t)
        if mvis and met.visibility_m is None and not t.startswith(("Q", "A")):
            met.visibility_m = int(mvis.group(1))
            i += 1
            continue

        # Visibilidade em SM (incomum no Brasil)
        msm = re.fullmatch(r"(M)?(\d{1,2})(?:/(\d))?SM", t)
        if msm and met.visibility_m is None:
            whole = int(msm.group(2))
            frac = int(msm.group(3)) if msm.group(3) else 0
            sm = whole + (1 / frac if frac else 0)
            met.visibility_m = round(sm * 1609.34)
            i += 1
            continue

        # Visibilidade vertical (céu obscurecido)
        mvv = re.fullmatch(r"VV(\d{3})", t)
        if mvv:
            met.vert_vis_ft = int(mvv.group(1)) * 100
            i += 1
            continue

        # Nuvens
        mc = re.fullmatch(r"(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?", t)
        if mc:
            met.clouds.append(Cloud(mc.group(1), int(mc.group(2)) * 100, bool(mc.group(3))))
            i += 1
            continue
        if t in ("NSC", "NCD", "SKC", "CLR"):
            i += 1
            continue

        # Temperatura / ponto de orvalho
        mt = re.fullmatch(r"(M?\d{2})/(M?\d{2})", t)
        if mt:
            met.temp_c = int(mt.group(1).replace("M", "-"))
            met.dewpoint_c = int(mt.group(2).replace("M", "-"))
            i += 1
            continue

        # QNH
        mq = re.fullmatch(r"Q(\d{4})", t)
        if mq:
            met.qnh_hpa = int(mq.group(1))
            i += 1
            continue
        ma = re.fullmatch(r"A(\d{4})", t)
        if ma:
            met.qnh_hpa = round(int(ma.group(1)) / 100 * 33.8639)
            i += 1
            continue

        # Tendência
        if t in ("NOSIG", "BECMG", "TEMPO"):
            met.trend = " ".join(toks[i:])
            break
        if t == "RMK":
            break

        # Fenômeno significativo
        ph = _parse_weather(t)
        if ph:
            met.weather.append(ph)
            i += 1
            continue

        i += 1  # token não reconhecido — ignora

    _classify(met)
    return met


def _parse_weather(tok: str) -> tuple[str, list[str], list[str]] | None:
    """Componentes de um grupo de fenômeno: (intensidade, [descritores], [fenômenos]).

    Guardar os códigos (em vez do texto já traduzido) permite gerar o resumo em
    qualquer idioma depois, em _weather_phrase().
    """
    m = re.fullmatch(r"([+-]|VC)?((?:MI|BC|PR|DR|BL|SH|TS|FZ)*)((?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+)?", tok)
    if not m or (not m.group(2) and not m.group(3)):
        return None
    intens, desc, phen = m.group(1) or "", m.group(2) or "", m.group(3) or ""
    descs = [desc[j:j + 2] for j in range(0, len(desc), 2) if desc[j:j + 2] in _DESC]
    phens = [phen[j:j + 2] for j in range(0, len(phen), 2) if phen[j:j + 2] in _PHEN]
    if not descs and not phens and not intens:
        return None
    return (intens, descs, phens)


def _weather_phrase(comp: tuple[str, list[str], list[str]], lang: str) -> str:
    """Texto de um grupo de fenômeno no idioma (a partir dos códigos)."""
    intens, descs, phens = comp
    parts: list[str] = []
    if intens == "VC":
        parts.append(_tr(_INTENS, "VC", lang))
    elif intens:
        parts.append(_tr(_INTENS, intens, lang))
    parts += [_tr(_DESC, k, lang) for k in descs]
    parts += [_tr(_PHEN, k, lang) for k in phens]
    return " ".join(parts)


def ceiling_from_clouds(clouds: list[Cloud], vert_vis_ft: int | None = None) -> int | None:
    """Teto = base da camada BKN/OVC mais baixa (ou visibilidade vertical)."""
    ceil = None
    for c in clouds:
        if c.cover in ("BKN", "OVC") and c.base_ft is not None:
            ceil = c.base_ft if ceil is None else min(ceil, c.base_ft)
    if vert_vis_ft is not None:
        ceil = vert_vis_ft if ceil is None else min(ceil, vert_vis_ft)
    return ceil


def flight_category(visibility_m: int | None, ceiling_ft: int | None) -> str:
    """Categoria VFR/MVFR/IFR/LIFR pela pior entre visibilidade e teto."""
    if visibility_m is None:
        return "UNKNOWN"

    def cat_vis(v: int) -> str:
        if v < 1600:
            return "LIFR"
        if v < 5000:
            return "IFR"
        if v <= 8000:
            return "MVFR"
        return "VFR"

    def cat_ceil(c: int | None) -> str:
        if c is None:
            return "VFR"  # sem teto
        if c < 500:
            return "LIFR"
        if c < 1000:
            return "IFR"
        if c <= 3000:
            return "MVFR"
        return "VFR"

    order = ["VFR", "MVFR", "IFR", "LIFR"]
    return max(cat_vis(visibility_m), cat_ceil(ceiling_ft), key=order.index)


def _classify(met: Metar) -> None:
    """Define teto e categoria de voo (VFR/MVFR/IFR/LIFR)."""
    met.ceiling_ft = ceiling_from_clouds(met.clouds, met.vert_vis_ft)
    vis = 9999 if met.cavok else met.visibility_m
    met.category = flight_category(vis, met.ceiling_ft)


# Cor e rótulo do semáforo, por categoria (desc traduzido em category_info()).
CATEGORY_INFO = {
    "VFR": {"color": "#2fbf71", "emoji": "🟢", "label": "VFR", "desc": "Condições visuais boas"},
    "MVFR": {"color": "#e0b020", "emoji": "🟡", "label": "MVFR", "desc": "Visual marginal"},
    "IFR": {"color": "#e8590c", "emoji": "🟠", "label": "IFR", "desc": "Por instrumentos"},
    "LIFR": {"color": "#e03131", "emoji": "🔴", "label": "LIFR", "desc": "Instrumentos — teto/vis muito baixos"},
    "UNKNOWN": {"color": "#6f87a8", "emoji": "⚪", "label": "—", "desc": "Sem dados suficientes"},
}

_CAT_DESC = {
    "VFR": {"pt": "Condições visuais boas", "en": "Good visual conditions", "es": "Buenas condiciones visuales"},
    "MVFR": {"pt": "Visual marginal", "en": "Marginal visual", "es": "Visual marginal"},
    "IFR": {"pt": "Por instrumentos", "en": "Instrument conditions", "es": "Por instrumentos"},
    "LIFR": {"pt": "Instrumentos — teto/vis muito baixos", "en": "Instruments — very low ceiling/visibility", "es": "Instrumentos — techo/vis muy bajos"},
    "UNKNOWN": {"pt": "Sem dados suficientes", "en": "Not enough data", "es": "Sin datos suficientes"},
}


def category_info(cat: str, lang: str = "pt") -> dict:
    """Info do semáforo (cor/emoji/label neutros; desc no idioma pedido)."""
    base = CATEGORY_INFO.get(cat, CATEGORY_INFO["UNKNOWN"])
    return {**base, "desc": _tr(_CAT_DESC, cat if cat in _CAT_DESC else "UNKNOWN", lang)}


# Modelos de frase do resumo, por idioma (interpolação por .format).
_SUM = {
    "wind_vrb": {"pt": "vento variável a {s} kt", "en": "variable wind at {s} kt", "es": "viento variable a {s} kt"},
    "wind_calm": {"pt": "vento calmo", "en": "calm wind", "es": "viento en calma"},
    "wind_dir": {"pt": "vento de {d:03d}° ({c}) a {s} kt", "en": "wind from {d:03d}° ({c}) at {s} kt", "es": "viento de {d:03d}° ({c}) a {s} kt"},
    "gust": {"pt": ", rajadas {g} kt", "en": ", gusting {g} kt", "es": ", ráfagas {g} kt"},
    "cavok": {"pt": "CAVOK (céu limpo, visibilidade ≥ 10 km)", "en": "CAVOK (clear sky, visibility ≥ 10 km)", "es": "CAVOK (cielo despejado, visibilidad ≥ 10 km)"},
    "vis": {"pt": "visibilidade {v}", "en": "visibility {v}", "es": "visibilidad {v}"},
    "vv": {"pt": "céu obscurecido, teto vertical {ft} ft", "en": "sky obscured, vertical visibility {ft} ft", "es": "cielo oscurecido, visibilidad vertical {ft} ft"},
    "cloud": {"pt": "{cover} a {ft} ft{cb}", "en": "{cover} at {ft} ft{cb}", "es": "{cover} a {ft} ft{cb}"},
    "temp": {"pt": "temperatura {t}°C, orvalho {d}°C", "en": "temperature {t}°C, dew point {d}°C", "es": "temperatura {t}°C, rocío {d}°C"},
    "qnh": {"pt": "QNH {q} hPa", "en": "QNH {q} hPa", "es": "QNH {q} hPa"},
    "cb": {"pt": " (CB/torre)", "en": " (CB/towering)", "es": " (CB/torre)"},
    "vis_10plus": {"pt": "10 km ou mais", "en": "10 km or more", "es": "10 km o más"},
}


def _s(key: str, lang: str, **kw) -> str:
    return _SUM[key].get(lang, _SUM[key]["pt"]).format(**kw)


def _fmt_vis(m: int, lang: str = "pt") -> str:
    if m >= 9999:
        return _s("vis_10plus", lang)
    if m >= 1000:
        return f"{m / 1000:.0f} km".replace(".0", "")
    return f"{m} m"


def _summarize(met: Metar, lang: str = "pt") -> str:
    parts: list[str] = []
    if met.wind:
        w = met.wind
        if w["vrb"]:
            base = _s("wind_vrb", lang, s=w["speed_kt"])
        elif w["speed_kt"] == 0:
            base = _s("wind_calm", lang)
        else:
            base = _s("wind_dir", lang, d=w["dir"], c=_compass(w["dir"]), s=w["speed_kt"])
        if w["gust_kt"]:
            base += _s("gust", lang, g=w["gust_kt"])
        parts.append(base)
    if met.cavok:
        parts.append(_s("cavok", lang))
    elif met.visibility_m is not None:
        parts.append(_s("vis", lang, v=_fmt_vis(met.visibility_m, lang)))
    if met.weather:
        parts.append("; ".join(_weather_phrase(c, lang) for c in met.weather))
    if met.vert_vis_ft is not None:
        parts.append(_s("vv", lang, ft=met.vert_vis_ft))
    for c in met.clouds:
        cb = _s("cb", lang) if c.cb else ""
        parts.append(_s("cloud", lang, cover=_tr(_CLOUD, c.cover, lang), ft=c.base_ft, cb=cb))
    if met.temp_c is not None:
        parts.append(_s("temp", lang, t=met.temp_c, d=met.dewpoint_c))
    if met.qnh_hpa is not None:
        parts.append(_s("qnh", lang, q=met.qnh_hpa))
    return ". ".join(p[0].upper() + p[1:] for p in parts) + ("." if parts else "")


def to_dict(met: Metar, lang: str = "pt") -> dict:
    return {
        "raw": met.raw,
        "station": met.station,
        "day": met.day,
        "time_utc": met.time_utc,
        "wind": met.wind,
        "visibility_m": met.visibility_m,
        "cavok": met.cavok,
        "weather": [_weather_phrase(c, lang) for c in met.weather],
        "clouds": [{"cover": c.cover, "base_ft": c.base_ft, "cb": c.cb} for c in met.clouds],
        "vert_vis_ft": met.vert_vis_ft,
        "temp_c": met.temp_c,
        "dewpoint_c": met.dewpoint_c,
        "qnh_hpa": met.qnh_hpa,
        "trend": met.trend,
        "ceiling_ft": met.ceiling_ft,
        "category": met.category,
        "category_info": category_info(met.category, lang),
        # Chave mantida como "summary_pt" por compatibilidade; conteúdo no idioma pedido.
        "summary_pt": _summarize(met, lang),
    }


def decode(raw: str, lang: str = "pt") -> dict:
    """Atalho: METAR cru -> dicionário serializável (prosa no idioma pedido)."""
    return to_dict(parse(raw), lang)

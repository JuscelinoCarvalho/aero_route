"""Decodificador de TAF (previsão de aeródromo) em português.

Reaproveita os analisadores de grupos do app/metar.py (vento, visibilidade,
nuvens, fenômenos) e a classificação VFR/IFR. Quebra o TAF em períodos
(base + grupos de mudança FM/BECMG/TEMPO/PROB), cada um com janela de validade,
condições e categoria de voo.

É função pura: recebe o TAF cru e devolve estrutura + resumo em pt-BR.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from . import metar as M

_ORDER = ["VFR", "MVFR", "IFR", "LIFR"]

# Modelos de texto do TAF por idioma (pt/en/es). Reusa M._s/M._tr/M._fmt_vis
# para vento/nuvens/visibilidade; aqui ficam os textos específicos do TAF.
_T = {
    "label_base": {"pt": "Período base", "en": "Base period", "es": "Período base"},
    "label_FM": {"pt": "A partir de", "en": "From", "es": "A partir de"},
    "label_BECMG": {"pt": "Mudança gradual", "en": "Gradual change", "es": "Cambio gradual"},
    "label_TEMPO": {"pt": "Temporário", "en": "Temporary", "es": "Temporal"},
    "label_PROB": {"pt": "Probabilidade", "en": "Probability", "es": "Probabilidad"},
    "dh": {"pt": "dia {d} {h}Z", "en": "day {d} {h}Z", "es": "día {d} {h}Z"},
    "when_valid": {"pt": "válido {a} a {b}", "en": "valid {a} to {b}", "es": "válido {a} a {b}"},
    "when_from": {"pt": "a partir de dia {d} {h}:{m}Z", "en": "from day {d} {h}:{m}Z", "es": "desde el día {d} {h}:{m}Z"},
    "when_prob": {"pt": "{p}% de chance{tempo} ({tw})", "en": "{p}% chance{tempo} ({tw})", "es": "{p}% de probabilidad{tempo} ({tw})"},
    "prob_tempo": {"pt": " temporário", "en": " temporary", "es": " temporal"},
    "window": {"pt": "{a} a {b}", "en": "{a} to {b}", "es": "{a} a {b}"},
    "nochange": {"pt": "sem alteração significativa", "en": "no significant change", "es": "sin cambios significativos"},
    "vv": {"pt": "céu obscurecido, teto {ft} ft", "en": "sky obscured, ceiling {ft} ft", "es": "cielo oscurecido, techo {ft} ft"},
    "tl_all_vfr": {"pt": "Previsão VFR nas próximas {n}h.", "en": "VFR forecast for the next {n}h.", "es": "Pronóstico VFR en las próximas {n}h."},
    "tl_vfr_then": {"pt": "VFR agora; previsão de {cat} a partir de {at}.", "en": "VFR now; {cat} forecast from {at}.", "es": "VFR ahora; pronóstico de {cat} a partir de {at}."},
    "tl_below_all": {"pt": "Abaixo de VFR ({cat}) em toda a previsão das próximas {n}h.", "en": "Below VFR ({cat}) throughout the next {n}h.", "es": "Por debajo de VFR ({cat}) durante las próximas {n}h."},
    "tl_improves": {"pt": "{cat} agora; melhora para VFR a partir de {at}.", "en": "{cat} now; improving to VFR from {at}.", "es": "{cat} ahora; mejora a VFR a partir de {at}."},
    "tl_risk": {"pt": " ({lead} de {worst} entre {span})", "en": " ({lead} of {worst} between {span})", "es": " ({lead} de {worst} entre {span})"},
    "tl_risk_prob": {"pt": "{p}% de risco", "en": "{p}% risk", "es": "{p}% de riesgo"},
    "tl_risk_temp": {"pt": "risco temporário", "en": "temporary risk", "es": "riesgo temporal"},
}


def _t(key: str, lang: str, **kw) -> str:
    s = _T[key].get(lang, _T[key]["pt"])
    return s.format(**kw) if kw else s


def _worse(a: str, b: str) -> bool:
    """True se a categoria a é pior que b."""
    try:
        return _ORDER.index(a) > _ORDER.index(b)
    except ValueError:
        return False


def _fc_empty() -> dict:
    return {"wind": None, "visibility_m": None, "cavok": False, "weather": [],
            "clouds": [], "vert_vis_ft": None}


def _parse_fc(tokens: list[str]) -> dict:
    """Condições meteorológicas de um período (mesma sintaxe do METAR)."""
    fc = _fc_empty()
    for t in tokens:
        w = M._parse_wind(t)
        if w and fc["wind"] is None:
            fc["wind"] = w
            continue
        if t == "CAVOK":
            fc["cavok"] = True
            fc["visibility_m"] = 9999
            continue
        if re.fullmatch(r"\d{4}", t) and fc["visibility_m"] is None:
            fc["visibility_m"] = int(t)
            continue
        msm = re.fullmatch(r"P?(\d{1,2})SM", t)
        if msm and fc["visibility_m"] is None:
            fc["visibility_m"] = int(msm.group(1)) * 1609
            continue
        mvv = re.fullmatch(r"VV(\d{3})", t)
        if mvv:
            fc["vert_vis_ft"] = int(mvv.group(1)) * 100
            continue
        mc = re.fullmatch(r"(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?", t)
        if mc:
            fc["clouds"].append(M.Cloud(mc.group(1), int(mc.group(2)) * 100, bool(mc.group(3))))
            continue
        if t in ("NSC", "NCD", "SKC", "CLR"):
            continue
        ph = M._parse_weather(t)
        if ph:
            fc["weather"].append(ph)
    return fc


def _category(fc: dict) -> tuple[str, int | None]:
    ceil = M.ceiling_from_clouds(fc["clouds"], fc["vert_vis_ft"])
    vis = 9999 if fc["cavok"] else fc["visibility_m"]
    return M.flight_category(vis, ceil), ceil


def _fc_to_dict(fc: dict, lang: str = "pt") -> dict:
    """Versão serializável do forecast (nuvens viram dicts; fenômenos traduzidos)."""
    return {
        "wind": fc["wind"], "visibility_m": fc["visibility_m"], "cavok": fc["cavok"],
        "weather": [M._weather_phrase(c, lang) for c in fc["weather"]],
        "vert_vis_ft": fc["vert_vis_ft"],
        "clouds": [{"cover": c.cover, "base_ft": c.base_ft, "cb": c.cb} for c in fc["clouds"]],
    }


def _cat_of(fcd: dict) -> str:
    """Categoria a partir de um forecast serializável (dict)."""
    ceil = None
    for c in fcd["clouds"]:
        if c["cover"] in ("BKN", "OVC") and c["base_ft"] is not None:
            ceil = c["base_ft"] if ceil is None else min(ceil, c["base_ft"])
    if fcd.get("vert_vis_ft") is not None:
        ceil = fcd["vert_vis_ft"] if ceil is None else min(ceil, fcd["vert_vis_ft"])
    vis = 9999 if fcd["cavok"] else fcd["visibility_m"]
    return M.flight_category(vis, ceil)


def _fmt_dh(dh: str, lang: str = "pt") -> str:
    """'2912' -> 'dia 29 12Z' (no idioma)."""
    if len(dh) >= 4:
        return _t("dh", lang, d=dh[:2], h=dh[2:4])
    return dh


def _describe(fc: dict, lang: str = "pt") -> str:
    """Texto curto das condições de um período (no idioma). Reusa os modelos do METAR."""
    parts: list[str] = []
    w = fc["wind"]
    if w:
        if w["vrb"]:
            base = M._s("wind_vrb", lang, s=w["speed_kt"])
        elif w["speed_kt"] == 0:
            base = M._s("wind_calm", lang)
        else:
            base = M._s("wind_dir", lang, d=w["dir"], c=M._compass(w["dir"]), s=w["speed_kt"])
        if w["gust_kt"]:
            base += M._s("gust", lang, g=w["gust_kt"])
        parts.append(base)
    if fc["cavok"]:
        parts.append("CAVOK")
    elif fc["visibility_m"] is not None:
        parts.append(M._s("vis", lang, v=M._fmt_vis(fc["visibility_m"], lang)))
    if fc["weather"]:
        parts.append("; ".join(M._weather_phrase(c, lang) for c in fc["weather"]))
    if fc["vert_vis_ft"] is not None:
        parts.append(_t("vv", lang, ft=fc["vert_vis_ft"]))
    for c in fc["clouds"]:
        cb = M._s("cb", lang) if c.cb else ""
        parts.append(M._s("cloud", lang, cover=M._tr(M._CLOUD, c.cover, lang), ft=c.base_ft, cb=cb))
    if not parts:
        return _t("nochange", lang)
    return ", ".join(parts)


def parse(raw: str, lang: str = "pt") -> dict:
    """Decodifica um TAF cru em uma estrutura serializável (prosa no idioma pedido)."""
    s = raw.strip().rstrip("=").strip()
    toks = s.split()
    out: dict = {"raw": s, "station": None, "issued_utc": None,
                 "valid_from": None, "valid_to": None, "periods": []}
    i = 0
    if i < len(toks) and toks[i] == "TAF":
        i += 1
    if i < len(toks) and toks[i] in ("AMD", "COR"):
        out["amendment"] = toks[i]
        i += 1
    if i < len(toks) and re.fullmatch(r"[A-Z]{4}", toks[i]):
        out["station"] = toks[i]
        i += 1
    if i < len(toks) and re.fullmatch(r"\d{6}Z", toks[i]):
        out["issued_utc"] = toks[i][2:4] + ":" + toks[i][4:6]
        out["issued_day"] = toks[i][:2]
        i += 1
    if i < len(toks) and re.fullmatch(r"\d{4}/\d{4}", toks[i]):
        a, b = toks[i].split("/")
        out["valid_from"], out["valid_to"] = a, b
        i += 1

    # Segmenta o restante em períodos (base + mudanças), parando em RMK.
    segments: list[dict] = [{"type": "base", "from": out["valid_from"],
                             "to": out["valid_to"], "prob": None, "tokens": []}]
    temps: list[str] = []
    while i < len(toks):
        t = toks[i]
        if t == "RMK":
            break
        m_fm = re.fullmatch(r"FM(\d{6})", t)
        m_temp = re.fullmatch(r"T[XN](M?\d{2})/(\d{4})Z?", t)
        if m_fm:
            ddhhmm = m_fm.group(1)
            segments.append({"type": "FM", "from": ddhhmm[:4], "fm_min": ddhhmm[4:6],
                             "to": None, "prob": None, "tokens": []})
            i += 1
            continue
        if t in ("BECMG", "TEMPO"):
            seg = {"type": t, "from": None, "to": None, "prob": None, "tokens": []}
            if i + 1 < len(toks) and re.fullmatch(r"\d{4}/\d{4}", toks[i + 1]):
                seg["from"], seg["to"] = toks[i + 1].split("/")
                i += 1
            segments.append(seg)
            i += 1
            continue
        m_prob = re.fullmatch(r"PROB(\d{2})", t)
        if m_prob:
            seg = {"type": "PROB", "prob": int(m_prob.group(1)), "from": None, "to": None, "tokens": []}
            i += 1
            if i < len(toks) and toks[i] == "TEMPO":
                seg["tempo"] = True
                i += 1
            if i < len(toks) and re.fullmatch(r"\d{4}/\d{4}", toks[i]):
                seg["from"], seg["to"] = toks[i].split("/")
                i += 1
            segments.append(seg)
            continue
        if m_temp:
            temps.append(t)  # TX/TN: tratado à parte
            i += 1
            continue
        segments[-1]["tokens"].append(t)
        i += 1

    # Temperaturas previstas (TX = máx, TN = mín).
    for tt in temps:
        mt = re.fullmatch(r"T([XN])(M?\d{2})/(\d{4})Z?", tt)
        if mt:
            val = int(mt.group(2).replace("M", "-"))
            key = "temp_max_c" if mt.group(1) == "X" else "temp_min_c"
            out[key] = val
            out[key.replace("_c", "_at")] = _fmt_dh(mt.group(3), lang)

    for seg in segments:
        fc = _parse_fc(seg["tokens"])
        cat, ceil = _category(fc)
        info = M.category_info(cat, lang)
        if seg["type"] == "base":
            when = _t("when_valid", lang, a=_fmt_dh(seg["from"], lang), b=_fmt_dh(seg["to"], lang)) if seg["from"] else ""
        elif seg["type"] == "FM":
            when = _t("when_from", lang, d=seg["from"][:2], h=seg["from"][2:4], m=seg.get("fm_min", "00"))
        elif seg["type"] == "PROB":
            tw = _t("window", lang, a=_fmt_dh(seg["from"], lang), b=_fmt_dh(seg["to"], lang)) if seg["from"] else ""
            tempo = _t("prob_tempo", lang) if seg.get("tempo") else ""
            when = _t("when_prob", lang, p=seg["prob"], tempo=tempo, tw=tw)
        else:  # BECMG / TEMPO
            when = _t("window", lang, a=_fmt_dh(seg["from"], lang), b=_fmt_dh(seg["to"], lang)) if seg["from"] else ""
        out["periods"].append({
            "type": seg["type"],
            "type_label": _t("label_" + seg["type"], lang) if ("label_" + seg["type"]) in _T else seg["type"],
            "prob": seg.get("prob"),
            "tempo": seg.get("tempo", False),
            "when": when,
            "from": seg["from"], "to": seg["to"],
            "fm_min": seg.get("fm_min"),
            "category": cat,
            "category_info": info,
            "ceiling_ft": ceil,
            "summary_pt": _describe(fc, lang),
            "fc": _fc_to_dict(fc, lang),
        })
    return out


def _dh_to_dt(dh: str | None, ref: datetime) -> datetime | None:
    """'DDHH' (HH pode ser 24) -> datetime UTC próximo de ref."""
    if not dh or len(dh) < 4:
        return None
    day, hh = int(dh[:2]), int(dh[2:4])
    extra = 1 if hh >= 24 else 0
    hh = hh - 24 if hh >= 24 else hh
    for back in (0, 1):
        y, m = ref.year, ref.month - back
        if m <= 0:
            y, m = y - 1, m + 12
        try:
            dt = datetime(y, m, day, hh, tzinfo=timezone.utc) + timedelta(days=extra)
        except ValueError:
            continue
        if abs((dt - ref).total_seconds()) <= 3 * 86400:
            return dt
    return None


def _apply(prev: dict, fcd: dict) -> dict:
    """Carry-forward: o período de mudança redefine só os campos que especifica."""
    out = dict(prev)
    out["clouds"] = list(prev["clouds"])
    if fcd["wind"] is not None:
        out["wind"] = fcd["wind"]
    if fcd["cavok"]:
        out.update(cavok=True, visibility_m=9999, clouds=[], vert_vis_ft=None, weather=[])
        return out
    if fcd["visibility_m"] is not None:
        out["visibility_m"] = fcd["visibility_m"]
        out["cavok"] = False
    if fcd["clouds"]:
        out["clouds"] = list(fcd["clouds"])
        out["cavok"] = False
    if fcd["vert_vis_ft"] is not None:
        out["vert_vis_ft"] = fcd["vert_vis_ft"]
    if fcd["weather"]:
        out["weather"] = list(fcd["weather"])
    return out


def timeline(decoded: dict, max_hours: int = 18, now: datetime | None = None,
             lang: str = "pt") -> dict:
    """Linha do tempo horária de categoria VFR/IFR prevista (das próximas horas)."""
    ref = (now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    periods = decoded.get("periods") or []
    if not periods:
        return {"hours": [], "summary_pt": "", "now_category": None}

    base_fc = periods[0]["fc"]
    perm: list[tuple[datetime, dict]] = []   # FM/BECMG (mudanças permanentes)
    temp: list[tuple[datetime, datetime, dict, int | None, bool]] = []  # TEMPO/PROB
    for p in periods:
        if p["type"] == "FM":
            eff = _dh_to_dt(p["from"], ref)
            if eff and p.get("fm_min"):
                eff += timedelta(minutes=int(p["fm_min"]))
            if eff:
                perm.append((eff, p["fc"]))
        elif p["type"] == "BECMG":
            eff = _dh_to_dt(p["from"], ref)
            if eff:
                perm.append((eff, p["fc"]))
        elif p["type"] in ("TEMPO", "PROB"):
            f, t = _dh_to_dt(p["from"], ref), _dh_to_dt(p["to"], ref)
            if f and t:
                temp.append((f, t, p["fc"], p.get("prob"), True))
    perm.sort(key=lambda x: x[0])

    vto = _dh_to_dt(decoded.get("valid_to"), ref)
    end = ref + timedelta(hours=max_hours)
    if vto:
        end = min(end, vto)

    hours = []
    h = ref
    while h < end and len(hours) < max_hours:
        prevailing = base_fc
        for eff, fcd in perm:
            if eff <= h:
                prevailing = _apply(prevailing, fcd)
        cat = _cat_of(prevailing)
        risk = None
        for f, t, fcd, prob, is_tempo in temp:
            if f <= h < t:
                tcat = _cat_of(fcd)
                if _worse(tcat, cat) and (risk is None or _worse(tcat, risk["category"])):
                    risk = {"category": tcat, "category_info": M.category_info(tcat, lang),
                            "prob": prob}
        hours.append({
            "utc": h.isoformat(), "hour": h.hour, "label": f"{h.hour:02d}Z",
            "category": cat, "category_info": M.category_info(cat, lang),
            "risk": risk,
        })
        h += timedelta(hours=1)

    cats = [x["category"] for x in hours]
    n = len(hours)
    if not cats:
        summary = ""
    elif all(c == "VFR" for c in cats):
        summary = _t("tl_all_vfr", lang, n=n)
    elif cats[0] == "VFR":
        i = next(i for i, c in enumerate(cats) if c != "VFR")
        summary = _t("tl_vfr_then", lang, cat=cats[i], at=hours[i]["label"])
    else:
        i = next((i for i, c in enumerate(cats) if c == "VFR"), None)
        if i is None:
            summary = _t("tl_below_all", lang, cat=cats[0], n=n)
        else:
            summary = _t("tl_improves", lang, cat=cats[0], at=hours[i]["label"])

    # Acrescenta o risco temporário mais severo (TEMPO/PROB), se houver.
    risk_hours = [x for x in hours if x["risk"]]
    if risk_hours:
        worst = max((x["risk"]["category"] for x in risk_hours), key=_ORDER.index)
        rh = [x for x in risk_hours if x["risk"]["category"] == worst]
        prob = rh[0]["risk"].get("prob")
        span = rh[0]["label"] if len(rh) == 1 else f"{rh[0]['label']}–{rh[-1]['label']}"
        lead = _t("tl_risk_prob", lang, p=prob) if prob else _t("tl_risk_temp", lang)
        summary += _t("tl_risk", lang, lead=lead, worst=worst, span=span)

    return {"hours": hours, "summary_pt": summary, "now_category": cats[0] if cats else None}


def decode(raw: str, now: datetime | None = None, lang: str = "pt") -> dict:
    out = parse(raw, lang)
    out["timeline"] = timeline(out, now=now, lang=lang)
    return out

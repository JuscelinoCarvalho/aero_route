"""NOTAMs de um aeródromo (AISWEB, área ``notam``).

NOTAM = aviso operacional temporário (obstáculo, auxílio fora do ar, pista
interditada…). São **de apoio** — não substituem o briefing oficial.

A API devolve cada NOTAM num nó ``<item>`` no formato ICAO cru: campo ``e`` é o
texto, ``b``/``c`` são início/fim no formato ``AAMMDDHHMM`` (UTC), ``n`` é o
número (ex.: ``F2934/26``). Aqui decodificamos as datas e expomos um subconjunto
útil ao piloto, preservando o texto original.
"""

from __future__ import annotations

import re

from . import aisweb


def configured() -> bool:
    return aisweb.configured()


# --------------------------------------------------------------------------- #
# Decodificação / triagem por Q-code (QABCD): AB = assunto, CD = condição.
# O Q-code é a forma estruturada de dizer "sobre o quê" e "o que houve" — muito
# mais confiável para triar do que tentar interpretar o texto livre.
# --------------------------------------------------------------------------- #

# Rótulos em (pt, en, es, ícone). Fallback pelo 2º caractere (grupo do assunto).
_QGROUP = {
    "A": ("Espaço aéreo", "Airspace", "Espacio aéreo", "🛰"),
    "C": ("Comunicações", "Communications", "Comunicaciones", "📡"),
    "F": ("Instalações e serviços", "Facilities and services", "Instalaciones y servicios", "🛠"),
    "G": ("GNSS", "GNSS", "GNSS", "🛰"),
    "I": ("ILS / instrumentos", "ILS / instruments", "ILS / instrumentos", "📶"),
    "L": ("Iluminação", "Lighting", "Iluminación", "💡"),
    "M": ("Área de manobras / pista", "Movement area / runway", "Área de maniobras / pista", "🛬"),
    "N": ("Auxílios à navegação", "Navigation aids", "Ayudas a la navegación", "📡"),
    "O": ("Outras informações", "Other information", "Otra información", "ℹ️"),
    "P": ("Procedimentos ATM", "ATM procedures", "Procedimientos ATM", "🧭"),
    "R": ("Restrição de espaço aéreo", "Airspace restriction", "Restricción de espacio aéreo", "⛔"),
    "S": ("Tráfego aéreo (ATS)", "Air traffic (ATS)", "Tráfico aéreo (ATS)", "🗼"),
    "W": ("Aviso / atividade", "Warning / activity", "Aviso / actividad", "⚠️"),
}

# Assunto específico (AB) em (pt, en, es, ícone) — sobrepõe o grupo quando conhecido.
_QSUBJECT = {
    "OB": ("Obstáculo", "Obstacle", "Obstáculo", "🏗"),
    "OL": ("Obstáculo luminoso", "Lighted obstacle", "Obstáculo luminoso", "🏗"),
    "OA": ("Info operacional", "Operational info", "Info operativa", "ℹ️"),
    "MR": ("Pista (RWY)", "Runway (RWY)", "Pista (RWY)", "🛬"),
    "MX": ("Pista de táxi (TWY)", "Taxiway (TWY)", "Calle de rodaje (TWY)", "🛣"),
    "MS": ("Stopway", "Stopway", "Zona de parada", "🛬"),
    "MT": ("Cabeceira (THR)", "Threshold (THR)", "Umbral (THR)", "🛬"),
    "MD": ("Distâncias declaradas", "Declared distances", "Distancias declaradas", "📏"),
    "MB": ("Atrito / frenagem da pista", "Runway friction / braking", "Rozamiento / frenado", "🛬"),
    "MK": ("Pátio / estacionamento", "Parking", "Estacionamiento", "🅿"),
    "MN": ("Pátio (apron)", "Apron", "Plataforma", "🅿"),
    "MP": ("Posição de estacionamento", "Aircraft stand", "Posición de estacionamiento", "🅿"),
    "IC": ("ILS", "ILS", "ILS", "📶"),
    "IL": ("ILS localizer", "ILS localizer", "ILS localizador", "📶"),
    "IG": ("ILS glide path", "ILS glide path", "ILS senda de planeo", "📶"),
    "ID": ("DME do ILS", "ILS DME", "DME del ILS", "📶"),
    "IM": ("Marcador do ILS", "ILS marker", "Baliza del ILS", "📶"),
    "NB": ("NDB", "NDB", "NDB", "📡"), "NV": ("VOR", "VOR", "VOR", "📡"), "ND": ("DME", "DME", "DME", "📡"),
    "NM": ("Auxílio à navegação", "Navigation aid", "Ayuda a la navegación", "📡"),
    "LR": ("Luzes de pista", "Runway lights", "Luces de pista", "💡"),
    "LA": ("Luzes de aproximação", "Approach lights", "Luces de aproximación", "💡"),
    "LP": ("PAPI / VASI", "PAPI / VASI", "PAPI / VASI", "💡"),
    "FA": ("Aeródromo", "Aerodrome", "Aeródromo", "🏢"),
    "FF": ("Combate a incêndio (SCI)", "Fire fighting (RFF)", "Extinción de incendios (SEI)", "🚒"),
    "FU": ("Combustível", "Fuel", "Combustible", "⛽"),
    "FT": ("Instalação / serviço", "Facility / service", "Instalación / servicio", "🛠"),
    "FM": ("Meteorologia", "Meteorology", "Meteorología", "🌦"),
    "RT": ("Área restrita temporária", "Temporary restricted area", "Área restringida temporal", "⛔"),
    "RR": ("Área restrita", "Restricted area", "Área restringida", "⛔"),
    "RD": ("Área perigosa", "Danger area", "Área peligrosa", "☢"),
    "RP": ("Área proibida", "Prohibited area", "Área prohibida", "⛔"),
    "RA": ("Rota / área", "Route / area", "Ruta / área", "⛔"),
    "WU": ("Atividade de drone (RPAS)", "Drone activity (RPAS)", "Actividad de dron (RPAS)", "🛸"),
    "WP": ("Salto de paraquedas", "Parachute jumping", "Salto en paracaídas", "🪂"),
    "WB": ("Acrobacia aérea", "Aerobatics", "Acrobacia aérea", "✈"),
    "WE": ("Exercício militar", "Military exercise", "Ejercicio militar", "🎖"),
    "WG": ("Detonação de explosivos", "Blasting", "Voladura", "💥"),
    "WL": ("Laser / balão", "Laser / balloon", "Láser / globo", "🔦"),
    "WW": ("Atividade significativa", "Significant activity", "Actividad significativa", "⚠️"),
    "PI": ("Aproximação por instrumentos (IAC)", "Instrument approach (IAP)", "Aproximación por instrumentos", "🧭"),
    "PD": ("Saída por instrumentos (SID)", "Instrument departure (SID)", "Salida por instrumentos (SID)", "🧭"),
    "PA": ("Mínimos de aproximação", "Approach minima", "Mínimos de aproximación", "🧭"),
    "PK": ("Chegada (STAR)", "Arrival (STAR)", "Llegada (STAR)", "🧭"),
    "PT": ("Procedimento", "Procedure", "Procedimiento", "🧭"),
    "XX": ("Aviso (texto livre)", "Notice (free text)", "Aviso (texto libre)", "ℹ️"),
}

# Condição (CD) em (pt, en, es, severidade 0-2).
_QCOND = {
    "LC": ("fechado(a)", "closed", "cerrado(a)", 2),
    "LW": ("em curso", "in progress", "en curso", 1),
    "LT": ("limitado(a)", "limited", "limitado(a)", 1),
    "LR": ("restrito(a)", "restricted", "restringido(a)", 1),
    "CH": ("alterado(a)", "changed", "modificado(a)", 1),
    "CE": ("erguido / instalado", "erected / installed", "erigido / instalado", 1),
    "CA": ("ativado(a) / em atividade", "activated / active", "activado(a) / en actividad", 1),
    "CG": ("rebaixado(a)", "downgraded", "degradado(a)", 1),
    "CF": ("frequência alterada", "frequency changed", "frecuencia modificada", 1),
    "CM": ("realocado(a)", "relocated", "reubicado(a)", 1),
    "CS": ("instalado(a)", "installed", "instalado(a)", 0),
    "CN": ("cancelado(a)", "cancelled", "cancelado(a)", 0),
    "CC": ("restabelecido(a)", "restored", "restablecido(a)", 0),
    "AS": ("inoperante (U/S)", "unserviceable (U/S)", "fuera de servicio (U/S)", 2),
    "AU": ("indisponível", "not available", "no disponible", 2),
    "AW": ("retirado(a)", "withdrawn", "retirado(a)", 0),
    "AH": ("horário alterado", "hours changed", "horario modificado", 0),
    "AM": ("uso militar", "military use", "uso militar", 1),
    "AK": ("operante", "operational", "operativo", 0),
    "AP": ("aprovado(a)", "approved", "aprobado(a)", 0),
    "TT": ("aviso relacionado (trigger)", "related notice (trigger)", "aviso relacionado (trigger)", 0),
    "XX": ("(ver texto)", "(see text)", "(ver texto)", 0),
}

# Assunto de ALTO impacto (fecha/derruba algo que você precisa para operar):
# pista, cabeceira, stopway, aeródromo, ILS, auxílios de navegação. Somam-se os
# grupos I (ILS), N (navegação), R (restrição de espaço aéreo) e A (espaço aéreo).
_HIGH_SUBJ = {"MR", "MT", "MS", "FA", "IC", "IL", "IG", "ID", "IM", "NB", "NV", "ND", "NM"}
# Condições que, num assunto de alto impacto, tornam o NOTAM crítico.
_SEVERE = {"LC", "AS", "AU", "CA", "CG", "CH", "CE", "LT"}
# Condições triviais (rebaixam para informativo): cancelamento, retirada, retorno…
_TRIVIAL = {"CN", "AW", "AK", "AH", "TT"}


_LANG_IDX = {"pt": 0, "en": 1, "es": 2}


def _decode_qcode(cod: str, lang: str = "pt") -> dict:
    """QABCD -> {assunto, condicao, titulo, icone, prioridade(0-2)} no idioma ``lang``.

    Prioridade por IMPACTO do assunto × condição: alto impacto + condição severa
    = ALTA (2); demais assuntos = MÉDIA (1); condição trivial = INFO (0).
    """
    i = _LANG_IDX.get(lang, 0)
    cod = (cod or "").strip().upper()
    if len(cod) != 5 or cod[0] != "Q":
        return {"assunto": "", "condicao": "", "titulo": "", "icone": "📄", "prioridade": 1}
    ab, cd = cod[1:3], cod[3:5]
    subj = _QSUBJECT.get(ab) or _QGROUP.get(ab[0], ("Aviso", "Notice", "Aviso", "📄"))
    assunto, icone = subj[i], subj[3]
    cond = _QCOND.get(cd)
    cond_label = cond[i] if cond else ""
    high = ab in _HIGH_SUBJ or ab[0] in ("I", "N", "R", "A")

    if cd in _TRIVIAL:
        prio = 0
    elif high:
        prio = 2 if cd in _SEVERE else 1
    else:
        prio = 1

    titulo = assunto + (f" — {cond_label}" if cd != "XX" and cond_label else "")
    return {"assunto": assunto, "condicao": cond_label, "titulo": titulo, "icone": icone, "prioridade": prio}


# --------------------------------------------------------------------------- #
# Expansão de abreviações no texto (campo E). O texto do DECEA já é semi-PT;
# expandir as siglas comuns torna-o legível. Substituição por palavra inteira.
# --------------------------------------------------------------------------- #
_ABBR = {
    "RWY": "pista", "TWY": "pista de táxi", "AD": "aeródromo", "APRON": "pátio", "TWR": "torre",
    "ACFT": "aeronave", "OBST": "obstáculo", "PSN": "posição", "COORD": "coordenadas",
    "HGT": "altura", "ELEV": "elevação", "AMSL": "acima do nível do mar", "AGL": "acima do solo",
    "LGT": "luz", "LGTD": "iluminado", "LIT": "iluminado", "UNLIT": "não iluminado", "U/S": "inoperante",
    "UNSER": "inoperante", "AVBL": "disponível", "CLSD": "fechado", "CLOSED": "fechado", "OPN": "aberto",
    "WIP": "obras em curso", "MAINT": "manutenção", "FREQ": "frequência", "CTC": "contato", "TEL": "telefone",
    "DUE": "devido a", "WEF": "a partir de", "TIL": "até", "UNTIL": "até", "EXC": "exceto", "BTN": "entre",
    "APRX": "aproximadamente", "APPROX": "aproximadamente", "RADIUS": "raio", "DEG": "graus",
    "PROC": "procedimento", "DEP": "decolagem", "ARR": "chegada", "APCH": "aproximação", "DIST": "distância",
    "CRANE": "guindaste", "RESTRICTED": "restrito", "PROHIBITED": "proibido", "DANGER": "perigo",
    "SFC": "superfície", "MSL": "nível médio do mar", "NM": "milhas náuticas", "FL": "nível de voo",
    "ESTABLISHED": "estabelecido", "OPS": "operações", "PPR": "prévia autorização", "TEMPO": "temporário",
    "AVGAS": "gasolina de aviação", "JET": "querosene de aviação", "RESCUE": "resgate", "FIRE": "incêndio",
    "NAVAID": "auxílio à navegação", "OTP": "topo do obstáculo", "MEHT": "altura mínima dos olhos",
    "RMK": "obs.", "REF": "ref.", "AVBLTY": "disponibilidade",
}
_ABBR_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(_ABBR, key=len, reverse=True)) + r")\b")


def _expand(text: str) -> str:
    """Expande abreviações conhecidas (palavra inteira). Mantém o resto do texto."""
    if not text:
        return ""
    return _ABBR_RE.sub(lambda m: _ABBR[m.group(1)], text)


def _fmt_dt(v: str) -> str:
    """``"2606022027"`` (AAMMDDHHMM, UTC) -> ``"2026-06-02 20:27Z"``.

    Valores não-numéricos (ex.: ``PERM``, ``EST``) voltam como estão; vazio -> ``""``.
    """
    v = (v or "").strip()
    if len(v) == 10 and v.isdigit():
        yy, mm, dd, hh, mi = v[0:2], v[2:4], v[4:6], v[6:8], v[8:10]
        return f"20{yy}-{mm}-{dd} {hh}:{mi}Z"
    return v


def fetch_notam(icao: str, lang: str = "pt") -> list[dict]:
    """Lista os NOTAMs ativos de um aeródromo (rótulos decodificados no idioma
    ``lang``). Lança ``RuntimeError`` em falha."""
    root = aisweb.fetch("notam", icaoCode=icao.upper())

    out: list[dict] = []
    for item in aisweb.iter_tag(root, "item"):
        d = aisweb.to_dict(item)
        texto = d.get("e", "")
        q = _decode_qcode(d.get("cod", ""), lang)
        out.append(
            {
                "numero": d.get("n", ""),
                "texto": texto,                     # texto ICAO original (preservado)
                "traduzido": _expand(texto),        # texto com abreviações expandidas
                "cod": d.get("cod", ""),            # Q-code (natureza)
                "assunto": q["assunto"],            # decodificado do Q-code
                "titulo": q["titulo"],              # "Pista — fechada", "Obstáculo — erguido"…
                "icone": q["icone"],
                "prioridade": q["prioridade"],      # 0=info · 1=média · 2=alta (triagem)
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
    # Triagem: mais crítico primeiro; empate pela data de início.
    out.sort(key=lambda n: (-n["prioridade"], n["inicio"]))
    return out

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

# Fallback pelo 2º caractere (grupo do assunto).
_QGROUP = {
    "A": ("Espaço aéreo", "🛰"), "C": ("Comunicações", "📡"),
    "F": ("Instalações e serviços", "🛠"), "G": ("GNSS", "🛰"),
    "I": ("ILS / instrumentos", "📶"), "L": ("Iluminação", "💡"),
    "M": ("Área de manobras / pista", "🛬"), "N": ("Auxílios à navegação", "📡"),
    "O": ("Outras informações", "ℹ️"), "P": ("Procedimentos ATM", "🧭"),
    "R": ("Restrição de espaço aéreo", "⛔"), "S": ("Tráfego aéreo (ATS)", "🗼"),
    "W": ("Aviso / atividade", "⚠️"),
}

# Assunto específico (AB) — sobrepõe o grupo quando conhecido.
_QSUBJECT = {
    "OB": ("Obstáculo", "🏗"), "OL": ("Obstáculo luminoso", "🏗"), "OA": ("Info operacional", "ℹ️"),
    "MR": ("Pista (RWY)", "🛬"), "MX": ("Pista de táxi (TWY)", "🛣"), "MS": ("Stopway", "🛬"),
    "MT": ("Cabeceira (THR)", "🛬"), "MD": ("Distâncias declaradas", "📏"),
    "MB": ("Atrito / frenagem da pista", "🛬"), "MK": ("Pátio / estacionamento", "🅿"),
    "MN": ("Pátio (apron)", "🅿"), "MP": ("Posição de estacionamento", "🅿"),
    "IC": ("ILS", "📶"), "IL": ("ILS localizer", "📶"), "IG": ("ILS glide path", "📶"),
    "ID": ("DME do ILS", "📶"), "IM": ("Marcador do ILS", "📶"),
    "NB": ("NDB", "📡"), "NV": ("VOR", "📡"), "ND": ("DME", "📡"), "NM": ("Auxílio à navegação", "📡"),
    "LR": ("Luzes de pista", "💡"), "LA": ("Luzes de aproximação", "💡"), "LP": ("PAPI / VASI", "💡"),
    "FA": ("Aeródromo", "🏢"), "FF": ("Combate a incêndio (SCI)", "🚒"), "FU": ("Combustível", "⛽"),
    "FT": ("Instalação / serviço", "🛠"), "FM": ("Meteorologia", "🌦"),
    "RT": ("Área restrita temporária", "⛔"), "RR": ("Área restrita", "⛔"),
    "RD": ("Área perigosa", "☢"), "RP": ("Área proibida", "⛔"), "RA": ("Rota / área", "⛔"),
    "WU": ("Atividade de drone (RPAS)", "🛸"), "WP": ("Salto de paraquedas", "🪂"),
    "WB": ("Acrobacia aérea", "✈"), "WE": ("Exercício militar", "🎖"),
    "WG": ("Detonação de explosivos", "💥"), "WL": ("Laser / balão", "🔦"), "WW": ("Atividade significativa", "⚠️"),
    "PI": ("Aproximação por instrumentos (IAC)", "🧭"), "PD": ("Saída por instrumentos (SID)", "🧭"),
    "PA": ("Mínimos de aproximação", "🧭"), "PK": ("Chegada (STAR)", "🧭"), "PT": ("Procedimento", "🧭"),
    "XX": ("Aviso (texto livre)", "ℹ️"),
}

# Condição (CD) -> (rótulo, severidade 0-2).
_QCOND = {
    "LC": ("fechado(a)", 2), "LW": ("em curso", 1), "LT": ("limitado(a)", 1),
    "LR": ("restrito(a)", 1),
    "CH": ("alterado(a)", 1), "CE": ("erguido / instalado", 1), "CA": ("ativado(a) / em atividade", 1),
    "CG": ("rebaixado(a)", 1), "CF": ("frequência alterada", 1), "CM": ("realocado(a)", 1),
    "CS": ("instalado(a)", 0), "CN": ("cancelado(a)", 0), "CC": ("restabelecido(a)", 0),
    "AS": ("inoperante (U/S)", 2), "AU": ("indisponível", 2), "AW": ("retirado(a)", 0),
    "AH": ("horário alterado", 0), "AM": ("uso militar", 1), "AK": ("operante", 0), "AP": ("aprovado(a)", 0),
    "TT": ("aviso relacionado (trigger)", 0), "XX": ("(ver texto)", 0),
}

# Assunto de ALTO impacto (fecha/derruba algo que você precisa para operar):
# pista, cabeceira, stopway, aeródromo, ILS, auxílios de navegação. Somam-se os
# grupos I (ILS), N (navegação), R (restrição de espaço aéreo) e A (espaço aéreo).
_HIGH_SUBJ = {"MR", "MT", "MS", "FA", "IC", "IL", "IG", "ID", "IM", "NB", "NV", "ND", "NM"}
# Condições que, num assunto de alto impacto, tornam o NOTAM crítico.
_SEVERE = {"LC", "AS", "AU", "CA", "CG", "CH", "CE", "LT"}
# Condições triviais (rebaixam para informativo): cancelamento, retirada, retorno…
_TRIVIAL = {"CN", "AW", "AK", "AH", "TT"}


def _decode_qcode(cod: str) -> dict:
    """QABCD -> {assunto, condicao, titulo, icone, prioridade(0-2)}.

    Prioridade por IMPACTO do assunto × condição: alto impacto + condição severa
    = ALTA (2); demais assuntos = MÉDIA (1); condição trivial = INFO (0).
    """
    cod = (cod or "").strip().upper()
    if len(cod) != 5 or cod[0] != "Q":
        return {"assunto": "", "condicao": "", "titulo": "", "icone": "📄", "prioridade": 1}
    ab, cd = cod[1:3], cod[3:5]
    assunto, icone = _QSUBJECT.get(ab) or _QGROUP.get(ab[0], ("Aviso", "📄"))
    cond_label = _QCOND.get(cd, ("", 1))[0]
    high = ab in _HIGH_SUBJ or ab[0] in ("I", "N", "R", "A")

    if cd in _TRIVIAL:
        prio = 0
    elif high:
        prio = 2 if cd in _SEVERE else 1
    else:
        prio = 1

    titulo = assunto + (f" — {cond_label}" if cond_label and cond_label != "(ver texto)" else "")
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


def fetch_notam(icao: str) -> list[dict]:
    """Lista os NOTAMs ativos de um aeródromo. Lança ``RuntimeError`` em falha."""
    root = aisweb.fetch("notam", icaoCode=icao.upper())

    out: list[dict] = []
    for item in aisweb.iter_tag(root, "item"):
        d = aisweb.to_dict(item)
        texto = d.get("e", "")
        q = _decode_qcode(d.get("cod", ""))
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

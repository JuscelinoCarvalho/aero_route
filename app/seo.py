"""SEO programático: páginas de rota indexáveis + sitemap.

Gera uma página HTML (renderizada no servidor, sem depender de JS) para cada
par de cidades populares — ex.: /rota/sao-paulo/lisboa. Cada página traz o
cálculo real (distância, tempo, combustível), um mapa em SVG e links internos
para outras rotas. Isso cria centenas de "portas de entrada" para o Google.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from . import aircraft as aircraft_mod
from . import calc
from . import i18n
from . import metar as metar_mod
from .airports import Airport, AirportStore
from .calc import Point

BASE_URL = "https://aero.jussa.com.br"

# --------------------------------------------------------------------------- #
# i18n das páginas SEO (Leva 2): pt (padrão), en, es.
# Estas páginas são geradas por f-strings em Python (não pelo motor de tokens
# do i18n.py), então trazem o próprio catálogo. Templates com {} recebem
# .format(); o switcher/hreflang/canonical vêm de i18n.switcher_block/hreflang_block.
# --------------------------------------------------------------------------- #
TR: dict[str, dict[str, str]] = {
    # ---- comum ----
    "all_routes": {"pt": "todas as rotas", "en": "all routes", "es": "todas las rutas"},
    "brand_planning": {"pt": "flight planning · jussa.com.br", "en": "flight planning · jussa.com.br", "es": "flight planning · jussa.com.br"},
    "foot_calc": {"pt": "Calculadora", "en": "Calculator", "es": "Calculadora"},
    "foot_routes": {"pt": "Rotas", "en": "Routes", "es": "Rutas"},
    "foot_about": {"pt": "Sobre", "en": "About", "es": "Acerca de"},
    "foot_privacy": {"pt": "Privacidade", "en": "Privacy", "es": "Privacidad"},
    "foot_curio": {"pt": "Curiosidades", "en": "Facts", "es": "Curiosidades"},
    "note_est": {
        "pt": "Estimativas de cruzeiro, sem vento. Não usar para planejamento operacional real.",
        "en": "Cruise estimates, no wind. Not for real operational planning.",
        "es": "Estimaciones de crucero, sin viento. No usar para planificación operacional real.",
    },
    # ---- nav ----
    "nav_calc": {"pt": "Calculadora", "en": "Calculator", "es": "Calculadora"},
    "nav_compare": {"pt": "Comparar aeronaves", "en": "Compare aircraft", "es": "Comparar aeronaves"},
    "nav_tempo": {"pt": "Tempo", "en": "Weather", "es": "Meteo"},
    "nav_radar": {"pt": "Radar", "en": "Radar", "es": "Radar"},
    "nav_cartas": {"pt": "Cartas", "en": "Charts", "es": "Cartas"},
    "nav_curio": {"pt": "Curiosidades", "en": "Facts", "es": "Curiosidades"},
    "nav_rotas": {"pt": "Rotas", "en": "Routes", "es": "Rutas"},

    # ---- página de rota (/rota) ----
    "rt_tag": {"pt": "ROTA {0} → {1}", "en": "ROUTE {0} → {1}", "es": "RUTA {0} → {1}"},
    "rt_title": {
        "pt": "Distância de {0} a {1}: {2} km e tempo de voo",
        "en": "Distance from {0} to {1}: {2} km and flight time",
        "es": "Distancia de {0} a {1}: {2} km y tiempo de vuelo",
    },
    "rt_desc": {
        "pt": "A distância de {0} ({1}) a {2} ({3}) é {4} km ({5} milhas náuticas). Tempo de voo aproximado de {6} e consumo estimado de combustível por aeronave.",
        "en": "The distance from {0} ({1}) to {2} ({3}) is {4} km ({5} nautical miles). Approximate flight time of {6} and estimated fuel burn per aircraft.",
        "es": "La distancia de {0} ({1}) a {2} ({3}) es {4} km ({5} millas náuticas). Tiempo de vuelo aproximado de {6} y consumo estimado de combustible por aeronave.",
    },
    "rt_h2": {"pt": "Distância de {0} para {1}", "en": "Distance from {0} to {1}", "es": "Distancia de {0} a {1}"},
    "rt_intro": {
        "pt": "A distância em linha reta (great-circle) entre <strong>{0}</strong> ({1}, {2}) e <strong>{3}</strong> ({4}, {5}) é de <strong>{6} km</strong> ({7} milhas náuticas). A proa inicial é de <strong>{8}°</strong>. Em um {9}, o voo leva cerca de <strong>{10}</strong>.",
        "en": "The straight-line (great-circle) distance between <strong>{0}</strong> ({1}, {2}) and <strong>{3}</strong> ({4}, {5}) is <strong>{6} km</strong> ({7} nautical miles). The initial heading is <strong>{8}°</strong>. In a {9}, the flight takes about <strong>{10}</strong>.",
        "es": "La distancia en línea recta (ortodrómica) entre <strong>{0}</strong> ({1}, {2}) y <strong>{3}</strong> ({4}, {5}) es de <strong>{6} km</strong> ({7} millas náuticas). El rumbo inicial es de <strong>{8}°</strong>. En un {9}, el vuelo dura cerca de <strong>{10}</strong>.",
    },
    "rt_ro_dist": {"pt": "Distância", "en": "Distance", "es": "Distancia"},
    "rt_ro_time": {"pt": "Tempo · {0}", "en": "Time · {0}", "es": "Tiempo · {0}"},
    "rt_ro_bearing": {"pt": "Proa inicial", "en": "Initial heading", "es": "Rumbo inicial"},
    "rt_cta": {"pt": "Abrir esta rota na calculadora interativa →", "en": "Open this route in the interactive calculator →", "es": "Abrir esta ruta en la calculadora interactiva →"},
    "rt_link_time": {"pt": "Quantas horas de voo de {0} para {1}? →", "en": "How many hours is the flight from {0} to {1}? →", "es": "¿Cuántas horas de vuelo de {0} a {1}? →"},
    "rt_h3_fuel": {"pt": "Tempo e combustível por aeronave", "en": "Time and fuel per aircraft", "es": "Tiempo y combustible por aeronave"},
    "rt_th_ac": {"pt": "Aeronave", "en": "Aircraft", "es": "Aeronave"},
    "rt_th_block": {"pt": "Tempo de bloco", "en": "Block time", "es": "Tiempo de bloque"},
    "rt_th_fuel": {"pt": "Combustível", "en": "Fuel", "es": "Combustible"},
    "rt_h3_other": {"pt": "Outras rotas saindo de {0}", "en": "Other routes from {0}", "es": "Otras rutas desde {0}"},
    # resposta direta (topo) — otimizada para o featured snippet
    "rt_answer": {
        "pt": "A distância de {0} para {1} é de <strong>{2} km</strong> ({3} milhas náuticas). Um voo direto leva cerca de <strong>{4}</strong> num {5}, com proa inicial de <strong>{6}°</strong>.",
        "en": "The distance from {0} to {1} is <strong>{2} km</strong> ({3} nautical miles). A direct flight takes about <strong>{4}</strong> in a {5}, with an initial heading of <strong>{6}°</strong>.",
        "es": "La distancia de {0} a {1} es de <strong>{2} km</strong> ({3} millas náuticas). Un vuelo directo dura cerca de <strong>{4}</strong> en un {5}, con rumbo inicial de <strong>{6}°</strong>.",
    },
    # FAQ (visível + JSON-LD FAQPage). Respostas em texto puro (sem HTML).
    "faq_h": {"pt": "Perguntas frequentes", "en": "Frequently asked questions", "es": "Preguntas frecuentes"},
    "faq_q_dist": {"pt": "Qual é a distância de {0} para {1}?", "en": "What is the distance from {0} to {1}?", "es": "¿Cuál es la distancia de {0} a {1}?"},
    "faq_a_dist": {
        "pt": "A distância em linha reta (great-circle) de {0} para {1} é de {2} km, o equivalente a {3} milhas náuticas.",
        "en": "The straight-line (great-circle) distance from {0} to {1} is {2} km, equivalent to {3} nautical miles.",
        "es": "La distancia en línea recta (ortodrómica) de {0} a {1} es de {2} km, equivalente a {3} millas náuticas.",
    },
    "faq_q_time": {"pt": "Quantas horas de voo de {0} para {1}?", "en": "How many hours is the flight from {0} to {1}?", "es": "¿Cuántas horas de vuelo de {0} a {1}?"},
    "faq_a_time": {
        "pt": "Um voo direto de {0} para {1} leva cerca de {2} num {3}, já incluindo o tempo de táxi, subida e descida.",
        "en": "A direct flight from {0} to {1} takes about {2} in a {3}, already including taxi, climb and descent time.",
        "es": "Un vuelo directo de {0} a {1} dura cerca de {2} en un {3}, incluyendo el tiempo de rodaje, ascenso y descenso.",
    },
    "faq_q_bearing": {"pt": "Qual é a direção (proa) de {0} para {1}?", "en": "What is the heading from {0} to {1}?", "es": "¿Cuál es la dirección (rumbo) de {0} a {1}?"},
    "faq_a_bearing": {
        "pt": "A proa inicial de {0} para {1} é de {2}° (rumo verdadeiro), medida no ponto de partida da rota great-circle.",
        "en": "The initial heading from {0} to {1} is {2}° (true bearing), measured at the departure point of the great-circle route.",
        "es": "El rumbo inicial de {0} a {1} es de {2}° (rumbo verdadero), medido en el punto de salida de la ruta ortodrómica.",
    },

    # ---- página de tempo de voo (/voo) ----
    "vo_tag": {"pt": "TEMPO DE VOO {0} → {1}", "en": "FLIGHT TIME {0} → {1}", "es": "TIEMPO DE VUELO {0} → {1}"},
    "vo_title": {"pt": "Quantas horas de voo de {0} para {1}?", "en": "How many hours is the flight from {0} to {1}?", "es": "¿Cuántas horas de vuelo de {0} a {1}?"},
    "vo_desc": {
        "pt": "O voo de {0} ({1}) a {2} ({3}) leva cerca de {4} sem escalas em um {5}. Veja o tempo por aeronave e a distância ({6} km).",
        "en": "The flight from {0} ({1}) to {2} ({3}) takes about {4} nonstop in a {5}. See the time per aircraft and the distance ({6} km).",
        "es": "El vuelo de {0} ({1}) a {2} ({3}) dura cerca de {4} sin escalas en un {5}. Ve el tiempo por aeronave y la distancia ({6} km).",
    },
    "vo_intro": {
        "pt": "Um voo direto de <strong>{0}</strong> ({1}) para <strong>{2}</strong> ({3}) leva aproximadamente <strong>{4}</strong> em um {5}, considerando velocidade de cruzeiro e cerca de 25 min de táxi, subida e descida. A distância é de <strong>{6} km</strong> ({7} milhas náuticas).",
        "en": "A direct flight from <strong>{0}</strong> ({1}) to <strong>{2}</strong> ({3}) takes approximately <strong>{4}</strong> in a {5}, considering cruise speed and about 25 min of taxi, climb and descent. The distance is <strong>{6} km</strong> ({7} nautical miles).",
        "es": "Un vuelo directo de <strong>{0}</strong> ({1}) a <strong>{2}</strong> ({3}) dura aproximadamente <strong>{4}</strong> en un {5}, considerando la velocidad de crucero y cerca de 25 min de rodaje, ascenso y descenso. La distancia es de <strong>{6} km</strong> ({7} millas náuticas).",
    },
    "vo_cta": {"pt": "Calcular na ferramenta interativa →", "en": "Calculate in the interactive tool →", "es": "Calcular en la herramienta interactiva →"},
    "vo_link_dist": {"pt": "Ver distância de {0} para {1} →", "en": "See distance from {0} to {1} →", "es": "Ver distancia de {0} a {1} →"},
    "vo_h3_ac": {"pt": "Tempo de voo por aeronave", "en": "Flight time per aircraft", "es": "Tiempo de vuelo por aeronave"},
    "vo_th_cruise": {"pt": "Cruzeiro", "en": "Cruise", "es": "Crucero"},
    "vo_th_time": {"pt": "Tempo estimado", "en": "Estimated time", "es": "Tiempo estimado"},
    "vo_note": {
        "pt": "Estimativa de voo direto, sem vento. Voos comerciais com escalas levam mais tempo. Não usar para planejamento operacional real.",
        "en": "Direct flight estimate, no wind. Commercial flights with stops take longer. Not for real operational planning.",
        "es": "Estimación de vuelo directo, sin viento. Los vuelos comerciales con escalas tardan más. No usar para planificación operacional real.",
    },
    "vo_h3_other": {"pt": "Tempo de voo de {0} para outros destinos", "en": "Flight time from {0} to other destinations", "es": "Tiempo de vuelo de {0} a otros destinos"},

    # ---- índice de rotas (/rotas) ----
    "ix_title": {"pt": "Distâncias e tempos de voo entre cidades | Aero Jussa", "en": "Distances and flight times between cities | Aero Jussa", "es": "Distancias y tiempos de vuelo entre ciudades | Aero Jussa"},
    "ix_desc": {
        "pt": "Veja a distância, o tempo de voo e o consumo de combustível entre as principais cidades do Brasil e do mundo. Escolha origem e destino por estado e aeródromo.",
        "en": "See the distance, flight time and fuel burn between major cities in Brazil and worldwide. Pick origin and destination by state and airport.",
        "es": "Ve la distancia, el tiempo de vuelo y el consumo de combustible entre las principales ciudades de Brasil y del mundo. Elige origen y destino por estado y aeródromo.",
    },
    "ix_brand": {"pt": "distâncias e tempos de voo", "en": "distances and flight times", "es": "distancias y tiempos de vuelo"},
    "ix_intro": {
        "pt": "Escolha a <strong>origem</strong> e o <strong>destino</strong> pelo estado (ou país) e o aeródromo. No Brasil, o segundo combo lista <strong>todos os aeródromos do estado</strong>; lá fora, as principais cidades. O cálculo abre na <a href=\"/\" style=\"color:var(--cyan)\">calculadora interativa</a>.",
        "en": "Pick the <strong>origin</strong> and <strong>destination</strong> by state (or country) and airport. In Brazil, the second box lists <strong>all airports in the state</strong>; abroad, the major cities. The calculation opens in the <a href=\"/\" style=\"color:var(--cyan)\">interactive calculator</a>.",
        "es": "Elige el <strong>origen</strong> y el <strong>destino</strong> por estado (o país) y aeródromo. En Brasil, el segundo combo lista <strong>todos los aeródromos del estado</strong>; fuera, las principales ciudades. El cálculo abre en la <a href=\"/\" style=\"color:var(--cyan)\">calculadora interactiva</a>.",
    },
    "ix_origin": {"pt": "Origem", "en": "Origin", "es": "Origen"},
    "ix_dest": {"pt": "Destino", "en": "Destination", "es": "Destino"},
    "ix_state": {"pt": "Estado / País", "en": "State / Country", "es": "Estado / País"},
    "ix_aero": {"pt": "Aeródromo", "en": "Airport", "es": "Aeródromo"},
    "ix_placeholder": {"pt": "Digite o nome ou código…", "en": "Type the name or code…", "es": "Escribe el nombre o código…"},
    "ix_btn": {"pt": "Ver rota no mapa →", "en": "See route on the map →", "es": "Ver ruta en el mapa →"},
    "ix_popular": {"pt": "Rotas populares", "en": "Popular routes", "es": "Rutas populares"},
    # picker JS
    "pk_select": {"pt": "— selecione —", "en": "— select —", "es": "— selecciona —"},
    "pk_brazil": {"pt": "Brasil", "en": "Brazil", "es": "Brasil"},
    "pk_intl": {"pt": "Internacional", "en": "International", "es": "Internacional"},
    "pk_loading": {"pt": "Carregando…", "en": "Loading…", "es": "Cargando…"},
    "pk_load_err": {"pt": "Erro ao carregar", "en": "Load error", "es": "Error al cargar"},
    "pk_choose_state": {"pt": "Escolha o estado/país", "en": "Choose the state/country", "es": "Elige el estado/país"},
    "pk_msg_pick": {"pt": "Escolha a origem e o destino na lista.", "en": "Pick the origin and destination from the list.", "es": "Elige el origen y el destino de la lista."},
    "pk_msg_diff": {"pt": "Origem e destino devem ser diferentes.", "en": "Origin and destination must be different.", "es": "El origen y el destino deben ser diferentes."},

    # ---- curiosidades (/curiosidades) ----
    "cu_title": {"pt": "Curiosidades de rotas aéreas: a mais longa, a mais curta e mais | Aero Jussa", "en": "Air route facts: the longest, the shortest and more | Aero Jussa", "es": "Curiosidades de rutas aéreas: la más larga, la más corta y más | Aero Jussa"},
    "cu_desc": {
        "pt": "Curiosidades sobre rotas aéreas calculadas com dados reais: a rota mais longa, a mais curta, a que mais consome combustível e rankings de distância e tempo de voo.",
        "en": "Facts about air routes computed from real data: the longest route, the shortest, the most fuel-hungry and rankings of distance and flight time.",
        "es": "Curiosidades sobre rutas aéreas calculadas con datos reales: la ruta más larga, la más corta, la que más combustible consume y rankings de distancia y tiempo de vuelo.",
    },
    "cu_og_title": {"pt": "Curiosidades de rotas aéreas | Aero Jussa", "en": "Air route facts | Aero Jussa", "es": "Curiosidades de rutas aéreas | Aero Jussa"},
    "cu_og_desc": {"pt": "A rota mais longa, a mais curta e a que mais consome combustível — com dados reais.", "en": "The longest route, the shortest and the most fuel-hungry — with real data.", "es": "La ruta más larga, la más corta y la que más combustible consume — con datos reales."},
    "cu_brand": {"pt": "curiosidades de rotas", "en": "route facts", "es": "curiosidades de rutas"},
    "cu_tag": {"pt": "CURIOSIDADES DE ROTAS", "en": "ROUTE FACTS", "es": "CURIOSIDADES DE RUTAS"},
    "cu_h2": {"pt": "Curiosidades de rotas aéreas", "en": "Air route facts", "es": "Curiosidades de rutas aéreas"},
    "cu_intro": {
        "pt": "Fatos calculados com dados reais entre as principais cidades do Brasil e do mundo. Clique em qualquer rota para ver os detalhes.",
        "en": "Facts computed from real data between major cities in Brazil and worldwide. Click any route to see the details.",
        "es": "Datos calculados con información real entre las principales ciudades de Brasil y del mundo. Haz clic en cualquier ruta para ver los detalles.",
    },
    "cu_c_long": {"pt": "Rota mais longa", "en": "Longest route", "es": "Ruta más larga"},
    "cu_c_long_d": {"pt": "{0} km · do outro lado do mundo", "en": "{0} km · on the other side of the world", "es": "{0} km · al otro lado del mundo"},
    "cu_c_fuel": {"pt": "Mais \"sedenta\" de combustível", "en": "Most fuel-hungry", "es": "La más \"sedienta\" de combustible"},
    "cu_c_fuel_v": {"pt": "{0} toneladas", "en": "{0} tons", "es": "{0} toneladas"},
    "cu_c_fuel_d": {"pt": "{0} → {1} num Airbus A380", "en": "{0} → {1} in an Airbus A380", "es": "{0} → {1} en un Airbus A380"},
    "cu_c_short": {"pt": "Rota mais curta", "en": "Shortest route", "es": "Ruta más corta"},
    "cu_c_short_d": {"pt": "{0} km · só {1} de voo", "en": "{0} km · just {1} of flight", "es": "{0} km · solo {1} de vuelo"},
    "cu_h3_long": {"pt": "As 12 rotas mais longas", "en": "The 12 longest routes", "es": "Las 12 rutas más largas"},
    "cu_h3_short": {"pt": "As 12 rotas mais curtas", "en": "The 12 shortest routes", "es": "Las 12 rutas más cortas"},
    "cu_th_route": {"pt": "Rota", "en": "Route", "es": "Ruta"},
    "cu_th_dist": {"pt": "Distância", "en": "Distance", "es": "Distancia"},
    "cu_th_time": {"pt": "Tempo (A320)", "en": "Time (A320)", "es": "Tiempo (A320)"},
    "cu_note": {
        "pt": "Distância great-circle (linha reta sobre a esfera). Estimativas didáticas, sem vento.",
        "en": "Great-circle distance (straight line over the sphere). Educational estimates, no wind.",
        "es": "Distancia ortodrómica (línea recta sobre la esfera). Estimaciones didácticas, sin viento.",
    },
    "cu_cta": {"pt": "Calcular a minha rota →", "en": "Calculate my route →", "es": "Calcular mi ruta →"},

    # ---- página de tempo por aeródromo (/tempo/{icao}) ----
    "tp_title": {"pt": "METAR e condição de voo (VFR/IFR) em {0} — {1}", "en": "METAR and flight condition (VFR/IFR) at {0} — {1}", "es": "METAR y condición de vuelo (VFR/IFR) en {0} — {1}"},
    "tp_desc": {
        "pt": "METAR mais recente de {0} ({1}) decodificado: vento, visibilidade, teto, temperatura e a condição de voo VFR/IFR. Fonte oficial REDEMET/DECEA.",
        "en": "Latest METAR for {0} ({1}) decoded: wind, visibility, ceiling, temperature and the VFR/IFR flight condition. Official REDEMET/DECEA source.",
        "es": "METAR más reciente de {0} ({1}) decodificado: viento, visibilidad, techo, temperatura y la condición de vuelo VFR/IFR. Fuente oficial REDEMET/DECEA.",
    },
    "tp_brand": {"pt": "metar · condição de voo", "en": "metar · flight condition", "es": "metar · condición de vuelo"},
    "tp_live": {"pt": "consulta ao vivo", "en": "live lookup", "es": "consulta en vivo"},
    "tp_now": {"pt": "agora", "en": "now", "es": "ahora"},
    "tp_sub": {"pt": "{0} · {1} · METAR decodificado e condição de voo (VFR/IFR)", "en": "{0} · {1} · decoded METAR and flight condition (VFR/IFR)", "es": "{0} · {1} · METAR decodificado y condición de vuelo (VFR/IFR)"},
    "tp_c_wind": {"pt": "Vento", "en": "Wind", "es": "Viento"},
    "tp_c_vis": {"pt": "Visibilidade", "en": "Visibility", "es": "Visibilidad"},
    "tp_c_ceil": {"pt": "Teto", "en": "Ceiling", "es": "Techo"},
    "tp_c_temp": {"pt": "Temp/orvalho", "en": "Temp/dew point", "es": "Temp/rocío"},
    "tp_c_cond": {"pt": "Condição", "en": "Condition", "es": "Condición"},
    "tp_calm": {"pt": "calmo", "en": "calm", "es": "calma"},
    "tp_noceil": {"pt": "sem teto", "en": "no ceiling", "es": "sin techo"},
    "tp_obs": {"pt": "(obs.)", "en": "(obs.)", "es": "(obs.)"},
    "tp_open": {"pt": "Abrir a consulta interativa (METAR + TAF + janela de voo) →", "en": "Open the interactive lookup (METAR + TAF + flight window) →", "es": "Abrir la consulta interactiva (METAR + TAF + ventana de vuelo) →"},
    "tp_other": {"pt": "Tempo em outros aeródromos", "en": "Weather at other airports", "es": "Tiempo en otros aeródromos"},
    "tp_note": {
        "pt": "Dados oficiais da <strong>REDEMET/DECEA</strong>, atualizados periodicamente (último METAR gravado). Classificação VFR/IFR automática por teto e visibilidade, de apoio — não substitui o briefing oficial.",
        "en": "Official <strong>REDEMET/DECEA</strong> data, updated periodically (latest recorded METAR). Automatic VFR/IFR classification by ceiling and visibility, for support — it does not replace the official briefing.",
        "es": "Datos oficiales de <strong>REDEMET/DECEA</strong>, actualizados periódicamente (último METAR registrado). Clasificación VFR/IFR automática por techo y visibilidad, de apoyo — no sustituye el briefing oficial.",
    },
    "tp_empty": {
        "pt": "Ainda não temos um METAR recente deste aeródromo no histórico. Use a <a href=\"/tempo\" style=\"color:var(--cyan)\">consulta interativa</a> para buscar ao vivo.",
        "en": "We don't have a recent METAR for this airport in the history yet. Use the <a href=\"/tempo\" style=\"color:var(--cyan)\">interactive lookup</a> to fetch it live.",
        "es": "Aún no tenemos un METAR reciente de este aeródromo en el histórico. Usa la <a href=\"/tempo\" style=\"color:var(--cyan)\">consulta interactiva</a> para buscarlo en vivo.",
    },
    "tp_metar_of": {"pt": "METAR decodificado e condição de voo (VFR/IFR)", "en": "decoded METAR and flight condition (VFR/IFR)", "es": "METAR decodificado y condición de vuelo (VFR/IFR)"},
}


def _t(key: str, lang: str, *args) -> str:
    """Texto SEO no idioma (cai para pt), com .format(*args) opcional."""
    entry = TR.get(key, {})
    s = entry.get(lang) or entry.get("pt") or key
    return s.format(*args) if args else s


# Caminhos root-relative que ganham prefixo de idioma nas páginas traduzidas.
# Exclui /static, /api e /tempo/{icao} (este último ainda só em pt — Leva 2 futura).
_PREFIX_EXACT = {"/", "/comparar", "/tempo", "/radar", "/cartas", "/sobre", "/rotas", "/curiosidades"}
_LINK_RE = re.compile(r'(href|action)="(/[^":]*)"')
_LANGSW_RE = re.compile(r'<div class="langsw".*?</div>', re.S)


def _localize_links(html: str, lang: str) -> str:
    """Reescreve links internos para o prefixo do idioma (en/es).

    O seletor de idioma (bloco .langsw) é protegido: seus hrefs já vêm corretos
    por idioma (o link pt deve ficar SEM prefixo), então não pode ser reescrito.
    """
    if lang == i18n.DEFAULT:
        return html
    pre = i18n.prefix(lang)
    stash: list[str] = []

    def keep(m: "re.Match[str]") -> str:
        stash.append(m.group(0))
        return f"\x00SW{len(stash) - 1}\x00"

    html = _LANGSW_RE.sub(keep, html)

    def rep(m: "re.Match[str]") -> str:
        attr, url = m.group(1), m.group(2)
        path = re.split(r"[?#]", url, 1)[0]
        if path in _PREFIX_EXACT or path.startswith(("/rota/", "/tempo/")):
            return f'{attr}="{i18n.loc_url(pre, url)}"'
        return m.group(0)

    html = _LINK_RE.sub(rep, html)
    for i, block in enumerate(stash):
        html = html.replace(f"\x00SW{i}\x00", block)
    return html

# Google tag (gtag.js) — inserido no <head> de toda página gerada.
# Emite dimensões para segmentar receita por idioma e rota no GA4:
#   content_group -> dimensão NATIVA "Grupo de conteúdo" (seção da página).
#   page_language -> dimensão personalizada: idioma do CONTEÚDO (pt/en/es),
#                    distinto do idioma do navegador que o GA4 já coleta.
#   page_route    -> dimensão personalizada: slug da rota / ICAO, unificando
#                    as versões pt/en/es da mesma página num único valor.
GTAG_ID = "G-7C0B22Z8EC"

def gtag_block(lang: str = "pt", content_group: str = "", route: str = "") -> str:
    params = {"page_language": lang}
    if content_group:
        params["content_group"] = content_group
    if route:
        params["page_route"] = route
    cfg = json.dumps(params, ensure_ascii=False)
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={GTAG_ID}"></script>\n'
        "<script>\n"
        "  window.dataLayer = window.dataLayer || [];\n"
        "  function gtag(){dataLayer.push(arguments);}\n"
        "  gtag('js', new Date());\n"
        f"  gtag('config', '{GTAG_ID}', {cfg});\n"
        "</script>\n"
        '<script defer src="/static/track.js"></script>'
    )

# PWA — manifest, ícones e registro do service worker. Inserido em todo <head>.
PWA_HEAD = (
    '<link rel="manifest" href="/manifest.webmanifest" />\n'
    '<meta name="theme-color" content="#070d18" />\n'
    '<meta name="mobile-web-app-capable" content="yes" />\n'
    '<meta name="apple-mobile-web-app-capable" content="yes" />\n'
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />\n'
    '<meta name="apple-mobile-web-app-title" content="Aero Jussa" />\n'
    '<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png" />\n'
    '<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png" />\n'
    '<link rel="icon" type="image/png" sizes="16x16" href="/static/icons/favicon-16.png" />\n'
    "<script>if('serviceWorker' in navigator){var _swR=false;"
    "navigator.serviceWorker.addEventListener('controllerchange',function(){"
    "if(_swR)return;_swR=true;location.reload();});"
    "window.addEventListener('load',function(){"
    "navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(function(){});});}</script>\n"
    '<script defer src="/static/install.js"></script>'
)

# Aeronaves da tabela consolidada de cada página de rota (boa amplitude de portes).
TIME_COMPARE = ["phenom300", "e195e2", "a320neo", "b738", "b77w"]
DEFAULT_AC = "a320neo"


@dataclass(frozen=True)
class City:
    slug: str
    name: str
    code: str  # IATA do aeroporto principal


# Cidades populares (BR + internacionais). Códigos IATA presentes no OurAirports.
# As cidades brasileiras vêm primeiro (usadas como origens no índice /rotas).
CITIES: list[City] = [
    # --- Brasil ---
    City("sao-paulo", "São Paulo", "GRU"),
    City("rio-de-janeiro", "Rio de Janeiro", "GIG"),
    City("brasilia", "Brasília", "BSB"),
    City("belo-horizonte", "Belo Horizonte", "CNF"),
    City("salvador", "Salvador", "SSA"),
    City("recife", "Recife", "REC"),
    City("fortaleza", "Fortaleza", "FOR"),
    City("porto-alegre", "Porto Alegre", "POA"),
    City("curitiba", "Curitiba", "CWB"),
    City("manaus", "Manaus", "MAO"),
    City("belem", "Belém", "BEL"),
    City("florianopolis", "Florianópolis", "FLN"),
    City("natal", "Natal", "NAT"),
    City("goiania", "Goiânia", "GYN"),
    City("vitoria", "Vitória", "VIX"),
    City("cuiaba", "Cuiabá", "CGB"),
    City("campo-grande", "Campo Grande", "CGR"),
    City("joao-pessoa", "João Pessoa", "JPA"),
    City("maceio", "Maceió", "MCZ"),
    City("campinas", "Campinas", "VCP"),
    City("foz-do-iguacu", "Foz do Iguaçu", "IGU"),
    City("navegantes", "Navegantes", "NVT"),
    # --- Internacionais ---
    City("lisboa", "Lisboa", "LIS"),
    City("porto", "Porto", "OPO"),
    City("madri", "Madri", "MAD"),
    City("barcelona", "Barcelona", "BCN"),
    City("londres", "Londres", "LHR"),
    City("paris", "Paris", "CDG"),
    City("frankfurt", "Frankfurt", "FRA"),
    City("amsterda", "Amsterdã", "AMS"),
    City("roma", "Roma", "FCO"),
    City("milao", "Milão", "MXP"),
    City("munique", "Munique", "MUC"),
    City("zurique", "Zurique", "ZRH"),
    City("dublin", "Dublin", "DUB"),
    City("istambul", "Istambul", "IST"),
    City("nova-york", "Nova York", "JFK"),
    City("miami", "Miami", "MIA"),
    City("orlando", "Orlando", "MCO"),
    City("los-angeles", "Los Angeles", "LAX"),
    City("chicago", "Chicago", "ORD"),
    City("atlanta", "Atlanta", "ATL"),
    City("boston", "Boston", "BOS"),
    City("toronto", "Toronto", "YYZ"),
    City("cancun", "Cancún", "CUN"),
    City("cidade-do-mexico", "Cidade do México", "MEX"),
    City("panama", "Panamá", "PTY"),
    City("buenos-aires", "Buenos Aires", "EZE"),
    City("santiago", "Santiago", "SCL"),
    City("montevideu", "Montevidéu", "MVD"),
    City("assuncao", "Assunção", "ASU"),
    City("lima", "Lima", "LIM"),
    City("bogota", "Bogotá", "BOG"),
    City("dubai", "Dubai", "DXB"),
    City("doha", "Doha", "DOH"),
    City("joanesburgo", "Joanesburgo", "JNB"),
    City("singapura", "Singapura", "SIN"),
    City("toquio", "Tóquio", "HND"),
    City("pequim", "Pequim", "PEK"),
    City("sydney", "Sydney", "SYD"),
]

CITY_BY_SLUG: dict[str, City] = {c.slug: c for c in CITIES}

# Agrupamento das cidades para os seletores dependentes da página /rotas:
# (grupo, rótulo) — grupo "Brasil" usa o estado (UF) como rótulo; "Internacional"
# usa o país. O primeiro combo lista os rótulos; o segundo, os aeródromos do rótulo.
REGIONS: dict[str, tuple[str, str]] = {
    # --- Brasil (rótulo = estado) ---
    "sao-paulo": ("Brasil", "São Paulo"),
    "campinas": ("Brasil", "São Paulo"),
    "rio-de-janeiro": ("Brasil", "Rio de Janeiro"),
    "brasilia": ("Brasil", "Distrito Federal"),
    "belo-horizonte": ("Brasil", "Minas Gerais"),
    "salvador": ("Brasil", "Bahia"),
    "recife": ("Brasil", "Pernambuco"),
    "fortaleza": ("Brasil", "Ceará"),
    "porto-alegre": ("Brasil", "Rio Grande do Sul"),
    "curitiba": ("Brasil", "Paraná"),
    "foz-do-iguacu": ("Brasil", "Paraná"),
    "manaus": ("Brasil", "Amazonas"),
    "belem": ("Brasil", "Pará"),
    "florianopolis": ("Brasil", "Santa Catarina"),
    "navegantes": ("Brasil", "Santa Catarina"),
    "natal": ("Brasil", "Rio Grande do Norte"),
    "goiania": ("Brasil", "Goiás"),
    "vitoria": ("Brasil", "Espírito Santo"),
    "cuiaba": ("Brasil", "Mato Grosso"),
    "campo-grande": ("Brasil", "Mato Grosso do Sul"),
    "joao-pessoa": ("Brasil", "Paraíba"),
    "maceio": ("Brasil", "Alagoas"),
    # --- Internacional (rótulo = país) ---
    "lisboa": ("Internacional", "Portugal"),
    "porto": ("Internacional", "Portugal"),
    "madri": ("Internacional", "Espanha"),
    "barcelona": ("Internacional", "Espanha"),
    "londres": ("Internacional", "Reino Unido"),
    "paris": ("Internacional", "França"),
    "frankfurt": ("Internacional", "Alemanha"),
    "munique": ("Internacional", "Alemanha"),
    "amsterda": ("Internacional", "Holanda"),
    "roma": ("Internacional", "Itália"),
    "milao": ("Internacional", "Itália"),
    "zurique": ("Internacional", "Suíça"),
    "dublin": ("Internacional", "Irlanda"),
    "istambul": ("Internacional", "Turquia"),
    "nova-york": ("Internacional", "Estados Unidos"),
    "miami": ("Internacional", "Estados Unidos"),
    "orlando": ("Internacional", "Estados Unidos"),
    "los-angeles": ("Internacional", "Estados Unidos"),
    "chicago": ("Internacional", "Estados Unidos"),
    "atlanta": ("Internacional", "Estados Unidos"),
    "boston": ("Internacional", "Estados Unidos"),
    "toronto": ("Internacional", "Canadá"),
    "cancun": ("Internacional", "México"),
    "cidade-do-mexico": ("Internacional", "México"),
    "panama": ("Internacional", "Panamá"),
    "buenos-aires": ("Internacional", "Argentina"),
    "santiago": ("Internacional", "Chile"),
    "montevideu": ("Internacional", "Uruguai"),
    "assuncao": ("Internacional", "Paraguai"),
    "lima": ("Internacional", "Peru"),
    "bogota": ("Internacional", "Colômbia"),
    "dubai": ("Internacional", "Emirados Árabes"),
    "doha": ("Internacional", "Catar"),
    "joanesburgo": ("Internacional", "África do Sul"),
    "singapura": ("Internacional", "Singapura"),
    "toquio": ("Internacional", "Japão"),
    "pequim": ("Internacional", "China"),
    "sydney": ("Internacional", "Austrália"),
}

# --------------------------------------------------------------------------- #
# Curadoria dos pares /rota (poda + direção canônica).
#
# O produto cartesiano (60×59, em duas variantes /rota e /voo) gerava ~7 mil
# páginas quase-duplicadas que o Google detectava mas se recusava a indexar
# ("thin content"). Aqui restringimos a um conjunto com demanda de busca
# plausível do público BR e mantemos UMA direção canônica por par (a ordem de
# aparição em CITIES). A direção reversa e os pares fora do conjunto são
# tratados em main.py (301 para a canônica / 404).
# --------------------------------------------------------------------------- #
_BR_SLUGS: set[str] = {slug for slug, (grupo, _) in REGIONS.items() if grupo == "Brasil"}

# Hubs brasileiros de maior tráfego (âncoras das rotas domésticas fortes).
BR_HUBS: set[str] = {
    "sao-paulo", "rio-de-janeiro", "brasilia", "belo-horizonte", "salvador",
    "recife", "fortaleza", "porto-alegre", "curitiba", "campinas",
}
# Destinos internacionais de alta busca do público brasileiro.
INTL_TOP: set[str] = {
    "lisboa", "porto", "madri", "barcelona", "londres", "paris", "frankfurt",
    "roma", "nova-york", "miami", "orlando", "buenos-aires", "santiago",
    "montevideu", "cancun", "toronto", "dubai",
}


def _keep_pair(a: City, b: City) -> bool:
    """Regra de poda (agressiva): mantém só pares com demanda plausível."""
    abr, bbr = a.slug in _BR_SLUGS, b.slug in _BR_SLUGS
    if abr and bbr:                       # doméstico: exige ao menos um hub
        return a.slug in BR_HUBS or b.slug in BR_HUBS
    if abr != bbr:                        # BR ↔ internacional
        br, intl = (a, b) if abr else (b, a)
        return br.slug in BR_HUBS and intl.slug in INTL_TOP
    return False                          # internacional ↔ internacional: fora


def route_pairs() -> list[tuple[City, City]]:
    """Pares canônicos mantidos (não-ordenados; origem = a 1ª em CITIES)."""
    out: list[tuple[City, City]] = []
    for i, a in enumerate(CITIES):
        for b in CITIES[i + 1:]:
            if _keep_pair(a, b):
                out.append((a, b))
    return out


ROUTE_PAIRS: list[tuple[City, City]] = route_pairs()
ROUTE_PAIR_SET: set[tuple[str, str]] = {(o.slug, d.slug) for o, d in ROUTE_PAIRS}


def canonical_pair(o_slug: str, d_slug: str) -> tuple[str, str] | None:
    """Direção canônica de um par mantido, ou None se o par foi podado."""
    if (o_slug, d_slug) in ROUTE_PAIR_SET:
        return (o_slug, d_slug)
    if (d_slug, o_slug) in ROUTE_PAIR_SET:
        return (d_slug, o_slug)
    return None


def related_pairs(origin: City, dest: City, limit: int = 8) -> list[tuple[City, City]]:
    """Até `limit` pares canônicos envolvendo `origin` (preferência) ou `dest`,
    excluindo o par atual — para os links de 'rotas relacionadas'."""
    cur = (origin.slug, dest.slug)
    out = [p for p in ROUTE_PAIRS
           if origin.slug in (p[0].slug, p[1].slug) and (p[0].slug, p[1].slug) != cur]
    if len(out) < limit:
        seen = {(p[0].slug, p[1].slug) for p in out}
        for p in ROUTE_PAIRS:
            key = (p[0].slug, p[1].slug)
            if dest.slug in key and key != cur and key not in seen:
                out.append(p)
    return out[:limit]


# Estados do Brasil (iso_region do OurAirports). Primeiro combo da origem/destino.
BR_STATES: list[tuple[str, str]] = [
    ("BR-AC", "Acre"), ("BR-AL", "Alagoas"), ("BR-AP", "Amapá"), ("BR-AM", "Amazonas"),
    ("BR-BA", "Bahia"), ("BR-CE", "Ceará"), ("BR-DF", "Distrito Federal"),
    ("BR-ES", "Espírito Santo"), ("BR-GO", "Goiás"), ("BR-MA", "Maranhão"),
    ("BR-MT", "Mato Grosso"), ("BR-MS", "Mato Grosso do Sul"), ("BR-MG", "Minas Gerais"),
    ("BR-PA", "Pará"), ("BR-PB", "Paraíba"), ("BR-PR", "Paraná"), ("BR-PE", "Pernambuco"),
    ("BR-PI", "Piauí"), ("BR-RJ", "Rio de Janeiro"), ("BR-RN", "Rio Grande do Norte"),
    ("BR-RS", "Rio Grande do Sul"), ("BR-RO", "Rondônia"), ("BR-RR", "Roraima"),
    ("BR-SC", "Santa Catarina"), ("BR-SP", "São Paulo"), ("BR-SE", "Sergipe"),
    ("BR-TO", "Tocantins"),
]

# JS dos seletores da página /rotas. Mantido como string normal (tem chaves {}
# que quebrariam a f-string do template).
# Fluxo: combo de Estado/País → campo de aeródromo que FILTRA conforme a digitação
# (autocomplete). Brasil: aeródromos do estado vêm de /api/aerodromos (dados locais
# do OurAirports) e são filtrados em memória. Internacional: lista curada embutida.
# O botão navega para a calculadora interativa (/?origin=&dest=).
_ROUTES_PICKER_JS = """
(function () {
  var cfg = JSON.parse(document.getElementById('cities-data').textContent);
  function norm(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, ''); }
  function opt(value, text) {
    var o = document.createElement('option'); o.value = value; o.textContent = text; return o;
  }
  var I = cfg.i18n || {};
  function fillStates(sel) {
    sel.appendChild(opt('', I.select || '— selecione —'));
    var br = document.createElement('optgroup'); br.label = I.brazil || 'Brasil';
    cfg.states.forEach(function (s) { br.appendChild(opt('BR|' + s.uf, s.name)); });
    sel.appendChild(br);
    var seen = {};
    cfg.intl.forEach(function (c) { seen[c.country] = true; });
    var intl = document.createElement('optgroup'); intl.label = I.intl || 'Internacional';
    Object.keys(seen).sort(function (a, b) { return a.localeCompare(b, 'pt-BR'); })
      .forEach(function (c) { intl.appendChild(opt('INT|' + c, c)); });
    sel.appendChild(intl);
  }
  function setState(sel, val) {
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === val) { sel.selectedIndex = i; return; }
    }
  }
  // Cada lado (origem/destino) gerencia seu combo de estado + campo com autocomplete.
  function Side(stateId, inputId, acId) {
    var stateSel = document.getElementById(stateId);
    var input = document.getElementById(inputId);
    var ac = document.getElementById(acId);
    var list = [], code = null;

    function hide() { ac.classList.remove('open'); ac.innerHTML = ''; }
    function choose(a) { code = a.code; input.value = a.name + ' (' + a.code + ')'; hide(); }
    function render(items) {
      ac.innerHTML = '';
      items.slice(0, 12).forEach(function (a) {
        var d = document.createElement('div');
        var cs = document.createElement('span'); cs.className = 'code'; cs.textContent = a.code;
        var ns = document.createElement('span'); ns.className = 'nm';
        ns.textContent = ' ' + a.name + (a.city ? ' — ' + a.city : '');
        d.appendChild(cs); d.appendChild(ns);
        d.addEventListener('mousedown', function (e) { e.preventDefault(); choose(a); });
        ac.appendChild(d);
      });
      if (items.length) ac.classList.add('open'); else hide();
    }
    function filter() {
      code = null;
      var q = norm(input.value);
      if (!q) { render(list); return; }
      render(list.filter(function (a) {
        return norm(a.code).indexOf(q) >= 0 || norm(a.name).indexOf(q) >= 0 || norm(a.city).indexOf(q) >= 0;
      }));
    }
    function resolveTyped() {
      if (code) return;
      var q = norm(input.value);
      var m = list.filter(function (a) {
        return norm(a.code) === q || norm(a.name + ' (' + a.code + ')') === q;
      })[0];
      if (m) choose(m);
    }
    function setList(items, preferCode) {
      list = items; code = null; input.value = ''; input.disabled = false;
      input.placeholder = I.placeholder || 'Digite o nome ou código…';
      if (preferCode) {
        var f = items.filter(function (a) { return a.code === preferCode; })[0];
        if (f) choose(f);
      }
    }
    function load(value, preferCode) {
      hide();
      if (!value) { list = []; code = null; input.value = ''; input.disabled = true; input.placeholder = I.choose_state || 'Escolha o estado/país'; return; }
      var p = value.split('|');
      if (p[0] === 'BR') {
        list = []; code = null; input.value = ''; input.disabled = true; input.placeholder = I.loading || 'Carregando…';
        fetch('/api/aerodromos?region=' + encodeURIComponent(p[1]))
          .then(function (r) { return r.json(); })
          .then(function (j) { setList(j.aerodromos || [], preferCode); })
          .catch(function () { list = []; input.disabled = false; input.placeholder = I.load_err || 'Erro ao carregar'; });
      } else {
        setList(cfg.intl.filter(function (c) { return c.country === p[1]; })
          .map(function (c) { return { code: c.code, name: c.name, city: '' }; }), preferCode);
      }
    }
    input.addEventListener('input', filter);
    input.addEventListener('focus', filter);
    input.addEventListener('blur', function () { setTimeout(function () { resolveTyped(); hide(); }, 150); });
    stateSel.addEventListener('change', function () { load(stateSel.value); });
    return {
      state: stateSel, load: load,
      pick: function (v, pc) { setState(stateSel, v); load(v, pc); },
      get code() { return code; },
    };
  }
  var o = Side('o-state', 'o-air-input', 'o-air-ac');
  var d = Side('d-state', 'd-air-input', 'd-air-ac');
  fillStates(o.state); fillStates(d.state);
  // Abre vazio: o usuário escolhe estado/país e depois o aeródromo.
  o.load(''); d.load('');
  function go() {
    var oc = o.code, dc = d.code, msg = document.getElementById('r-msg');
    if (!oc || !dc) { if (msg) msg.textContent = I.msg_pick || 'Escolha a origem e o destino na lista.'; return; }
    if (oc === dc) { if (msg) msg.textContent = I.msg_diff || 'Origem e destino devem ser diferentes.'; return; }
    window.location.href = (cfg.prefix || '') + '/?origin=' + encodeURIComponent(oc) + '&dest=' + encodeURIComponent(dc);
  }
  document.getElementById('go-rota').addEventListener('click', go);
})();
"""


def _fmt(n: float, lang: str = "pt") -> str:
    """Inteiro com separador de milhar por idioma: pt/es usam ponto, en usa vírgula."""
    s = f"{round(n):,}"
    return s if lang == "en" else s.replace(",", ".")


def _nav(active: str = "", lang: str = "pt") -> str:
    """Menu de navegação compartilhado por todas as páginas (links prefixados depois)."""
    items = [
        ("/", "nav_calc"),
        ("/comparar", "nav_compare"),
        ("/tempo", "nav_tempo"),
        ("/radar", "nav_radar"),
        ("/cartas", "nav_cartas"),
        ("/curiosidades", "nav_curio"),
        ("/rotas", "nav_rotas"),
    ]
    links = "".join(
        f'<a href="{href}"{" class=\"active\"" if href == active else ""}>{_t(key, lang)}</a>'
        for href, key in items
    )
    return f'<nav class="nav">{links}</nav>'


# --------------------------------------------------------------------------- #
# Mapa em SVG (renderizado no servidor, sem JS) — projeção equiretangular.
# --------------------------------------------------------------------------- #
_W, _H, _PAD = 680, 300, 18


def _proj(lat: float, lon: float) -> tuple[float, float]:
    x = _PAD + ((lon + 180) / 360) * (_W - 2 * _PAD)
    y = _PAD + ((90 - lat) / 180) * (_H - 2 * _PAD)
    return x, y


def _svg_map(a: Point, b: Point, code_a: str, code_b: str) -> str:
    g: list[str] = []
    for lon in range(-150, 151, 30):
        x, _ = _proj(0, lon)
        g.append(f'<line x1="{x:.1f}" y1="{_PAD}" x2="{x:.1f}" y2="{_H - _PAD}" stroke="#102540" stroke-width="1"/>')
    for lat in range(-60, 61, 30):
        _, y = _proj(lat, 0)
        g.append(f'<line x1="{_PAD}" y1="{y:.1f}" x2="{_W - _PAD}" y2="{y:.1f}" stroke="#102540" stroke-width="1"/>')
    _, eqy = _proj(0, 0)
    g.append(f'<line x1="{_PAD}" y1="{eqy:.1f}" x2="{_W - _PAD}" y2="{eqy:.1f}" stroke="#16314f" stroke-width="1.4"/>')

    pts = [_proj(p[0], p[1]) for p in calc.great_circle_path(a, b, 64)]
    # quebra a linha em saltos pela antimeridiano (180°)
    segs: list[list[tuple[float, float]]] = [[]]
    for i, p in enumerate(pts):
        if i > 0 and abs(p[0] - pts[i - 1][0]) > _W * 0.5:
            segs.append([])
        segs[-1].append(p)
    for s in segs:
        if len(s) > 1:
            pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in s)
            g.append(f'<polyline points="{pts_str}" fill="none" stroke="#1fd8e6" stroke-width="2" stroke-linecap="round" opacity=".95"/>')

    ax, ay = _proj(a.lat, a.lon)
    bx, by = _proj(b.lat, b.lon)
    g.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="4.5" fill="#5ef08a"/>')
    g.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="4.5" fill="#ffb23e"/>')
    g.append(f'<text x="{ax:.1f}" y="{ay - 11:.1f}" fill="#5ef08a" font-family="Chakra Petch" font-size="12" font-weight="700" text-anchor="middle">{code_a}</text>')
    g.append(f'<text x="{bx:.1f}" y="{by - 11:.1f}" fill="#ffb23e" font-family="Chakra Petch" font-size="12" font-weight="700" text-anchor="middle">{code_b}</text>')

    return (
        f'<svg class="plot" viewBox="0 0 {_W} {_H}" preserveAspectRatio="xMidYMid slice" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(g)}</svg>'
    )


# --------------------------------------------------------------------------- #
# Página de rota
def _route_jsonld(origin: City, dest: City, faq_pairs: list[tuple[str, str]],
                  canonical: str, lang: str) -> str:
    """Dados estruturados schema.org da página de rota: FAQPage + BreadcrumbList.

    Reforça para o Google a intenção 'distância/tempo de voo entre X e Y'. As
    perguntas/respostas são as MESMAS exibidas na FAQ visível (fonte única).
    """
    graph = [
        {
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": ans}}
                for q, ans in faq_pairs
            ],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": _t("nav_calc", lang),
                 "item": f"{BASE_URL}{i18n.loc(lang, '/')}"},
                {"@type": "ListItem", "position": 2, "name": _t("nav_rotas", lang),
                 "item": f"{BASE_URL}{i18n.loc(lang, '/rotas')}"},
                {"@type": "ListItem", "position": 3,
                 "name": f"{origin.name} → {dest.name}", "item": canonical},
            ],
        },
    ]
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False)
    return f'<script type="application/ld+json">{payload}</script>'


# --------------------------------------------------------------------------- #
def render_route_page(store: AirportStore, origin: City, dest: City, lang: str = "pt") -> str | None:
    a = store.resolve(origin.code)
    b = store.resolve(dest.code)
    if a is None or b is None or origin.slug == dest.slug:
        return None

    pa, pb = Point(a.lat, a.lon), Point(b.lat, b.lon)
    dist_nm = calc.great_circle_distance_nm(pa, pb)
    dist_km = dist_nm * calc.NM_TO_KM
    bearing = round(calc.initial_bearing_deg(pa, pb))

    default = aircraft_mod.get(DEFAULT_AC)
    default_h = calc.flight_time_hours(dist_nm, default.cruise_kt)

    # tabela consolidada: cruzeiro, tempo de bloco e combustível por aeronave
    rows = []
    for key in TIME_COMPARE:
        ac = aircraft_mod.get(key)
        h = calc.flight_time_hours(dist_nm, ac.cruise_kt)
        fuel = calc.fuel_estimate(h, ac.burn_kg_h)
        rows.append(
            f"<tr><td>{ac.name}</td><td>{ac.cruise_kt} kt</td>"
            f"<td>{calc.format_hm(h)}</td><td>{_fmt(fuel['total_kg'], lang)} kg</td></tr>"
        )
    table = "".join(rows)

    # rotas relacionadas — apenas pares canônicos que existem
    rel_links = "".join(
        f'<a class="rel" href="/rota/{o.slug}/{d.slug}">{o.name} → {d.name}</a>'
        for o, d in related_pairs(origin, dest)
    )

    svg = _svg_map(pa, pb, a.code, b.code)
    base_path = f"/rota/{origin.slug}/{dest.slug}"
    canonical = f"{BASE_URL}{i18n.prefix(lang)}{base_path}"

    # Resposta direta (topo) + FAQ (visível e JSON-LD) para o featured snippet.
    bearing_s = f"{bearing:03d}"
    answer = _t("rt_answer", lang, origin.name, dest.name, _fmt(dist_km, lang),
                _fmt(dist_nm, lang), calc.format_hm(default_h), default.name, bearing_s)
    faq_pairs = [
        (_t("faq_q_dist", lang, origin.name, dest.name),
         _t("faq_a_dist", lang, origin.name, dest.name, _fmt(dist_km, lang), _fmt(dist_nm, lang))),
        (_t("faq_q_time", lang, origin.name, dest.name),
         _t("faq_a_time", lang, origin.name, dest.name, calc.format_hm(default_h), default.name)),
        (_t("faq_q_bearing", lang, origin.name, dest.name),
         _t("faq_a_bearing", lang, origin.name, dest.name, bearing_s)),
    ]
    faq_html = "".join(
        f'<div class="faq-q">{q}</div><p class="faq-a">{ans}</p>' for q, ans in faq_pairs
    )
    jsonld = _route_jsonld(origin, dest, faq_pairs, canonical, lang)

    title = _t("rt_title", lang, origin.name, dest.name, _fmt(dist_km, lang))
    desc = _t("rt_desc", lang, origin.name, a.code, dest.name, b.code,
              _fmt(dist_km, lang), _fmt(dist_nm, lang), calc.format_hm(default_h))

    html = f"""<!DOCTYPE html>
<html lang="{i18n.html_lang(lang)}">
<head>
<meta charset="UTF-8" />
{gtag_block(lang, "rota", f"{origin.slug}-{dest.slug}")}
{PWA_HEAD}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title} | Aero Jussa</title>
<meta name="description" content="{desc}" />
{i18n.hreflang_block(base_path, lang)}
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{canonical}" />
{jsonld}
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/static/style.css" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4915226991502750" crossorigin="anonymous"></script>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="badge">
      <svg viewBox="0 0 24 24" fill="none" stroke="#1fd8e6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12l8-1 4-8 2 0-1 8 6 1-6 1 1 8-2 0-4-8-8-1z" /></svg>
    </div>
    <h1 style="font-size:18px">Aero Jussa<small>{_t("brand_planning", lang)}</small></h1>
  </div>

  <div class="tag"><span>{_t("rt_tag", lang, a.code, b.code)}</span><span><a href="/rotas" style="color:var(--muted);text-decoration:none">{_t("all_routes", lang)}</a></span></div>
  {_nav("/rotas", lang)}
  {i18n.switcher_block(base_path, lang)}

  <h2 style="font-family:'Chakra Petch',sans-serif;font-size:22px;letter-spacing:.02em;margin:6px 0 10px">{_t("rt_h2", lang, origin.name, dest.name)}</h2>
  <div class="answer">{answer}</div>
  <p style="font-size:14px;color:#c3d3e6;margin-bottom:16px">
    {_t("rt_intro", lang, origin.name, a.name, a.code, dest.name, b.name, b.code,
        _fmt(dist_km, lang), _fmt(dist_nm, lang), f"{bearing:03d}", default.name, calc.format_hm(default_h))}
  </p>

  <div class="panel">
    {svg}
    <div class="readouts">
      <div class="cell cyan"><div class="k">{_t("rt_ro_dist", lang)}</div><div class="v">{_fmt(dist_nm, lang)}<span class="u">nm</span></div></div>
      <div class="cell"><div class="k">{_t("rt_ro_dist", lang)}</div><div class="v">{_fmt(dist_km, lang)}<span class="u">km</span></div></div>
      <div class="cell green"><div class="k">{_t("rt_ro_time", lang, default.name)}</div><div class="v">{calc.format_hm(default_h)}</div></div>
      <div class="cell"><div class="k">{_t("rt_ro_bearing", lang)}</div><div class="v">{bearing:03d}<span class="u">°</span></div></div>
    </div>
  </div>

  <a class="cta-link" href="/?origin={a.code}&dest={b.code}"
     style="display:inline-block;margin:16px 0;background:rgba(31,216,230,.12);border:1px solid var(--cyan);color:var(--cyan);padding:12px 20px;border-radius:9px;text-decoration:none;font-family:'Chakra Petch',sans-serif;font-weight:600;letter-spacing:.04em">
    {_t("rt_cta", lang)}
  </a>

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:20px 0 8px">{_t("rt_h3_fuel", lang)}</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13.5px;color:#c3d3e6">
    <thead><tr style="color:var(--muted);text-align:left;font-family:'JetBrains Mono',monospace;font-size:11px">
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("rt_th_ac", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("vo_th_cruise", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("rt_th_block", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("rt_th_fuel", lang)}</th>
    </tr></thead>
    <tbody>{table}</tbody>
  </table>
  <p style="font-size:11px;color:var(--muted);margin-top:8px;font-family:'JetBrains Mono',monospace">{_t("note_est", lang)}</p>

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:24px 0 8px">{_t("faq_h", lang)}</h3>
  <div class="faq">{faq_html}</div>

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:24px 0 10px">{_t("rt_h3_other", lang, origin.name)}</h3>
  <div style="display:flex;flex-wrap:wrap;gap:8px">{rel_links}</div>

  <footer class="foot" style="margin-top:28px">
    <a href="/" style="color:var(--cyan);text-decoration:none">{_t("foot_calc", lang)}</a> ·
    <a href="/rotas" style="color:var(--cyan);text-decoration:none">{_t("foot_routes", lang)}</a> ·
    <a href="/sobre" style="color:var(--cyan);text-decoration:none">{_t("foot_about", lang)}</a> ·
    <a href="/static/privacidade.html" style="color:var(--cyan);text-decoration:none">{_t("foot_privacy", lang)}</a>
  </footer>
</div>
<style>.rel{{background:var(--panel-2);border:1px solid var(--line);border-radius:30px;padding:7px 13px;font-size:12.5px;color:var(--cyan);text-decoration:none}}.rel:hover{{background:#16335a}}table td{{padding:9px 6px;border-bottom:1px solid var(--line)}}
.answer{{background:rgba(31,216,230,.08);border-left:3px solid var(--cyan);border-radius:8px;padding:12px 14px;font-size:14.5px;color:#dce6f3;line-height:1.55;margin:0 0 16px}}
.faq-q{{font-family:'Chakra Petch',sans-serif;font-weight:600;color:var(--ink);font-size:15px;margin-top:14px}}
.faq-a{{font-size:13.5px;color:#c3d3e6;line-height:1.55;margin:5px 0 0}}</style>
</body>
</html>"""
    return _localize_links(html, lang)


def render_routes_index(lang: str = "pt") -> str:
    """Índice de rotas: seletores dependentes (estado → aeródromo) + rotas populares."""
    # Config dos combos: estados do Brasil (aeródromos vêm da API por estado) +
    # cidades internacionais curadas (embutidas, pois não há API por país aqui).
    cfg = {
        "states": [{"uf": uf, "name": name} for uf, name in BR_STATES],
        "intl": [
            {"name": c.name, "code": c.code, "country": REGIONS[c.slug][1]}
            for c in CITIES
            if REGIONS[c.slug][0] == "Internacional"
        ],
        "prefix": i18n.prefix(lang),
        "i18n": {
            "select": _t("pk_select", lang), "brazil": _t("pk_brazil", lang),
            "intl": _t("pk_intl", lang), "placeholder": _t("ix_placeholder", lang),
            "loading": _t("pk_loading", lang), "load_err": _t("pk_load_err", lang),
            "choose_state": _t("pk_choose_state", lang), "msg_pick": _t("pk_msg_pick", lang),
            "msg_diff": _t("pk_msg_diff", lang),
        },
    }
    # Construído fora da f-string: o JSON e o JS têm chaves {} que a quebrariam.
    scripts_block = (
        '<script id="cities-data" type="application/json">'
        + json.dumps(cfg, ensure_ascii=False)
        + "</script>\n<script>"
        + _ROUTES_PICKER_JS
        + "</script>"
    )

    # Rotas populares (curadas) — mantêm links internos para SEO sem poluir a tela.
    popular = [
        ("sao-paulo", "rio-de-janeiro"), ("sao-paulo", "lisboa"), ("sao-paulo", "nova-york"),
        ("sao-paulo", "miami"), ("sao-paulo", "buenos-aires"), ("sao-paulo", "paris"),
        ("sao-paulo", "madri"), ("rio-de-janeiro", "lisboa"), ("rio-de-janeiro", "nova-york"),
        ("brasilia", "sao-paulo"), ("belo-horizonte", "sao-paulo"), ("recife", "lisboa"),
        ("porto-alegre", "sao-paulo"), ("salvador", "sao-paulo"), ("fortaleza", "lisboa"),
        ("manaus", "sao-paulo"),
    ]
    # Canoniza a direção e descarta pares podados, para não linkar 404.
    pop_seen: set[tuple[str, str]] = set()
    pop_html: list[str] = []
    for o, d in popular:
        canon = canonical_pair(o, d)
        if canon is None or canon in pop_seen:
            continue
        pop_seen.add(canon)
        co, cd = canon
        pop_html.append(
            f'<a class="rel" href="/rota/{co}/{cd}">'
            f"{CITY_BY_SLUG[co].name} → {CITY_BY_SLUG[cd].name}</a>"
        )
    pop_links = "".join(pop_html)

    html = f"""<!DOCTYPE html>
<html lang="{i18n.html_lang(lang)}">
<head>
<meta charset="UTF-8" />
{gtag_block(lang, "rotas-index")}
{PWA_HEAD}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{_t("ix_title", lang)}</title>
<meta name="description" content="{_t("ix_desc", lang)}" />
{i18n.hreflang_block("/rotas", lang)}
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/static/style.css" />
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="#1fd8e6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12l8-1 4-8 2 0-1 8 6 1-6 1 1 8-2 0-4-8-8-1z" /></svg></div>
    <h1 style="font-size:18px">Aero Jussa<small>{_t("ix_brand", lang)}</small></h1>
  </div>
  {_nav("/rotas", lang)}
  {i18n.switcher_block("/rotas", lang)}
  <p style="font-size:14px;color:#c3d3e6;margin:14px 0 14px">{_t("ix_intro", lang)}</p>

  <div class="route-picker">
    <div class="rp-col">
      <span class="rp-h">{_t("ix_origin", lang)}</span>
      <label class="rp-l" for="o-state">{_t("ix_state", lang)}</label>
      <select id="o-state" class="rp-sel"></select>
      <label class="rp-l" for="o-air-input">{_t("ix_aero", lang)}</label>
      <div class="rp-ac">
        <input id="o-air-input" class="rp-sel" type="text" autocomplete="off" spellcheck="false" placeholder="{_t("ix_placeholder", lang)}" />
        <div class="ac" id="o-air-ac"></div>
      </div>
    </div>
    <div class="rp-col">
      <span class="rp-h">{_t("ix_dest", lang)}</span>
      <label class="rp-l" for="d-state">{_t("ix_state", lang)}</label>
      <select id="d-state" class="rp-sel"></select>
      <label class="rp-l" for="d-air-input">{_t("ix_aero", lang)}</label>
      <div class="rp-ac">
        <input id="d-air-input" class="rp-sel" type="text" autocomplete="off" spellcheck="false" placeholder="{_t("ix_placeholder", lang)}" />
        <div class="ac" id="d-air-ac"></div>
      </div>
    </div>
  </div>
  <div class="rp-actions">
    <button id="go-rota" class="rp-btn" type="button">{_t("ix_btn", lang)}</button>
  </div>
  <div id="r-msg" class="rp-msg"></div>

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:22px 0 10px">{_t("ix_popular", lang)}</h3>
  <div style="display:flex;flex-wrap:wrap;gap:8px">{pop_links}</div>

  <footer class="foot" style="margin-top:28px"><a href="/" style="color:var(--cyan);text-decoration:none">{_t("foot_calc", lang)}</a> · <a href="/curiosidades" style="color:var(--cyan);text-decoration:none">{_t("foot_curio", lang)}</a> · <a href="/sobre" style="color:var(--cyan);text-decoration:none">{_t("foot_about", lang)}</a></footer>
</div>
<style>
.route-picker{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:8px 0 14px}}
.rp-col{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}}
.rp-h{{display:block;font-family:'Chakra Petch',sans-serif;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--cyan);font-size:13px;margin-bottom:6px}}
.rp-l{{display:block;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:9px 0 4px}}
.rp-sel{{width:100%;background:var(--panel-2);border:1px solid var(--line);color:var(--ink);font-family:'Inter',sans-serif;font-size:15px;padding:10px 11px;border-radius:9px;outline:none;cursor:pointer}}
.rp-sel:focus{{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(31,216,230,.16)}}
.rp-sel option,.rp-sel optgroup{{background:#0d1729;color:var(--ink)}}
.rp-ac{{position:relative}}
.rp-ac input{{cursor:text}}
.rp-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:4px}}
.rp-btn{{background:rgba(31,216,230,.12);border:1px solid var(--cyan);color:var(--cyan);padding:12px 20px;border-radius:9px;cursor:pointer;font-family:'Chakra Petch',sans-serif;font-weight:600;letter-spacing:.04em;font-size:14px}}
.rp-btn:hover{{background:rgba(31,216,230,.22)}}
.rp-btn.ghost{{background:transparent;border-color:var(--line);color:var(--muted)}}
.rp-btn.ghost:hover{{color:var(--cyan);border-color:var(--cyan)}}
.rp-msg{{color:var(--amber);font-family:'JetBrains Mono',monospace;font-size:12px;min-height:16px;margin-top:8px}}
.rel{{background:var(--panel-2);border:1px solid var(--line);border-radius:30px;padding:7px 13px;font-size:12.5px;color:var(--cyan);text-decoration:none}}
.rel:hover{{background:#16335a}}
@media (max-width:520px){{.route-picker{{grid-template-columns:1fr}}}}
</style>
{scripts_block}
</body>
</html>"""
    return _localize_links(html, lang)


def render_curiosidades(store: AirportStore, lang: str = "pt") -> str:
    """Página de curiosidades, computada a partir dos dados reais das rotas."""
    # Só pares que têm página real (mantidos e na direção canônica): todo link
    # aponta para uma /rota que existe.
    pairs: list[tuple[City, City, float]] = []
    for o, d in ROUTE_PAIRS:
        a = store.resolve(o.code)
        b = store.resolve(d.code)
        if a is None or b is None:
            continue
        nm = calc.great_circle_distance_nm(Point(a.lat, a.lon), Point(b.lat, b.lon))
        pairs.append((o, d, nm))
    pairs.sort(key=lambda t: t[2])

    a320 = aircraft_mod.get("a320neo")
    a380 = aircraft_mod.get("a380")

    def row(o: City, d: City, nm: float) -> str:
        km = nm * calc.NM_TO_KM
        h = calc.flight_time_hours(nm, a320.cruise_kt)
        return (
            f'<tr><td><a href="/rota/{o.slug}/{d.slug}" style="color:var(--cyan);text-decoration:none">'
            f"{o.name} → {d.name}</a></td><td>{_fmt(km, lang)} km</td><td>{calc.format_hm(h)}</td></tr>"
        )

    longest = list(reversed(pairs[-12:]))
    shortest = pairs[:12]
    rows_long = "".join(row(o, d, nm) for o, d, nm in longest)
    rows_short = "".join(row(o, d, nm) for o, d, nm in shortest)

    # destaques computados
    lo_o, lo_d, lo_nm = pairs[-1]
    sh_o, sh_d, sh_nm = pairs[0]
    lo_km = lo_nm * calc.NM_TO_KM
    lo_h380 = calc.flight_time_hours(lo_nm, a380.cruise_kt)
    lo_fuel = calc.fuel_estimate(lo_h380, a380.burn_kg_h)
    sh_h = calc.flight_time_hours(sh_nm, a320.cruise_kt)

    cards = f"""
    <div class="cur-grid">
      <a class="cur-card" href="/rota/{lo_o.slug}/{lo_d.slug}">
        <div class="cur-k">{_t("cu_c_long", lang)}</div>
        <div class="cur-v">{lo_o.name} → {lo_d.name}</div>
        <div class="cur-d">{_t("cu_c_long_d", lang, _fmt(lo_km, lang))}</div>
      </a>
      <a class="cur-card" href="/rota/{lo_o.slug}/{lo_d.slug}">
        <div class="cur-k">{_t("cu_c_fuel", lang)}</div>
        <div class="cur-v">{_t("cu_c_fuel_v", lang, _fmt(lo_fuel['total_kg'] / 1000, lang))}</div>
        <div class="cur-d">{_t("cu_c_fuel_d", lang, lo_o.name, lo_d.name)}</div>
      </a>
      <a class="cur-card" href="/rota/{sh_o.slug}/{sh_d.slug}">
        <div class="cur-k">{_t("cu_c_short", lang)}</div>
        <div class="cur-v">{sh_o.name} → {sh_d.name}</div>
        <div class="cur-d">{_t("cu_c_short_d", lang, _fmt(sh_nm * calc.NM_TO_KM, lang), calc.format_hm(sh_h))}</div>
      </a>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="{i18n.html_lang(lang)}">
<head>
<meta charset="UTF-8" />
{gtag_block(lang, "curiosidades")}
{PWA_HEAD}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{_t("cu_title", lang)}</title>
<meta name="description" content="{_t("cu_desc", lang)}" />
{i18n.hreflang_block("/curiosidades", lang)}
<meta property="og:title" content="{_t("cu_og_title", lang)}" />
<meta property="og:description" content="{_t("cu_og_desc", lang)}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE_URL}{i18n.prefix(lang)}/curiosidades" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/static/style.css" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4915226991502750" crossorigin="anonymous"></script>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="#1fd8e6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12l8-1 4-8 2 0-1 8 6 1-6 1 1 8-2 0-4-8-8-1z" /></svg></div>
    <h1 style="font-size:18px">Aero Jussa<small>{_t("cu_brand", lang)}</small></h1>
  </div>

  <div class="tag"><span>{_t("cu_tag", lang)}</span><span><a href="/rotas" style="color:var(--muted);text-decoration:none">{_t("all_routes", lang)}</a></span></div>
  {_nav("/curiosidades", lang)}
  {i18n.switcher_block("/curiosidades", lang)}

  <h2 style="font-family:'Chakra Petch',sans-serif;font-size:22px;margin:6px 0 10px">{_t("cu_h2", lang)}</h2>
  <p style="font-size:14px;color:#c3d3e6;margin-bottom:4px">{_t("cu_intro", lang)}</p>
  {cards}

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:24px 0 8px">{_t("cu_h3_long", lang)}</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13.5px;color:#c3d3e6">
    <thead><tr style="color:var(--muted);text-align:left;font-family:'JetBrains Mono',monospace;font-size:11px">
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("cu_th_route", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("cu_th_dist", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("cu_th_time", lang)}</th>
    </tr></thead>
    <tbody>{rows_long}</tbody>
  </table>

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:24px 0 8px">{_t("cu_h3_short", lang)}</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13.5px;color:#c3d3e6">
    <thead><tr style="color:var(--muted);text-align:left;font-family:'JetBrains Mono',monospace;font-size:11px">
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("cu_th_route", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("cu_th_dist", lang)}</th>
      <th style="padding:8px 6px;border-bottom:1px solid var(--line)">{_t("cu_th_time", lang)}</th>
    </tr></thead>
    <tbody>{rows_short}</tbody>
  </table>
  <p style="font-size:11px;color:var(--muted);margin-top:8px;font-family:'JetBrains Mono',monospace">{_t("cu_note", lang)}</p>

  <a class="cta-link" href="/"
     style="display:inline-block;margin:20px 0;background:rgba(31,216,230,.12);border:1px solid var(--cyan);color:var(--cyan);padding:12px 20px;border-radius:9px;text-decoration:none;font-family:'Chakra Petch',sans-serif;font-weight:600;letter-spacing:.04em">
    {_t("cu_cta", lang)}
  </a>

  <footer class="foot" style="margin-top:20px">
    <a href="/" style="color:var(--cyan);text-decoration:none">{_t("foot_calc", lang)}</a> ·
    <a href="/rotas" style="color:var(--cyan);text-decoration:none">{_t("foot_routes", lang)}</a> ·
    <a href="/sobre" style="color:var(--cyan);text-decoration:none">{_t("foot_about", lang)}</a> ·
    <a href="/static/privacidade.html" style="color:var(--cyan);text-decoration:none">{_t("foot_privacy", lang)}</a>
  </footer>
</div>
<style>
.cur-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:14px 0 8px}}
.cur-card{{background:linear-gradient(180deg,var(--panel) 0%,#0a1424 100%);border:1px solid var(--line);border-radius:12px;padding:14px;text-decoration:none;display:block}}
.cur-card:hover{{border-color:var(--cyan)}}
.cur-k{{font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}}
.cur-v{{font-family:'Chakra Petch',sans-serif;font-weight:700;font-size:18px;color:var(--cyan);margin:5px 0 3px}}
.cur-d{{font-size:12px;color:#c3d3e6}}
table td{{padding:9px 6px;border-bottom:1px solid var(--line)}}
@media (max-width:560px){{.cur-grid{{grid-template-columns:1fr}}}}
</style>
</body>
</html>"""
    return _localize_links(html, lang)


def render_tempo_page(ap: Airport, raw: str | None, observed_epoch: int | None,
                      related: list[tuple[str, str]], lang: str = "pt") -> str:
    """Página SEO de tempo por aeródromo (/tempo/{icao}), com o último METAR gravado."""
    icao = ap.icao or ap.code
    place = ap.city or ap.name
    base_path = f"/tempo/{icao}"
    canonical = f"{BASE_URL}{i18n.prefix(lang)}{base_path}"
    title = _t("tp_title", lang, place, icao)
    desc = _t("tp_desc", lang, ap.name, icao)

    if raw:
        d = metar_mod.decode(raw, lang)
        ci = d["category_info"]
        w = d["wind"]
        if not w:
            wind = "—"
        elif w["vrb"]:
            wind = f"VRB {w['speed_kt']} kt"
        elif w["speed_kt"] == 0:
            wind = _t("tp_calm", lang)
        else:
            wind = f"{w['dir']:03d}° {w['speed_kt']} kt" + (f" G{w['gust_kt']}" if w["gust_kt"] else "")
        if d["cavok"]:
            vis = "CAVOK"
        elif d["visibility_m"] is None:
            vis = "—"
        elif d["visibility_m"] >= 9999:
            vis = "≥10 km"
        elif d["visibility_m"] >= 1000:
            vis = f"{round(d['visibility_m'] / 1000)} km"
        else:
            vis = f"{d['visibility_m']} m"
        ceil = _t("tp_noceil", lang) if d["ceiling_ft"] is None else f"{d['ceiling_ft']} ft"
        temp = "—" if d["temp_c"] is None else f"{d['temp_c']}° / {d['dewpoint_c']}°"
        qnh = "—" if d["qnh_hpa"] is None else f"{d['qnh_hpa']} hPa"
        when = ""
        if observed_epoch:
            when = datetime.fromtimestamp(observed_epoch, timezone.utc).strftime("%d/%m %H:%MZ")
        cell = lambda k, v: f'<div class="wxc-cell"><div class="k">{k}</div><div class="v">{v}</div></div>'
        card = (
            f'<div class="wxc">'
            f'<div class="wxc-flag" style="background:linear-gradient(90deg,{ci["color"]}22,transparent)">'
            f'<div class="wxc-dot" style="background:{ci["color"]}22;border:1px solid {ci["color"]}">{ci["emoji"]}</div>'
            f'<div class="wxc-cat" style="color:{ci["color"]}">{ci["label"]}<small>{ci["desc"]}</small></div>'
            f'<div class="wxc-when">{icao}{("<br>" + when + " " + _t("tp_obs", lang)) if when else ""}</div></div>'
            f'<div class="wxc-sum">{d["summary_pt"]}</div>'
            f'<div class="wxc-grid">{cell(_t("tp_c_wind", lang), wind)}{cell(_t("tp_c_vis", lang), vis)}{cell(_t("tp_c_ceil", lang), ceil)}'
            f'{cell(_t("tp_c_temp", lang), temp)}{cell("QNH", qnh)}{cell(_t("tp_c_cond", lang), ci["label"])}</div>'
            f'<div class="wxc-raw">{d["raw"]}</div></div>'
        )
        h1cat = f' — {_t("tp_now", lang)} {ci["emoji"]} {ci["label"]}'
    else:
        card = f'<div class="wxc empty2">{_t("tp_empty", lang)}</div>'
        h1cat = ""

    rel = "".join(f'<a class="rel" href="/tempo/{ic}">{lb}</a>' for ic, lb in related if ic != icao)

    html = f"""<!DOCTYPE html>
<html lang="{i18n.html_lang(lang)}">
<head>
<meta charset="UTF-8" />
{gtag_block(lang, "tempo", icao)}
{PWA_HEAD}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title} | Aero Jussa</title>
<meta name="description" content="{desc}" />
{i18n.hreflang_block(base_path, lang)}
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{canonical}" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/static/style.css" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4915226991502750" crossorigin="anonymous"></script>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="badge"><svg viewBox="0 0 24 24" fill="none" stroke="#1fd8e6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12l8-1 4-8 2 0-1 8 6 1-6 1 1 8-2 0-4-8-8-1z" /></svg></div>
    <h1 style="font-size:18px">Aero Jussa<small>{_t("tp_brand", lang)}</small></h1>
  </div>
  <div class="tag"><span>METAR {icao}</span><span><a href="/tempo" style="color:var(--muted);text-decoration:none">{_t("tp_live", lang)}</a></span></div>
  {_nav("/tempo", lang)}
  {i18n.switcher_block(base_path, lang)}

  <h2 style="font-family:'Chakra Petch',sans-serif;font-size:22px;margin:6px 0 4px">{ap.name} ({icao}){h1cat}</h2>
  <p style="font-size:13px;color:var(--muted);margin-bottom:14px">{_t("tp_sub", lang, place, ap.country)}</p>
  {card}

  <p style="font-size:13px;margin:16px 0 8px"><a href="/tempo" style="color:var(--cyan)">{_t("tp_open", lang)}</a></p>

  <h3 style="font-family:'Chakra Petch',sans-serif;font-size:14px;text-transform:uppercase;letter-spacing:.04em;color:var(--cyan);margin:22px 0 10px">{_t("tp_other", lang)}</h3>
  <div style="display:flex;flex-wrap:wrap;gap:8px">{rel}</div>

  <div class="note" style="margin-top:18px">{_t("tp_note", lang)}</div>
  <footer class="foot" style="margin-top:24px"><a href="/" style="color:var(--cyan);text-decoration:none">{_t("foot_calc", lang)}</a> · <a href="/tempo" style="color:var(--cyan);text-decoration:none">{_t("nav_tempo", lang)}</a> · <a href="/rotas" style="color:var(--cyan);text-decoration:none">{_t("foot_routes", lang)}</a> · <a href="/sobre" style="color:var(--cyan);text-decoration:none">{_t("foot_about", lang)}</a></footer>
</div>
<style>
.rel{{background:var(--panel-2);border:1px solid var(--line);border-radius:30px;padding:7px 13px;font-size:12.5px;color:var(--cyan);text-decoration:none}}.rel:hover{{background:#16335a}}
.wxc{{background:linear-gradient(180deg,var(--panel) 0%,#0a1424 100%);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
.wxc-flag{{display:flex;align-items:center;gap:14px;padding:16px 18px;border-bottom:1px solid var(--line)}}
.wxc-dot{{width:46px;height:46px;border-radius:12px;flex:none;display:flex;align-items:center;justify-content:center;font-size:24px}}
.wxc-cat{{font-family:'Chakra Petch',sans-serif;font-weight:700;font-size:22px;letter-spacing:.04em;line-height:1}}
.wxc-cat small{{display:block;font-family:'Inter',sans-serif;font-weight:500;font-size:12px;letter-spacing:0;color:var(--muted);margin-top:3px}}
.wxc-when{{margin-left:auto;text-align:right;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted)}}
.wxc-sum{{padding:14px 18px;font-size:14px;color:#dce6f3;line-height:1.6}}
.wxc-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:var(--line)}}
.wxc-cell{{background:#0b1626;padding:12px 14px}}
.wxc-cell .k{{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase}}
.wxc-cell .v{{font-family:'Chakra Petch',sans-serif;font-weight:700;font-size:17px;color:var(--ink);margin-top:4px}}
.wxc-raw{{padding:12px 18px;border-top:1px solid var(--line);font-family:'JetBrains Mono',monospace;font-size:12px;color:#9fb3cc;word-break:break-word;background:#070f1d}}
.empty2{{padding:18px;color:#c3d3e6;font-size:14px}}
@media (max-width:560px){{.wxc-grid{{grid-template-columns:1fr 1fr}}}}
</style>
</body>
</html>"""
    return _localize_links(html, lang)


def _url_i18n(path: str) -> str:
    """Bloco <url> para cada idioma de um caminho traduzido, com alternates hreflang."""
    alts = "".join(
        f'<xhtml:link rel="alternate" hreflang="{i18n.HREFLANG[lg]}" '
        f'href="{BASE_URL}{i18n.loc(lg, path)}"/>'
        for lg in i18n.LANGS
    )
    alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE_URL}{path}"/>'
    return "".join(
        f"<url><loc>{BASE_URL}{i18n.loc(lg, path)}</loc>{alts}</url>"
        for lg in i18n.LANGS
    )


def build_sitemap(tempo_icaos: list[str] | None = None) -> str:
    # Páginas traduzidas (pt/en/es): cada idioma vira um <url> com alternates hreflang.
    translated = ["/", "/comparar", "/tempo", "/radar", "/cartas", "/rotas",
                  "/curiosidades", "/sobre"]
    translated += [f"/rota/{o.slug}/{d.slug}" for o, d in ROUTE_PAIRS]
    translated += [f"/tempo/{ic}" for ic in (tempo_icaos or [])]
    body = "".join(_url_i18n(p) for p in translated)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        f"{body}</urlset>"
    )


def build_robots() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n"

"""Internacionalização (i18n) do Aero Jussa — pt (padrão), en, es.

Estratégia: páginas estáticas são renderizadas server-side por idioma para SEO.
- URLs por subpasta: pt na raiz (/, /cartas…), en em /en/…, es em /es/…
- Cada página HTML traz tokens `{{chave}}` (texto visível) + os marcadores
  especiais `{{lang_switcher}}` e `{{hreflang}}`. O motor substitui pelos textos
  do idioma, injeta hreflang/canonical, ajusta `<html lang>`, reescreve os links
  internos para o prefixo do idioma e expõe `window.APP_LANG` para os JS.

Assim o Google indexa 3 versões distintas e rastreáveis de cada página.
"""

from __future__ import annotations

import re

LANGS = ("pt", "en", "es")
DEFAULT = "pt"
BASE = "https://aero.jussa.com.br"

HTML_LANG = {"pt": "pt-BR", "en": "en", "es": "es"}
HREFLANG = {"pt": "pt-BR", "en": "en", "es": "es"}
FLAG = {"pt": "🇧🇷", "en": "🇺🇸", "es": "🇪🇸"}
LANG_NAME = {"pt": "Português", "en": "English", "es": "Español"}

# Slugs das páginas traduzidas (Leva 1). "" = home. Só estes links recebem
# prefixo de idioma; links para páginas ainda não traduzidas ficam em pt.
TRANSLATED_SLUGS = ("", "comparar", "tempo", "radar", "cartas", "aerodromo", "sobre")

# ---------------------------------------------------------------------------
# Catálogo de textos. Cada chave -> {pt, en, es}.
# ---------------------------------------------------------------------------
STRINGS: dict[str, dict[str, str]] = {
    # ---- Navegação (comum a todas as páginas) ----
    "nav_calc": {"pt": "Calculadora", "en": "Calculator", "es": "Calculadora"},
    "nav_compare": {"pt": "Comparar aeronaves", "en": "Compare aircraft", "es": "Comparar aeronaves"},
    "nav_tempo": {"pt": "Tempo", "en": "Weather", "es": "Meteo"},
    "nav_radar": {"pt": "Mapa", "en": "Map", "es": "Mapa"},
    "nav_cartas": {"pt": "Cartas", "en": "Charts", "es": "Cartas"},
    "nav_aero": {"pt": "Aeródromo", "en": "Aerodrome", "es": "Aeródromo"},
    "nav_curio": {"pt": "Curiosidades", "en": "Facts", "es": "Curiosidades"},
    "nav_rotas": {"pt": "Rotas", "en": "Routes", "es": "Rutas"},
    # ---- Rodapé (comum) ----
    "foot_routes": {"pt": "Rotas populares", "en": "Popular routes", "es": "Rutas populares"},
    "foot_curio": {"pt": "Curiosidades", "en": "Facts", "es": "Curiosidades"},
    "foot_about": {"pt": "Sobre", "en": "About", "es": "Acerca de"},
    "foot_privacy": {"pt": "Política de Privacidade", "en": "Privacy Policy", "es": "Política de Privacidad"},
    "foot_calc": {"pt": "Calculadora", "en": "Calculator", "es": "Calculadora"},
    "aff_header": {"pt": "Recomendados para aviação", "en": "Recommended for aviation", "es": "Recomendados para aviación"},
    "status_online": {"pt": "● ONLINE", "en": "● ONLINE", "es": "● ONLINE"},
    # ---- Home / Calculadora ----
    "home_title": {
        "pt": "Aero Jussa · Calculadora de Rotas, Tempo e Combustível de Voo",
        "en": "Aero Jussa · Flight Route, Time and Fuel Calculator",
        "es": "Aero Jussa · Calculadora de Rutas, Tiempo y Combustible de Vuelo",
    },
    "home_desc": {
        "pt": "Calcule distância, proa, tempo de voo e consumo de combustível entre aeroportos de todo o mundo. Rota great-circle no mapa.",
        "en": "Calculate distance, heading, flight time and fuel burn between airports worldwide. Great-circle route on the map.",
        "es": "Calcula distancia, rumbo, tiempo de vuelo y consumo de combustible entre aeropuertos de todo el mundo. Ruta ortodrómica en el mapa.",
    },
    "home_tag": {"pt": "CALCULADORA DE ROTA", "en": "ROUTE CALCULATOR", "es": "CALCULADORA DE RUTA"},
    "home_origin": {"pt": "Origem", "en": "Origin", "es": "Origen"},
    "home_dest": {"pt": "Destino", "en": "Destination", "es": "Destino"},
    "home_swap": {"pt": "Inverter", "en": "Swap", "es": "Invertir"},
    "home_aircraft": {"pt": "Aeronave", "en": "Aircraft", "es": "Aeronave"},
    "home_reserve": {
        "pt": "Reserva de combustível (etapa = alcance × usável)",
        "en": "Fuel reserve (leg = range × usable)",
        "es": "Reserva de combustible (etapa = alcance × utilizable)",
    },
    "home_reserve_none": {"pt": "100% · sem reserva", "en": "100% · no reserve", "es": "100% · sin reserva"},
    "home_reserve_rec": {"pt": "85% · recomendado", "en": "85% · recommended", "es": "85% · recomendado"},
    "home_reserve_cons": {"pt": "75% · conservador", "en": "75% · conservative", "es": "75% · conservador"},
    "home_note": {
        "pt": "Estimativas de cruzeiro · velocidades e consumo são valores médios de catálogo, ideais para calibrar com dados reais do seu amigo piloto. Tempo de bloco inclui ~25 min de táxi/subida/descida. Não usar para planejamento operacional real.",
        "en": "Cruise estimates · speeds and burn are average catalog figures, ideal to calibrate with real data. Block time includes ~25 min of taxi/climb/descent. Not for real operational planning.",
        "es": "Estimaciones de crucero · velocidades y consumo son valores medios de catálogo, ideales para calibrar con datos reales. El tiempo de bloque incluye ~25 min de rodaje/ascenso/descenso. No usar para planificación operacional real.",
    },
    "home_foot": {
        "pt": "Python + FastAPI · dados de aeroportos: OurAirports (domínio público)",
        "en": "Python + FastAPI · airport data: OurAirports (public domain)",
        "es": "Python + FastAPI · datos de aeropuertos: OurAirports (dominio público)",
    },
    # ---- Títulos/descrições por página (Leva 1) ----
    "cmp_title": {
        "pt": "Comparar aeronaves e alcance no mapa | Aero Jussa",
        "en": "Compare aircraft and range on the map | Aero Jussa",
        "es": "Comparar aeronaves y alcance en el mapa | Aero Jussa",
    },
    "cmp_desc": {
        "pt": "Compare de 2 a 4 aeronaves lado a lado e veja o raio de alcance de cada uma a partir de um aeroporto, com cores diferentes no mapa.",
        "en": "Compare 2 to 4 aircraft side by side and see each one's range from an airport, in different colors on the map.",
        "es": "Compara de 2 a 4 aeronaves lado a lado y ve el radio de alcance de cada una desde un aeropuerto, con colores distintos en el mapa.",
    },
    "wx_title": {
        "pt": "METAR decodificado e condição VFR/IFR por aeródromo | Aero Jussa",
        "en": "Decoded METAR and VFR/IFR conditions by airport | Aero Jussa",
        "es": "METAR decodificado y condición VFR/IFR por aeródromo | Aero Jussa",
    },
    "wx_desc": {
        "pt": "Consulte o METAR mais recente de qualquer aeródromo do Brasil decodificado em português, com semáforo VFR/IFR (visual ou por instrumentos). Dados oficiais da REDEMET/DECEA.",
        "en": "Check the latest METAR for any airport in Brazil, decoded in plain language, with a VFR/IFR light (visual or instrument). Official REDEMET/DECEA data.",
        "es": "Consulta el METAR más reciente de cualquier aeródromo de Brasil, decodificado, con semáforo VFR/IFR (visual o por instrumentos). Datos oficiales de REDEMET/DECEA.",
    },
    "rdr_title": {
        "pt": "Radar Meteorológico · Chuva em tempo real | Aero Jussa",
        "en": "Weather Radar · Real-time rain | Aero Jussa",
        "es": "Radar Meteorológico · Lluvia en tiempo real | Aero Jussa",
    },
    "rdr_desc": {
        "pt": "Radar meteorológico em tempo real: veja as células de chuva, anime o radar (passado e previsão), camada de satélite, zoom, tela cheia e sua localização. Útil para pilotos e aviação.",
        "en": "Real-time weather radar: see the rain cells, animate the radar (past and forecast), satellite layer, zoom, fullscreen and your location. Useful for pilots and aviation.",
        "es": "Radar meteorológico en tiempo real: mira las celdas de lluvia, anima el radar (pasado y pronóstico), capa de satélite, zoom, pantalla completa y tu ubicación. Útil para pilotos y aviación.",
    },
    "chr_title": {
        "pt": "Cartas de Aproximação · Brasil, EUA e Europa | Aero Jussa",
        "en": "Approach Charts · Brazil, USA and Europe | Aero Jussa",
        "es": "Cartas de Aproximación · Brasil, EE. UU. y Europa | Aero Jussa",
    },
    "chr_desc": {
        "pt": "Consulte as cartas de aproximação (IAC) e demais cartas aeronáuticas dos aeródromos do Brasil (DECEA/AISWEB) e dos EUA (FAA d-TPP) — e acesse o eAIP oficial de vários países da Europa. Visualize, imprima, baixe e compartilhe em PDF.",
        "en": "Look up approach charts (IAC) and other aeronautical charts for airports in Brazil (DECEA/AISWEB) and the USA (FAA d-TPP) — and reach the official eAIP of several European countries. View, print, download and share as PDF.",
        "es": "Consulta las cartas de aproximación (IAC) y otras cartas aeronáuticas de los aeródromos de Brasil (DECEA/AISWEB) y EE. UU. (FAA d-TPP) — y accede al eAIP oficial de varios países de Europa. Visualiza, imprime, descarga y comparte en PDF.",
    },
    "abt_title": {
        "pt": "Sobre · Aero Jussa",
        "en": "About · Aero Jussa",
        "es": "Acerca de · Aero Jussa",
    },
    "abt_desc": {
        "pt": "O que é o Aero Jussa, como os cálculos de rota, tempo e combustível de voo são feitos, e quem está por trás do projeto.",
        "en": "What Aero Jussa is, how the route, time and fuel of flight calculations are made, and who is behind the project.",
        "es": "Qué es Aero Jussa, cómo se hacen los cálculos de ruta, tiempo y combustible de vuelo, y quién está detrás del proyecto.",
    },
    "src": {"pt": "FONTE", "en": "SOURCE", "es": "FUENTE"},

    # ---- Cartas (corpo) ----
    "cb_tag": {"pt": "CARTAS DE APROXIMAÇÃO", "en": "APPROACH CHARTS", "es": "CARTAS DE APROXIMACIÓN"},
    "cb_sub": {"pt": "cartas aeronáuticas · jussa.com.br", "en": "aeronautical charts · jussa.com.br", "es": "cartas aeronáuticas · jussa.com.br"},
    "cb_h2": {"pt": "Cartas de aproximação por aeródromo", "en": "Approach charts by airport", "es": "Cartas de aproximación por aeródromo"},
    "cb_intro": {
        "pt": "Escolha um <strong>aeródromo do Brasil ou dos EUA</strong> e veja as cartas oficiais aqui mesmo — <strong>visualizar</strong>, <strong>imprimir</strong>, <strong>baixar</strong> e <strong>compartilhar em PDF</strong>, sempre na emenda (AIRAC) vigente do <strong>AISWEB (DECEA)</strong> e do <strong>d-TPP (FAA)</strong>. Para a <strong>Europa</strong>, levamos você ao <strong>eAIP oficial</strong> do país.",
        "en": "Pick a <strong>Brazilian or U.S. airport</strong> and see the official charts right here — <strong>view</strong>, <strong>print</strong>, <strong>download</strong> and <strong>share as PDF</strong>, always on the current (AIRAC) amendment from <strong>AISWEB (DECEA)</strong> and <strong>d-TPP (FAA)</strong>. For <strong>Europe</strong>, we take you to the country's <strong>official eAIP</strong>.",
        "es": "Elige un <strong>aeródromo de Brasil o EE. UU.</strong> y consulta las cartas oficiales aquí mismo — <strong>ver</strong>, <strong>imprimir</strong>, <strong>descargar</strong> y <strong>compartir en PDF</strong>, siempre en la enmienda (AIRAC) vigente de <strong>AISWEB (DECEA)</strong> y <strong>d-TPP (FAA)</strong>. Para <strong>Europa</strong>, te llevamos al <strong>eAIP oficial</strong> del país.",
    },
    "cb_lbl_aero": {"pt": "Aeródromo (Brasil / EUA / Europa)", "en": "Airport (Brazil / USA / Europe)", "es": "Aeródromo (Brasil / EE. UU. / Europa)"},
    "cb_lbl_type": {"pt": "Tipo de carta", "en": "Chart type", "es": "Tipo de carta"},
    "cb_opt_iac": {"pt": "Aproximação por instrumentos (IAC)", "en": "Instrument approach (IAC)", "es": "Aproximación por instrumentos (IAC)"},
    "cb_opt_vac": {"pt": "Aproximação visual (VAC)", "en": "Visual approach (VAC)", "es": "Aproximación visual (VAC)"},
    "cb_opt_adc": {"pt": "Aeródromo (ADC)", "en": "Aerodrome (ADC)", "es": "Aeródromo (ADC)"},
    "cb_opt_sid": {"pt": "Saída por instrumentos (SID)", "en": "Instrument departure (SID)", "es": "Salida por instrumentos (SID)"},
    "cb_opt_star": {"pt": "Chegada por instrumentos (STAR)", "en": "Instrument arrival (STAR)", "es": "Llegada por instrumentos (STAR)"},
    "cb_opt_aoc": {"pt": "Obstáculos (AOC)", "en": "Obstacles (AOC)", "es": "Obstáculos (AOC)"},
    "cb_opt_all": {"pt": "Todas as cartas", "en": "All charts", "es": "Todas las cartas"},
    "cb_print": {"pt": "Imprimir", "en": "Print", "es": "Imprimir"},
    "cb_download": {"pt": "Baixar PDF", "en": "Download PDF", "es": "Descargar PDF"},
    "cb_share": {"pt": "Compartilhar", "en": "Share", "es": "Compartir"},
    "cb_newtab": {"pt": "Abrir em nova aba", "en": "Open in new tab", "es": "Abrir en pestaña nueva"},
    "cb_prevp": {"pt": "Página anterior", "en": "Previous page", "es": "Página anterior"},
    "cb_nextp": {"pt": "Próxima página", "en": "Next page", "es": "Página siguiente"},
    "cb_zoomout": {"pt": "Menos zoom", "en": "Zoom out", "es": "Menos zoom"},
    "cb_zoomin": {"pt": "Mais zoom", "en": "Zoom in", "es": "Más zoom"},
    "cb_fit": {"pt": "Ajustar à largura", "en": "Fit width", "es": "Ajustar al ancho"},
    "cb_status0": {"pt": "Selecione um aeródromo para listar as cartas.", "en": "Select an airport to list the charts.", "es": "Selecciona un aeródromo para listar las cartas."},
    "cb_note": {
        "pt": "Cartas oficiais do <strong>DECEA</strong> (Brasil, via AISWEB) e da <strong>FAA</strong> (EUA, d-TPP), servidas ao vivo na emenda vigente — este site não armazena nem altera as cartas. Na <strong>Europa</strong>, cada país publica seu eAIP com direitos próprios, então apenas encaminhamos ao portal oficial. Use sempre a publicação oficial e o briefing (NOTAM) para planejamento de voo real.",
        "en": "Official charts from <strong>DECEA</strong> (Brazil, via AISWEB) and the <strong>FAA</strong> (USA, d-TPP), served live on the current amendment — this site does not store or alter the charts. In <strong>Europe</strong>, each country publishes its own eAIP under its own rights, so we only forward you to the official portal. Always use the official publication and briefing (NOTAM) for real flight planning.",
        "es": "Cartas oficiales de <strong>DECEA</strong> (Brasil, vía AISWEB) y la <strong>FAA</strong> (EE. UU., d-TPP), servidas en vivo en la enmienda vigente — este sitio no almacena ni altera las cartas. En <strong>Europa</strong>, cada país publica su eAIP con derechos propios, así que solo te reenviamos al portal oficial. Usa siempre la publicación oficial y el briefing (NOTAM) para planificación de vuelo real.",
    },

    # ---- Aeródromo: título/descrição (Leva 1) ----
    "adt_title": {
        "pt": "Informações do Aeródromo · ROTAER, NOTAM e Sol | Aero Jussa",
        "en": "Aerodrome Information · ROTAER, NOTAM and Sun | Aero Jussa",
        "es": "Información del Aeródromo · ROTAER, NOTAM y Sol | Aero Jussa",
    },
    "adt_desc": {
        "pt": "Consulte a ficha ROTAER de qualquer aeródromo do Brasil — pistas, elevação, FIR e auxílios de navegação —, os NOTAM ativos e os horários de nascer e pôr do sol. Dados oficiais do DECEA/AISWEB.",
        "en": "Look up the ROTAER record of any airport in Brazil — runways, elevation, FIR and navigation aids —, the active NOTAMs and the sunrise and sunset times. Official DECEA/AISWEB data.",
        "es": "Consulta la ficha ROTAER de cualquier aeródromo de Brasil — pistas, elevación, FIR y ayudas a la navegación —, los NOTAM activos y los horarios de amanecer y atardecer. Datos oficiales de DECEA/AISWEB.",
    },
    # ---- Aeródromo (corpo) ----
    "adb_sub": {"pt": "ficha · notam · sol", "en": "record · notam · sun", "es": "ficha · notam · sol"},
    "adb_tag": {"pt": "INFORMAÇÕES DO AERÓDROMO", "en": "AERODROME INFORMATION", "es": "INFORMACIÓN DEL AERÓDROMO"},
    "adb_h2": {"pt": "Aeródromo: ficha, NOTAM e sol", "en": "Aerodrome: record, NOTAM and sun", "es": "Aeródromo: ficha, NOTAM y sol"},
    "adb_intro": {
        "pt": "Digite um <strong>aeródromo do Brasil</strong> e veja a <strong>ficha ROTAER</strong> (pistas, elevação, FIR, auxílios de navegação), os <strong>NOTAM ativos</strong> e os <strong>horários de nascer e pôr do sol</strong> — tudo do <strong>AISWEB (DECEA)</strong>.",
        "en": "Type a <strong>Brazilian airport</strong> and see the <strong>ROTAER record</strong> (runways, elevation, FIR, navigation aids), the <strong>active NOTAMs</strong> and the <strong>sunrise and sunset times</strong> — all from <strong>AISWEB (DECEA)</strong>.",
        "es": "Escribe un <strong>aeródromo de Brasil</strong> y consulta la <strong>ficha ROTAER</strong> (pistas, elevación, FIR, ayudas a la navegación), los <strong>NOTAM activos</strong> y los <strong>horarios de amanecer y atardecer</strong> — todo de <strong>AISWEB (DECEA)</strong>.",
    },
    "adb_lbl_aero": {"pt": "Aeródromo (Brasil)", "en": "Airport (Brazil)", "es": "Aeródromo (Brasil)"},
    "adb_status0": {"pt": "Selecione um aeródromo para ver as informações.", "en": "Select an airport to see the information.", "es": "Selecciona un aeródromo para ver la información."},
    "adb_note": {
        "pt": "Dados oficiais do <strong>DECEA</strong> (Brasil, via AISWEB): ficha <strong>ROTAER</strong>, <strong>NOTAM</strong> e horários do sol. Informação de <strong>apoio</strong> — o NOTAM e o ROTAER aqui não substituem o briefing oficial (AIS) para planejamento de voo real. Horários do sol em hora local do aeródromo (e UTC).",
        "en": "Official <strong>DECEA</strong> data (Brazil, via AISWEB): <strong>ROTAER</strong> record, <strong>NOTAM</strong> and sun times. <strong>Supporting</strong> information — the NOTAM and ROTAER here do not replace the official briefing (AIS) for real flight planning. Sun times in the airport's local time (and UTC).",
        "es": "Datos oficiales de <strong>DECEA</strong> (Brasil, vía AISWEB): ficha <strong>ROTAER</strong>, <strong>NOTAM</strong> y horarios del sol. Información de <strong>apoyo</strong> — el NOTAM y el ROTAER aquí no sustituyen el briefing oficial (AIS) para planificación de vuelo real. Horarios del sol en hora local del aeródromo (y UTC).",
    },

    # ---- Tempo (corpo) ----
    "tb_sub": {"pt": "metar · condição de voo", "en": "metar · flight conditions", "es": "metar · condición de vuelo"},
    "tb_h2": {"pt": "Condição de voo por aeródromo", "en": "Flight conditions by airport", "es": "Condición de vuelo por aeródromo"},
    "tb_intro": {
        "pt": "Digite um aeródromo para ver o <strong>METAR mais recente decodificado em português</strong> e o <strong>semáforo VFR/IFR</strong> — verde para voo visual tranquilo, amarelo marginal, laranja/vermelho por instrumentos. Útil no briefing pré-voo.",
        "en": "Type an airport to see the <strong>latest decoded METAR</strong> and the <strong>VFR/IFR light</strong> — green for easy visual flight, yellow marginal, orange/red for instruments. Handy for the pre-flight briefing.",
        "es": "Escribe un aeródromo para ver el <strong>METAR más reciente decodificado</strong> y el <strong>semáforo VFR/IFR</strong> — verde para vuelo visual tranquilo, amarillo marginal, naranja/rojo por instrumentos. Útil en el briefing previo al vuelo.",
    },
    "tb_lbl_aero": {"pt": "Aeródromo", "en": "Airport", "es": "Aeródromo"},
    "tb_related": {"pt": "Tempo nos principais aeródromos", "en": "Weather at major airports", "es": "Tiempo en los principales aeródromos"},

    # ---- Radar (corpo) ----
    "rb_tag": {"pt": "RADAR METEOROLÓGICO", "en": "WEATHER RADAR", "es": "RADAR METEOROLÓGICO"},
    "rb_live": {"pt": "● AO VIVO", "en": "● LIVE", "es": "● EN VIVO"},
    "rb_h2": {"pt": "Radar de chuva em tempo real", "en": "Real-time rain radar", "es": "Radar de lluvia en tiempo real"},
    "rb_intro": {
        "pt": "Acompanhe as células de precipitação em tempo real. Use <strong>play</strong> para animar o radar (histórico recente + previsão de curto prazo), arraste a linha do tempo, troque para a camada de <strong>satélite</strong>, dê zoom, centralize na <strong>sua localização</strong> ou abra em <strong>tela cheia</strong>.",
        "en": "Follow precipitation cells in real time. Use <strong>play</strong> to animate the radar (recent history + short-term forecast), drag the timeline, switch to the <strong>satellite</strong> layer, zoom in, center on <strong>your location</strong> or open <strong>fullscreen</strong>.",
        "es": "Sigue las celdas de precipitación en tiempo real. Usa <strong>play</strong> para animar el radar (histórico reciente + pronóstico a corto plazo), arrastra la línea de tiempo, cambia a la capa de <strong>satélite</strong>, haz zoom, céntrate en <strong>tu ubicación</strong> o abre en <strong>pantalla completa</strong>.",
    },
    "rb_note": {
        "pt": "Dados de radar e satélite por <strong>RainViewer</strong> (cobertura global, atualização a cada ~10 min). A escala em cores indica a intensidade da precipitação (refletividade) — azul/verde para chuva fraca, amarelo/vermelho para forte e rosa para extrema. Quadros marcados como <em>previsão (nowcast)</em> são uma estimativa de curtíssimo prazo. Informação meteorológica de apoio — não substitui o briefing oficial (METAR/TAF/SIGMET) para planejamento de voo real.",
        "en": "Radar and satellite data by <strong>RainViewer</strong> (global coverage, updated every ~10 min). The color scale shows precipitation intensity (reflectivity) — blue/green for light rain, yellow/red for heavy and pink for extreme. Frames marked as <em>forecast (nowcast)</em> are a very short-term estimate. Supporting weather information — it does not replace the official briefing (METAR/TAF/SIGMET) for real flight planning.",
        "es": "Datos de radar y satélite por <strong>RainViewer</strong> (cobertura global, actualización cada ~10 min). La escala de colores indica la intensidad de la precipitación (reflectividad) — azul/verde para lluvia débil, amarillo/rojo para fuerte y rosa para extrema. Los cuadros marcados como <em>pronóstico (nowcast)</em> son una estimación a muy corto plazo. Información meteorológica de apoyo — no sustituye el briefing oficial (METAR/TAF/SIGMET) para planificación de vuelo real.",
    },
    "rb_play": {"pt": "Reproduzir", "en": "Play", "es": "Reproducir"},
    "rb_prevf": {"pt": "Quadro anterior", "en": "Previous frame", "es": "Cuadro anterior"},
    "rb_nextf": {"pt": "Próximo quadro", "en": "Next frame", "es": "Cuadro siguiente"},
    "rb_timeline": {"pt": "Linha do tempo", "en": "Timeline", "es": "Línea de tiempo"},
    "rb_mode_radar": {"pt": "Radar", "en": "Radar", "es": "Radar"},
    "rb_mode_sat": {"pt": "Satélite", "en": "Satellite", "es": "Satélite"},
    "rb_mode_both": {"pt": "Ambos", "en": "Both", "es": "Ambos"},
    "rb_loc": {"pt": "Minha localização", "en": "My location", "es": "Mi ubicación"},
    "rb_refresh": {"pt": "Atualizar dados", "en": "Refresh data", "es": "Actualizar datos"},
    "rb_full": {"pt": "Tela cheia", "en": "Fullscreen", "es": "Pantalla completa"},
    "rb_leg_rain": {"pt": "Intensidade da chuva", "en": "Rain intensity", "es": "Intensidad de la lluvia"},
    "rb_weak": {"pt": "Fraca", "en": "Light", "es": "Débil"},
    "rb_strong": {"pt": "Forte", "en": "Heavy", "es": "Fuerte"},
    "rb_extreme": {"pt": "Extrema", "en": "Extreme", "es": "Extrema"},
    "rb_leg_sat": {"pt": "Satélite (infravermelho)", "en": "Satellite (infrared)", "es": "Satélite (infrarrojo)"},
    "rb_clearsky": {"pt": "Céu limpo", "en": "Clear sky", "es": "Cielo despejado"},
    "rb_highcloud": {"pt": "Nuvens altas / frias", "en": "High / cold clouds", "es": "Nubes altas / frías"},

    # ---- Comparar (corpo) ----
    "mb_sub": {"pt": "comparar aeronaves", "en": "compare aircraft", "es": "comparar aeronaves"},
    "mb_tag": {"pt": "COMPARADOR DE AERONAVES", "en": "AIRCRAFT COMPARATOR", "es": "COMPARADOR DE AERONAVES"},
    "mb_tag2": {"pt": "2 A 4 AERONAVES", "en": "2 TO 4 AIRCRAFT", "es": "2 A 4 AERONAVES"},
    "mb_h2": {"pt": "Comparador de aeronaves & alcance", "en": "Aircraft & range comparator", "es": "Comparador de aeronaves y alcance"},
    "mb_intro": {
        "pt": "Adicione de 2 a 4 aeronaves e escolha um aeroporto: o mapa desenha o raio de alcance de cada aeronave, cada uma com uma cor.",
        "en": "Add 2 to 4 aircraft and pick an airport: the map draws each aircraft's range ring, each in its own color.",
        "es": "Añade de 2 a 4 aeronaves y elige un aeropuerto: el mapa dibuja el radio de alcance de cada aeronave, cada una con un color.",
    },
    "mb_lbl_ac": {"pt": "Aeronaves (até 4)", "en": "Aircraft (up to 4)", "es": "Aeronaves (hasta 4)"},
    "mb_lbl_base": {"pt": "Aeroporto base (centro dos círculos)", "en": "Base airport (center of the rings)", "es": "Aeropuerto base (centro de los círculos)"},

    # ---- Sobre (corpo) ----
    "ab_back": {"pt": "← voltar para a calculadora", "en": "← back to the calculator", "es": "← volver a la calculadora"},
    "ab_sub": {"pt": "sobre o projeto", "en": "about the project", "es": "sobre el proyecto"},
    "ab_h_what": {"pt": "O que é o Aero Jussa", "en": "What Aero Jussa is", "es": "Qué es Aero Jussa"},
    "ab_p_what1": {
        "pt": "O Aero Jussa é uma ferramenta gratuita de planejamento de voo que calcula, entre dois aeroportos quaisquer do mundo, a <strong>distância great-circle</strong> (a rota mais curta sobre a esfera terrestre), a <strong>proa inicial</strong>, o <strong>tempo de bloco estimado</strong> e o <strong>consumo de combustível</strong> de acordo com a aeronave escolhida. Tudo aparece também desenhado no mapa.",
        "en": "Aero Jussa is a free flight-planning tool that calculates, between any two airports in the world, the <strong>great-circle distance</strong> (the shortest route over the Earth's sphere), the <strong>initial heading</strong>, the <strong>estimated block time</strong> and the <strong>fuel burn</strong> for the chosen aircraft. Everything is also drawn on the map.",
        "es": "Aero Jussa es una herramienta gratuita de planificación de vuelo que calcula, entre dos aeropuertos cualesquiera del mundo, la <strong>distancia ortodrómica</strong> (la ruta más corta sobre la esfera terrestre), el <strong>rumbo inicial</strong>, el <strong>tiempo de bloque estimado</strong> y el <strong>consumo de combustible</strong> según la aeronave elegida. Todo aparece también dibujado en el mapa.",
    },
    "ab_p_what2": {
        "pt": "Foi pensado para estudantes de aviação, pilotos em formação, entusiastas e usuários de simuladores de voo (MSFS, X-Plane) que querem uma estimativa rápida sem abrir um software complexo.",
        "en": "It was designed for aviation students, trainee pilots, enthusiasts and flight-sim users (MSFS, X-Plane) who want a quick estimate without opening complex software.",
        "es": "Fue pensado para estudiantes de aviación, pilotos en formación, entusiastas y usuarios de simuladores de vuelo (MSFS, X-Plane) que quieren una estimación rápida sin abrir un software complejo.",
    },
    "ab_h_how": {"pt": "Como os cálculos são feitos", "en": "How the calculations are made", "es": "Cómo se hacen los cálculos"},
    "ab_li_dist": {
        "pt": "<strong>Distância:</strong> fórmula de haversine sobre a rota great-circle, em milhas náuticas e quilômetros.",
        "en": "<strong>Distance:</strong> haversine formula over the great-circle route, in nautical miles and kilometers.",
        "es": "<strong>Distancia:</strong> fórmula de haversine sobre la ruta ortodrómica, en millas náuticas y kilómetros.",
    },
    "ab_li_hdg": {
        "pt": "<strong>Proa inicial:</strong> rumo verdadeiro de partida (0–360°).",
        "en": "<strong>Initial heading:</strong> true departure heading (0–360°).",
        "es": "<strong>Rumbo inicial:</strong> rumbo verdadero de salida (0–360°).",
    },
    "ab_li_time": {
        "pt": "<strong>Tempo de bloco:</strong> distância dividida pela velocidade de cruzeiro da aeronave, mais uma folga de ~25 min para táxi, subida e descida.",
        "en": "<strong>Block time:</strong> distance divided by the aircraft's cruise speed, plus a ~25 min allowance for taxi, climb and descent.",
        "es": "<strong>Tiempo de bloque:</strong> distancia dividida por la velocidad de crucero de la aeronave, más un margen de ~25 min para rodaje, ascenso y descenso.",
    },
    "ab_li_fuel": {
        "pt": "<strong>Combustível:</strong> consumo médio de cruzeiro × tempo de bloco, mais uma reserva aproximada.",
        "en": "<strong>Fuel:</strong> average cruise burn × block time, plus an approximate reserve.",
        "es": "<strong>Combustible:</strong> consumo medio de crucero × tiempo de bloque, más una reserva aproximada.",
    },
    "ab_p_data": {
        "pt": "A base de aeroportos vem do <a href=\"https://ourairports.com/data/\" target=\"_blank\" rel=\"noopener\">OurAirports</a> (domínio público), com cerca de 72 mil aeroportos ativos em todo o mundo, pesquisáveis por código ICAO/IATA ou nome da cidade.",
        "en": "The airport database comes from <a href=\"https://ourairports.com/data/\" target=\"_blank\" rel=\"noopener\">OurAirports</a> (public domain), with about 72,000 active airports worldwide, searchable by ICAO/IATA code or city name.",
        "es": "La base de aeropuertos viene de <a href=\"https://ourairports.com/data/\" target=\"_blank\" rel=\"noopener\">OurAirports</a> (dominio público), con unos 72 mil aeropuertos activos en todo el mundo, buscables por código ICAO/IATA o nombre de la ciudad.",
    },
    "ab_h_disc": {"pt": "Importante: estimativas didáticas", "en": "Important: educational estimates", "es": "Importante: estimaciones didácticas"},
    "ab_p_disc": {
        "pt": "Os valores de velocidade e consumo são médias de catálogo, sem considerar vento, peso real, altitude de cruzeiro ou perfil operacional específico. São ótimos para estudo e comparação, mas <strong>não devem ser usados para planejamento operacional real de voo</strong>.",
        "en": "Speed and fuel figures are catalog averages, without considering wind, actual weight, cruise altitude or a specific operational profile. They are great for study and comparison, but <strong>must not be used for real operational flight planning</strong>.",
        "es": "Los valores de velocidad y consumo son medias de catálogo, sin considerar viento, peso real, altitud de crucero o perfil operacional específico. Son ideales para estudio y comparación, pero <strong>no deben usarse para planificación operacional real de vuelo</strong>.",
    },
    "ab_h_who": {"pt": "Quem faz", "en": "Who makes it", "es": "Quién lo hace"},
    "ab_p_who": {
        "pt": "Projeto pessoal mantido por Juscelino Carvalho, desenvolvido em Python (FastAPI). A precisão dos perfis de aeronaves é continuamente refinada com apoio de pilotos. Sugestões e correções são bem-vindas: ",
        "en": "A personal project maintained by Juscelino Carvalho, built in Python (FastAPI). Aircraft profile accuracy is continuously refined with help from pilots. Suggestions and corrections are welcome: ",
        "es": "Proyecto personal mantenido por Juscelino Carvalho, desarrollado en Python (FastAPI). La precisión de los perfiles de aeronaves se refina continuamente con ayuda de pilotos. Sugerencias y correcciones son bienvenidas: ",
    },
    "ab_cta": {"pt": "Calcular uma rota →", "en": "Calculate a route →", "es": "Calcular una ruta →"},
}


def t(key: str, lang: str) -> str:
    """Texto de uma chave no idioma; cai para pt e, por fim, para a própria chave."""
    entry = STRINGS.get(key, {})
    return entry.get(lang) or entry.get(DEFAULT) or key


def prefix(lang: str) -> str:
    return "" if lang == DEFAULT else f"/{lang}"


def loc(lang: str, base_path: str) -> str:
    """URL root-relative localizada de um caminho.

    A home (base_path == "/") no idioma não-padrão fica SEM barra final
    ("/en", "/es"): a rota servida é "/en", e "/en/" devolve 307. Emitir
    "/en/" em canonical/hreflang/sitemap fazia o Google ver um redirecionamento
    e descartar a canônica ("Cópia sem página canônica selecionada").
    """
    pre = prefix(lang)
    if not pre:
        return base_path
    if base_path == "/":
        return pre
    return pre + base_path


def loc_url(pre: str, url: str) -> str:
    """Prefixa um href/action interno com `pre` (ex.: '/en') sem gerar '/en/'.

    `url` começa com '/'. Preserva query/hash: '/?x=1' -> '/en?x=1'.
    """
    if url == "/":
        return pre or "/"
    if url.startswith(("/?", "/#")):
        return pre + url[1:]
    return pre + url


# --- reescrita de links internos para o prefixo do idioma --------------------
_LINK_RE = re.compile(r'(href|action)="(/[^":]*)"')
_LANGSW_RE = re.compile(r'<div class="langsw".*?</div>', re.S)
# caminhos exatos que devem receber prefixo (com barra inicial)
_TRANSLATED_PATHS = {("/" + s if s else "/") for s in TRANSLATED_SLUGS}


def _rewrite_links(html: str, lang: str) -> str:
    if lang == DEFAULT:
        return html
    pre = prefix(lang)
    # Protege o seletor de idioma: o link pt dele deve ficar SEM prefixo.
    stash: list[str] = []

    def keep(m: re.Match) -> str:
        stash.append(m.group(0))
        return f"\x00SW{len(stash) - 1}\x00"

    html = _LANGSW_RE.sub(keep, html)

    def rep(m: re.Match) -> str:
        attr, url = m.group(1), m.group(2)
        # separa path de query/hash
        pathpart = re.split(r"[?#]", url, 1)[0]
        if pathpart in _TRANSLATED_PATHS:
            return f'{attr}="{loc_url(pre, url)}"'
        return m.group(0)

    html = _LINK_RE.sub(rep, html)
    for i, block in enumerate(stash):
        html = html.replace(f"\x00SW{i}\x00", block)
    return html


def html_lang(lang: str) -> str:
    """Valor do atributo <html lang> para o idioma."""
    return HTML_LANG.get(lang, HTML_LANG[DEFAULT])


def switcher_block(base_path: str, current: str) -> str:
    """Seletor de idioma (bandeiras) para um caminho root-relative qualquer.

    `base_path` já vem com barra inicial (ex.: "/", "/rota/sao-paulo/lisboa").
    Reusável pelas páginas geradas em Python (seo.py), não só pelos slugs da Leva 1.
    """
    parts = []
    for lang in LANGS:
        href = loc(lang, base_path)
        on = " on" if lang == current else ""
        parts.append(
            f'<a class="langsw-a{on}" href="{href}" hreflang="{HREFLANG[lang]}" '
            f'title="{LANG_NAME[lang]}"><span class="fl">{FLAG[lang]}</span>{LANG_NAME[lang]}</a>'
        )
    return '<div class="langsw" aria-label="Idioma">' + "".join(parts) + "</div>"


def hreflang_block(base_path: str, current: str) -> str:
    """Tags <link hreflang> (pt/en/es + x-default) e o canonical do idioma atual."""
    lines = []
    for lang in LANGS:
        href = BASE + loc(lang, base_path)
        lines.append(f'<link rel="alternate" hreflang="{HREFLANG[lang]}" href="{href}" />')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{BASE}{base_path}" />')
    canonical = BASE + loc(current, base_path)
    lines.append(f'<link rel="canonical" href="{canonical}" />')
    return "\n  ".join(lines)


def _switcher_html(slug: str, current: str) -> str:
    return switcher_block("/" + slug if slug else "/", current)


def _hreflang_html(slug: str, current: str) -> str:
    return hreflang_block("/" + slug if slug else "/", current)


_TOKEN_RE = re.compile(r"\{\{([a-z0-9_]+)\}\}")


def render(html: str, lang: str, slug: str) -> str:
    """Renderiza uma página estática no idioma pedido.

    - substitui {{chave}} pelos textos (inclui {{lang_switcher}} e {{hreflang}});
    - ajusta <html lang>, reescreve links internos, injeta window.APP_LANG.
    """
    if lang not in LANGS:
        lang = DEFAULT

    specials = {
        "lang_switcher": _switcher_html(slug, lang),
        "hreflang": _hreflang_html(slug, lang),
    }

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key in specials:
            return specials[key]
        return t(key, lang)

    out = _TOKEN_RE.sub(sub, html)
    out = re.sub(r'<html[^>]*\blang="[^"]*"', f'<html lang="{HTML_LANG[lang]}"', out, count=1)
    out = _rewrite_links(out, lang)
    # expõe o idioma + carrega o dicionário de runtime (antes dos JS das páginas)
    inject = (
        f'  <script>window.APP_LANG="{lang}";</script>\n'
        '  <script src="/static/i18n.js"></script>\n</head>'
    )
    out = out.replace("</head>", inject, 1)
    return out

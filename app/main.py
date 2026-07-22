"""AeroRoute — calculadora de rotas, tempo e combustível de voo.

API em FastAPI que serve tanto os endpoints JSON quanto o frontend estático.
Pensada para crescer: hoje rota/distância/combustível; amanhã planos de voo,
fusos, vento, etc.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles

from . import aircraft as aircraft_mod
from . import aip_japan as japan_mod
from . import calc
from . import cartas as cartas_mod
from . import eaip as eaip_mod
from . import faa_charts as faa_mod
from . import history as history_mod
from . import i18n
from . import metar as metar_mod
from . import push as push_mod
from . import radar_wx
from . import redemet
from . import routing as routing_mod
from . import seo
from . import taf as taf_mod
from .airports import AirportStore
from .calc import Point

STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="AeroRoute",
    description="Calculadora de rotas, tempo e combustível de voo.",
    version="0.1.0",
)

store = AirportStore()


@app.middleware("http")
async def no_cache_assets(request, call_next):
    """Faz o navegador revalidar HTML/JS/CSS (sempre na versão atual, sem cache velho)."""
    response = await call_next(request)
    ctype = response.headers.get("content-type", "")
    if ctype.startswith(("text/html", "text/css")) or "javascript" in ctype:
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "airports_loaded": len(store)}


@app.get("/api/aircraft")
def list_aircraft() -> dict:
    return {"aircraft": aircraft_mod.as_options()}


@app.get("/api/airports/search")
def search_airports(q: str = Query(..., min_length=1)) -> dict:
    return {"results": [ap.to_dict() for ap in store.search(q)]}


@app.get("/api/aerodromos")
def aerodromos(
    region: str = Query(..., min_length=2, description="iso_region, ex.: BR-SP"),
) -> dict:
    """Lista os aeródromos de uma região (estado), em ordem alfabética."""
    aps = store.by_region(region)
    return {"region": region.upper(), "aerodromos": [ap.to_dict() for ap in aps]}


@app.get("/api/cartas")
def api_cartas(
    icao: str = Query(..., min_length=4, max_length=4, description="Código ICAO do aeródromo"),
    tipo: str = Query("IAC", description="Tipo de carta (IAC, VAC, ADC, SID, STAR, AOC, ALL)"),
) -> dict:
    # Roteia pela fonte do país do aeroporto:
    #  - EUA  -> FAA d-TPP (embutido, com visualizador)
    #  - Brasil -> DECEA/AISWEB (embutido, com visualizador)
    #  - Japão -> espelho NagoDede (embutido; portal oficial exige login). Se o
    #             ICAO não estiver no espelho, cai no deep-link do portal oficial.
    #  - Europa/demais -> deep-link para o eAIP oficial (não redistribuível; o
    #             portal resolve o AIRAC vigente)
    #  - sem fonte -> nada
    ap = store.resolve(icao)
    country = ap.country.upper() if ap else ""
    cartas: list[dict] = []
    link: dict | None = None
    source = ""
    try:
        if country == "US":
            cartas = faa_mod.fetch_cartas(icao, tipo)
            source = "FAA d-TPP · EUA"
        elif country == "BR":
            cartas = cartas_mod.fetch_cartas(icao, tipo)
            source = "DECEA / AISWEB · Brasil"
        elif country == "JP":
            cartas = japan_mod.fetch_cartas(icao, tipo)
            if cartas:
                _vig = japan_mod.effective_date()
                source = "AIP Japan · NagoDede (não oficial)" + (
                    f" · vig. {_vig}" if _vig else ""
                )
            else:  # ICAO fora do espelho -> portal oficial (deep-link)
                link = eaip_mod.link_for(country)
                if link:
                    source = f"eAIP · {link['provider']}"
        else:
            link = eaip_mod.link_for(country)
            if link:
                source = f"eAIP · {link['provider']}"
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
    return {
        "icao": icao.upper(),
        "tipo": tipo.upper(),
        "country": country,
        "source": source,
        "cartas": cartas,
        "link": link,
    }


@app.get("/api/cartas/countries")
def api_cartas_countries() -> dict:
    """Países com alguma fonte de cartas (para o autocomplete filtrar)."""
    return {"embed": ["BR", "US"], "link": eaip_mod.covered_countries()}


@app.get("/api/carta")
def api_carta(
    t: str = Query(..., description="Token opaco da carta"),
    dl: int = Query(0, description="1 = força download (attachment)"),
    nome: str = Query("carta", description="Nome do arquivo para download"),
):
    url = cartas_mod.url_for_token(t)
    if url is None:
        raise HTTPException(404, "Carta não encontrada ou sessão expirada. Refaça a busca.")
    try:
        data, ctype, stale_epoch = cartas_mod.fetch_pdf(url)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
    safe = "".join(c for c in nome if c.isalnum() or c in " -_.").strip() or "carta"
    disp = "attachment" if dl else "inline"
    headers = {
        "Content-Disposition": f'{disp}; filename="{safe}.pdf"',
        "Cache-Control": "public, max-age=900",
    }
    if stale_epoch is not None:
        # Fonte fora do ar: servindo cópia local. Sinaliza a defasagem ao front e
        # não deixa o navegador cachear (para retentar a fonte na próxima).
        cached_at = datetime.fromtimestamp(stale_epoch, timezone.utc)
        headers["X-Chart-Stale"] = "1"
        headers["X-Chart-Cached-At"] = cached_at.isoformat()
        headers["X-Chart-Age-Seconds"] = str(max(0, int(time.time()) - stale_epoch))
        headers["Cache-Control"] = "no-store"
    return Response(content=data, media_type=ctype, headers=headers)


def _lang(lang: str) -> str:
    """Normaliza o idioma da query (?lang=) para pt/en/es."""
    return lang if lang in ("pt", "en", "es") else "pt"


@app.get("/api/metar")
def api_metar(
    icao: str = Query(..., min_length=3, max_length=4, description="Código ICAO/IATA do aeródromo"),
    lang: str = Query("pt", description="Idioma da prosa decodificada (pt/en/es)"),
) -> dict:
    """METAR mais recente, decodificado + categoria VFR/IFR (prosa no idioma pedido)."""
    ap = store.resolve(icao)
    code = ap.icao if ap and ap.icao else icao.upper()
    if not redemet.configured():
        raise HTTPException(503, "Consulta de METAR indisponível: chave da REDEMET não configurada.")
    try:
        raw = redemet.fetch_metar(code)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
    decoded = metar_mod.decode(raw, _lang(lang))
    if ap is not None:
        decoded["airport"] = ap.to_dict()
    return decoded


@app.get("/api/taf")
def api_taf(
    icao: str = Query(..., min_length=3, max_length=4, description="Código ICAO/IATA do aeródromo"),
    lang: str = Query("pt", description="Idioma da prosa decodificada (pt/en/es)"),
) -> dict:
    """TAF (previsão) mais recente, decodificado por período (prosa no idioma pedido)."""
    ap = store.resolve(icao)
    code = ap.icao if ap and ap.icao else icao.upper()
    if not redemet.configured():
        raise HTTPException(503, "Consulta de TAF indisponível: chave da REDEMET não configurada.")
    try:
        raw = redemet.fetch_taf(code)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
    decoded = taf_mod.decode(raw, lang=_lang(lang))

    # Camada climatológica: anota cada hora da janela com o % VFR histórico.
    tz = -3
    clim = history_mod.climatology(code, tz_offset_h=tz)
    by_local = {h["hour"]: h for h in clim["hours"]}
    tl = decoded.get("timeline", {})
    for hh in tl.get("hours", []):
        ch = by_local.get((hh["hour"] + tz) % 24)
        hh["hist_vfr"] = ch["pct_vfr"] if ch else None
        hh["hist_n"] = ch["total"] if ch else 0
    tl["clim_samples"] = clim["samples"]
    return decoded


@app.get("/api/push/key")
def push_key() -> dict:
    """Chave pública VAPID para o navegador se inscrever nos alertas."""
    if not push_mod.configured():
        raise HTTPException(503, "Alertas indisponíveis: VAPID não configurado.")
    return {"key": push_mod.public_key()}


@app.post("/api/push/subscribe")
def push_subscribe(payload: dict = Body(...)) -> dict:
    """Salva a inscrição do navegador + aeródromo a monitorar."""
    if not push_mod.configured():
        raise HTTPException(503, "Alertas indisponíveis: VAPID não configurado.")
    sub = payload.get("subscription")
    station = (payload.get("station") or "").upper()
    if not sub or not sub.get("endpoint") or not station:
        raise HTTPException(400, "subscription e station são obrigatórios.")
    ap = store.resolve(station)
    code = ap.icao if ap and ap.icao else station
    push_mod.save_sub(sub, code, payload.get("min_category", "IFR"))
    return {"ok": True, "station": code}


@app.post("/api/push/unsubscribe")
def push_unsubscribe(payload: dict = Body(...)) -> dict:
    endpoint = (payload.get("subscription") or {}).get("endpoint") or payload.get("endpoint")
    if not endpoint:
        raise HTTPException(400, "endpoint obrigatório.")
    push_mod.delete_sub(endpoint)
    return {"ok": True}


@app.get("/api/nowcast")
def api_nowcast(
    icao: str = Query(..., min_length=3, max_length=4, description="Código ICAO/IATA"),
    lang: str = Query("pt", description="Idioma da prosa (pt/en/es)"),
) -> dict:
    """Chuva sobre o aeródromo agora + tendência/nowcast (radar RainViewer)."""
    ap = store.resolve(icao)
    if ap is None:
        raise HTTPException(404, f"Aeroporto não encontrado: {icao!r}")
    try:
        return radar_wx.precip_at(ap.lat, ap.lon, lang=_lang(lang))
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


@app.get("/api/metar/historico")
def api_metar_historico(
    icao: str = Query(..., min_length=3, max_length=4, description="Código ICAO/IATA"),
    tz: int = Query(-3, ge=-12, le=14, description="Fuso para agrupar por hora local"),
) -> dict:
    """Climatologia: distribuição VFR/IFR por hora local e melhores horários para voar.

    Funciona com o que houver gravado; devolve samples=0 enquanto não há histórico.
    """
    ap = store.resolve(icao)
    code = ap.icao if ap and ap.icao else icao.upper()
    return history_mod.climatology(code, tz_offset_h=tz)


@app.get("/api/route")
def route(
    origin: str = Query(..., description="Código ICAO/IATA de origem"),
    dest: str = Query(..., description="Código ICAO/IATA de destino"),
    aircraft: str = Query(aircraft_mod.DEFAULT_KEY),
) -> dict:
    a = store.resolve(origin)
    b = store.resolve(dest)
    if a is None:
        raise HTTPException(404, f"Aeroporto de origem não encontrado: {origin!r}")
    if b is None:
        raise HTTPException(404, f"Aeroporto de destino não encontrado: {dest!r}")

    ac = aircraft_mod.get(aircraft)
    pa, pb = Point(a.lat, a.lon), Point(b.lat, b.lon)

    dist_nm = calc.great_circle_distance_nm(pa, pb)
    bearing = calc.initial_bearing_deg(pa, pb)
    # Tempo/combustível só quando a aeronave tem o dado; senão, ficam nulos (n/d).
    block_h = calc.flight_time_hours(dist_nm, ac.cruise_kt) if ac.cruise_kt else None
    density = aircraft_mod.fuel_density(ac.category)
    fuel = calc.fuel_estimate(block_h, ac.burn_kg_h, fuel_density_kg_per_l=density) if (block_h is not None and ac.burn_kg_h) else None

    return {
        "origin": a.to_dict(),
        "dest": b.to_dict(),
        "aircraft": {
            "key": ac.key,
            "name": ac.name,
            "category": ac.category,
            "cruise_kt": ac.cruise_kt,
            "burn_kg_h": ac.burn_kg_h,
        },
        "distance": {
            "nm": round(dist_nm, 1),
            "km": round(dist_nm * calc.NM_TO_KM, 1),
        },
        "bearing_deg": round(bearing),
        "time": {
            "block_hours": round(block_h, 2) if block_h is not None else None,
            "block_hm": calc.format_hm(block_h) if block_h is not None else None,
        },
        "fuel": fuel,
        "path": calc.great_circle_path(pa, pb),
        "midpoint": (lambda m: {"lat": m.lat, "lon": m.lon})(calc.midpoint(pa, pb)),
    }


@app.get("/api/route/multi")
def route_multi(
    origin: str = Query(..., description="Código ICAO/IATA de origem"),
    dest: str = Query(..., description="Código ICAO/IATA de destino"),
    aircraft: str = Query(aircraft_mod.DEFAULT_KEY),
    reserve: float = Query(0.85, ge=0.5, le=1.0, description="Fração do alcance usável (reserva)"),
) -> dict:
    """Rota com escalas de reabastecimento (menos paradas; empate por distância).

    Quando a distância direta cabe no alcance da aeronave, devolve direct=True
    e nenhuma escala. Quando não há caminho possível, reachable=False (o front
    desenha a reta + alerta de rota inalcançável).
    """
    a = store.resolve(origin)
    b = store.resolve(dest)
    if a is None:
        raise HTTPException(404, f"Aeroporto de origem não encontrado: {origin!r}")
    if b is None:
        raise HTTPException(404, f"Aeroporto de destino não encontrado: {dest!r}")

    ac = aircraft_mod.get(aircraft)
    pa, pb = Point(a.lat, a.lon), Point(b.lat, b.lon)
    # Sem autonomia conhecida não dá para planejar escalas: devolve só a rota direta.
    if ac.range_nm:
        plan = routing_mod.plan(store, a, b, ac.range_nm, reserve=reserve)
    else:
        plan = {
            "reachable": True, "direct": True, "waypoints": [a, b], "stops": [],
            "max_leg_nm": 0.0, "direct_nm": calc.great_circle_distance_nm(pa, pb),
        }

    legs = []
    path: list[list[float]] = []
    total_nm = total_h = total_fuel = 0.0
    have_time = have_fuel = True
    wpts = plan["waypoints"]
    for x, y in zip(wpts, wpts[1:]):
        px, py = Point(x.lat, x.lon), Point(y.lat, y.lon)
        dnm = calc.great_circle_distance_nm(px, py)
        h = calc.flight_time_hours(dnm, ac.cruise_kt) if ac.cruise_kt else None
        fuel = calc.fuel_estimate(h, ac.burn_kg_h, fuel_density_kg_per_l=aircraft_mod.fuel_density(ac.category)) if (h is not None and ac.burn_kg_h) else None
        total_nm += dnm
        if h is not None:
            total_h += h
        else:
            have_time = False
        if fuel is not None:
            total_fuel += fuel["total_kg"]
        else:
            have_fuel = False
        legs.append({
            "from": x.to_dict(), "to": y.to_dict(),
            "nm": round(dnm, 1), "km": round(dnm * calc.NM_TO_KM, 1),
            "hm": calc.format_hm(h) if h is not None else None,
            "fuel_kg": fuel["total_kg"] if fuel is not None else None,
        })
        path.extend(calc.great_circle_path(px, py, 32))

    return {
        "reachable": plan["reachable"],
        "direct": plan.get("direct", False),
        "aircraft": {"key": ac.key, "name": ac.name, "range_nm": ac.range_nm},
        "max_leg_nm": round(plan["max_leg_nm"], 1),
        "direct_nm": round(plan["direct_nm"], 1),
        "num_stops": len(plan["stops"]),
        "stops": [s.to_dict() for s in plan["stops"]],
        "waypoints": [w.to_dict() for w in wpts],
        "legs": legs,
        "path": path if plan["reachable"] else calc.great_circle_path(pa, pb),
        "totals": {
            "nm": round(total_nm, 1),
            "km": round(total_nm * calc.NM_TO_KM, 1),
            "hm": calc.format_hm(total_h) if have_time else None,
            "fuel_kg": round(total_fuel, 1) if have_fuel else None,
        },
    }


# Frontend estático. Montado por último para não capturar as rotas /api/*.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---- Páginas estáticas i18n (pt na raiz; en/es em subpasta /en /es) -------
PAGES = {
    "": "index.html",
    "comparar": "comparar.html",
    "tempo": "tempo.html",
    "radar": "radar.html",
    "cartas": "cartas.html",
    "sobre": "sobre.html",
}


def _page_response(slug: str, lang: str) -> HTMLResponse:
    html = (STATIC_DIR / PAGES[slug]).read_text(encoding="utf-8")
    return HTMLResponse(i18n.render(html, lang, slug))


def _make_page_route(slug: str, lang: str):
    def _route() -> HTMLResponse:
        return _page_response(slug, lang)

    return _route


for _slug in PAGES:
    app.add_api_route(
        "/" + _slug if _slug else "/",
        _make_page_route(_slug, "pt"),
        methods=["GET"],
        response_class=HTMLResponse,
    )
    for _lg in ("en", "es"):  # não usar "_lang": rebindaria a função _lang()
        app.add_api_route(
            f"/{_lg}" + (("/" + _slug) if _slug else ""),
            _make_page_route(_slug, _lg),
            methods=["GET"],
            response_class=HTMLResponse,
        )


@app.get("/ads.txt")
def ads_txt() -> FileResponse:
    """Autorização de vendedores do AdSense (precisa ficar na raiz do domínio)."""
    return FileResponse(STATIC_DIR / "ads.txt", media_type="text/plain")


@app.get("/reset")
def reset_page() -> FileResponse:
    """Página que desregistra o service worker e limpa o cache (autoatendimento)."""
    return FileResponse(STATIC_DIR / "reset.html", headers={"Cache-Control": "no-cache"})


@app.get("/sw.js")
def service_worker() -> FileResponse:
    """Service worker do PWA — servido da raiz para controlar todo o site."""
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    """Web App Manifest do PWA (instalação em Android/iPhone)."""
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


# ----- SEO: páginas de rota + sitemap (pt na raiz; en/es em /en /es) ----- #
def _rotas_index(lang: str) -> str:
    return seo.render_routes_index(lang)


def _curiosidades(lang: str) -> str:
    return seo.render_curiosidades(store, lang)


# Aeródromos para os links cruzados das páginas SEO de tempo.
_POPULAR_TEMPO = ["SBGR", "SBSP", "SBBR", "SBGL", "SBRJ", "SBCF", "SBSV", "SBPA",
                  "SBCT", "SBKP", "SBRF", "SBFZ", "SBEG", "SBBE", "SBFL", "SBGO"]


def _tempo_aerodromo(icao: str, lang: str) -> str:
    """Página SEO de tempo por aeródromo, do último METAR gravado no histórico."""
    ap = store.resolve(icao)
    if ap is None:
        raise HTTPException(404, f"Aeródromo não encontrado: {icao!r}")
    code = ap.icao or ap.code
    raw, obs = history_mod.latest_metar(code)
    related = []
    for ic in _POPULAR_TEMPO:
        a = store.resolve(ic)
        if a is not None:
            related.append((a.icao or ic, a.city or a.name))
    return seo.render_tempo_page(ap, raw, obs, related, lang)


def _rota_page(origin: str, dest: str, lang: str) -> Response:
    o = seo.CITY_BY_SLUG.get(origin)
    d = seo.CITY_BY_SLUG.get(dest)
    if o is None or d is None:
        raise HTTPException(404, "Rota não encontrada.")
    # Direção canônica: renderiza. Reversa: 301 para a canônica. Podada: 404.
    if (origin, dest) in seo.ROUTE_PAIR_SET:
        html = seo.render_route_page(store, o, d, lang)
        if html is None:
            raise HTTPException(404, "Rota não encontrada.")
        return HTMLResponse(html)
    if (dest, origin) in seo.ROUTE_PAIR_SET:
        return RedirectResponse(f"{i18n.prefix(lang)}/rota/{dest}/{origin}", status_code=301)
    raise HTTPException(404, "Rota não encontrada.")


def _voo_page(origin: str, dest: str, lang: str) -> Response:
    """A antiga página /voo foi consolidada em /rota — 301 para a canônica."""
    o = seo.CITY_BY_SLUG.get(origin)
    d = seo.CITY_BY_SLUG.get(dest)
    if o is None or d is None:
        raise HTTPException(404, "Rota não encontrada.")
    canon = seo.canonical_pair(origin, dest)
    if canon is None:
        raise HTTPException(404, "Rota não encontrada.")
    co, cd = canon
    return RedirectResponse(f"{i18n.prefix(lang)}/rota/{co}/{cd}", status_code=301)


# Registra pt na raiz + en/es em subpasta para as 4 páginas SEO traduzidas.
def _make_index_route(fn, lang: str):
    def _r() -> str:
        return fn(lang)
    return _r


def _make_pair_route(fn, lang: str):
    def _r(origin: str, dest: str) -> str:
        return fn(origin, dest, lang)
    return _r


def _make_tempo_route(lang: str):
    def _r(icao: str) -> str:
        return _tempo_aerodromo(icao, lang)
    return _r


# NB: não usar "_lang" como variável do loop — isso rebindaria a função _lang()
# do topo do módulo (usada pelos endpoints /api/metar, /api/taf, /api/nowcast).
for _lg in ("pt", "en", "es"):
    _pre = "" if _lg == "pt" else f"/{_lg}"
    app.add_api_route(f"{_pre}/rotas", _make_index_route(_rotas_index, _lg),
                      methods=["GET"], response_class=HTMLResponse)
    app.add_api_route(f"{_pre}/curiosidades", _make_index_route(_curiosidades, _lg),
                      methods=["GET"], response_class=HTMLResponse)
    app.add_api_route(f"{_pre}/rota/{{origin}}/{{dest}}", _make_pair_route(_rota_page, _lg),
                      methods=["GET"], response_class=HTMLResponse)
    app.add_api_route(f"{_pre}/voo/{{origin}}/{{dest}}", _make_pair_route(_voo_page, _lg),
                      methods=["GET"], response_class=HTMLResponse)
    app.add_api_route(f"{_pre}/tempo/{{icao}}", _make_tempo_route(_lg),
                      methods=["GET"], response_class=HTMLResponse)


@app.get("/sitemap.xml")
def sitemap() -> Response:
    icaos = history_mod.stations_with_metar()
    return Response(content=seo.build_sitemap(icaos), media_type="application/xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> str:
    return seo.build_robots()

"""Planejador de rota com escalas de reabastecimento (caminho mínimo em grafo).

Dado origem, destino e o alcance da aeronave, encontra a sequência de paradas
(aeroportos onde dá para reabastecer) que liga os dois pontos com o **menor
número de escalas** e, em empate, a **menor distância total**. Se não houver
caminho possível (nenhuma parada dentro do alcance — ex.: travessia oceânica
longa demais para a aeronave), devolve `reachable=False` para o front desenhar
a reta + alerta de "rota inalcançável".

Aproximações honestas (limitações dos dados OurAirports):
  - "tem combustível" ≈ aeroporto dos tipos small/medium/large (não há dado real
    de combustível).
  - Não modela espaço aéreo proibido nem regras de voo sobre o mar.
Para desempenho, os candidatos são restritos a um corredor elíptico ao redor da
linha origem→destino.
"""

from __future__ import annotations

import heapq
import math

from . import calc
from .airports import Airport, AirportStore
from .calc import Point

# Tipos aceitos como parada de reabastecimento (escolha do produto).
STOP_TYPES = {"small_airport", "medium_airport", "large_airport"}
_TYPE_RANK = {"large_airport": 3, "medium_airport": 2, "small_airport": 1}

RESERVE_FACTOR = 0.85   # usa 85% do alcance máximo (reserva/vento)
MAX_NODES = 3500        # teto de candidatos no corredor (desempenho)
_REMOTE_MAX_LEG = 2000.0  # acima disso (jatos) não checa "remoto" — cruzam água ok


def _cover_cell_deg(max_leg: float) -> float:
    """Célula da grade de cobertura, ~1/6 da perna: nós densos p/ pouco alcance,
    esparsos p/ muito alcance (mantém o grafo conexo e o nº de nós sob controle)."""
    return min(20.0, max(0.5, max_leg / 360.0))

# Penalidade (em nm-equivalente) para preferir aeroportos MAIORES no desempate
# entre soluções com o mesmo nº de escalas. Não afeta a contagem de escalas
# (que é o critério primário), só a escolha de QUAIS paradas usar.
_PEN_TYPE = {"large_airport": 0.0, "medium_airport": 120.0, "small_airport": 400.0}

# Pernas "remotas" (sobre o mar / sem aeroporto de diversão por perto) recebem
# penalidade — desencoraja travessias oceânicas quando há alternativa com o mesmo
# nº de escalas. Proxy honesto: usa a densidade de aeroportos (não há dado de costa).
_DIVERT_NM = 180.0      # raio de diversão considerado "seguro"
_REMOTE_PEN = 1500.0    # penalidade nm-equiv. por perna remota

_cand_cache: dict[int, list[Airport]] = {}
_grid_cache: dict[int, set[tuple[int, int]]] = {}


def _candidates(store: AirportStore) -> list[Airport]:
    key = id(store)
    if key not in _cand_cache:
        _cand_cache[key] = store.candidates(STOP_TYPES)
    return _cand_cache[key]


def _presence_grid(store: AirportStore) -> set[tuple[int, int]]:
    """Células de 1°×1° que contêm ao menos um aeroporto (p/ checar diversão)."""
    key = id(store)
    if key not in _grid_cache:
        cells = {(int(math.floor(a.lat)), int(math.floor(a.lon))) for a in _candidates(store)}
        _grid_cache[key] = cells
    return _grid_cache[key]


def _has_divert(cells: set[tuple[int, int]], lat: float, lon: float, n: int) -> bool:
    ci, cj = int(math.floor(lat)), int(math.floor(lon))
    for di in range(-n, n + 1):
        for dj in range(-n, n + 1):
            if (ci + di, cj + dj) in cells:
                return True
    return False


def _corridor(store: AirportStore, o: Point, d: Point, direct: float, max_leg: float) -> list[Airport]:
    """Candidatos a parada num corredor ao redor de O→D.

    O corredor é largo o bastante para permitir desvios reais (contornar mar,
    seguir cadeias de ilhas/costa). Para manter o grafo conexo sem explodir o nº
    de nós, faz-se uma seleção por COBERTURA: 1 aeroporto (o maior/mais perto da
    linha) por célula da grade. Assim sempre há "degraus" para o A* pular.
    """
    # Desvio permitido cresce com a rota: rotas longas precisam de corredor largo.
    slack = max(max_leg * 1.5, direct * 0.6)
    sum_limit = direct + slack
    cell_deg = _cover_cell_deg(max_leg)
    margin_deg = slack / 60.0 + 1.0
    lat_lo = min(o.lat, d.lat) - margin_deg
    lat_hi = max(o.lat, d.lat) + margin_deg
    lon_lo = min(o.lon, d.lon) - margin_deg
    lon_hi = max(o.lon, d.lon) + margin_deg

    # Melhor candidato por célula: (chave da grade) -> (ordem, aeroporto).
    best: dict[tuple[int, int], tuple[tuple[int, float], Airport]] = {}
    for ap in _candidates(store):
        if not (lat_lo <= ap.lat <= lat_hi and lon_lo <= ap.lon <= lon_hi):
            continue
        p = Point(ap.lat, ap.lon)
        s = calc.great_circle_distance_nm(o, p) + calc.great_circle_distance_nm(p, d)
        if s > sum_limit:
            continue
        key = (round(ap.lat / cell_deg), round(ap.lon / cell_deg))
        order = (-_TYPE_RANK.get(ap.type, 1), s)  # maior aeroporto; depois, mais perto da linha
        cur = best.get(key)
        if cur is None or order < cur[0]:
            best[key] = (order, ap)

    nodes = [ap for _, ap in best.values()]
    if len(nodes) > MAX_NODES:
        nodes.sort(key=lambda ap: calc.great_circle_distance_nm(o, Point(ap.lat, ap.lon))
                   + calc.great_circle_distance_nm(Point(ap.lat, ap.lon), d))
        nodes = nodes[:MAX_NODES]
    return nodes


def _grid_key(lat: float, lon: float, cell: float) -> tuple[int, int]:
    return (int(math.floor(lat / cell)), int(math.floor(lon / cell)))


def plan(store: AirportStore, origin: Airport, dest: Airport, range_nm: float,
         reserve: float = RESERVE_FACTOR) -> dict:
    """Planeja a rota. Devolve dict com waypoints (Airport) e metadados."""
    o = Point(origin.lat, origin.lon)
    d = Point(dest.lat, dest.lon)
    direct = calc.great_circle_distance_nm(o, d)
    max_leg = range_nm * reserve

    base = {"direct_nm": direct, "max_leg_nm": max_leg, "range_nm": range_nm, "reserve": reserve}

    if max_leg <= 0:
        return {**base, "reachable": False, "waypoints": [origin, dest], "stops": []}
    if direct <= max_leg:
        return {**base, "reachable": True, "direct": True, "waypoints": [origin, dest], "stops": []}

    # Nós: 0 = origem, 1 = destino, 2.. = candidatos do corredor.
    cand = _corridor(store, o, d, direct, max_leg)
    aps: list[Airport] = [origin, dest, *cand]
    pts: list[Point] = [Point(a.lat, a.lon) for a in aps]
    n = len(aps)

    # Índice espacial (grade) para achar vizinhos dentro de max_leg.
    cell = max(max_leg / 60.0, 0.1)
    grid: dict[tuple[int, int], list[int]] = {}
    for i, p in enumerate(pts):
        grid.setdefault(_grid_key(p.lat, p.lon, cell), []).append(i)

    cells = _presence_grid(store)
    div_n = max(1, math.ceil(_DIVERT_NM / 60.0))
    remote_cache: dict[tuple[int, int], float] = {}

    check_remote = max_leg <= _REMOTE_MAX_LEG  # jatos de longo alcance cruzam água

    def pen_remote(u: int, v: int) -> float:
        """Penaliza a perna u→v se trechos dela ficam longe de aeroporto de diversão."""
        if not check_remote:
            return 0.0
        kk = (u, v) if u < v else (v, u)
        cached = remote_cache.get(kk)
        if cached is not None:
            return cached
        remote = False
        for q in calc.great_circle_path(pts[u], pts[v], 4)[1:-1]:  # 3 pontos internos
            if not _has_divert(cells, q[0], q[1], div_n):
                remote = True
                break
        val = _REMOTE_PEN if remote else 0.0
        remote_cache[kk] = val
        return val

    def pen_arrive(v: int) -> float:
        """Penalidade por aterrissar num aeroporto menor (0 na origem/destino)."""
        if v == 0 or v == 1:
            return 0.0
        return _PEN_TYPE.get(aps[v].type, 400.0)

    def neighbors(u: int):
        ku = _grid_key(pts[u].lat, pts[u].lon, cell)
        for du in range(-2, 3):
            for dv in range(-2, 3):
                for v in grid.get((ku[0] + du, ku[1] + dv), ()):
                    if v == u:
                        continue
                    dist = calc.great_circle_distance_nm(pts[u], pts[v])
                    if dist <= max_leg:
                        yield v, dist

    # A* lexicográfico: (nº de escalas, custo). custo = distância + penalidades
    # (aeroporto maior e evitar perna remota). Heurística admissível (≤ custo real).
    def h_legs(u: int) -> int:
        return math.ceil(calc.great_circle_distance_nm(pts[u], d) / max_leg)

    def h_dist(u: int) -> float:
        return calc.great_circle_distance_nm(pts[u], d)

    g_legs = {0: 0}
    g_cost = {0: 0.0}
    came: dict[int, int] = {}
    counter = 0
    pq: list[tuple[int, float, int, int]] = [(h_legs(0), h_dist(0), counter, 0)]
    closed: set[int] = set()

    while pq:
        _, _, _, u = heapq.heappop(pq)
        if u in closed:
            continue
        if u == 1:
            break
        closed.add(u)
        for v, dist in neighbors(u):
            nl = g_legs[u] + 1
            nc = g_cost[u] + dist + pen_arrive(v) + pen_remote(u, v)
            if v not in g_legs or (nl, nc) < (g_legs[v], g_cost[v]):
                g_legs[v], g_cost[v] = nl, nc
                came[v] = u
                counter += 1
                heapq.heappush(pq, (nl + h_legs(v), nc + h_dist(v), counter, v))

    if 1 not in came and 1 not in closed:
        return {**base, "reachable": False, "waypoints": [origin, dest], "stops": []}

    # Reconstrói o caminho de nós (índices) até a origem.
    path_idx = [1]
    while path_idx[-1] != 0:
        path_idx.append(came[path_idx[-1]])
    path_idx.reverse()

    waypoints = [aps[i] for i in path_idx]
    stops = waypoints[1:-1]
    return {**base, "reachable": True, "direct": False, "waypoints": waypoints,
            "stops": stops, "num_stops": len(stops)}

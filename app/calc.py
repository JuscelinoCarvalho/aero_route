"""Cálculos de navegação aérea: distância great-circle, rumo, tempo e combustível.

Todas as funções são puras (sem efeitos colaterais) para facilitar testes e
evolução. Unidades náuticas são o padrão da aviação:
  - distância em milhas náuticas (NM); 1 NM = 1.852 km
  - velocidade em nós (kt) = NM por hora
"""

from __future__ import annotations

import math
from dataclasses import dataclass

NM_TO_KM = 1.852
EARTH_RADIUS_NM = 3440.065  # raio médio da Terra em milhas náuticas


@dataclass(frozen=True)
class Point:
    """Coordenada geográfica em graus decimais."""

    lat: float
    lon: float


def great_circle_distance_nm(a: Point, b: Point) -> float:
    """Distância great-circle (ortodrômica) entre dois pontos, em NM.

    Usa a fórmula de haversine, numericamente estável para distâncias curtas.
    """
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(h))


def initial_bearing_deg(a: Point, b: Point) -> float:
    """Rumo verdadeiro inicial (0-360°) ao partir de A em direção a B."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlon = math.radians(b.lon - a.lon)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def midpoint(a: Point, b: Point) -> Point:
    """Ponto médio ao longo da rota great-circle (útil para centralizar o mapa)."""
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    bx = math.cos(lat2) * math.cos(lon2 - lon1)
    by = math.cos(lat2) * math.sin(lon2 - lon1)
    lat3 = math.atan2(
        math.sin(lat1) + math.sin(lat2),
        math.sqrt((math.cos(lat1) + bx) ** 2 + by**2),
    )
    lon3 = lon1 + math.atan2(by, math.cos(lat1) + bx)
    return Point(math.degrees(lat3), math.degrees(lon3))


def great_circle_path(a: Point, b: Point, segments: int = 64) -> list[list[float]]:
    """Lista de [lat, lon] interpolando a rota great-circle, para desenhar no mapa.

    A interpolação esférica (slerp) garante que a linha siga a curva real da
    rota, e não uma reta na projeção do mapa.
    """
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    d = great_circle_distance_nm(a, b) / EARTH_RADIUS_NM  # distância angular em rad
    if d == 0:
        return [[a.lat, a.lon], [b.lat, b.lon]]
    path: list[list[float]] = []
    for i in range(segments + 1):
        f = i / segments
        sin_d = math.sin(d)
        A = math.sin((1 - f) * d) / sin_d
        B = math.sin(f * d) / sin_d
        x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
        y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
        z = A * math.sin(lat1) + B * math.sin(lat2)
        lat = math.atan2(z, math.sqrt(x * x + y * y))
        lon = math.atan2(y, x)
        path.append([math.degrees(lat), math.degrees(lon)])
    return path


def flight_time_hours(distance_nm: float, cruise_speed_kt: float | None, taxi_climb_min: float = 25.0) -> float:
    """Tempo de bloco estimado em horas.

    Soma o tempo de cruzeiro (distância / velocidade) a uma folga fixa para
    taxi, decolagem, subida e descida (`taxi_climb_min`). É uma aproximação;
    o piloto valida com dados reais da aeronave. Velocidade ausente (None) ou
    não positiva devolve 0.
    """
    if not cruise_speed_kt or cruise_speed_kt <= 0:
        return 0.0
    return distance_nm / cruise_speed_kt + taxi_climb_min / 60.0


def fuel_estimate(
    block_time_h: float,
    burn_kg_per_h: float | None,
    reserve_min: float = 45.0,
    fuel_density_kg_per_l: float = 0.8,
) -> dict[str, float]:
    """Estimativa simples de combustível.

    - trip: combustível para o trajeto (tempo de bloco x consumo)
    - reserve: reserva regulamentar aproximada (`reserve_min` de voo)
    - total: trip + reserve
    Retorna kg e litros (densidade média do Jet A ~0,8 kg/L). Consumo ausente
    (None) é tratado como 0 — os chamadores devem checar antes se preferem n/d.
    """
    burn_kg_per_h = burn_kg_per_h or 0.0
    trip_kg = block_time_h * burn_kg_per_h
    reserve_kg = (reserve_min / 60.0) * burn_kg_per_h
    total_kg = trip_kg + reserve_kg
    return {
        "trip_kg": round(trip_kg, 1),
        "reserve_kg": round(reserve_kg, 1),
        "total_kg": round(total_kg, 1),
        "trip_l": round(trip_kg / fuel_density_kg_per_l, 1),
        "total_l": round(total_kg / fuel_density_kg_per_l, 1),
    }


def format_hm(hours: float) -> str:
    """Formata horas decimais como 'Xh Ymin'."""
    total_min = round(hours * 60)
    h, m = divmod(total_min, 60)
    return f"{h}h {m:02d}min"

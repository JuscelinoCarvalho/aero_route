"""Declinação magnética (variação) no Brasil — modelo WMM-2025 (época 2026.5).

Grade de 5° (lat −35..5, lon −75..−30) com valores de declinação em graus
(Leste positivo, Oeste negativo), pré-calculados do World Magnetic Model da NOAA.
``declination(lat, lon)`` interpola bilinearmente. Usado só como *fallback* no
cálculo do rumo verdadeiro de pista quando o ROTAER não traz as coordenadas das
cabeceiras (com coordenadas, o rumo é geométrico e não precisa de declinação).

A declinação varia ~0,1°/ano; regerar a grade a cada ~2 anos (script no histórico).
"""

from __future__ import annotations

_LAT0, _LON0, _STEP = -35, -75, 5
_NLAT, _NLON = 9, 10

# _GRID[i][j] = declinação em (lat=_LAT0+i*_STEP, lon=_LON0+j*_STEP), em graus.
_GRID = [
    [5.03, 0.47, -4.21, -8.66, -12.59, -15.82, -18.29, -20.07, -21.26, -22.01],
    [2.14, -2.50, -7.19, -11.59, -15.38, -18.41, -20.66, -22.22, -23.23, -23.83],
    [-0.47, -5.07, -9.66, -13.87, -17.42, -20.17, -22.14, -23.43, -24.17, -24.51],
    [-2.68, -7.16, -11.55, -15.48, -18.72, -21.17, -22.81, -23.76, -24.14, -24.07],
    [-4.46, -8.74, -12.85, -16.47, -19.38, -21.49, -22.78, -23.33, -23.26, -22.67],
    [-5.81, -9.85, -13.66, -16.95, -19.52, -21.27, -22.18, -22.31, -21.75, -20.64],
    [-6.81, -10.60, -14.09, -17.04, -19.27, -20.66, -21.19, -20.90, -19.90, -18.36],
    [-7.58, -11.08, -14.26, -16.88, -18.76, -19.80, -19.96, -19.31, -17.97, -16.14],
    [-8.18, -11.42, -14.29, -16.56, -18.09, -18.77, -18.61, -17.68, -16.13, -14.14],
]

def declination(lat: float, lon: float) -> float:
    """Declinação magnética (graus, Leste +) em (lat, lon). Fora da grade, usa a borda."""
    fi = (lat - _LAT0) / _STEP
    fj = (lon - _LON0) / _STEP
    i = max(0, min(_NLAT - 2, int(fi)))
    j = max(0, min(_NLON - 2, int(fj)))
    di = max(0.0, min(1.0, fi - i))
    dj = max(0.0, min(1.0, fj - j))
    v00, v01 = _GRID[i][j], _GRID[i][j + 1]
    v10, v11 = _GRID[i + 1][j], _GRID[i + 1][j + 1]
    top = v00 * (1 - dj) + v01 * dj
    bot = v10 * (1 - dj) + v11 * dj
    return round(top * (1 - di) + bot * di, 1)

"""Carga e busca na base de aeroportos (OurAirports, domínio público).

A base (~85 mil registros) é carregada uma vez na memória ao iniciar o app.
Índices por código ICAO/IATA permitem resolução O(1); a busca textual é
insensível a acentos (importante p/ cidades) e prioriza aeroportos maiores.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "airports.csv"

# Peso por tipo para ordenar resultados de busca (maior = mais relevante).
_TYPE_RANK = {
    "large_airport": 4,
    "medium_airport": 3,
    "small_airport": 1,
    "seaplane_base": 0,
    "heliport": 0,
    "balloonport": 0,
}

# Tipos considerados "aeródromo" para listagem por estado (exclui heliponto etc.).
AERODROME_TYPES = {"large_airport", "medium_airport", "small_airport"}


def normalize(text: str) -> str:
    """Minúsculas e sem acentos, para busca tolerante (ex.: 'São' -> 'sao')."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Apelidos de cidades em português/espanhol → nome da cidade na base (inglês).
# A base OurAirports só traz o nome em inglês, então "Tóquio", "Londres" ou
# "Nova York" não encontrariam nada. Aqui mapeamos o apelido para o termo em
# inglês; a busca então também casa aeródromos dessa cidade. Só listamos casos
# em que a grafia difere do inglês (Paris/Berlin já casam direto). Chave e valor
# são normalizados (sem acento, minúsculas) no carregamento.
_CITY_ALIASES_RAW: dict[str, str] = {
    # Ásia
    "tóquio": "tokyo", "tokio": "tokyo",
    "quioto": "kyoto", "kioto": "kyoto",
    "osaka": "osaka", "nagoia": "nagoya", "sapporo": "sapporo", "okinawa": "okinawa",
    "seul": "seoul",
    "pequim": "beijing", "pekin": "beijing",
    "xangai": "shanghai", "cantão": "guangzhou",
    "cingapura": "singapore", "singapura": "singapore", "singapur": "singapore",
    "bangcoc": "bangkok", "bangcoque": "bangkok",
    "nova delhi": "new delhi", "nueva delhi": "new delhi",
    "bombaim": "mumbai", "calcutá": "kolkata",
    "taipé": "taipei", "taipe": "taipei",
    "dubai": "dubai", "abu dhabi": "abu dhabi", "doha": "doha",
    # Europa
    "londres": "london",
    "roma": "rome", "milão": "milan", "veneza": "venice",
    "florença": "florence", "turim": "turin", "nápoles": "naples", "gênova": "genoa",
    "genebra": "geneva", "ginebra": "geneva", "zurique": "zurich", "basileia": "basel", "berna": "bern",
    "munique": "munich", "colônia": "cologne", "hamburgo": "hamburg", "berlim": "berlin",
    "viena": "vienna",
    "praga": "prague", "varsóvia": "warsaw", "cracóvia": "krakow",
    "bruxelas": "brussels", "antuérpia": "antwerp", "amberes": "antwerp",
    "haia": "the hague", "la haya": "the hague", "roterdã": "rotterdam", "roterdão": "rotterdam",
    "amsterdã": "amsterdam", "amsterdão": "amsterdam",
    "copenhague": "copenhagen", "estocolmo": "stockholm", "gotemburgo": "gothenburg",
    "helsinque": "helsinki", "helsínquia": "helsinki",
    "atenas": "athens", "lisboa": "lisbon",
    "istambul": "istanbul", "estambul": "istanbul", "moscou": "moscow", "moscovo": "moscow", "moscu": "moscow",
    # Américas
    "nova york": "new york", "nova iorque": "new york", "nueva york": "new york",
    "cidade do méxico": "mexico city", "ciudad de mexico": "mexico city",
    # África
    "joanesburgo": "johannesburg", "cidade do cabo": "cape town",
    "cairo": "cairo", "el cairo": "cairo", "casablanca": "casablanca",
}
_CITY_ALIASES: dict[str, str] = {
    normalize(k): normalize(v) for k, v in _CITY_ALIASES_RAW.items()
}


def _alias_city_terms(q: str) -> set[str]:
    """Termos-alvo (cidade em inglês) dos apelidos cuja chave começa por ``q``.

    Casa incrementalmente para o autocomplete: "toq" já aponta para "tokyo".
    """
    if len(q) < 2:
        return set()
    return {target for alias, target in _CITY_ALIASES.items() if alias.startswith(q)}


@dataclass(frozen=True)
class Airport:
    icao: str
    iata: str
    name: str
    city: str
    country: str
    region: str  # iso_region do OurAirports, ex.: "BR-SP"
    lat: float
    lon: float
    type: str

    @property
    def code(self) -> str:
        """Melhor código para exibir: prefere IATA, cai para ICAO."""
        return self.iata or self.icao

    def to_dict(self) -> dict:
        return asdict(self) | {"code": self.code}


@dataclass(frozen=True)
class _Indexed:
    """Aeroporto + campos pré-normalizados para a busca."""

    ap: Airport
    n_code: str  # "icao iata" normalizado
    n_city: str
    n_name: str


class AirportStore:
    def __init__(self, csv_path: Path = DATA_FILE) -> None:
        self._index: list[_Indexed] = []
        self._by_icao: dict[str, Airport] = {}
        self._by_iata: dict[str, Airport] = {}
        self._load(csv_path)

    def _load(self, csv_path: Path) -> None:
        with csv_path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row["type"] == "closed":
                    continue
                try:
                    lat = float(row["latitude_deg"])
                    lon = float(row["longitude_deg"])
                except (ValueError, KeyError):
                    continue
                icao = (row["icao_code"] or row["ident"] or "").upper()
                iata = (row["iata_code"] or "").upper()
                ap = Airport(
                    icao=icao,
                    iata=iata,
                    name=row["name"],
                    city=row["municipality"] or "",
                    country=row["iso_country"] or "",
                    region=row["iso_region"] or "",
                    lat=lat,
                    lon=lon,
                    type=row["type"],
                )
                self._index.append(
                    _Indexed(
                        ap=ap,
                        n_code=normalize(f"{icao} {iata}"),
                        n_city=normalize(ap.city),
                        n_name=normalize(ap.name),
                    )
                )
                if icao:
                    self._by_icao.setdefault(icao, ap)
                if iata:
                    self._by_iata.setdefault(iata, ap)

    def __len__(self) -> int:
        return len(self._index)

    def resolve(self, code: str) -> Airport | None:
        """Resolve um código ICAO (4 letras) ou IATA (3 letras)."""
        c = code.strip().upper()
        if len(c) == 3 and c in self._by_iata:
            return self._by_iata[c]
        return self._by_icao.get(c) or self._by_iata.get(c)

    def candidates(self, types: set[str]) -> list[Airport]:
        """Aeroportos de certos tipos (p/ planejamento de rota com escalas)."""
        return [it.ap for it in self._index if it.ap.type in types]

    def by_region(self, region: str) -> list[Airport]:
        """Aeródromos de uma região (iso_region, ex.: 'BR-SP'), em ordem alfabética."""
        reg = region.strip().upper()
        out = [
            it.ap
            for it in self._index
            if it.ap.region.upper() == reg and it.ap.type in AERODROME_TYPES
        ]
        out.sort(key=lambda a: normalize(a.name))
        return out

    def search(self, query: str, limit: int = 10) -> list[Airport]:
        """Busca por código, nome ou cidade (sem acento). Mais relevantes 1º."""
        q = normalize(query)
        if not q:
            return []

        # Apelidos de cidade PT/ES (ex.: "tóquio" -> "tokyo") para casar a base inglesa.
        alias_terms = _alias_city_terms(q)

        # Código exato tem prioridade absoluta.
        exact = self.resolve(query)
        results: list[tuple[int, Airport]] = []
        seen: set[int] = set()
        if exact:
            results.append((1000, exact))
            seen.add(id(exact))

        for item in self._index:
            if id(item.ap) in seen:
                continue
            score = 0
            if q in item.n_code:
                score = 50
            elif item.n_city and q in item.n_city:
                # Cidade que começa com a busca pontua mais (ex.: "rio" -> Rio).
                score = 30 if item.n_city.startswith(q) else 20
            elif alias_terms and item.n_city and any(item.n_city.startswith(t) for t in alias_terms):
                # Apelido PT/ES (ex.: "tóquio" -> aeródromos de Tokyo).
                score = 28
            elif q in item.n_name:
                score = 10
            if score:
                results.append((score + _TYPE_RANK.get(item.ap.type, 0), item.ap))

        results.sort(key=lambda t: t[0], reverse=True)
        return [ap for _, ap in results[:limit]]

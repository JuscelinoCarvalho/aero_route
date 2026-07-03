"""Histórico de METAR + climatologia (SQLite).

Grava observações METAR ao longo do tempo e responde "qual o melhor horário para
voar" (distribuição de categorias VFR/IFR por hora do dia) em cada aeródromo.

É o alicerce das fases preditiva e de alertas: quanto mais histórico, melhores os
padrões ("este aeródromo costuma fechar de manhã no inverno").

Fluxo previsto em produção: um cron chama `capture([...ICAOs...])` de tempos em
tempos (ex.: a cada 30 min). Cada METAR é decodificado por app/metar.py e gravado
com deduplicação por (estação, horário de observação).

Banco: app/data/wx_history.db (ou env WX_DB_PATH). Sem dependências externas.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import metar as metar_mod

DEFAULT_DB = Path(__file__).parent / "data" / "wx_history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metar_obs (
    station        TEXT    NOT NULL,
    obs_epoch      INTEGER NOT NULL,   -- horário da observação (UTC, epoch s)
    hour_utc       INTEGER NOT NULL,   -- hora do dia (UTC) pré-computada p/ climatologia
    category       TEXT    NOT NULL,   -- VFR/MVFR/IFR/LIFR/UNKNOWN
    ceiling_ft     INTEGER,
    visibility_m   INTEGER,
    wind_speed_kt  INTEGER,
    wind_gust_kt   INTEGER,
    temp_c         INTEGER,
    qnh_hpa        INTEGER,
    raw            TEXT    NOT NULL,
    captured_epoch INTEGER NOT NULL,
    PRIMARY KEY (station, obs_epoch)
);
CREATE INDEX IF NOT EXISTS idx_obs_station_hour ON metar_obs (station, hour_utc);

CREATE TABLE IF NOT EXISTS taf_obs (
    station        TEXT    NOT NULL,
    issued_epoch   INTEGER NOT NULL,   -- horário de emissão (UTC, epoch s)
    valid_from     TEXT,               -- DDHH
    valid_to       TEXT,               -- DDHH
    raw            TEXT    NOT NULL,
    captured_epoch INTEGER NOT NULL,
    PRIMARY KEY (station, issued_epoch)
);
"""


def _db_path(path: str | os.PathLike | None) -> str:
    return str(path or os.environ.get("WX_DB_PATH") or DEFAULT_DB)


def connect(path: str | os.PathLike | None = None) -> sqlite3.Connection:
    p = _db_path(path)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def observed_datetime(day: int | None, hhmm: str | None, now: datetime | None = None) -> datetime:
    """Reconstrói o instante UTC da observação a partir do DD/HHMM do METAR.

    Usa o ano/mês do momento da captura; se o dia cair no futuro (virada de mês),
    recua um mês.
    """
    now = now or datetime.now(timezone.utc)
    if day is None or not hhmm or len(hhmm) < 4:
        return now.replace(second=0, microsecond=0)
    hh, mm = int(hhmm[:2]), int(hhmm[2:4])
    for back in (0, 1):  # mês atual; se necessário, mês anterior
        y, m = now.year, now.month - back
        if m <= 0:
            y, m = y - 1, m + 12
        try:
            dt = datetime(y, m, day, hh, mm, tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt <= now + timedelta(hours=2):
            return dt
    return now.replace(second=0, microsecond=0)


def record(
    decoded: dict,
    *,
    path: str | os.PathLike | None = None,
    conn: sqlite3.Connection | None = None,
    now: datetime | None = None,
) -> bool:
    """Grava uma observação decodificada (de metar.decode). True se foi nova."""
    own = conn is None
    conn = conn or connect(path)
    try:
        dt = observed_datetime(decoded.get("day"), decoded.get("time_utc"), now)
        obs_epoch = int(dt.timestamp())
        w = decoded.get("wind") or {}
        cur = conn.execute(
            """INSERT OR IGNORE INTO metar_obs
               (station, obs_epoch, hour_utc, category, ceiling_ft, visibility_m,
                wind_speed_kt, wind_gust_kt, temp_c, qnh_hpa, raw, captured_epoch)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                decoded.get("station") or "?",
                obs_epoch,
                dt.hour,
                decoded.get("category") or "UNKNOWN",
                decoded.get("ceiling_ft"),
                decoded.get("visibility_m"),
                w.get("speed_kt"),
                w.get("gust_kt"),
                decoded.get("temp_c"),
                decoded.get("qnh_hpa"),
                decoded.get("raw") or "",
                int((now or datetime.now(timezone.utc)).timestamp()),
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        if own:
            conn.close()


def record_raw(raw: str, **kw) -> bool:
    """Decodifica e grava um METAR cru."""
    return record(metar_mod.decode(raw), **kw)


def record_taf(
    decoded: dict,
    *,
    path: str | os.PathLike | None = None,
    conn: sqlite3.Connection | None = None,
    now: datetime | None = None,
) -> bool:
    """Grava um TAF decodificado (de taf.decode). Dedup por (estação, emissão)."""
    own = conn is None
    conn = conn or connect(path)
    try:
        day = decoded.get("issued_day")
        hhmm = (decoded.get("issued_utc") or "").replace(":", "")
        dt = observed_datetime(int(day) if day else None, hhmm, now)
        cur = conn.execute(
            """INSERT OR IGNORE INTO taf_obs
               (station, issued_epoch, valid_from, valid_to, raw, captured_epoch)
               VALUES (?,?,?,?,?,?)""",
            (
                decoded.get("station") or "?",
                int(dt.timestamp()),
                decoded.get("valid_from"),
                decoded.get("valid_to"),
                decoded.get("raw") or "",
                int((now or datetime.now(timezone.utc)).timestamp()),
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        if own:
            conn.close()


def capture(icaos: list[str], *, path: str | os.PathLike | None = None) -> dict:
    """Busca o METAR atual de cada ICAO na REDEMET e grava. Para uso por cron."""
    from . import redemet  # import tardio: só necessário na captura ao vivo

    conn = connect(path)
    new = saved = 0
    errors: list[str] = []
    try:
        for icao in icaos:
            try:
                raw = redemet.fetch_metar(icao)
            except RuntimeError as exc:
                errors.append(f"{icao}: {exc}")
                continue
            saved += 1
            if record(metar_mod.decode(raw), conn=conn):
                new += 1
    finally:
        conn.close()
    return {"requested": len(icaos), "fetched": saved, "new": new, "errors": errors}


def capture_country(
    country_substr: str = "BRAS",
    *,
    chunk: int = 60,
    path: str | os.PathLike | None = None,
) -> dict:
    """Captura o METAR de TODAS as estações de um país, em lote (poucas requisições).

    Descobre as estações pela própria REDEMET (lista atual) e busca o METAR em
    blocos vírgula-separados. Ideal para o cron cobrir o país inteiro.
    """
    from . import redemet
    from . import taf as taf_mod

    stations = redemet.list_stations(country_substr)
    conn = connect(path)
    metar_n = metar_new = taf_n = taf_new = 0
    try:
        for i in range(0, len(stations), chunk):
            block = stations[i:i + chunk]
            for raw in redemet.fetch_metar_batch(block).values():
                metar_n += 1
                if record(metar_mod.decode(raw), conn=conn):
                    metar_new += 1
            for raw in redemet.fetch_taf_batch(block).values():
                taf_n += 1
                if record_taf(taf_mod.decode(raw), conn=conn):
                    taf_new += 1
    finally:
        conn.close()
    return {"stations": len(stations), "with_metar": metar_n, "metar_new": metar_new,
            "with_taf": taf_n, "taf_new": taf_new}


# --- Consultas (climatologia) -------------------------------------------- #
_GREEN = {"VFR"}              # voo visual tranquilo
_FLYABLE = {"VFR", "MVFR"}    # visual (inclui marginal)


def climatology(
    station: str,
    *,
    tz_offset_h: int = -3,  # Brasil ~ UTC-3; agrupa por hora local
    min_samples: int = 1,
    path: str | os.PathLike | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict:
    """Distribuição de categorias por hora local do dia, para um aeródromo."""
    own = conn is None
    conn = conn or connect(path)
    try:
        rows = conn.execute(
            """SELECT hour_utc, category, COUNT(*) AS n,
                      AVG(ceiling_ft) AS ceil, AVG(visibility_m) AS vis
               FROM metar_obs WHERE station = ? GROUP BY hour_utc, category""",
            (station.upper(),),
        ).fetchall()
    finally:
        if own:
            conn.close()

    hours: dict[int, dict] = {
        h: {"hour": h, "total": 0, "vfr": 0, "flyable": 0,
            "by_cat": {}, "_ceil": 0.0, "_vis": 0.0}
        for h in range(24)
    }
    total = 0
    for r in rows:
        lh = (r["hour_utc"] + tz_offset_h) % 24
        b = hours[lh]
        n = r["n"]
        b["total"] += n
        b["by_cat"][r["category"]] = b["by_cat"].get(r["category"], 0) + n
        if r["category"] in _GREEN:
            b["vfr"] += n
        if r["category"] in _FLYABLE:
            b["flyable"] += n
        if r["ceil"] is not None:
            b["_ceil"] += (r["ceil"] or 0) * n
        if r["vis"] is not None:
            b["_vis"] += (r["vis"] or 0) * n
        total += n

    out_hours = []
    for h in range(24):
        b = hours[h]
        t = b["total"]
        out_hours.append({
            "hour": h,
            "total": t,
            "pct_vfr": round(100 * b["vfr"] / t) if t else None,
            "pct_flyable": round(100 * b["flyable"] / t) if t else None,
            "avg_ceiling_ft": round(b["_ceil"] / t) if t and b["_ceil"] else None,
            "avg_visibility_m": round(b["_vis"] / t) if t and b["_vis"] else None,
            "by_cat": b["by_cat"],
        })

    ranked = [h for h in out_hours if h["total"] >= min_samples and h["pct_vfr"] is not None]
    ranked.sort(key=lambda h: (h["pct_vfr"], h["total"]), reverse=True)
    return {
        "station": station.upper(),
        "samples": total,
        "tz_offset_h": tz_offset_h,
        "hours": out_hours,
        "best_hours": ranked[:3],
        "worst_hours": list(reversed(ranked))[:3],
    }


def latest_metar(station: str, *, path: str | os.PathLike | None = None) -> tuple[str | None, int | None]:
    """METAR mais recente gravado de uma estação: (raw, obs_epoch) ou (None, None)."""
    conn = connect(path)
    try:
        row = conn.execute(
            "SELECT raw, obs_epoch FROM metar_obs WHERE station = ? ORDER BY obs_epoch DESC LIMIT 1",
            (station.upper(),),
        ).fetchone()
    finally:
        conn.close()
    return (row["raw"], row["obs_epoch"]) if row else (None, None)


def stations_with_metar(*, path: str | os.PathLike | None = None) -> list[str]:
    """Estações com METAR no histórico (para o sitemap das páginas /tempo/{icao})."""
    conn = connect(path)
    try:
        rows = conn.execute("SELECT DISTINCT station FROM metar_obs ORDER BY station").fetchall()
    finally:
        conn.close()
    return [r["station"] for r in rows]


def recent(station: str, limit: int = 10, *, path: str | os.PathLike | None = None) -> list[dict]:
    conn = connect(path)
    try:
        rows = conn.execute(
            """SELECT obs_epoch, category, ceiling_ft, visibility_m, raw
               FROM metar_obs WHERE station = ? ORDER BY obs_epoch DESC LIMIT ?""",
            (station.upper(), limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "observed_utc": datetime.fromtimestamp(r["obs_epoch"], timezone.utc).isoformat(),
            "category": r["category"],
            "ceiling_ft": r["ceiling_ft"],
            "visibility_m": r["visibility_m"],
            "raw": r["raw"],
        }
        for r in rows
    ]


def _main(argv: list[str]) -> int:
    """CLI: python -m app.history capture SBGR SBSP  |  climatology SBGR"""
    if not argv:
        print("uso: capture <ICAO...> | climatology <ICAO> | recent <ICAO>")
        return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "capture-br":
        print(capture_country("BRAS"))
    elif cmd == "capture-country" and args:
        print(capture_country(args[0].upper()))
    elif cmd == "capture":
        print(capture([a.upper() for a in args]))
    elif cmd == "climatology" and args:
        import json
        print(json.dumps(climatology(args[0]), ensure_ascii=False, indent=2))
    elif cmd == "recent" and args:
        for r in recent(args[0]):
            print(r["observed_utc"], r["category"], r["raw"])
    else:
        print("comando inválido")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))

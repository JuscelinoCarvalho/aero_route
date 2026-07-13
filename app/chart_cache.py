"""Cache de resiliência das cartas (arquivo local + índice SQLite).

Toda carta que servimos pelo proxy (``cartas.fetch_pdf``) passa por aqui: guardamos
uma cópia do PDF e indexamos quando a capturamos. O acesso é **sempre fonte-primeiro**
— a cópia local só é servida quando a fonte oficial cai (rede/quebra), e nesse caso
o proxy avisa há quanto tempo aquela cópia foi capturada (defasagem), para o piloto
julgar a validade.

Diferente do histórico de METAR, os bytes do PDF **não** ficam no SQLite (são
grandes: 6–17 MB no Japão): o índice guarda metadados e o PDF vai para um arquivo
em ``CHART_CACHE_DIR`` nomeado pelo sha256 da URL de origem.

Retenção: por padrão **guardamos tudo para sempre** (o servidor tem disco de
sobra) e cada novo acesso **sobrescreve** a cópia anterior — assim a última versão
vista sempre fica salva. Se um dia quiser limitar, defina ``CHART_CACHE_MAX_BYTES``
(> 0) e o cache passa a descartar as cópias menos recentemente capturadas (LRU por
``last_fetched``) ao ultrapassar o teto. Os caminhos são configuráveis:
``CHART_CACHE_DIR`` (arquivos) e ``CHART_CACHE_DB`` (índice).
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DEFAULT_DB = Path(__file__).parent / "data" / "chart_cache.db"
DEFAULT_DIR = Path(__file__).parent / "data" / "chart_cache"
DEFAULT_MAX_BYTES = 0  # 0 = ilimitado: guarda tudo, nunca descarta (padrão)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chart_cache (
    url_hash          TEXT    PRIMARY KEY,
    url               TEXT    NOT NULL,
    content_type      TEXT    NOT NULL,
    byte_size         INTEGER NOT NULL,
    first_cached_epoch INTEGER NOT NULL,  -- primeira vez que capturamos esta URL
    last_fetched_epoch INTEGER NOT NULL,  -- última captura bem-sucedida (= idade da cópia)
    fetch_count       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_lru ON chart_cache (last_fetched_epoch);
"""

# Serializa as gravações no índice dentro do processo: SQLite só admite um escritor
# e, sob acessos concorrentes à mesma carta popular, connections disputando a trava
# davam "database is locked". Leituras (get) não passam por aqui (WAL permite vários
# leitores). Entre processos (workers), o busy_timeout do connect resolve a espera.
_write_lock = threading.Lock()


def _db_path() -> str:
    return str(os.environ.get("CHART_CACHE_DB") or DEFAULT_DB)


def _dir() -> Path:
    return Path(os.environ.get("CHART_CACHE_DIR") or DEFAULT_DIR)


def _max_bytes() -> int:
    try:
        return int(os.environ.get("CHART_CACHE_MAX_BYTES") or DEFAULT_MAX_BYTES)
    except ValueError:
        return DEFAULT_MAX_BYTES


def _hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    p = _db_path()
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def _blob_path(url_hash: str) -> Path:
    return _dir() / f"{url_hash}.bin"


def store(url: str, data: bytes, content_type: str, *, now: int | None = None) -> None:
    """Guarda/atualiza a cópia local de uma carta capturada com sucesso da fonte."""
    now = now or int(time.time())
    h = _hash(url)
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    # Grava o arquivo primeiro (via .tmp + replace: nunca deixa arquivo parcial).
    # Nome do tmp único por chamada (uuid): dois acessos concorrentes à MESMA
    # carta não podem escrever/renomear o mesmo .tmp e um perder a corrida.
    tmp = d / f"{h}.{uuid.uuid4().hex}.tmp"
    tmp.write_bytes(data)
    tmp.replace(_blob_path(h))

    with _write_lock:
        _write_index(h, url, content_type, len(data), now)


def _write_index(h: str, url: str, content_type: str, size: int, now: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO chart_cache
                 (url_hash, url, content_type, byte_size,
                  first_cached_epoch, last_fetched_epoch, fetch_count)
               VALUES (?,?,?,?,?,?,1)
               ON CONFLICT(url_hash) DO UPDATE SET
                 content_type=excluded.content_type,
                 byte_size=excluded.byte_size,
                 last_fetched_epoch=excluded.last_fetched_epoch,
                 fetch_count=chart_cache.fetch_count+1""",
            (h, url, content_type, size, now, now),
        )
        conn.commit()
        _evict(conn)
    finally:
        conn.close()


def get(url: str) -> tuple[bytes, str, int] | None:
    """Cópia local de uma carta: ``(bytes, content_type, last_fetched_epoch)`` ou None.

    ``last_fetched_epoch`` permite ao chamador calcular a defasagem (idade da cópia).
    """
    h = _hash(url)
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT content_type, last_fetched_epoch FROM chart_cache WHERE url_hash=?",
            (h,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    path = _blob_path(h)
    try:
        data = path.read_bytes()
    except OSError:
        return None  # índice sem o arquivo (limpeza externa): trata como ausente
    return data, row["content_type"], row["last_fetched_epoch"]


def _evict(conn: sqlite3.Connection) -> None:
    """Descarta cópias LRU até o total ficar abaixo de ~90% do teto.

    Só age se houver teto configurado (``CHART_CACHE_MAX_BYTES`` > 0). Padrão é
    ilimitado: nunca descarta.
    """
    cap = _max_bytes()
    if cap <= 0:
        return
    total = conn.execute("SELECT COALESCE(SUM(byte_size),0) AS s FROM chart_cache").fetchone()["s"]
    if total <= cap:
        return
    target = int(cap * 0.9)
    rows = conn.execute(
        "SELECT url_hash, byte_size FROM chart_cache ORDER BY last_fetched_epoch ASC"
    ).fetchall()
    for r in rows:
        if total <= target:
            break
        try:
            _blob_path(r["url_hash"]).unlink(missing_ok=True)
        except OSError:
            pass
        conn.execute("DELETE FROM chart_cache WHERE url_hash=?", (r["url_hash"],))
        total -= r["byte_size"]
    conn.commit()


def stats() -> dict:
    """Métricas do cache (para diagnóstico/administração)."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(byte_size),0) AS bytes FROM chart_cache"
        ).fetchone()
    finally:
        conn.close()
    return {"entries": row["n"], "bytes": row["bytes"], "max_bytes": _max_bytes()}

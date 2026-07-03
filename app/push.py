"""Web Push (VAPID): armazena inscrições e envia notificações.

Inscrições (PushSubscription do navegador) ficam num SQLite, junto do aeródromo
que o usuário quer monitorar e do limite (alerta quando a previsão fica abaixo
desta categoria). O envio usa pywebpush + chaves VAPID das variáveis de ambiente:

    VAPID_PUBLIC_KEY   exposta ao front (/api/push/key)
    VAPID_PRIVATE_KEY  só no servidor
    VAPID_SUB          contato (mailto:) exigido pelo protocolo
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from pywebpush import WebPushException, webpush

from .history import _db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS push_subs (
    endpoint        TEXT PRIMARY KEY,
    p256dh          TEXT NOT NULL,
    auth            TEXT NOT NULL,
    station         TEXT NOT NULL,
    min_category    TEXT NOT NULL DEFAULT 'IFR',
    last_alert_key  TEXT,
    created_epoch   INTEGER NOT NULL
);
"""


def configured() -> bool:
    return bool(os.environ.get("VAPID_PUBLIC_KEY") and os.environ.get("VAPID_PRIVATE_KEY"))


def public_key() -> str:
    return os.environ.get("VAPID_PUBLIC_KEY", "")


def connect(path: str | os.PathLike | None = None) -> sqlite3.Connection:
    p = _db_path(path)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def save_sub(subscription: dict, station: str, min_category: str = "IFR",
             *, path: str | os.PathLike | None = None) -> None:
    keys = subscription.get("keys", {})
    conn = connect(path)
    try:
        conn.execute(
            """INSERT INTO push_subs (endpoint, p256dh, auth, station, min_category, created_epoch)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(endpoint) DO UPDATE SET
                 station=excluded.station, min_category=excluded.min_category,
                 p256dh=excluded.p256dh, auth=excluded.auth""",
            (subscription["endpoint"], keys.get("p256dh", ""), keys.get("auth", ""),
             station.upper(), min_category.upper(), int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


def delete_sub(endpoint: str, *, path: str | os.PathLike | None = None) -> None:
    conn = connect(path)
    try:
        conn.execute("DELETE FROM push_subs WHERE endpoint = ?", (endpoint,))
        conn.commit()
    finally:
        conn.close()


def list_subs(*, path: str | os.PathLike | None = None) -> list[sqlite3.Row]:
    conn = connect(path)
    try:
        return conn.execute("SELECT * FROM push_subs").fetchall()
    finally:
        conn.close()


def mark_alerted(endpoint: str, key: str, *, path: str | os.PathLike | None = None) -> None:
    conn = connect(path)
    try:
        conn.execute("UPDATE push_subs SET last_alert_key = ? WHERE endpoint = ?", (key, endpoint))
        conn.commit()
    finally:
        conn.close()


def send(row: sqlite3.Row, payload: dict) -> bool:
    """Envia uma notificação. Remove a inscrição se o endpoint estiver morto (404/410)."""
    try:
        webpush(
            subscription_info={"endpoint": row["endpoint"],
                               "keys": {"p256dh": row["p256dh"], "auth": row["auth"]}},
            data=json.dumps(payload),
            vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": os.environ.get("VAPID_SUB", "mailto:contato@jussa.com.br")},
            timeout=10,
        )
        return True
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            delete_sub(row["endpoint"])  # inscrição expirada — limpa
        return False
    except Exception:  # noqa: BLE001 — uma inscrição inválida não pode quebrar o job
        return False

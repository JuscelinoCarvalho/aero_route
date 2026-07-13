"""Avalia a previsão (TAF) de cada inscrição e envia alerta push quando o tempo
fica abaixo do limite VFR. Pensado para rodar por timer (a cada ~2h).

Deduplicação: cada inscrição guarda a "chave" do último alerta (estação + emissão
do TAF + categoria + hora). Enquanto o TAF não muda, não reenvia; quando sai um
TAF novo ainda ruim, alerta de novo.
"""

from __future__ import annotations

import os

from . import push
from . import redemet
from . import taf as taf_mod

_ORDER = ["VFR", "MVFR", "IFR", "LIFR"]


def _worst_below(timeline: dict, threshold: str) -> dict | None:
    """Hora com a pior categoria que atinge/ultrapassa o limite (ex.: IFR)."""
    try:
        ti = _ORDER.index(threshold)
    except ValueError:
        ti = _ORDER.index("IFR")
    worst = None
    for h in timeline.get("hours", []):
        try:
            ci = _ORDER.index(h["category"])
        except ValueError:
            continue
        if ci >= ti and (worst is None or ci > _ORDER.index(worst["category"])):
            worst = h
    return worst


def check_all(*, path: str | os.PathLike | None = None, now=None) -> dict:
    if not (push.configured() and redemet.configured()):
        return {"error": "push/redemet não configurados", "sent": 0}
    subs = push.list_subs(path=path)
    cache: dict[str, dict] = {}
    sent = skipped = 0
    for s in subs:
        st = s["station"]
        if st not in cache:
            try:
                parsed = taf_mod.parse(redemet.fetch_taf(st))
                # horizonte completo (~30h) para alcançar "amanhã de manhã".
                parsed["timeline"] = taf_mod.timeline(parsed, max_hours=30, now=now)
                cache[st] = parsed
            except Exception:  # noqa: BLE001
                continue
        d = cache[st]
        worst = _worst_below(d.get("timeline", {}), s["min_category"])
        if not worst:
            continue
        key = f"{st}:{d.get('issued_day')}{d.get('issued_utc')}:{worst['category']}:{worst['label']}"
        if s["last_alert_key"] == key:
            skipped += 1
            continue
        ci = worst["category_info"]
        payload = {
            "title": f"{ci['emoji']} {st}: previsão {worst['category']}",
            "body": f"Previsão de {worst['category']} por volta de {worst['label']} — "
                    f"teto/visibilidade abaixo de VFR. Toque para o briefing.",
            "url": "/tempo",
            "tag": f"wx-{st}",
        }
        if push.send(s, payload):
            push.mark_alerted(s["endpoint"], key, path=path)
            sent += 1
    return {"subs": len(subs), "sent": sent, "skipped": skipped}


def test_all(*, path: str | os.PathLike | None = None) -> dict:
    """Envia uma notificação de teste a todas as inscrições (verificação manual)."""
    subs = push.list_subs(path=path)
    sent = 0
    for s in subs:
        if push.send(s, {"title": "🔔 Aero Jussa",
                         "body": f"Alertas ativados para {s['station']}. "
                                 f"Você será avisado quando a previsão ficar abaixo de VFR.",
                         "url": "/tempo"}):
            sent += 1
    return {"subs": len(subs), "sent": sent}


def _main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "check":
        print(check_all())
    elif cmd == "test":
        print(test_all())
    else:
        print("uso: python -m app.alerts check | test")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))

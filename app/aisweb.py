"""Cliente da API oficial credenciada do AISWEB (DECEA).

Núcleo compartilhado pelos módulos que consultam as áreas que só existem via API
(``notam``, ``rotaer``, ``sol``, …). As **cartas** têm o seu próprio caminho
(scraping-primeiro, com esta API só como fallback) em ``cartas.py`` — aqui ficam
as áreas em que a API é a única fonte.

Credenciais nas envs ``AISWEB_API_KEY``/``AISWEB_API_PASS`` (o mesmo par usado por
``cartas.py``; carregadas pelo systemd de ``/etc/aeroroute.env``). O cliente nunca
as expõe ao navegador — devolve sempre dados já parseados.

Endpoint: ``https://aisweb.decea.mil.br/api/?apiKey=&apiPass=&area=…``. A resposta
é XML com raiz ``<aisweb>``; erro de serviço vem como
``<service total="error"><msg>…</msg></service>``.
"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_BASE = "https://aisweb.decea.mil.br/api/"
_UA = "Mozilla/5.0 (JussaAero/1.0; +https://aero.jussa.com.br)"


def configured() -> bool:
    """As credenciais da API do AISWEB estão presentes?"""
    return bool(os.environ.get("AISWEB_API_KEY") and os.environ.get("AISWEB_API_PASS"))


def _tag(el: ET.Element) -> str:
    """Nome da tag em minúsculas, sem namespace."""
    return el.tag.split("}")[-1].lower()


def to_dict(el: ET.Element) -> dict[str, str]:
    """``{tag_minúscula: texto}`` dos filhos diretos com texto, + atributos do nó.

    Tolerante a variações de caixa/namespace. O primeiro valor de cada tag vence
    (``setdefault``), então atributos não sobrescrevem um filho de mesmo nome.
    """
    d: dict[str, str] = {}
    for child in el:
        if child.text and child.text.strip():
            d.setdefault(_tag(child), child.text.strip())
    for k, v in el.attrib.items():
        d.setdefault(k.lower(), v)
    return d


def iter_tag(root: ET.Element, name: str):
    """Itera os nós cuja tag (sem namespace, minúscula) é ``name``."""
    name = name.lower()
    for el in root.iter():
        if _tag(el) == name:
            yield el


def fetch(area: str, **params: str) -> ET.Element:
    """Consulta uma área da API e devolve a raiz ``<aisweb>`` já parseada.

    Injeta as credenciais e o ``area``; parâmetros extra vazios são descartados.
    Levanta ``RuntimeError`` com mensagem amigável em qualquer falha (credenciais
    ausentes, rede, XML inválido ou erro de serviço reportado pela própria API).
    """
    if not configured():
        raise RuntimeError("Credenciais da API do AISWEB não configuradas.")

    query = {
        "apiKey": os.environ["AISWEB_API_KEY"],
        "apiPass": os.environ["AISWEB_API_PASS"],
        "area": area,
    }
    query.update({k: v for k, v in params.items() if v})
    url = API_BASE + "?" + urllib.parse.urlencode(query)

    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except Exception as exc:  # noqa: BLE001 — rede: mensagem amigável
        raise RuntimeError(f"Falha ao consultar a API do AISWEB ({area}): {exc}") from exc

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RuntimeError(f"Resposta inválida da API do AISWEB ({area}).") from exc

    # Erro de serviço: <service total="error"><msg>…</msg></service>
    for svc in iter_tag(root, "service"):
        if (svc.get("total") or "").lower() == "error":
            msg = " ".join(
                (m.text or "").strip() for m in iter_tag(svc, "msg")
            ).strip()
            raise RuntimeError(msg or f"Serviço AISWEB '{area}' indisponível.")
    return root

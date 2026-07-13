"""Cartas do resto do mundo — deep-link para o eAIP/AIP oficial de cada país.

Só **Brasil** (DECEA/AISWEB) e **EUA** (FAA d-TPP) permitem embutir o PDF: a FAA
publica em domínio público com um metafile por ciclo, e a página do DECEA expõe o
PDF com a apikey pública de download. **Nenhum outro Estado junta as duas coisas**
(licença de reserviço + descoberta computável do AIRAC vigente):

- Cada país publica seu próprio eAIP, com copyright estatal e redistribuição
  restrita — "livre para ver", não para reservir.
- Os agregadores (Eurocontrol EAD / autorouter / PAMS) cobrem várias regiões, mas
  os termos **proíbem** espelhar/servir os documentos num site público sem licença.
- A descoberta do ciclo AIRAC vigente é específica por país (portais em SPA/JS,
  padrões de URL não computáveis), então embutir o PDF quebraria a cada 28 dias.

Por isso, para o resto do mundo, **não embutimos** o PDF: fazemos *deep-link* para
o portal oficial do país, que resolve o ciclo vigente sozinho e é sempre a fonte
correta. O restante da arquitetura (roteamento por país em ``main``) deixa o slot
de "embed" pronto para plugar um país específico caso, no futuro, exista uma
resolução estável e um eAIP com licença de reserviço.

As URLs abaixo são portais oficiais verificados (respondem 200/redirect válido).
Alguns exigem **registro gratuito** para ver as cartas (ex.: Japão, Coreia do Sul,
Austrália) — ainda assim o deep-link leva à fonte oficial correta. Países com eAIP
fechado/pago (China, Canadá) ficam de fora de propósito: exibimos "sem fonte".
"""

from __future__ import annotations

# ISO country (OurAirports iso_country) -> (provedor oficial, URL do portal eAIP).
# Só entram países cujo portal foi verificado como acessível publicamente.
EAIP_PORTALS: dict[str, tuple[str, str]] = {
    # --- Europa ---
    "FR": ("SIA", "https://www.sia.aviation-civile.gouv.fr/"),
    "DE": ("DFS", "https://aip.dfs.de/"),
    "ES": ("ENAIRE", "https://aip.enaire.es/"),
    "GB": ("NATS", "https://nats-uk.ead-it.com/cms-nats/opencms/en/Publications/AIP/"),
    "IE": ("IAA / AirNav Ireland", "https://www.airnav.ie/publications"),
    "NL": ("LVNL", "https://eaip.lvnl.nl/"),
    "BE": ("skeyes", "https://ops.skeyes.be/html/belgocontrol_static/eaip/"),
    "AT": ("Austro Control", "https://eaip.austrocontrol.at/"),
    "CH": ("skyguide", "https://www.skybriefing.com/"),
    "IT": ("ENAV", "https://www.enav.it/"),
    "PT": ("NAV Portugal", "https://www.nav.pt/"),
    "NO": ("Avinor", "https://avinor.no/"),
    "SE": ("LFV", "https://aro.lfv.se/"),
    "DK": ("Naviair", "https://aim.naviair.dk/"),
    "FI": ("Fintraffic ANS", "https://www.ais.fi/"),
    "CZ": ("ANS CR", "https://aim.rlp.cz/"),
    "PL": ("PANSA", "https://www.ais.pansa.pl/"),
    "RO": ("ROMATSA", "https://www.aisro.ro/"),
    "RS": ("SMATSA", "https://www.smatsa.rs/"),
    "HU": ("HungaroControl", "https://www.hungarocontrol.hu/"),
    # --- Ásia / Oriente Médio ---
    "IN": ("AAI / AIM India", "https://aim-india.aai.aero/"),
    "JP": ("AIS Japan (JCAB) · exige registro", "https://aisjapan.mlit.go.jp/"),
    "KR": ("AIM Korea (KOCA) · exige registro", "https://aim.koca.go.kr/"),
    "TH": ("CAAT / AEROTHAI", "https://ais.caat.or.th/"),
    "SG": ("CAAS", "https://aim-sg.caas.gov.sg/"),
    "MY": ("CAAM", "https://aip.caam.gov.my/"),
    "ID": ("AirNav Indonesia", "https://www.airnavindonesia.co.id/"),
    "PH": ("CAAP", "https://www.caap.gov.ph/"),
    "HK": ("CAD Hong Kong", "https://www.ais.gov.hk/"),
    "TW": ("CAA Taiwan", "https://ais.caa.gov.tw/"),
    "AE": ("GCAA", "https://www.gcaa.gov.ae/"),
    "QA": ("QCAA", "https://www.caa.gov.qa/"),
    "IL": ("IAA", "https://www.iaa.gov.il/en/aviation/aip/"),
    # --- Oceania ---
    "AU": ("Airservices Australia · exige registro",
           "https://www.airservicesaustralia.com/aip/aip.asp"),
    "NZ": ("AIP New Zealand", "https://www.aip.net.nz/"),
    # --- África ---
    "ZA": ("ATNS", "https://www.atns.co.za/"),
    "KE": ("KCAA", "https://www.kcaa.or.ke/"),
    "EG": ("ECAA", "https://www.civilaviation.gov.eg/"),
    "MA": ("ONDA", "https://www.onda.ma/"),
    "DZ": ("ENNA", "https://www.enna.dz/"),
    "NG": ("NAMA", "https://nama.gov.ng/"),
    # --- Américas (além de BR/US) ---
    "MX": ("SENEAM", "https://www.gob.mx/seneam"),
    "AR": ("EANA", "https://www.eana.com.ar/"),
    "CL": ("DGAC Chile", "https://aipchile.dgac.gob.cl/"),
    "CO": ("Aerocivil",
           "https://www.aerocivil.gov.co/servicios-a-la-navegacion/"
           "servicio-de-informacion-aeronautica-ais"),
}

# ASECNA: um único portal cobre a informação aeronáutica de ~17 Estados
# africanos (África Ocidental/Central + Madagascar/Comores). Um deep-link, todos
# os membros. https://aim.asecna.aero/
_ASECNA = ("ASECNA", "https://aim.asecna.aero/")
_ASECNA_MEMBERS = (
    "BJ",  # Benim
    "BF",  # Burkina Faso
    "CF",  # Rep. Centro-Africana
    "KM",  # Comores
    "CG",  # Congo (Brazzaville)
    "CI",  # Costa do Marfim
    "GA",  # Gabão
    "GQ",  # Guiné Equatorial
    "GW",  # Guiné-Bissau
    "ML",  # Mali
    "MR",  # Mauritânia
    "NE",  # Níger
    "SN",  # Senegal
    "TD",  # Chade
    "TG",  # Togo
    "CM",  # Camarões
    "MG",  # Madagascar
)
for _iso in _ASECNA_MEMBERS:
    EAIP_PORTALS.setdefault(_iso, _ASECNA)


def covered_countries() -> list[str]:
    """Países (ISO) com deep-link de eAIP disponível."""
    return sorted(EAIP_PORTALS)


def link_for(country: str) -> dict | None:
    """Deep-link para o eAIP oficial do país, ou None se não coberto.

    Retorna ``{"provider": ..., "url": ...}``. O front monta o texto do botão
    (localizado); o provedor é nome próprio, igual em todos os idiomas.
    """
    entry = EAIP_PORTALS.get(country.upper())
    if not entry:
        return None
    provider, url = entry
    return {"provider": provider, "url": url}

"""Perfis de aeronaves para estimativas de tempo, combustível e alcance.

Valores médios de cruzeiro, alcance, anos de produção e preço aproximado de
referência. São aproximações didáticas — um piloto/corretor deve validar. Por
isso ficam centralizados aqui: dá para refinar sem mexer no resto do código.

  cruise_kt     velocidade de cruzeiro típica (nós / TAS)
  burn_kg_h     consumo médio em cruzeiro (kg por hora)
  range_nm      alcance máximo aproximado (milhas náuticas)
  years         faixa de produção (texto)
  price_usd_m   preço aproximado de referência, em MILHÕES de dólares
                (novo p/ em produção; valor de mercado típico p/ fora de linha).
                É só uma referência — preços reais variam muito.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Aircraft:
    key: str
    name: str
    category: str
    cruise_kt: float | None  # None = dado não disponível
    burn_kg_h: float | None
    range_nm: float | None
    years: str
    price_usd_m: float | None
    family: str = ""  # agrupa variantes do mesmo modelo (ex.: "Cessna 210"); "" = sem variantes


# Lista do treinador ao jumbo. Fácil de expandir/refinar (peça ajuda ao piloto).
AIRCRAFT: list[Aircraft] = [
    # --- Monomotor pistão (treinadores e GA) ---
    Aircraft("c152", "Cessna 152", "Monomotor pistão", 107, 16, 415, "1977–1985", 0.05),
    # Família Cessna 172 — por geração de motor
    Aircraft("c172a", "Cessna 172 (O-300, 145 hp)", "Monomotor pistão", 113, 22, 500, "1956–1967", 0.05, family="Cessna 172"),
    Aircraft("c172d", "Cessna 172 Skyhawk (O-320, 150 hp)", "Monomotor pistão", 115, 23, 500, "1968–1976", 0.06, family="Cessna 172"),
    Aircraft("c172n", "Cessna 172N/P Skyhawk (160 hp)", "Monomotor pistão", 120, 24, 520, "1977–1986", 0.09, family="Cessna 172"),
    Aircraft("c172", "Cessna 172R/S Skyhawk (IO-360)", "Monomotor pistão", 124, 26, 640, "1996–em produção", 0.40, family="Cessna 172"),
    Aircraft("c172xp", "Cessna R172K Hawk XP (195 hp)", "Monomotor pistão", 131, 30, 600, "1977–1981", 0.12, family="Cessna 172"),
    Aircraft("c172rg", "Cessna 172RG Cutlass RG (retrátil)", "Monomotor pistão", 140, 28, 720, "1980–1985", 0.10, family="Cessna 172"),
    # Família Cessna 182 Skylane — por geração de motor
    Aircraft("c182", "Cessna 182 Skylane (O-470, 230 hp)", "Monomotor pistão", 140, 42, 900, "1956–1986", 0.16, family="Cessna 182"),
    Aircraft("c182t", "Cessna 182T Skylane (moderno)", "Monomotor pistão", 145, 43, 930, "2001–em produção", 0.55, family="Cessna 182"),
    Aircraft("ct182", "Cessna T182 Turbo Skylane", "Monomotor pistão", 158, 46, 1000, "1981–em produção", 0.55, family="Cessna 182"),
    Aircraft("c182rg", "Cessna R182 Skylane RG (retrátil)", "Monomotor pistão", 156, 45, 1000, "1978–1986", 0.18, family="Cessna 182"),
    # Família Piper PA-28 — por geração/motor
    Aircraft("pa28_140", "Piper PA-28-140 Cherokee (150 hp)", "Monomotor pistão", 108, 22, 465, "1964–1977", 0.06, family="Piper PA-28"),
    Aircraft("pa28_warrior", "Piper PA-28 Warrior (160 hp)", "Monomotor pistão", 118, 24, 520, "1974–em produção", 0.20, family="Piper PA-28"),
    Aircraft("pa28", "Piper PA-28 Cherokee 180 / Archer (180 hp)", "Monomotor pistão", 128, 27, 550, "1963–em produção", 0.35, family="Piper PA-28"),
    Aircraft("pa28_235", "Piper PA-28-235 / Dakota (235 hp)", "Monomotor pistão", 140, 34, 700, "1963–1994", 0.20, family="Piper PA-28"),
    Aircraft("pa28r", "Piper PA-28R Arrow (retrátil, 180–200 hp)", "Monomotor pistão", 137, 30, 700, "1967–em produção", 0.22, family="Piper PA-28"),
    Aircraft("pa28rt", "Piper Turbo Arrow (TSIO-360)", "Monomotor pistão", 150, 32, 800, "1977–1990", 0.25, family="Piper PA-28"),
    Aircraft("da40", "Diamond DA40 (Lycoming 180 hp)", "Monomotor pistão", 150, 22, 800, "1997–em produção", 0.45, family="Diamond DA40"),
    Aircraft("da40ng", "Diamond DA40 NG (diesel)", "Monomotor pistão", 154, 18, 940, "2010–em produção", 0.55, family="Diamond DA40"),
    # Família Mooney M20 — por geração/motor
    Aircraft("m20_early", "Mooney M20 / M20E (curto, 150–200 hp)", "Monomotor pistão", 155, 38, 800, "1955–1967", 0.10, family="Mooney M20"),
    Aircraft("m20", "Mooney M20J 201 (200 hp)", "Monomotor pistão", 163, 40, 900, "1977–1998", 0.16, family="Mooney M20"),
    Aircraft("m20k", "Mooney M20K 231/252 (turbo)", "Monomotor pistão", 195, 46, 1000, "1979–1998", 0.20, family="Mooney M20"),
    Aircraft("m20m", "Mooney M20M Bravo (turbo, 270 hp)", "Monomotor pistão", 200, 55, 1000, "1989–2004", 0.28, family="Mooney M20"),
    Aircraft("m20r", "Mooney M20R Ovation (280 hp)", "Monomotor pistão", 190, 52, 1000, "1994–2019", 0.45, family="Mooney M20"),
    Aircraft("m20v", "Mooney M20V Acclaim (turbo, 280 hp)", "Monomotor pistão", 220, 55, 1100, "2006–2019", 0.77, family="Mooney M20"),
    Aircraft("sr20", "Cirrus SR20 (200 hp)", "Monomotor pistão", 155, 32, 709, "1999–em produção", 0.65, family="Cirrus SR2x"),
    Aircraft("sr22", "Cirrus SR22 (310 hp)", "Monomotor pistão", 183, 52, 1049, "2001–em produção", 1.0, family="Cirrus SR2x"),
    Aircraft("sr22t", "Cirrus SR22T (turbo)", "Monomotor pistão", 213, 55, 1021, "2010–em produção", 1.1, family="Cirrus SR2x"),
    # Família Cessna 177 Cardinal
    Aircraft("c177", "Cessna 177/177B Cardinal", "Monomotor pistão", 122, 28, 600, "1968–1978", 0.13, family="Cessna 177"),
    Aircraft("c177rg", "Cessna 177RG Cardinal RG (retrátil)", "Monomotor pistão", 148, 32, 700, "1971–1978", 0.16, family="Cessna 177"),
    # Cessna 205
    Aircraft("c205", "Cessna 205", "Monomotor pistão", 150, 42, 750, "1963–1964", 0.10, family="Cessna 205"),
    # Família Cessna 206/207 Stationair — aspirado e turbo, por geração
    Aircraft("c206", "Cessna 206 Stationair (IO-520/540, 300 hp)", "Monomotor pistão", 145, 48, 700, "1964–1986", 0.30, family="Cessna 206"),
    Aircraft("t206", "Cessna T206 Turbo Stationair", "Monomotor pistão", 160, 50, 700, "1966–1986", 0.35, family="Cessna 206"),
    Aircraft("c206h", "Cessna 206H Stationair (moderno)", "Monomotor pistão", 142, 48, 730, "1998–em produção", 0.70, family="Cessna 206"),
    Aircraft("t206h", "Cessna T206H Turbo Stationair", "Monomotor pistão", 164, 50, 700, "1999–em produção", 0.75, family="Cessna 206"),
    Aircraft("c207", "Cessna 207 Stationair 8", "Monomotor pistão", 140, 50, 600, "1969–1984", 0.20, family="Cessna 207"),
    Aircraft("t207", "Cessna T207 Turbo Stationair 8", "Monomotor pistão", 155, 52, 600, "1969–1984", 0.22, family="Cessna 207"),
    # Família Cessna 210 — variantes por geração de motor (cobre todos os submodelos)
    Aircraft("c210e", "Cessna 210 / 210A–C", "Monomotor pistão", 160, 40, 800, "1957–1963", 0.09, family="Cessna 210"),
    Aircraft("c210", "Cessna 210D–R Centurion", "Monomotor pistão", 167, 43, 950, "1964–1986", 0.15, family="Cessna 210"),
    Aircraft("t210", "Cessna T210 Turbo Centurion", "Monomotor pistão", 193, 46, 900, "1966–1986", 0.24, family="Cessna 210"),
    Aircraft("p210", "Cessna P210 Pressurizado", "Monomotor pistão", 183, 47, 1000, "1978–1986", 0.30, family="Cessna 210"),
    # Família Piper PA-32 — Cherokee Six / Saratoga / Lance
    Aircraft("pa32_6", "Piper PA-32 Cherokee Six (260–300 hp)", "Monomotor pistão", 145, 46, 700, "1965–1979", 0.20, family="Piper PA-32"),
    Aircraft("pa32", "Piper PA-32 Saratoga (300 hp)", "Monomotor pistão", 150, 48, 800, "1980–2009", 0.35, family="Piper PA-32"),
    Aircraft("pa32r", "Piper PA-32R Saratoga SP / Lance (retrátil)", "Monomotor pistão", 165, 52, 900, "1975–2009", 0.35, family="Piper PA-32"),
    Aircraft("pa32rt", "Piper Turbo Saratoga / Turbo Lance", "Monomotor pistão", 185, 58, 900, "1977–2009", 0.40, family="Piper PA-32"),
    # Família Piper PA-46 (pistão) — Malibu / Mirage / Matrix
    Aircraft("pa46_malibu", "Piper PA-46 Malibu (310 hp, Continental)", "Monomotor pistão", 213, 48, 1400, "1983–1988", 0.6, family="Piper PA-46"),
    Aircraft("pa46", "Piper PA-46 Mirage / M350 (350 hp, Lycoming)", "Monomotor pistão", 213, 55, 1343, "1988–em produção", 1.2, family="Piper PA-46"),
    Aircraft("pa46m", "Piper PA-46 Matrix (não pressurizado)", "Monomotor pistão", 213, 55, 1300, "2008–2015", 0.9, family="Piper PA-46"),
    # Família Beechcraft Bonanza (ver também be35 V-tail nos clássicos)
    Aircraft("be33", "Beechcraft 33 Debonair / Bonanza", "Monomotor pistão", 168, 45, 800, "1960–1995", 0.16, family="Beechcraft Bonanza"),
    Aircraft("be36", "Beechcraft A36/G36 Bonanza (300 hp)", "Monomotor pistão", 176, 50, 920, "1968–em produção", 1.0, family="Beechcraft Bonanza"),
    Aircraft("be36tc", "Beechcraft B36TC Bonanza (turbo)", "Monomotor pistão", 200, 55, 1000, "1979–2002", 0.4, family="Beechcraft Bonanza"),
    # Monomotores brasileiros (Neiva/Embraer, licenciados e nacionais)
    Aircraft("emb711", "Neiva/Embraer EMB-711 Corisco (PA-28R, 200 hp)", "Monomotor pistão", 137, 30, 700, "1976–1990", 0.12, family="Neiva EMB-711 Corisco"),
    Aircraft("emb711t", "Neiva/Embraer EMB-711T Corisco Turbo", "Monomotor pistão", 150, 32, 800, "1980–1990", 0.15, family="Neiva EMB-711 Corisco"),
    Aircraft("emb720", "Neiva EMB-720 Minuano / EMB-721 Sertanejo (300 hp)", "Monomotor pistão", 145, 46, 700, "1974–1986", 0.15),
    Aircraft("aeroboero", "Aero Boero AB-180 (roda de bequilha)", "Monomotor pistão", 100, 22, 500, "1959–em produção", 0.06),
    # Bush / utilitários e clássicos utilitários
    Aircraft("c170", "Cessna 170 (145 hp, roda de bequilha)", "Monomotor pistão", 105, 22, 500, "1948–1956", 0.09),
    Aircraft("c180", "Cessna 180 Skywagon (230 hp)", "Monomotor pistão", 140, 42, 800, "1953–1981", 0.15, family="Cessna 180/185 Skywagon"),
    Aircraft("c185", "Cessna 185 Skywagon (260–300 hp)", "Monomotor pistão", 145, 48, 720, "1961–1985", 0.18, family="Cessna 180/185 Skywagon"),
    Aircraft("maule7", "Maule M-7 (180–235 hp, STOL)", "Monomotor pistão", 130, 34, 550, "1984–em produção", 0.28),
    # Monomotores-escola e touring adicionais
    Aircraft("pa38", "Piper PA-38 Tomahawk (112 hp)", "Monomotor pistão", 100, 18, 460, "1978–1982", 0.05),
    Aircraft("da20", "Diamond DA20 Katana/Eclipse (125 hp)", "Monomotor pistão", 138, 18, 500, "1994–em produção", 0.25),
    Aircraft("tb10", "Socata TB-9 Tampico / TB-10 Tobago (160–180 hp)", "Monomotor pistão", 130, 28, 680, "1979–2002", 0.15, family="Socata TB"),
    Aircraft("tb20", "Socata TB-20/21 Trinidad (250 hp, TB-21 turbo)", "Monomotor pistão", 165, 42, 1000, "1980–2002", 0.20, family="Socata TB"),
    Aircraft("aa5a", "Grumman AA-5A Cheetah (150 hp)", "Monomotor pistão", 120, 24, 600, "1976–1979", 0.08, family="Grumman AA-5"),
    Aircraft("aa5b", "Grumman/AGAC AA-5B Tiger (180 hp)", "Monomotor pistão", 139, 28, 690, "1975–2006", 0.12, family="Grumman AA-5"),
    # --- Bimotor pistão ---
    # Família Piper PA-34 Seneca
    Aircraft("seneca1", "Piper PA-34 Seneca I (aspirado, 200 hp)", "Bimotor pistão", 168, 76, 800, "1971–1974", 0.15, family="Piper PA-34 Seneca"),
    Aircraft("seneca", "Piper PA-34 Seneca II–V (turbo)", "Bimotor pistão", 190, 80, 870, "1974–2019", 0.6, family="Piper PA-34 Seneca"),
    # Família Beechcraft Baron
    Aircraft("be55", "Beechcraft Baron 55 (260–285 hp)", "Bimotor pistão", 195, 90, 900, "1961–1983", 0.20, family="Beechcraft Baron"),
    Aircraft("be58", "Beechcraft Baron 58 (300 hp)", "Bimotor pistão", 200, 95, 1480, "1969–em produção", 1.5, family="Beechcraft Baron"),
    Aircraft("be58p", "Beechcraft Baron 58P/TC (turbo/pressurizado)", "Bimotor pistão", 220, 105, 1400, "1976–1985", 0.5, family="Beechcraft Baron"),
    Aircraft("da62", "Diamond DA62", "Bimotor pistão", 192, 42, 1283, "2015–em produção", 1.4),
    # Família Cessna 310
    Aircraft("c310", "Cessna 310 (aspirado)", "Bimotor pistão", 190, 95, 1100, "1954–1980", 0.20, family="Cessna 310"),
    Aircraft("t310", "Cessna T310 Turbo", "Bimotor pistão", 220, 100, 1200, "1969–1980", 0.25, family="Cessna 310"),
    Aircraft("c421", "Cessna 421 Golden Eagle", "Bimotor pistão", 210, 115, 1480, "1968–1985", 0.35),
    # Família Piper PA-31 Navajo
    Aircraft("pa31", "Piper PA-31 Navajo (310 hp turbo)", "Bimotor pistão", 205, 110, 1000, "1967–1984", 0.30, family="Piper PA-31 Navajo"),
    Aircraft("pa31_350", "Piper PA-31-350 Chieftain (350 hp)", "Bimotor pistão", 210, 120, 1000, "1973–1984", 0.35, family="Piper PA-31 Navajo"),
    Aircraft("pa31p", "Piper PA-31P Pressurized Navajo (425 hp)", "Bimotor pistão", 230, 130, 1200, "1970–1977", 0.35, family="Piper PA-31 Navajo"),
    # Família Piper PA-23 Apache/Aztec
    Aircraft("pa23_apache", "Piper PA-23 Apache (150–160 hp)", "Bimotor pistão", 140, 58, 900, "1954–1962", 0.10, family="Piper PA-23"),
    Aircraft("pa23", "Piper PA-23 Aztec (250 hp)", "Bimotor pistão", 170, 75, 1100, "1959–1981", 0.18, family="Piper PA-23"),
    Aircraft("pa23t", "Piper Turbo Aztec", "Bimotor pistão", 190, 80, 1100, "1966–1981", 0.22, family="Piper PA-23"),
    # Neiva/Embraer EMB-810 — Seneca fabricado no Brasil (bimotor mais comum no país)
    Aircraft("emb810", "Neiva/Embraer EMB-810 Seneca (Brasil)", "Bimotor pistão", 190, 80, 870, "1975–2019", 0.4, family="Piper PA-34 Seneca"),
    # Cessna cabin-class twins (miolo da linha 300/400, entre o 310 e o 421)
    Aircraft("c340", "Cessna 340 (pressurizado, turbo)", "Bimotor pistão", 220, 105, 1400, "1971–1984", 0.25),
    Aircraft("c402", "Cessna 402 (commuter, 300 hp)", "Bimotor pistão", 200, 110, 1200, "1966–1985", 0.20),
    Aircraft("c404", "Cessna 404 Titan (375 hp)", "Bimotor pistão", 200, 130, 1200, "1976–1982", 0.30),
    Aircraft("c414", "Cessna 414 Chancellor (pressurizado)", "Bimotor pistão", 215, 110, 1330, "1968–1985", 0.28),
    # Bimotores-escola
    Aircraft("pa44", "Piper PA-44 Seminole (2×180 hp)", "Bimotor pistão", 162, 60, 700, "1979–em produção", 0.9),
    Aircraft("be76", "Beechcraft Model 76 Duchess (2×180 hp)", "Bimotor pistão", 154, 58, 780, "1978–1983", 0.15),
    Aircraft("da42", "Diamond DA42 Twin Star (diesel)", "Bimotor pistão", 170, 30, 1200, "2004–em produção", 0.9),
    # --- Turboélice ---
    # Família Cessna 208 Caravan
    Aircraft("c208", "Cessna 208 Caravan (675 shp)", "Turboélice", 186, 160, 1070, "1984–em produção", 2.3, family="Cessna 208 Caravan"),
    Aircraft("c208b", "Cessna 208B Grand Caravan EX (867 shp)", "Turboélice", 197, 175, 964, "2013–em produção", 2.8, family="Cessna 208 Caravan"),
    # Família Piper M-class (turboélice)
    Aircraft("m500", "Piper M500 (Meridian)", "Turboélice", 260, 120, 1000, "2015–em produção", 2.3, family="Piper M-class"),
    Aircraft("m600", "Piper M600 SLS", "Turboélice", 274, 135, 1658, "2016–em produção", 3.4, family="Piper M-class"),
    # Família Daher/Socata TBM
    Aircraft("tbm700", "Daher/Socata TBM 700", "Turboélice", 300, 150, 1500, "1990–2005", 1.5, family="Daher TBM"),
    Aircraft("tbm850", "Daher TBM 850", "Turboélice", 320, 160, 1520, "2006–2013", 2.5, family="Daher TBM"),
    Aircraft("tbm940", "Daher TBM 900–960", "Turboélice", 330, 165, 1730, "2014–em produção", 4.1, family="Daher TBM"),
    Aircraft("pc12", "Pilatus PC-12", "Turboélice", 280, 180, 1803, "1994–em produção", 5.0),
    # Família Beechcraft King Air
    Aircraft("kingairc90", "Beechcraft King Air C90GTx", "Turboélice", 272, 230, 1260, "1971–em produção", 4.0, family="Beechcraft King Air"),
    Aircraft("kingair200", "Beechcraft King Air 200/B200", "Turboélice", 290, 300, 1580, "1974–em produção", 3.0, family="Beechcraft King Air"),
    Aircraft("kingair250", "Beechcraft King Air 250", "Turboélice", 305, 280, 1720, "2011–2020", 6.5, family="Beechcraft King Air"),
    Aircraft("kingair350", "Beechcraft King Air 350/360", "Turboélice", 312, 310, 1806, "1990–em produção", 8.5, family="Beechcraft King Air"),
    Aircraft("emb110", "Embraer EMB-110 Bandeirante", "Turboélice", 220, 350, 1060, "1968–1990", 0.6),
    Aircraft("emb120", "Embraer EMB-120 Brasília", "Turboélice", 300, 450, 1020, "1985–2001", 1.8),
    Aircraft("be1900", "Beechcraft 1900D", "Turboélice", 280, 430, 1480, "1982–2002", 2.0),
    Aircraft("atr72", "ATR 72-600", "Turboélice", 275, 650, 825, "1988–em produção", 26.0, family="ATR"),
    Aircraft("dash8q400", "De Havilland Dash 8 Q400", "Turboélice", 360, 1100, 1100, "1999–2021", 32.0, family="De Havilland Dash 8"),
    # Turboélices brasileiros (Embraer)
    Aircraft("emb121", "Embraer EMB-121 Xingu (2×PT6A)", "Turboélice", 248, 250, 1300, "1977–1987", 0.8),
    Aircraft("emb312", "Embraer EMB-312 Tucano (T-27)", "Turboélice", 222, 150, 1000, "1983–1996", None),
    Aircraft("a29", "Embraer A-29 Super Tucano (EMB-314)", "Turboélice", 320, 200, 720, "2003–em produção", 14.0),
    # Turboélices utilitários e commuter adicionais
    Aircraft("p180", "Piaggio P.180 Avanti (pusher)", "Turboélice", 320, 340, 1470, "1990–em produção", 7.5),
    Aircraft("pa31t", "Piper PA-31T Cheyenne I/II", "Turboélice", 280, 260, 1200, "1974–1984", 0.7, family="Piper Cheyenne"),
    Aircraft("pa42", "Piper PA-42 Cheyenne III/400", "Turboélice", 300, 300, 1500, "1980–1993", 1.0, family="Piper Cheyenne"),
    Aircraft("kodiak", "Daher Kodiak 100", "Turboélice", 174, 160, 1130, "2007–em produção", 2.5),
    Aircraft("l410", "LET L-410 Turbolet", "Turboélice", 205, 300, 800, "1971–em produção", 4.5),
    Aircraft("saab340", "Saab 340B", "Turboélice", 250, 500, 870, "1983–1999", 3.0),
    Aircraft("pc6", "Pilatus PC-6 Turbo Porter (STOL)", "Turboélice", 120, 150, 500, "1961–2019", 1.5),
    # --- Jato executivo ---
    Aircraft("sf50", "Cirrus Vision Jet SF50", "Jato executivo", 300, 230, 1275, "2016–em produção", 3.0),
    Aircraft("mustang", "Cessna Citation Mustang", "Jato executivo", 340, 320, 1150, "2006–2017", 2.5, family="Cessna Citation"),
    Aircraft("citm2", "Cessna Citation M2", "Jato executivo", 400, 300, 1550, "2013–em produção", 4.5, family="Cessna Citation"),
    Aircraft("phenom100", "Embraer Phenom 100", "Jato executivo", 380, 360, 1178, "2008–em produção", 4.5, family="Embraer Phenom"),
    Aircraft("hondajet", "Honda HA-420 HondaJet", "Jato executivo", 422, 340, 1223, "2015–em produção", 6.5),
    Aircraft("cj3", "Cessna Citation CJ3+", "Jato executivo", 416, 460, 2040, "2014–em produção", 9.0, family="Cessna Citation"),
    Aircraft("cj4", "Cessna Citation CJ4", "Jato executivo", 451, 510, 2165, "2010–em produção", 10.0, family="Cessna Citation"),
    Aircraft("phenom300", "Embraer Phenom 300", "Jato executivo", 453, 520, 2010, "2009–em produção", 10.5, family="Embraer Phenom"),
    Aircraft("learjet75", "Learjet 75 Liberty", "Jato executivo", 465, 700, 2080, "2013–2021", 13.5, family="Learjet"),
    Aircraft("citationxls", "Cessna Citation XLS+", "Jato executivo", 441, 590, 2100, "2008–em produção", 14.0, family="Cessna Citation"),
    Aircraft("praetor500", "Embraer Praetor 500", "Jato executivo", 466, 600, 3340, "2019–em produção", 17.0, family="Embraer Praetor"),
    Aircraft("latitude", "Cessna Citation Latitude", "Jato executivo", 446, 700, 2700, "2015–em produção", 18.0, family="Cessna Citation"),
    Aircraft("praetor600", "Embraer Praetor 600", "Jato executivo", 466, 660, 4018, "2019–em produção", 21.0, family="Embraer Praetor"),
    Aircraft("g280", "Gulfstream G280", "Jato executivo", 470, 850, 3600, "2012–em produção", 25.0, family="Gulfstream"),
    Aircraft("challenger350", "Bombardier Challenger 350", "Jato executivo", 470, 900, 3200, "2014–2022", 27.0, family="Bombardier Challenger/Global"),
    Aircraft("longitude", "Cessna Citation Longitude", "Jato executivo", 476, 800, 3500, "2019–em produção", 28.0, family="Cessna Citation"),
    Aircraft("falcon2000", "Dassault Falcon 2000LXS", "Jato executivo", 482, 900, 4000, "1995–em produção", 35.0, family="Dassault Falcon"),
    Aircraft("falcon7x", "Dassault Falcon 7X", "Jato executivo", 488, 1100, 5950, "2007–2022", 54.0, family="Dassault Falcon"),
    Aircraft("falcon8x", "Dassault Falcon 8X", "Jato executivo", 488, 1150, 6450, "2016–em produção", 60.0, family="Dassault Falcon"),
    Aircraft("g550", "Gulfstream G550", "Jato executivo", 488, 1300, 6750, "2003–2021", 62.0, family="Gulfstream"),
    Aircraft("g650", "Gulfstream G650ER", "Jato executivo", 516, 1500, 7000, "2012–em produção", 70.0, family="Gulfstream"),
    Aircraft("global7500", "Bombardier Global 7500", "Jato executivo", 516, 1700, 7700, "2018–em produção", 78.0, family="Bombardier Challenger/Global"),
    # Citation — variantes de alta performance que faltavam na família
    Aircraft("citx", "Cessna Citation X+ (M0.935)", "Jato executivo", 525, 900, 3460, "1996–2018", 15.0, family="Cessna Citation"),
    Aircraft("citsov", "Cessna Citation Sovereign+", "Jato executivo", 458, 640, 3200, "2004–em produção", 18.0, family="Cessna Citation"),
    # Família Learjet
    Aircraft("lear31", "Learjet 31A", "Jato executivo", 447, 550, 1400, "1988–2003", 3.0, family="Learjet"),
    Aircraft("lear45", "Learjet 45/45XR", "Jato executivo", 464, 560, 1710, "1998–2012", 6.0, family="Learjet"),
    Aircraft("lear60", "Learjet 60XR", "Jato executivo", 466, 700, 2400, "1993–2013", 7.0, family="Learjet"),
    # Família Hawker (Beechjet/Hawker)
    Aircraft("hawker400", "Hawker 400XP / Beechjet 400", "Jato executivo", 448, 500, 1500, "1985–2011", 3.0, family="Hawker"),
    Aircraft("hawker800", "Hawker 800/850XP", "Jato executivo", 448, 700, 2540, "1984–2013", 5.0, family="Hawker"),
    Aircraft("hawker900", "Hawker 900XP", "Jato executivo", 448, 680, 2930, "2007–2013", 8.0, family="Hawker"),
    Aircraft("pc24", "Pilatus PC-24", "Jato executivo", 440, 550, 2000, "2018–em produção", 11.0),
    # --- Jato regional ---
    Aircraft("crj900", "Bombardier CRJ900", "Jato regional", 470, 1300, 1550, "2001–2020", 48.0, family="Bombardier CRJ"),
    Aircraft("e175", "Embraer E175", "Jato regional", 447, 1150, 2200, "2004–em produção", 50.0, family="Embraer E-Jet"),
    Aircraft("e190", "Embraer E190", "Jato regional", 470, 1500, 2400, "2004–em produção", 52.0, family="Embraer E-Jet"),
    Aircraft("e195e2", "Embraer E195-E2", "Jato regional", 470, 1550, 2600, "2019–em produção", 60.4, family="Embraer E-Jet"),
    Aircraft("a220", "Airbus A220-300", "Jato regional", 470, 1750, 3400, "2016–em produção", 91.0),
    # --- Narrow-body (corredor único) ---
    Aircraft("a319", "Airbus A319", "Jato comercial", 450, 2200, 3700, "1995–2021", 93.0, family="Airbus A320"),
    Aircraft("a320neo", "Airbus A320neo", "Jato comercial", 455, 2400, 3500, "2016–em produção", 110.0, family="Airbus A320"),
    Aircraft("a321neo", "Airbus A321neo", "Jato comercial", 455, 2600, 4000, "2017–em produção", 129.0, family="Airbus A320"),
    Aircraft("a320ceo", "Airbus A320-200 (ceo)", "Jato comercial", 447, 2400, 3300, "1988–2021", 98.0, family="Airbus A320"),
    Aircraft("b737700", "Boeing 737-700", "Jato comercial", 450, 2400, 3010, "1997–2012", 89.0, family="Boeing 737"),
    Aircraft("b738", "Boeing 737-800", "Jato comercial", 453, 2600, 2935, "1997–2020", 106.0, family="Boeing 737"),
    Aircraft("b737max8", "Boeing 737 MAX 8", "Jato comercial", 453, 2300, 3550, "2017–em produção", 121.0, family="Boeing 737"),
    Aircraft("b739", "Boeing 737-900ER", "Jato comercial", 453, 2650, 2950, "2007–2019", 103.0, family="Boeing 737"),
    Aircraft("b757", "Boeing 757-200", "Jato comercial", 460, 3400, 3915, "1982–2004", 80.0),
    # --- Wide-body (fuselagem larga) ---
    Aircraft("b767", "Boeing 767-300ER", "Jato wide-body", 460, 4800, 5990, "1982–em produção", 217.0),
    Aircraft("a330", "Airbus A330-300", "Jato wide-body", 470, 5500, 6350, "1992–em produção", 264.0, family="Airbus A330"),
    Aircraft("a330neo", "Airbus A330-900neo", "Jato wide-body", 470, 5400, 7200, "2018–em produção", 296.0, family="Airbus A330"),
    Aircraft("b787", "Boeing 787-9 Dreamliner", "Jato wide-body", 488, 5400, 7635, "2011–em produção", 292.0, family="Boeing 787"),
    Aircraft("b787_8", "Boeing 787-8 Dreamliner", "Jato wide-body", 488, 5100, 7350, "2011–em produção", 248.0, family="Boeing 787"),
    Aircraft("b787_10", "Boeing 787-10 Dreamliner", "Jato wide-body", 488, 5600, 6430, "2018–em produção", 338.0, family="Boeing 787"),
    Aircraft("a350", "Airbus A350-900", "Jato wide-body", 488, 5800, 8100, "2014–em produção", 317.0, family="Airbus A350"),
    Aircraft("a3501000", "Airbus A350-1000", "Jato wide-body", 488, 6200, 8700, "2018–em produção", 366.0, family="Airbus A350"),
    Aircraft("b77l", "Boeing 777-200LR", "Jato wide-body", 490, 6800, 8555, "2006–em produção", 346.0, family="Boeing 777"),
    Aircraft("b77w", "Boeing 777-300ER", "Jato wide-body", 490, 7000, 7370, "2004–em produção", 375.0, family="Boeing 777"),
    Aircraft("b779", "Boeing 777-9", "Jato wide-body", 490, 7200, 7285, "2025–em produção", 442.0, family="Boeing 777"),
    Aircraft("b748", "Boeing 747-8", "Jato wide-body", 493, 10500, 7730, "2011–2023", 419.0, family="Boeing 747"),
    Aircraft("b744", "Boeing 747-400", "Jato wide-body", 490, 10200, 7260, "1989–2009", 260.0, family="Boeing 747"),
    Aircraft("a380", "Airbus A380-800", "Jato wide-body", 490, 11000, 8000, "2007–2021", 445.0),
    # --- Clássicos / fora de linha (alguns com dados não disponíveis) ---
    Aircraft("c150", "Cessna 150", "Monomotor pistão", 100, 16, 350, "1958–1977", 0.03),
    Aircraft("c195", "Cessna 195 Businessliner", "Clássico", 140, 60, 700, "1947–1954", None),
    # Família Cessna 337 Skymaster (push-pull)
    Aircraft("c337", "Cessna 337 Skymaster (aspirado)", "Bimotor pistão", 170, 85, 1000, "1963–1982", 0.12, family="Cessna 337 Skymaster"),
    Aircraft("t337", "Cessna T337 Turbo Skymaster", "Bimotor pistão", 190, 90, 1000, "1966–1982", 0.15, family="Cessna 337 Skymaster"),
    Aircraft("p337", "Cessna P337 Pressurized Skymaster", "Bimotor pistão", 200, 95, 1000, "1973–1980", 0.18, family="Cessna 337 Skymaster"),
    Aircraft("be35", "Beechcraft V35 Bonanza (V-tail, 285 hp)", "Monomotor pistão", 172, 48, 900, "1947–1982", 0.15, family="Beechcraft Bonanza"),
    Aircraft("staggerwing", "Beechcraft Model 17 Staggerwing", "Clássico", 175, None, 700, "1933–1949", None),
    Aircraft("be18", "Beechcraft Model 18", "Clássico", 150, 200, 1000, "1937–1970", None),
    Aircraft("pa18", "Piper PA-18 Super Cub", "Monomotor pistão", 100, 22, 460, "1949–1994", 0.12),
    Aircraft("j3", "Piper J-3 Cub", "Clássico", 65, 15, 220, "1938–1947", 0.06),
    Aircraft("paulistinha", "Neiva Paulistinha 56 (CAP-4)", "Clássico", 78, 15, 300, "1944–1959", None),
    Aircraft("pa24", "Piper PA-24 Comanche", "Monomotor pistão", 160, 50, 900, "1958–1972", 0.10),
    # Família Piper Twin Comanche
    Aircraft("pa30", "Piper PA-30/PA-39 Twin Comanche (160 hp)", "Bimotor pistão", 178, 55, 1000, "1963–1972", 0.10, family="Piper Twin Comanche"),
    Aircraft("pa30t", "Piper Turbo Twin Comanche", "Bimotor pistão", 190, 58, 1000, "1966–1972", 0.12, family="Piper Twin Comanche"),
    # Família Aerostar
    Aircraft("aerostar", "Ted Smith Aerostar 600 (aspirado)", "Bimotor pistão", 205, 105, 1000, "1968–1984", 0.22, family="Aerostar"),
    Aircraft("aerostar_p", "Aerostar 601P/602P (turbo pressurizado)", "Bimotor pistão", 240, 118, 1000, "1972–1984", 0.28, family="Aerostar"),
    Aircraft("navion", "Ryan Navion", "Clássico", 140, None, 600, "1946–1951", None),
    Aircraft("ercoupe", "ERCO Ercoupe 415", "Clássico", 95, 18, 480, "1940–1967", 0.04),
    Aircraft("t6", "North American T-6 Texan", "Clássico", 145, 180, 730, "1935–1945", None),
    Aircraft("dc3", "Douglas DC-3", "Clássico", 180, 600, 1500, "1936–1942", None),
    Aircraft("ipanema", "Embraer EMB-202 Ipanema", "Agrícola", 98, 70, None, "1970–em produção", 0.30),

    # ======================================================================= #
    # Ampliação do catálogo: clássicos de companhia (muitos voaram no Brasil),
    # regionais e marcas que faltavam. Valores didáticos (a validar por piloto).
    # ======================================================================= #
    # --- Boeing 737 clássicos/originais (estendem a família) ---
    Aircraft("b732", "Boeing 737-200", "Jato comercial", 430, 2900, 2300, "1967–1988", None, family="Boeing 737"),
    Aircraft("b733", "Boeing 737-300", "Jato comercial", 430, 2500, 2600, "1984–1999", None, family="Boeing 737"),
    Aircraft("b734", "Boeing 737-400", "Jato comercial", 430, 2700, 2350, "1988–2000", None, family="Boeing 737"),
    Aircraft("b735", "Boeing 737-500", "Jato comercial", 430, 2400, 2400, "1989–1999", None, family="Boeing 737"),
    # --- Trijatos e primeiros jatões (Jato comercial) ---
    Aircraft("b727", "Boeing 727-200", "Jato comercial", 467, 4500, 2400, "1967–1984", None, family="Boeing 727"),
    Aircraft("b707", "Boeing 707-320B", "Jato comercial", 480, 6000, 5000, "1958–1979", None),
    Aircraft("dc9", "McDonnell Douglas DC-9-30", "Jato comercial", 440, 2900, 1500, "1965–1982", None),
    Aircraft("md83", "McDonnell Douglas MD-83", "Jato comercial", 440, 3000, 2500, "1985–1999", None, family="McDonnell Douglas MD-80"),
    Aircraft("md88", "McDonnell Douglas MD-88", "Jato comercial", 440, 3000, 2050, "1987–1997", None, family="McDonnell Douglas MD-80"),
    Aircraft("md90", "McDonnell Douglas MD-90", "Jato comercial", 440, 2900, 2400, "1993–2000", None, family="McDonnell Douglas MD-80"),
    Aircraft("a318", "Airbus A318", "Jato comercial", 447, 2200, 3100, "2003–2013", None, family="Airbus A320"),
    Aircraft("c919", "COMAC C919", "Jato comercial", 450, 2400, 3000, "2023–em produção", 99.0),
    # --- Wide-body clássicos e famílias que faltavam ---
    Aircraft("md11", "McDonnell Douglas MD-11", "Jato wide-body", 490, 7000, 6800, "1990–2000", None),
    Aircraft("dc10", "McDonnell Douglas DC-10-30", "Jato wide-body", 490, 7200, 5200, "1971–1989", None),
    Aircraft("l1011", "Lockheed L-1011 TriStar", "Jato wide-body", 480, 7000, 4250, "1972–1984", None),
    Aircraft("a300", "Airbus A300-600R", "Jato wide-body", 470, 5200, 4050, "1972–2007", None, family="Airbus A300/A310"),
    Aircraft("a310", "Airbus A310-300", "Jato wide-body", 470, 4800, 5200, "1983–1998", None, family="Airbus A300/A310"),
    Aircraft("a343", "Airbus A340-300", "Jato wide-body", 488, 6800, 7300, "1993–2011", None, family="Airbus A340"),
    Aircraft("a346", "Airbus A340-600", "Jato wide-body", 488, 7800, 7500, "2002–2011", None, family="Airbus A340"),
    # --- Jatos regionais: Embraer ERJ (muito comum no Brasil), E-Jets E1, CRJ, Fokker, novos ---
    Aircraft("erj145", "Embraer ERJ-145", "Jato regional", 450, 1100, 1550, "1996–2020", 21.0, family="Embraer ERJ"),
    Aircraft("erj135", "Embraer ERJ-135", "Jato regional", 450, 1050, 1750, "1998–2010", 18.0, family="Embraer ERJ"),
    Aircraft("erj140", "Embraer ERJ-140", "Jato regional", 450, 1080, 1650, "2001–2008", 19.0, family="Embraer ERJ"),
    Aircraft("e170", "Embraer E170", "Jato regional", 447, 1050, 2100, "2004–em produção", 42.0, family="Embraer E-Jet"),
    Aircraft("e195e1", "Embraer E195 (E1)", "Jato regional", 470, 1500, 2300, "2004–2020", 50.0, family="Embraer E-Jet"),
    Aircraft("e190e2", "Embraer E190-E2", "Jato regional", 470, 1400, 2850, "2018–em produção", 58.0, family="Embraer E-Jet"),
    Aircraft("crj200", "Bombardier CRJ200", "Jato regional", 424, 1100, 1700, "1992–2006", None, family="Bombardier CRJ"),
    Aircraft("crj700", "Bombardier CRJ700", "Jato regional", 447, 1200, 1650, "1999–2020", 30.0, family="Bombardier CRJ"),
    Aircraft("fokker100", "Fokker 100", "Jato regional", 410, 1500, 1300, "1988–1997", None, family="Fokker"),
    Aircraft("fokker70", "Fokker 70", "Jato regional", 410, 1400, 1200, "1994–1997", None, family="Fokker"),
    Aircraft("b717", "Boeing 717-200", "Jato regional", 438, 2400, 2060, "1998–2006", None),
    Aircraft("superjet", "Sukhoi Superjet 100", "Jato regional", 450, 1600, 1600, "2011–em produção", 35.0),
    Aircraft("arj21", "COMAC ARJ21-700", "Jato regional", 420, 1700, 1200, "2016–em produção", 38.0),
    # --- Turboélices regionais/utilitários que faltavam ---
    Aircraft("atr42", "ATR 42-600", "Turboélice", 275, 500, 840, "1985–em produção", 20.0, family="ATR"),
    Aircraft("dash8_300", "De Havilland Dash 8-300", "Turboélice", 285, 600, 1000, "1989–2009", None, family="De Havilland Dash 8"),
    Aircraft("f27", "Fokker F27 Friendship", "Turboélice", 250, 550, 1000, "1958–1987", None),
    Aircraft("mu2", "Mitsubishi MU-2", "Turboélice", 290, 250, 1500, "1967–1986", 0.6),
    Aircraft("skycourier", "Cessna 408 SkyCourier", "Turboélice", 200, 320, 900, "2022–em produção", 5.5),
    Aircraft("c212", "CASA C-212 Aviocar", "Turboélice", 200, 300, 900, "1971–2012", None),
    # --- Jatos executivos: flagships e VLJ que faltavam ---
    Aircraft("global6000", "Bombardier Global 6000", "Jato executivo", 488, 1500, 6000, "2012–em produção", 62.0, family="Bombardier Challenger/Global"),
    Aircraft("challenger650", "Bombardier Challenger 650", "Jato executivo", 470, 1000, 4000, "2015–em produção", 32.0, family="Bombardier Challenger/Global"),
    Aircraft("g700", "Gulfstream G700", "Jato executivo", 516, 1600, 7500, "2022–em produção", 78.0, family="Gulfstream"),
    Aircraft("g500", "Gulfstream G500", "Jato executivo", 500, 1100, 5300, "2018–em produção", 48.0, family="Gulfstream"),
    Aircraft("falcon900", "Dassault Falcon 900LX", "Jato executivo", 480, 900, 4750, "1986–em produção", 44.0, family="Dassault Falcon"),
    Aircraft("eclipse500", "Eclipse 500 (VLJ)", "Jato executivo", 370, 250, 1125, "2006–2008", 2.0),
    # --- Clássicos icônicos ---
    Aircraft("concorde", "Aérospatiale/BAC Concorde (SST)", "Clássico", 1150, 25000, 3550, "1969–1979", None),
    Aircraft("constellation", "Lockheed L-1049 Super Constellation", "Clássico", 250, 1200, 4000, "1951–1958", None),
    Aircraft("an2", "Antonov An-2 (biplano)", "Clássico", 100, 130, 450, "1947–2001", None),
    Aircraft("beaver", "De Havilland Canada DHC-2 Beaver (bush)", "Monomotor pistão", 120, 60, 400, "1947–1967", 0.5),
]

_BY_KEY = {a.key: a for a in AIRCRAFT}

DEFAULT_KEY = "a320neo"

# Pistões/clássicos/agrícola usam Avgas (~0,72 kg/L); turbinas usam Jet-A (~0,8 kg/L).
_AVGAS_CATEGORIES = {"Monomotor pistão", "Bimotor pistão", "Clássico", "Agrícola"}


def fuel_density(category: str) -> float:
    """Densidade do combustível por categoria (kg/L)."""
    return 0.72 if category in _AVGAS_CATEGORIES else 0.8


def fuel_type(category: str) -> str:
    return "Avgas" if category in _AVGAS_CATEGORIES else "Jet-A"


def get(key: str) -> Aircraft:
    """Retorna a aeronave pela chave, caindo no padrão se não existir."""
    return _BY_KEY.get(key, _BY_KEY[DEFAULT_KEY])


def as_options() -> list[dict]:
    """Lista serializável para popular os seletores do frontend."""
    return [
        {
            "key": a.key,
            "name": a.name,
            "category": a.category,
            "cruise_kt": a.cruise_kt,
            "burn_kg_h": a.burn_kg_h,
            "range_nm": a.range_nm,
            "years": a.years,
            "price_usd_m": a.price_usd_m,
            "family": a.family,
            "fuel": fuel_type(a.category),
            "density_kg_l": fuel_density(a.category),
        }
        for a in AIRCRAFT
    ]

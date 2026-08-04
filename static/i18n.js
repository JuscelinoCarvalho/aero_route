/* i18n client — dicionário de strings de runtime (pt/en/es).
 * O idioma vem de window.APP_LANG (injetado pelo servidor no <head>).
 * Uso: T("chave")  ·  TF("chave", arg0, arg1)  (interpola {0},{1})
 * Locale numérico em window.I18N_LOCALE (para toLocaleString).
 */
(function () {
  var L = (window.APP_LANG || "pt");
  window.I18N_LOCALE = { pt: "pt-BR", en: "en-US", es: "es-ES" }[L] || "pt-BR";

  var D = {
    // ---- Afiliados (comuns a todas as páginas) ----
    aff_headsets_t: { pt: "Headsets de aviação", en: "Aviation headsets", es: "Auriculares de aviación" },
    aff_headsets_d: { pt: "Bose, David Clark e mais", en: "Bose, David Clark and more", es: "Bose, David Clark y más" },
    aff_courses_t: { pt: "Cursos de pilotagem", en: "Pilot training", es: "Cursos de pilotaje" },
    aff_courses_d: { pt: "Teoria PP/PC e simulados", en: "PPL/CPL theory and mock exams", es: "Teoría PP/PC y simulacros" },
    aff_sims_t: { pt: "Simuladores de voo", en: "Flight simulators", es: "Simuladores de vuelo" },
    aff_sims_d: { pt: "MSFS, X-Plane e periféricos", en: "MSFS, X-Plane and peripherals", es: "MSFS, X-Plane y periféricos" },
    aff_books_t: { pt: "Livros e cartas", en: "Books and charts", es: "Libros y cartas" },
    aff_books_d: { pt: "Material de navegação aérea", en: "Air navigation material", es: "Material de navegación aérea" },
    aff_soon: { pt: "Em breve", en: "Coming soon", es: "Próximamente" },
    aff_back: { pt: "← Voltar", en: "← Back", es: "← Volver" },

    // ---- Genéricos ----
    na: { pt: "não disponível", en: "not available", es: "no disponible" },
    nd: { pt: "n/d", en: "n/a", es: "n/d" },
    price_k: { pt: "mil", en: "k", es: "mil" },
    price_m: { pt: "mi", en: "M", es: "M" },
    ac_speed_nd: { pt: "vel. n/d", en: "spd n/a", es: "vel. n/d" },
    ac_range: { pt: "alcance", en: "range", es: "alcance" },
    ac_range_nd: { pt: "alcance n/d", en: "range n/a", es: "alcance n/d" },

    // ---- Ficha técnica / tabela (home + comparar) ----
    f_category: { pt: "Categoria", en: "Category", es: "Categoría" },
    f_cruise: { pt: "Cruzeiro", en: "Cruise", es: "Crucero" },
    f_burn: { pt: "Consumo", en: "Fuel burn", es: "Consumo" },
    f_range: { pt: "Alcance", en: "Range", es: "Alcance" },
    f_prod: { pt: "Produção", en: "Production", es: "Producción" },
    f_price: { pt: "Preço aprox.*", en: "Approx. price*", es: "Precio aprox.*" },
    ficha_tecnica: { pt: "Ficha técnica", en: "Specifications", es: "Ficha técnica" },
    comparativo: { pt: "Comparativo", en: "Comparison", es: "Comparativa" },

    // ---- Home / calculadora (app.js) ----
    empty_od: { pt: "Selecione origem e destino para calcular a rota.", en: "Select origin and destination to calculate the route.", es: "Selecciona origen y destino para calcular la ruta." },
    same_od: { pt: "Origem e destino são o mesmo aeroporto.", en: "Origin and destination are the same airport.", es: "El origen y el destino son el mismo aeropuerto." },
    route_fail: { pt: "Não foi possível calcular a rota.", en: "Could not calculate the route.", es: "No se pudo calcular la ruta." },
    conn_fail: { pt: "Erro de conexão ao calcular a rota.", en: "Connection error while calculating the route.", es: "Error de conexión al calcular la ruta." },
    r_dist: { pt: "Distância", en: "Distance", es: "Distancia" },
    r_dist_stops: { pt: "Distância c/ escalas", en: "Distance w/ stops", es: "Distancia c/ escalas" },
    r_block: { pt: "Tempo de bloco", en: "Block time", es: "Tiempo de bloque" },
    r_cruise: { pt: "Vel. cruzeiro", en: "Cruise speed", es: "Vel. crucero" },
    r_bearing: { pt: "Proa inicial", en: "Initial heading", es: "Rumbo inicial" },
    r_aircraft: { pt: "Aeronave", en: "Aircraft", es: "Aeronave" },
    pick_ac: { pt: "Selecione uma aeronave para ver tempo, combustível e escalas.", en: "Select an aircraft to see time, fuel and stops.", es: "Selecciona una aeronave para ver tiempo, combustible y escalas." },
    burn_na: { pt: "Consumo não disponível para o {0}.", en: "Fuel burn not available for the {0}.", es: "Consumo no disponible para el {0}." },
    fuel_est: { pt: "Combustível estimado · {0}", en: "Estimated fuel · {0}", es: "Combustible estimado · {0}" },
    unreach_title: { pt: "Rota inalcançável sem paradas.", en: "Route unreachable without stops.", es: "Ruta inalcanzable sin escalas." },
    unreach_body: {
      pt: "A distância ({0} nm) excede a autonomia útil do {1} ({2} nm por etapa) e não há paradas de reabastecimento possíveis no trajeto. Exibindo a rota direta.",
      en: "The distance ({0} nm) exceeds the usable range of the {1} ({2} nm per leg) and there are no possible refueling stops along the way. Showing the direct route.",
      es: "La distancia ({0} nm) supera la autonomía útil del {1} ({2} nm por etapa) y no hay escalas de reabastecimiento posibles en el trayecto. Mostrando la ruta directa.",
    },
    stops_title: { pt: "{0} escala(s) de reabastecimento", en: "{0} refueling stop(s)", es: "{0} escala(s) de reabastecimiento" },
    stops_body: {
      pt: "para o {0} (autonomia útil {1} nm por etapa). Passe o mouse nas paradas ⛽ no mapa.",
      en: "for the {0} (usable range {1} nm per leg). Hover over the ⛽ stops on the map.",
      es: "para el {0} (autonomía útil {1} nm por etapa). Pasa el ratón por las paradas ⛽ en el mapa.",
    },

    // ---- Comparar (comparar.js) ----
    max4: { pt: "Máximo de 4 aeronaves.", en: "Maximum of 4 aircraft.", es: "Máximo de 4 aeronaves." },
    remove: { pt: "Remover", en: "Remove", es: "Quitar" },
    add_ac: { pt: "Adicione aeronaves para comparar.", en: "Add aircraft to compare.", es: "Añade aeronaves para comparar." },

    // ---- Instalar PWA (install.js) ----
    install_btn: { pt: "📲 Baixar app", en: "📲 Install app", es: "📲 Instalar app" },
    install_ios: {
      pt: "Para instalar no iPhone/iPad: toque em Compartilhar (⬆) e depois em “Adicionar à Tela de Início”.",
      en: "To install on iPhone/iPad: tap Share (⬆) and then “Add to Home Screen”.",
      es: "Para instalar en iPhone/iPad: toca Compartir (⬆) y luego “Añadir a pantalla de inicio”.",
    },
    install_other: {
      pt: "Para instalar: abra o menu do navegador (⋮) e toque em “Instalar app” ou “Adicionar à tela inicial”.",
      en: "To install: open the browser menu (⋮) and tap “Install app” or “Add to Home screen”.",
      es: "Para instalar: abre el menú del navegador (⋮) y toca “Instalar app” o “Añadir a pantalla de inicio”.",
    },

    // ---- Cartas (cartas.js) ----
    c_searching: { pt: "Buscando cartas de {0}…", en: "Searching charts for {0}…", es: "Buscando cartas de {0}…" },
    c_query_fail: { pt: "Não foi possível consultar as cartas.", en: "Could not query the charts.", es: "No se pudieron consultar las cartas." },
    c_none: { pt: "Nenhuma carta do tipo selecionado encontrada para {0}. Tente “Todas as cartas”.", en: "No charts of the selected type found for {0}. Try “All charts”.", es: "No se encontraron cartas del tipo seleccionado para {0}. Prueba “Todas las cartas”." },
    c_found: { pt: "{0} carta(s) encontrada(s) para {1}. Toque em uma para visualizar.", en: "{0} chart(s) found for {1}. Tap one to view.", es: "{0} carta(s) encontrada(s) para {1}. Toca una para ver." },
    c_conn_fail: { pt: "Erro de conexão ao buscar as cartas.", en: "Connection error while fetching the charts.", es: "Error de conexión al buscar las cartas." },
    c_render_fail: { pt: "Não foi possível renderizar a carta aqui. Use “Abrir em nova aba”.", en: "Could not render the chart here. Use “Open in new tab”.", es: "No se pudo renderizar la carta aquí. Usa “Abrir en pestaña nueva”." },
    c_stale: { pt: "⚠ Fonte oficial indisponível agora. Exibindo a última cópia salva em {0} ({1}) — pode estar desatualizada. Confirme na fonte oficial antes de usar.", en: "⚠ Official source unavailable right now. Showing the last saved copy from {0} ({1}) — it may be outdated. Verify against the official source before use.", es: "⚠ Fuente oficial no disponible ahora. Mostrando la última copia guardada del {0} ({1}) — puede estar desactualizada. Verifica en la fuente oficial antes de usar." },
    c_stale_age_days: { pt: "há {0} dia(s)", en: "{0} day(s) ago", es: "hace {0} día(s)" },
    c_stale_age_today: { pt: "hoje", en: "today", es: "hoy" },
    c_copied: { pt: "Link da carta copiado para a área de transferência.", en: "Chart link copied to clipboard.", es: "Enlace de la carta copiado al portapapeles." },
    c_eaip_title: { pt: "Cartas oficiais no eAIP", en: "Official charts on the eAIP", es: "Cartas oficiales en el eAIP" },
    c_eaip_body: { pt: "Na Europa as cartas são publicadas por cada país e não podem ser reservidas aqui. Abra o eAIP oficial de <strong>{0}</strong> — o portal mostra a emenda (AIRAC) vigente do aeroporto.", en: "In Europe charts are published by each country and cannot be re-served here. Open the official <strong>{0}</strong> eAIP — the portal shows the airport's current (AIRAC) amendment.", es: "En Europa las cartas las publica cada país y no pueden reservirse aquí. Abre el eAIP oficial de <strong>{0}</strong> — el portal muestra la enmienda (AIRAC) vigente del aeropuerto." },
    c_eaip_btn: { pt: "Abrir eAIP oficial ↗", en: "Open official eAIP ↗", es: "Abrir eAIP oficial ↗" },
    c_eaip_status: { pt: "Cartas de {0} disponíveis no eAIP oficial ({1}).", en: "Charts for {0} available on the official eAIP ({1}).", es: "Cartas de {0} disponibles en el eAIP oficial ({1})." },
    c_nosource: { pt: "Ainda não há fonte de cartas para este país ({0}). Cobrimos Brasil, EUA e o eAIP oficial de vários países da Europa.", en: "No chart source for this country yet ({0}). We cover Brazil, the USA and the official eAIP of several European countries.", es: "Aún no hay fuente de cartas para este país ({0}). Cubrimos Brasil, EE. UU. y el eAIP oficial de varios países de Europa." },

    // ---- Tempo (tempo.js) — rótulos de UI (o texto decodificado vem do servidor em pt) ----
    wx_querying: { pt: "Consultando METAR de <strong>{0}</strong>…", en: "Querying METAR for <strong>{0}</strong>…", es: "Consultando METAR de <strong>{0}</strong>…" },
    wx_conn_fail: { pt: "Falha de conexão ao consultar o METAR. Tente novamente.", en: "Connection error while querying the METAR. Try again.", es: "Error de conexión al consultar el METAR. Inténtalo de nuevo." },
    wx_503: { pt: "⚙️ A consulta de METAR ainda não está ativa: falta configurar a chave da <strong>REDEMET</strong> no servidor.", en: "⚙️ METAR lookup is not active yet: the <strong>REDEMET</strong> key is not configured on the server.", es: "⚙️ La consulta de METAR aún no está activa: falta configurar la clave de <strong>REDEMET</strong> en el servidor." },
    wx_get_fail: { pt: "Não foi possível obter o METAR de <strong>{0}</strong>{1}", en: "Could not get the METAR for <strong>{0}</strong>{1}", es: "No se pudo obtener el METAR de <strong>{0}</strong>{1}" },
    wx_wind: { pt: "Vento", en: "Wind", es: "Viento" },
    wx_calm: { pt: "Calmo", en: "Calm", es: "Calma" },
    wx_vis: { pt: "Visibilidade", en: "Visibility", es: "Visibilidad" },
    wx_ceil: { pt: "Teto", en: "Ceiling", es: "Techo" },
    wx_noceil: { pt: "Sem teto", en: "No ceiling", es: "Sin techo" },
    wx_temp: { pt: "Temp / orvalho", en: "Temp / dew point", es: "Temp / rocío" },
    wx_cat: { pt: "Categoria", en: "Category", es: "Categoría" },
    wx_alert_btn: { pt: "🔔 Receber alertas de {0}", en: "🔔 Get alerts for {0}", es: "🔔 Recibir alertas de {0}" },
    wx_alert_note: { pt: "Aviso por notificação quando a previsão (TAF) ficar abaixo de VFR.", en: "Notification when the forecast (TAF) drops below VFR.", es: "Aviso por notificación cuando el pronóstico (TAF) baje de VFR." },
    wx_perm_denied: { pt: "Permissão de notificações negada. Ative nas configurações do navegador.", en: "Notification permission denied. Enable it in your browser settings.", es: "Permiso de notificaciones denegado. Actívalo en la configuración del navegador." },
    wx_alerts_unavail: { pt: "Alertas indisponíveis no servidor no momento.", en: "Alerts unavailable on the server right now.", es: "Alertas no disponibles en el servidor por ahora." },
    wx_sub_fail: { pt: "Não foi possível salvar a inscrição.", en: "Could not save the subscription.", es: "No se pudo guardar la suscripción." },
    wx_alerts_on: { pt: "✅ Alertas ativados para {0}", en: "✅ Alerts enabled for {0}", es: "✅ Alertas activadas para {0}" },
    wx_alerts_err: { pt: "Não foi possível ativar os alertas: ", en: "Could not enable alerts: ", es: "No se pudieron activar las alertas: " },
    wx_radar: { pt: "Radar:", en: "Radar:", es: "Radar:" },
    wx_taf_title: { pt: "Previsão (TAF)", en: "Forecast (TAF)", es: "Pronóstico (TAF)" },
    wx_taf_meta: { pt: "{0} · emitido {1}Z · válido {2}–{3}{4}", en: "{0} · issued {1}Z · valid {2}–{3}{4}", es: "{0} · emitido {1}Z · válido {2}–{3}{4}" },
    wx_temp_max: { pt: "máx", en: "max", es: "máx" },
    wx_temp_min: { pt: "mín", en: "min", es: "mín" },
    wx_flightwin: { pt: "🛫 <strong>Janela de voo:</strong> {0}", en: "🛫 <strong>Flight window:</strong> {0}", es: "🛫 <strong>Ventana de vuelo:</strong> {0}" },
    wx_risk: { pt: "risco de {0}", en: "risk of {0}", es: "riesgo de {0}" },
    wx_hist: { pt: "Histórico: {0}% VFR ({1} obs)", en: "History: {0}% VFR ({1} obs)", es: "Histórico: {0}% VFR ({1} obs)" },
    wx_hist_nodata: { pt: "histórico ainda sem dados", en: "history has no data yet", es: "histórico aún sin datos" },
    wx_legend_hist: { pt: "Barra colorida = previsão (TAF) · barra inferior verde = % VFR histórico daquela hora ({0} obs acumuladas)", en: "Colored bar = forecast (TAF) · green bottom bar = historical %VFR for that hour ({0} obs collected)", es: "Barra de color = pronóstico (TAF) · barra inferior verde = % VFR histórico de esa hora ({0} obs acumuladas)" },
    wx_legend_nohist: { pt: "Barra colorida = previsão (TAF). O histórico VFR por hora aparece aqui conforme acumula.", en: "Colored bar = forecast (TAF). The hourly VFR history shows up here as it accumulates.", es: "Barra de color = pronóstico (TAF). El histórico VFR por hora aparece aquí a medida que se acumula." },
    wx_best_title: { pt: "Melhores horários para voar", en: "Best times to fly", es: "Mejores horarios para volar" },
    wx_best_sub: { pt: "Histórico: {0} observações · % de METARs em VFR por hora local (UTC{1}{2})", en: "History: {0} observations · % of METARs in VFR per local hour (UTC{1}{2})", es: "Histórico: {0} observaciones · % de METAR en VFR por hora local (UTC{1}{2})" },
    wx_avoid: { pt: "⚠️ Evite ~{0} · {1}% VFR", en: "⚠️ Avoid ~{0} · {1}% VFR", es: "⚠️ Evita ~{0} · {1}% VFR" },
    wx_nodata: { pt: "sem dados", en: "no data", es: "sin datos" },
    wx_leg_vfr: { pt: "VFR provável", en: "VFR likely", es: "VFR probable" },
    wx_leg_marginal: { pt: "marginal", en: "marginal", es: "marginal" },
    wx_leg_ifr: { pt: "frequentemente IFR", en: "often IFR", es: "frecuentemente IFR" },
    wx_leg_nodata: { pt: "sem dados", en: "no data", es: "sin datos" },
    wx_ceil_avg: { pt: "teto médio {0} ft", en: "avg ceiling {0} ft", es: "techo medio {0} ft" },

    // ---- Radar (radar.js) ----
    rdr_loading: { pt: "Carregando dados de radar…", en: "Loading radar data…", es: "Cargando datos de radar…" },
    rdr_load_fail: { pt: "Não foi possível carregar os dados de radar. Tente atualizar.", en: "Could not load radar data. Try refreshing.", es: "No se pudieron cargar los datos de radar. Intenta actualizar." },
    rdr_nodata: { pt: "Sem dados disponíveis no momento para esta camada.", en: "No data available for this layer right now.", es: "Sin datos disponibles para esta capa por ahora." },
    rdr_sat: { pt: "SATÉLITE · NUVENS", en: "SATELLITE · CLOUDS", es: "SATÉLITE · NUBES" },
    rdr_sat_static: { pt: "Satélite (NASA GOES-East, infravermelho): imagem mais recente, sem animação.", en: "Satellite (NASA GOES-East, infrared): latest image, no animation.", es: "Satélite (NASA GOES-East, infrarrojo): imagen más reciente, sin animación." },
    rdr_nowcast: { pt: "PREVISÃO (NOWCAST)", en: "FORECAST (NOWCAST)", es: "PRONÓSTICO (NOWCAST)" },
    rdr_observed: { pt: "OBSERVADO", en: "OBSERVED", es: "OBSERVADO" },
    rdr_pause: { pt: "Pausar", en: "Pause", es: "Pausar" },
    rdr_play: { pt: "Reproduzir", en: "Play", es: "Reproducir" },
    rdr_geo_unsupported: { pt: "Geolocalização não suportada neste navegador.", en: "Geolocation is not supported in this browser.", es: "Geolocalización no soportada en este navegador." },
    rdr_locating: { pt: "Localizando…", en: "Locating…", es: "Localizando…" },
    rdr_here: { pt: "Você está aqui", en: "You are here", es: "Estás aquí" },
    rdr_loc_fail: { pt: "Não foi possível obter sua localização.", en: "Could not get your location.", es: "No se pudo obtener tu ubicación." },

    // ---- Aeródromo (aerodromo.js) ----
    ad_searching: { pt: "Consultando {0}…", en: "Looking up {0}…", es: "Consultando {0}…" },
    ad_loaded: { pt: "{0} · dados carregados.", en: "{0} · data loaded.", es: "{0} · datos cargados." },
    ad_query_fail: { pt: "Não foi possível consultar o aeródromo.", en: "Could not look up the airport.", es: "No se pudo consultar el aeródromo." },
    ad_conn_fail: { pt: "Erro de conexão ao consultar o aeródromo.", en: "Connection error while looking up the airport.", es: "Error de conexión al consultar el aeródromo." },
    ad_no_rotaer: { pt: "Ficha ROTAER indisponível para {0}.", en: "ROTAER record unavailable for {0}.", es: "Ficha ROTAER no disponible para {0}." },
    ad_sec_ficha: { pt: "Ficha do aeródromo (ROTAER)", en: "Aerodrome record (ROTAER)", es: "Ficha del aeródromo (ROTAER)" },
    ad_sec_sol: { pt: "Nascer e pôr do sol", en: "Sunrise and sunset", es: "Amanecer y atardecer" },
    ad_sec_pistas: { pt: "Pistas", en: "Runways", es: "Pistas" },
    ad_sec_nav: { pt: "Auxílios à navegação", en: "Navigation aids", es: "Ayudas a la navegación" },
    ad_sec_notam: { pt: "NOTAM ativos", en: "Active NOTAMs", es: "NOTAM activos" },
    ad_f_elev: { pt: "Elevação", en: "Elevation", es: "Elevación" },
    ad_f_fir: { pt: "FIR", en: "FIR", es: "FIR" },
    ad_f_utc: { pt: "Fuso (UTC)", en: "Time zone (UTC)", es: "Huso (UTC)" },
    ad_f_cat: { pt: "Categoria", en: "Category", es: "Categoría" },
    ad_f_type: { pt: "Tipo", en: "Type", es: "Type" },
    ad_f_use: { pt: "Utilização", en: "Use", es: "Utilización" },
    ad_f_opr: { pt: "Operação", en: "Operation", es: "Operación" },
    ad_sun_rise: { pt: "Nascer do sol", en: "Sunrise", es: "Amanecer" },
    ad_sun_set: { pt: "Pôr do sol", en: "Sunset", es: "Atardecer" },
    ad_sun_daylight: { pt: "Luz do dia: {0}", en: "Daylight: {0}", es: "Luz del día: {0}" },
    ad_rwy_dims: { pt: "{0} × {1} m", en: "{0} × {1} m", es: "{0} × {1} m" },
    ad_thr: { pt: "cab. {0}", en: "thr {0}", es: "cab. {0}" },
    ad_notam_none: { pt: "Nenhum NOTAM ativo para {0}.", en: "No active NOTAMs for {0}.", es: "Ningún NOTAM activo para {0}." },
    ad_notam_period: { pt: "{0} → {1}", en: "{0} → {1}", es: "{0} → {1}" },
    ad_notam_perm: { pt: "permanente", en: "permanent", es: "permanente" },
    ad_none: { pt: "—", en: "—", es: "—" },
    ad_prio_2: { pt: "ALTA", en: "HIGH", es: "ALTA" },
    ad_prio_1: { pt: "MÉDIA", en: "MEDIUM", es: "MEDIA" },
    ad_prio_0: { pt: "INFO", en: "INFO", es: "INFO" },
    ad_notam_crit: { pt: "{0} crítico(s)", en: "{0} critical", es: "{0} crítico(s)" },

    // ---- Vento nas pistas (aerodromo.js) ----
    ad_sec_wind: { pt: "Vento nas pistas", en: "Wind on the runways", es: "Viento en las pistas" },
    ad_wind_calm: { pt: "Calmo", en: "Calm", es: "Calma" },
    ad_wind_vrb: { pt: "Variável · {0} kt", en: "Variable · {0} kt", es: "Variable · {0} kt" },
    ad_wind_now: { pt: "{0}° / {1} kt", en: "{0}° / {1} kt", es: "{0}° / {1} kt" },
    ad_wind_gust: { pt: " raj {0}", en: " gust {0}", es: " ráf {0}" },
    ad_wind_na: { pt: "vento indisponível", en: "wind unavailable", es: "viento no disponible" },
    ad_wind_head: { pt: "Proa {0}", en: "Head {0}", es: "Proa {0}" },
    ad_wind_tail: { pt: "Cauda {0}", en: "Tail {0}", es: "Cola {0}" },
    ad_wind_cross: { pt: "Cruzado {0}", en: "Cross {0}", es: "Cruz. {0}" },
    ad_wind_from_r: { pt: "dir.", en: "right", es: "der." },
    ad_wind_from_l: { pt: "esq.", en: "left", es: "izq." },
    ad_wind_kt: { pt: "{0} kt", en: "{0} kt", es: "{0} kt" },
    ad_wind_gustx: { pt: "raj {0}", en: "gust {0}", es: "ráf {0}" },
    ad_wind_fav: { pt: "favorável", en: "favored", es: "favorable" },
    ad_wind_vrb_note: { pt: "Vento variável — componentes não calculáveis.", en: "Variable wind — components not computable.", es: "Viento variable — componentes no calculables." },
    ad_wind_limit: { pt: "Meu vento cruzado máx.", en: "My max crosswind", es: "Mi viento cruzado máx." },
    ad_wind_note: {
      pt: "Vento do METAR (verdadeiro) vs. rumo da pista; a torre informa em magnético. Rumo por geometria das cabeceiras ou ident + declinação. Apoio — confira sempre.",
      en: "METAR wind (true) vs. runway heading; the tower reports magnetic. Heading from threshold geometry or ident + declination. For support — always verify.",
      es: "Viento del METAR (verdadero) vs. rumbo de pista; la torre informa en magnético. Rumbo por geometría de cabeceras o ident + declinación. De apoyo — verifica siempre.",
    },

    // ---- Altitude-densidade (aerodromo.js) ----
    ad_sec_dens: { pt: "Altitude-densidade", en: "Density altitude", es: "Altitud-densidad" },
    ad_dens_ft: { pt: "{0} ft", en: "{0} ft", es: "{0} ft" },
    ad_dens_pa: { pt: "Alt. pressão {0} ft", en: "Pressure alt {0} ft", es: "Alt. presión {0} ft" },
    ad_dens_isa: { pt: "ISA {0}°C", en: "ISA {0}°C", es: "ISA {0}°C" },
    ad_dens_elev: { pt: "elev {0} ft", en: "elev {0} ft", es: "elev {0} ft" },
    ad_dens_dist: { pt: "Distâncias declaradas (m)", en: "Declared distances (m)", es: "Distancias declaradas (m)" },
    ad_dens_note: {
      pt: "Altitude-densidade estimada de QNH, temperatura e elevação. Quanto maior, maior a corrida de decolagem/pouso e menor a razão de subida — confira o desempenho no POH. Apoio.",
      en: "Density altitude estimated from QNH, temperature and elevation. The higher it is, the longer the takeoff/landing roll and the lower the climb rate — check performance in the POH. For support.",
      es: "Altitud-densidad estimada de QNH, temperatura y elevación. Cuanto mayor, mayor la carrera de despegue/aterrizaje y menor el régimen de ascenso — verifica el desempeño en el POH. De apoyo.",
    },

    // ---- Abas do aeródromo (aerodromo.js) ----
    ad_tab_cond: { pt: "Condições", en: "Conditions", es: "Condiciones" },
    ad_tab_tempo: { pt: "Tempo", en: "Weather", es: "Meteo" },
    ad_tab_cartas: { pt: "Cartas", en: "Charts", es: "Cartas" },
    ad_more_tempo: { pt: "Histórico, alertas e radar na página Tempo →", en: "History, alerts and radar on the Weather page →", es: "Histórico, alertas y radar en la página Meteo →" },
    ad_more_cartas: { pt: "Cartas de outros países na página Cartas →", en: "Charts for other countries on the Charts page →", es: "Cartas de otros países en la página Cartas →" },
  };

  // Categorias de aeronave — vêm do servidor em pt (app/aircraft.py); traduz na UI.
  // Chave = string pt exata; TCAT(pt) devolve o rótulo no idioma atual.
  var CAT = {
    "Monomotor pistão": { en: "Piston single", es: "Monomotor pistón" },
    "Bimotor pistão": { en: "Piston twin", es: "Bimotor pistón" },
    "Turboélice": { en: "Turboprop", es: "Turbohélice" },
    "Jato executivo": { en: "Business jet", es: "Jet ejecutivo" },
    "Jato regional": { en: "Regional jet", es: "Jet regional" },
    "Jato comercial": { en: "Commercial jet", es: "Jet comercial" },
    "Jato wide-body": { en: "Wide-body jet", es: "Jet wide-body" },
    "Clássico": { en: "Classic", es: "Clásico" },
    "Agrícola": { en: "Agricultural", es: "Agrícola" },
  };

  window.T = function (k) {
    var e = D[k];
    if (!e) return k;
    return e[L] != null ? e[L] : e.pt;
  };
  window.TCAT = function (pt) {
    var e = CAT[pt];
    if (!e || L === "pt") return pt;
    return e[L] != null ? e[L] : pt;
  };
  window.TF = function (k) {
    var s = window.T(k), args = arguments;
    return s.replace(/\{(\d+)\}/g, function (_, i) {
      var v = args[(+i) + 1];
      return v != null ? v : "";
    });
  };

  // Rola APENAS o dropdown do autocomplete (nunca a página) para manter a opção
  // destacada (.hl) visível ao navegar com as setas até o limite do combo.
  // Usado por todos os autocompletes (app, comparar, tempo, cartas).
  window.acScroll = function (acEl) {
    var el = acEl && acEl.querySelector(".hl");
    if (!el) return;
    var top = el.offsetTop;
    var bottom = top + el.offsetHeight;
    if (top < acEl.scrollTop) acEl.scrollTop = top;
    else if (bottom > acEl.scrollTop + acEl.clientHeight) acEl.scrollTop = bottom - acEl.clientHeight;
  };
})();

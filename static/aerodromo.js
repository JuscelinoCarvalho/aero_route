/* Aero Jussa · Informações do Aeródromo (DECEA/AISWEB)
 * Busca um aeródromo do Brasil e mostra, numa só tela:
 *   - ficha ROTAER (/api/rotaer): pistas, elevação, FIR, auxílios de navegação
 *   - NOTAM ativos (/api/notam)
 *   - nascer/pôr do sol (/api/sol)
 * As três chamadas são independentes (Promise.allSettled): se uma falhar, as
 * outras seções ainda aparecem.
 */

const $ = (s) => document.querySelector(s);

// Afiliados (mesmo conteúdo das outras páginas)
renderAffiliates($("#aff-grid"));

// Títulos de seção estáticos (data-i18n) — traduz no carregamento.
document.querySelectorAll("[data-i18n]").forEach((el) => {
  el.textContent = T(el.dataset.i18n);
});

let icao = "";

const status = $("#a-status");
function setStatus(msg, err) {
  status.textContent = msg;
  status.classList.toggle("err", !!err);
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
  );
}

// ===== Autocomplete de aeródromo (Brasil) =====
(function buildAeroAC() {
  const inputEl = $("#aero");
  const acEl = $("#acAero");
  let list = [];
  let hl = -1;
  let timer = null;

  function close() {
    acEl.classList.remove("open");
    acEl.innerHTML = "";
    hl = -1;
  }
  function render() {
    acEl.innerHTML = list
      .map(
        (a, i) =>
          `<div data-i="${i}" class="${i === hl ? "hl" : ""}">` +
          `<span class="code">${esc(a.icao)}</span>${a.iata ? " · " + esc(a.iata) : ""}` +
          `<div class="nm">${a.city ? esc(a.city) + " · " : ""}${esc(a.name)}</div></div>`
      )
      .join("");
    acEl.classList.toggle("open", list.length > 0);
    acScroll(acEl);
  }
  function pick(a) {
    inputEl.value = a.icao;
    icao = a.icao;
    close();
    load();
  }

  inputEl.addEventListener("input", () => {
    icao = "";
    const q = inputEl.value.trim();
    clearTimeout(timer);
    if (q.length < 2) return close();
    timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/airports/search?q=${encodeURIComponent(q)}`);
        const all = (await res.json()).results || [];
        // Só aeródromos do Brasil com ICAO de 4 letras (fonte é o DECEA).
        list = all.filter((a) => a.country === "BR" && a.icao && a.icao.length === 4).slice(0, 10);
        hl = -1;
        render();
      } catch (_) {
        close();
      }
    }, 160);
  });
  inputEl.addEventListener("keydown", (e) => {
    if (!acEl.classList.contains("open")) return;
    if (e.key === "ArrowDown") { hl = Math.min(hl + 1, list.length - 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { hl = Math.max(hl - 1, 0); render(); e.preventDefault(); }
    else if (e.key === "Enter" && list[hl >= 0 ? hl : 0]) { pick(list[hl >= 0 ? hl : 0]); e.preventDefault(); }
    else if (e.key === "Escape") close();
  });
  acEl.addEventListener("mousedown", (e) => {
    const d = e.target.closest("[data-i]");
    if (d) pick(list[+d.dataset.i]);
  });
  inputEl.addEventListener("blur", () => setTimeout(close, 180));
})();

// ===== Helpers de hora / duração =====
function shiftHHMM(hhmm, offsetH) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || "");
  if (!m) return "";
  const total = ((+m[1] + offsetH) * 60 + +m[2] + 1440 * 2) % 1440;
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}
function toMin(hhmm) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || "");
  return m ? +m[1] * 60 + +m[2] : null;
}
function fmtDur(mins) {
  if (mins == null) return "";
  if (mins < 0) mins += 1440;
  return `${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, "0")}min`;
}

// ===== Carrega tudo =====
async function load() {
  if (!icao) return;
  ["a-head", "a-wind", "a-dens", "a-sun", "a-pistas", "a-nav", "a-notam"].forEach((id) => ($("#" + id).style.display = "none"));
  $("#a-tabs").style.display = "";
  Tabs.newAerodrome(); // recarrega a aba ativa (Tempo/Cartas) para o novo aeródromo
  setStatus(TF("ad_searching", icao), false);
  if (window.track) window.track("aerodromo_open", { icao });

  const getJSON = (url) => fetch(url).then((r) => r.json().then((d) => ({ ok: r.ok, d })));

  try {
    const [rot, ntm, sun, met] = await Promise.allSettled([
      getJSON(`/api/rotaer?icao=${encodeURIComponent(icao)}`),
      getJSON(`/api/notam?icao=${encodeURIComponent(icao)}`),
      getJSON(`/api/sol?icao=${encodeURIComponent(icao)}`),
      getJSON(`/api/metar?icao=${encodeURIComponent(icao)}`),
    ]);

    // ROTAER (principal)
    let utc = -3;
    if (rot.status === "fulfilled" && rot.value.ok) {
      utc = parseInt(rot.value.d.utc, 10);
      if (isNaN(utc)) utc = -3;
      renderRotaer(rot.value.d);
      // Condições agora: ROTAER (cabeceiras/elevação/distâncias) + METAR (vento/temp/QNH).
      _cond = { rotaer: rot.value.d, metar: (met.status === "fulfilled" && met.value.ok) ? met.value.d : null };
      renderWind();
      renderDensity();
    } else {
      const msg = (rot.status === "fulfilled" && rot.value.d && rot.value.d.detail) || TF("ad_no_rotaer", icao);
      setStatus(msg, true);
    }

    // Sol (recalcula a hora local pelo fuso do ROTAER)
    if (sun.status === "fulfilled" && sun.value.ok) renderSol(sun.value.d, utc);

    // NOTAM
    if (ntm.status === "fulfilled" && ntm.value.ok) renderNotam(ntm.value.d);

    if (rot.status === "fulfilled" && rot.value.ok) setStatus(TF("ad_loaded", icao), false);
  } catch (_) {
    setStatus(T("ad_conn_fail"), true);
  }
}

function fact(key, value) {
  if (!value) return "";
  return `<div class="a-fact"><div class="k">${esc(T(key))}</div><div class="v">${esc(value)}</div></div>`;
}

function renderRotaer(d) {
  $("#a-icao").textContent = d.codigo || icao;
  $("#a-name").textContent = [d.nome, [d.cidade, d.uf].filter(Boolean).join("/")].filter(Boolean).join(" · ");
  const st = $("#a-astatus");
  st.textContent = d.status || "";
  st.classList.toggle("ok", /activ/i.test(d.status || ""));
  st.style.display = d.status ? "" : "none";

  const rnd = (v) => (v === "" || v == null || isNaN(v) ? v : Math.round(v));
  const elev = d.alt_ft ? `${rnd(d.alt_ft)} ft${d.alt_m ? ` · ${rnd(d.alt_m)} m` : ""}` : "";
  $("#a-facts").innerHTML =
    fact("ad_f_elev", elev) +
    fact("ad_f_fir", d.fir) +
    fact("ad_f_utc", d.utc) +
    fact("ad_f_cat", d.categoria) +
    fact("ad_f_type", d.tipo) +
    fact("ad_f_use", d.utilizacao) +
    fact("ad_f_opr", d.operacao);
  $("#a-head").style.display = "";

  // Pistas
  const pistas = d.pistas || [];
  if (pistas.length) {
    $("#a-pistas-list").innerHTML = pistas
      .map((p) => {
        const dim = p.comprimento_m && p.largura_m ? TF("ad_rwy_dims", p.comprimento_m, p.largura_m) : "";
        const meta = [dim, p.pcn && `PCN ${p.pcn}`].filter(Boolean).join(" · ");
        return (
          `<div class="a-card a-rwy"><div>` +
          `<div class="id">${esc(p.ident || "—")}</div>` +
          (meta ? `<div class="dim">${esc(meta)}</div>` : "") +
          `</div>${p.piso ? `<span class="a-chip">${esc(p.piso)}</span>` : ""}</div>`
        );
      })
      .join("");
    $("#a-pistas").style.display = "";
  }

  // Auxílios à navegação
  const nav = d.navaids || [];
  if (nav.length) {
    $("#a-nav-list").innerHTML = nav
      .map((n) => {
        const sub = [n.ident, n.cabeceira && TF("ad_thr", n.cabeceira)].filter(Boolean).join(" · ");
        return (
          `<div class="a-card a-rwy"><div>` +
          `<div class="id">${esc(n.tipo || "NAV")}</div>` +
          (sub ? `<div class="dim">${esc(sub)}</div>` : "") +
          `</div>${n.freq ? `<span class="a-chip">${esc(n.freq)}</span>` : ""}</div>`
        );
      })
      .join("");
    $("#a-nav").style.display = "";
  }
}

// ===== Condições agora (vento + altitude-densidade) =====
let _cond = null; // { rotaer, metar } da última consulta (p/ re-render ao mudar o limite)

function xwindLimit() {
  const v = parseInt(localStorage.getItem("xwind_limit"), 10);
  return v > 0 && v <= 60 ? v : 15; // kt (padrão)
}

// Componentes do vento numa cabeceira de rumo `hdg` (verdadeiro), vento de `dir`/`spd`.
function components(hdg, dir, spd) {
  const th = (((dir - hdg) % 360) + 540) % 360 - 180; // -180..180
  const r = (th * Math.PI) / 180;
  return { hw: spd * Math.cos(r), xw: spd * Math.sin(r), theta: th }; // hw+ = proa; xw+ = da direita
}

function xwClass(x, limit) {
  const a = Math.abs(x);
  if (a > limit) return "xw-bad";
  if (a > 0.6 * limit) return "xw-warn";
  return "xw-ok";
}

function renderWind() {
  if (!_cond) return;
  const box = $("#a-wind");
  const ends = [];
  ((_cond.rotaer.pistas) || []).forEach((p) => (p.cabeceiras || []).forEach((c) => ends.push(c)));
  if (!ends.length) return; // sem rumos de cabeceira, nada a mostrar

  const w = _cond.metar && _cond.metar.wind;
  const nowEl = $("#a-wind-now");
  // Cabeçalho: vento atual
  if (!w) {
    nowEl.textContent = T("ad_wind_na");
  } else if (w.vrb) {
    nowEl.textContent = TF("ad_wind_vrb", w.speed_kt);
  } else if (w.speed_kt === 0) {
    nowEl.textContent = T("ad_wind_calm");
  } else {
    let s = TF("ad_wind_now", String(w.dir).padStart(3, "0"), w.speed_kt);
    if (w.gust_kt) s += TF("ad_wind_gust", w.gust_kt);
    nowEl.textContent = s;
  }

  const limit = xwindLimit();
  const canCompute = w && !w.vrb && w.speed_kt > 0;
  // Pista favorável = maior componente de proa.
  let favIdent = null;
  if (canCompute) {
    let best = -Infinity;
    ends.forEach((c) => {
      const hw = components(c.heading, w.dir, w.speed_kt).hw;
      if (hw > best) { best = hw; favIdent = c.ident; }
    });
  }

  $("#a-wind-list").innerHTML = ends
    .map((c) => {
      const hdg = `${String(c.heading).padStart(3, "0")}°`;
      let compHtml = "";
      let xHtml = `<div class="a-wind-x"><span class="xw-ok">—</span></div>`;
      if (canCompute) {
        const cm = components(c.heading, w.dir, w.speed_kt);
        const hw = Math.round(cm.hw);
        const xw = Math.round(Math.abs(cm.xw));
        const side = cm.theta > 0 ? T("ad_wind_from_r") : T("ad_wind_from_l");
        const hwTxt = hw >= 0
          ? `<span class="hw-head">${TF("ad_wind_head", TF("ad_wind_kt", hw))}</span>`
          : `<span class="hw-tail">${TF("ad_wind_tail", TF("ad_wind_kt", -hw))}</span>`;
        let gustTxt = "";
        if (w.gust_kt) {
          const gx = Math.round(Math.abs(components(c.heading, w.dir, w.gust_kt).xw));
          gustTxt = ` · ${TF("ad_wind_gustx", TF("ad_wind_kt", gx))}`;
        }
        compHtml = `<div class="a-wind-line">${hwTxt}</div><div class="a-wind-line">${TF("ad_wind_cross", side)}${gustTxt}</div>`;
        xHtml = `<div class="a-wind-x"><span class="${xwClass(xw, limit)}">${xw}</span><small>kt xw</small></div>`;
      }
      const fav = c.ident === favIdent ? `<span class="a-wind-fav">${T("ad_wind_fav")}</span>` : "";
      return (
        `<div class="a-wind-row${c.ident === favIdent ? " fav" : ""}">` +
        `<div class="a-wind-rwy">${esc(c.ident)}<small>${hdg}</small></div>` +
        `<div class="a-wind-comp">${compHtml || `<div class="a-wind-line">${esc(hdg)} ${T("ad_wind_na")}</div>`}</div>` +
        `<div style="display:flex;align-items:center">${xHtml}${fav}</div>` +
        `</div>`
      );
    })
    .join("");

  box.style.display = "";
}

// Limite pessoal de vento cruzado (persistente) — re-renderiza as cores ao mudar.
(function windLimitCtl() {
  const el = $("#a-wind-limit");
  if (!el) return;
  el.value = xwindLimit();
  el.addEventListener("input", () => {
    const v = parseInt(el.value, 10);
    if (v > 0 && v <= 60) {
      localStorage.setItem("xwind_limit", String(v));
      renderWind();
    }
  });
})();

// ===== Altitude-densidade =====
function renderDensity() {
  if (!_cond) return;
  const box = $("#a-dens");
  const d = _cond.rotaer;
  const m = _cond.metar;
  const elevFt = parseFloat(d.alt_ft);
  const oat = m && m.temp_c != null ? m.temp_c : null;
  const qnh = m && m.qnh_hpa != null ? m.qnh_hpa : null;
  if (isNaN(elevFt) || oat == null || qnh == null) { box.style.display = "none"; return; }

  const N = (n) => Math.round(n).toLocaleString(window.I18N_LOCALE);
  const pa = elevFt + (1013.25 - qnh) * 30;         // altitude-pressão (ft) ~30 ft/hPa
  const isa = 15 - 1.98 * (pa / 1000);              // ISA na altitude-pressão
  const da = Math.round(pa + 118.8 * (oat - isa));  // altitude-densidade (ft)
  const dev = Math.round(oat - isa);

  const el = $("#a-dens-da");
  el.textContent = N(da);
  el.className = da > 6000 ? "da-bad" : da > 3000 ? "da-warn" : "da-ok";
  $("#a-dens-sub").textContent =
    `${TF("ad_dens_pa", N(pa))} · ${TF("ad_dens_isa", (dev >= 0 ? "+" : "") + dev)} · ${TF("ad_dens_elev", N(elevFt))}`;

  // Distâncias declaradas por cabeceira (quando o ROTAER publica).
  const rows = [];
  (d.pistas || []).forEach((p) => (p.cabeceiras || []).forEach((c) => {
    if (c.tora || c.lda) {
      const parts = [c.tora ? `TORA ${esc(c.tora)}` : "", c.lda ? `LDA ${esc(c.lda)}` : ""].filter(Boolean);
      rows.push(`<div class="a-dens-drow"><b>${esc(c.ident)}</b> ${parts.join(" · ")}</div>`);
    }
  }));
  $("#a-dens-dist").innerHTML = rows.length ? `<div class="h">${T("ad_dens_dist")}</div>${rows.join("")}` : "";

  box.style.display = "";
}

function renderSol(d, utc) {
  const riseL = shiftHHMM(d.sunrise_utc, utc) || d.sunrise_local || "—";
  const setL = shiftHHMM(d.sunset_utc, utc) || d.sunset_local || "—";
  $("#a-sunrise").textContent = riseL;
  $("#a-sunset").textContent = setL;
  $("#a-sunrise-utc").textContent = d.sunrise_utc ? d.sunrise_utc + "Z" : "";
  $("#a-sunset-utc").textContent = d.sunset_utc ? d.sunset_utc + "Z" : "";
  const dur = fmtDur(toMin(setL) - toMin(riseL));
  $("#a-daylight").textContent = dur ? TF("ad_sun_daylight", dur) : "";
  $("#a-sun").style.display = "";
}

function fmtNotamEnd(fim) {
  if (!fim) return "";
  if (/^\d{4}-\d\d-\d\d/.test(fim)) return fim;
  if (/perm/i.test(fim)) return T("ad_notam_perm");
  return fim;
}

function renderNotam(d) {
  const list = d.notams || [];
  $("#a-notam-h").textContent = `${T("ad_sec_notam")} · ${d.total != null ? d.total : list.length}`;
  if (!list.length) {
    $("#a-notam-list").innerHTML = `<div class="a-card"><div class="a-nt-txt">${esc(TF("ad_notam_none", icao))}</div></div>`;
    $("#a-notam").style.display = "";
    return;
  }
  $("#a-notam-list").innerHTML = list
    .map((n) => {
      const per = TF("ad_notam_period", n.inicio || "?", fmtNotamEnd(n.fim) || "?");
      return (
        `<div class="a-card">` +
        `<div class="a-nt-top"><span class="a-nt-n">${esc(n.numero || "NOTAM")}</span>` +
        `${n.categoria ? `<span class="a-nt-cat">${esc(n.categoria)}</span>` : ""}</div>` +
        `<div class="a-nt-per">${esc(per)}</div>` +
        `<div class="a-nt-txt">${esc(n.texto || "")}</div>` +
        `</div>`
      );
    })
    .join("");
  $("#a-notam").style.display = "";
}

// ===== Abas (Condições · Tempo · Cartas) =====
const Tabs = (function () {
  let current = "cond";
  let loaded = { tempo: false, cartas: false };
  function paint() {
    document.querySelectorAll(".a-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === current));
    ["cond", "tempo", "cartas"].forEach((t) => { const p = $("#pane-" + t); if (p) p.hidden = t !== current; });
  }
  function switchTo(tab) {
    current = tab;
    paint();
    // hash p/ deep-link/compartilhamento — não toca no ?icao= (refresh preservado).
    try { history.replaceState(null, "", location.pathname + location.search + (tab === "cond" ? "" : "#" + tab)); } catch (_) {}
    if (icao) {
      if (tab === "tempo" && !loaded.tempo) { loaded.tempo = true; loadTempo(); }
      if (tab === "cartas" && !loaded.cartas) { loaded.cartas = true; loadCartas(); }
    }
  }
  document.addEventListener("click", (e) => { const b = e.target.closest(".a-tab"); if (b) switchTo(b.dataset.tab); });
  return {
    setInitial(tab) { current = tab; paint(); },
    newAerodrome() { // aeródromo novo: zera caches das abas e recarrega a ativa
      loaded = { tempo: false, cartas: false };
      $("#wx-out").innerHTML = ""; $("#wx-taf").innerHTML = "";
      $("#adc-list").innerHTML = ""; $("#adc-viewer").style.display = "none"; $("#adc-status").textContent = "";
      if (current === "tempo") { loaded.tempo = true; loadTempo(); }
      else if (current === "cartas") { loaded.cartas = true; loadCartas(); }
    },
  };
})();

// ===== Aba Tempo: METAR + TAF (reuso da página Tempo) =====
function wxCell(k, v) {
  return v == null || v === "" ? "" : `<div class="wx-cell"><div class="k">${k}</div><div class="v">${v}</div></div>`;
}

function renderMetar(d) {
  const c = d.category_info || {};
  const w = d.wind;
  let wind = "—";
  if (w) {
    if (w.vrb) wind = `VRB <small>${w.speed_kt} kt</small>`;
    else if (w.speed_kt === 0) wind = T("wx_calm");
    else wind = `${String(w.dir).padStart(3, "0")}° <small>${w.speed_kt} kt${w.gust_kt ? " G" + w.gust_kt : ""}</small>`;
  }
  const vis = d.cavok ? "CAVOK" : (d.visibility_m == null ? "—" :
    (d.visibility_m >= 9999 ? "≥10 <small>km</small>" :
      (d.visibility_m >= 1000 ? `${Math.round(d.visibility_m / 1000)} <small>km</small>` : `${d.visibility_m} <small>m</small>`)));
  const ceil = d.ceiling_ft == null ? T("wx_noceil") : `${d.ceiling_ft} <small>ft</small>`;
  const temp = d.temp_c == null ? "—" : `${d.temp_c}° <small>/ ${d.dewpoint_c}°</small>`;
  const qnh = d.qnh_hpa == null ? "—" : `${d.qnh_hpa} <small>hPa</small>`;
  const name = (d.airport && (d.airport.name || d.airport.city)) || "";
  const when = d.time_utc ? `${d.time_utc.slice(0, 2)}:${d.time_utc.slice(2, 4)} UTC` : "";
  $("#wx-out").innerHTML =
    `<div class="wx-card">
      <div class="wx-flag" style="background:linear-gradient(90deg,${c.color}22,transparent)">
        <div class="wx-dot" style="background:${c.color}22;border:1px solid ${c.color}">${c.emoji || ""}</div>
        <div class="wx-cat" style="color:${c.color}">${c.label || d.category}<small>${c.desc || ""}</small></div>
        <div class="wx-when">${d.station || ""}${name ? "<br>" + esc(name) : ""}${when ? "<br>" + when : ""}</div>
      </div>
      <div class="wx-sum">${d.summary_pt || "—"}</div>
      <div class="wx-grid">
        ${wxCell(T("wx_wind"), wind)}${wxCell(T("wx_vis"), vis)}${wxCell(T("wx_ceil"), ceil)}
        ${wxCell(T("wx_temp"), temp)}${wxCell("QNH", qnh)}${wxCell(T("wx_cat"), `<span style="color:${c.color}">${c.label || d.category}</span>`)}
      </div>
      <div class="wx-raw">${d.raw || ""}</div>
    </div>`;
}

function renderTaf(d) {
  const temp = (d.temp_max_c != null || d.temp_min_c != null)
    ? ` · temp ${d.temp_max_c != null ? T("wx_temp_max") + " " + d.temp_max_c + "°" : ""}${d.temp_min_c != null ? " " + T("wx_temp_min") + " " + d.temp_min_c + "°" : ""}`
    : "";
  const periods = d.periods.map((p) => {
    const c = p.category_info || {};
    const known = p.category && p.category !== "UNKNOWN";
    const badge = p.prob != null
      ? `<span class="badge2" style="background:rgba(224,178,32,.18);color:#e0b020">PROB${p.prob}${p.tempo ? " TEMPO" : ""}</span>`
      : (p.type !== "base" && p.type !== "FM" ? `<span class="badge2" style="background:rgba(111,135,168,.18);color:var(--muted)">${p.type}</span>` : "");
    const catChip = known ? `<span class="badge2" style="background:${c.color}22;color:${c.color}">${c.emoji} ${c.label}</span>` : "";
    return `<div class="taf-p">
      <div class="taf-bar" style="background:${known ? c.color : "#1c3151"}"></div>
      <div><div class="taf-when">${catChip}${badge}${p.type_label}${p.when ? " " + p.when : ""}</div>
      <div class="taf-desc">${p.summary_pt}</div></div>
    </div>`;
  }).join("");
  let tl = "";
  const TL = d.timeline;
  if (TL && TL.hours && TL.hours.length) {
    let anyHist = false;
    const cells = TL.hours.map((h) => {
      const c = h.category_info || {};
      const risk = h.risk ? `<span title="${h.risk.prob ? h.risk.prob + "% " : ""}${TF("wx_risk", h.risk.category_info.label)}">⚠️</span>` : "";
      let hist;
      if (h.hist_vfr != null) { anyHist = true; hist = `<div class="tl-hist" title="${TF("wx_hist", h.hist_vfr, h.hist_n)}"><i style="width:${h.hist_vfr}%"></i></div>`; }
      else { hist = `<div class="tl-hist" title="${T("wx_hist_nodata")}"></div>`; }
      return `<div class="tl-cell"><div class="tl-bar" style="background:${c.color}">${risk}</div><div class="tl-hr">${h.label}</div>${hist}</div>`;
    }).join("");
    const legend = anyHist ? `<div class="tl-legend">${TF("wx_legend_hist", TL.clim_samples)}</div>` : `<div class="tl-legend">${T("wx_legend_nohist")}</div>`;
    tl = `<div class="tl-wrap"><div class="tl-sum">${TF("wx_flightwin", TL.summary_pt)}</div><div class="tl-strip">${cells}</div>${legend}</div>`;
  }
  $("#wx-taf").innerHTML =
    `<div class="taf">
      <div class="taf-h"><span class="t">${T("wx_taf_title")}</span>
        <span class="v">${TF("wx_taf_meta", d.station || "", d.issued_utc || "?", d.valid_from || "", d.valid_to || "", temp)}</span></div>
      ${tl}${periods}
      <div class="taf-raw">${d.raw || ""}</div>
    </div>`;
}

async function loadTempo() {
  const lang = window.APP_LANG || "pt";
  $("#wx-out").innerHTML = `<div class="wx-msg">${TF("wx_querying", icao)}</div>`;
  $("#wx-taf").innerHTML = "";
  let r, d;
  try {
    r = await fetch(`/api/metar?icao=${encodeURIComponent(icao)}&lang=${lang}`);
    d = await r.json().catch(() => ({}));
  } catch (_) { $("#wx-out").innerHTML = `<div class="wx-msg">${T("wx_conn_fail")}</div>`; return; }
  if (r.status === 503) { $("#wx-out").innerHTML = `<div class="wx-msg">${T("wx_503")}</div>`; return; }
  if (!r.ok) { $("#wx-out").innerHTML = `<div class="wx-msg">${TF("wx_get_fail", icao, d.detail ? ": " + d.detail : ".")}</div>`; return; }
  renderMetar(d);
  try {
    const rt = await fetch(`/api/taf?icao=${encodeURIComponent(icao)}&lang=${lang}`);
    const dt = await rt.json().catch(() => ({}));
    if (rt.ok && dt.periods && dt.periods.length) renderTaf(dt);
  } catch (_) { /* sem TAF: só o METAR */ }
}

// ===== Aba Cartas: lista + visor PDF (reuso da página Cartas) =====
let _pdfDoc = null, _loadTask = null, _pageNum = 1, _pageCount = 1, _zoom = 1;
let _rendering = false, _pendingRender = false, _curCarta = null, _pdfWorkerSet = false;
const _DPR = Math.min(window.devicePixelRatio || 1, 2);

function cStatus(msg, err) { const s = $("#adc-status"); s.textContent = msg; s.classList.toggle("err", !!err); }

function cartaUrl(c, dl) {
  const nome = encodeURIComponent(`${icao}-${c.nome}`.replace(/\s+/g, "_"));
  return `/api/carta?t=${encodeURIComponent(c.token)}&nome=${nome}${dl ? "&dl=1" : ""}`;
}

async function loadCartas() {
  const tipo = $("#adc-tipo").value;
  $("#adc-list").innerHTML = "";
  $("#adc-viewer").style.display = "none";
  _curCarta = null;
  cStatus(TF("c_searching", icao), false);
  let res, data;
  try {
    res = await fetch(`/api/cartas?icao=${encodeURIComponent(icao)}&tipo=${encodeURIComponent(tipo)}`);
    data = await res.json();
  } catch (_) { return cStatus(T("c_conn_fail"), true); }
  if (!res.ok) return cStatus(data.detail || T("c_query_fail"), true);
  const cartas = data.cartas || [];
  if (!cartas.length) return cStatus(TF("c_none", icao), false);
  const list = $("#adc-list");
  list.innerHTML = "";
  cartas.forEach((c) => {
    const meta = [c.amdt && `AMDT ${c.amdt}`, c.dt].filter(Boolean).join(" · ");
    const el = document.createElement("div");
    el.className = "c-card";
    el.innerHTML = `<div><div class="c-nm">${esc(c.nome)}</div>${meta ? `<div class="c-meta">${esc(meta)}</div>` : ""}</div><span class="c-type">${esc(c.tipo || "—")}</span>`;
    el.addEventListener("click", () => openCarta(c, el));
    list.appendChild(el);
  });
  cStatus(TF("c_found", cartas.length, icao), false);
  openCarta(cartas[0]);
}

async function renderCartaPage() {
  if (!_pdfDoc) return;
  if (_rendering) { _pendingRender = true; return; }
  _rendering = true;
  try {
    const page = await _pdfDoc.getPage(_pageNum);
    const wrap = $("#adc-view");
    const base = page.getViewport({ scale: 1 });
    const fit = (wrap.clientWidth || base.width) / base.width;
    const vp = page.getViewport({ scale: fit * _zoom * _DPR });
    const canvas = $("#adc-canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = Math.floor(vp.width);
    canvas.height = Math.floor(vp.height);
    canvas.style.width = Math.floor(vp.width / _DPR) + "px";
    canvas.style.height = Math.floor(vp.height / _DPR) + "px";
    await page.render({ canvasContext: ctx, viewport: vp }).promise;
    $("#adc-page").textContent = `${_pageNum} / ${_pageCount}`;
    $("#adc-zoom").textContent = Math.round(_zoom * 100) + "%";
  } finally {
    _rendering = false;
    if (_pendingRender) { _pendingRender = false; renderCartaPage(); }
  }
}

async function openCarta(c, el) {
  _curCarta = c;
  if (!_pdfWorkerSet) { pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.js"; _pdfWorkerSet = true; }
  document.querySelectorAll("#adc-list .c-card").forEach((x) => x.classList.remove("on"));
  if (el) el.classList.add("on");
  $("#adc-title").textContent = `${c.tipo ? c.tipo + " · " : ""}${c.nome}`;
  $("#adc-viewer").style.display = "";
  _zoom = 1;
  _pageNum = 1;
  $("#adc-load").hidden = false;
  try {
    if (_loadTask) { try { await _loadTask.destroy(); } catch (_) {} }
    const resp = await fetch(cartaUrl(c, false));
    if (!resp.ok) throw new Error("http " + resp.status);
    const buf = await resp.arrayBuffer();
    _loadTask = pdfjsLib.getDocument({ data: new Uint8Array(buf) });
    _pdfDoc = await _loadTask.promise;
    _pageCount = _pdfDoc.numPages;
    await renderCartaPage();
  } catch (_) {
    cStatus(T("c_render_fail"), true);
  } finally {
    $("#adc-load").hidden = true;
  }
}

(function cartaControls() {
  const on = (id, fn) => { const el = $("#" + id); if (el) el.addEventListener("click", fn); };
  const setZoom = (z) => { _zoom = Math.max(0.5, Math.min(z, 6)); renderCartaPage(); };
  on("adc-prev", () => { if (_pageNum > 1) { _pageNum--; renderCartaPage(); } });
  on("adc-next", () => { if (_pageNum < _pageCount) { _pageNum++; renderCartaPage(); } });
  on("adc-zin", () => setZoom(_zoom + 0.25));
  on("adc-zout", () => setZoom(_zoom - 0.25));
  on("adc-zfit", () => setZoom(1));
  on("adc-down", () => {
    if (!_curCarta) return;
    const a = document.createElement("a");
    a.href = cartaUrl(_curCarta, true);
    a.download = `${icao}-${_curCarta.nome}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
  });
  on("adc-open", () => { if (_curCarta) window.open(cartaUrl(_curCarta, false), "_blank"); });
  const sel = $("#adc-tipo");
  if (sel) sel.addEventListener("change", () => { if (icao) loadCartas(); });
})();

// Deep-link: /aerodromo?icao=SBGR (+ #tempo | #cartas) abre direto.
(function fromQuery() {
  const q = new URLSearchParams(location.search).get("icao");
  if (q && /^[A-Za-z]{4}$/.test(q)) {
    icao = q.toUpperCase();
    $("#aero").value = icao;
    const h = (location.hash || "").replace("#", "");
    if (h === "tempo" || h === "cartas") Tabs.setInitial(h);
    load();
  }
})();

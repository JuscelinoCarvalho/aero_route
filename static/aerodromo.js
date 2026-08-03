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

// Deep-link: /aerodromo?icao=SBGR abre direto.
(function fromQuery() {
  const q = new URLSearchParams(location.search).get("icao");
  if (q && /^[A-Za-z]{4}$/.test(q)) {
    icao = q.toUpperCase();
    $("#aero").value = icao;
    load();
  }
})();

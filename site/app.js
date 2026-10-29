/* DOM wiring for index.html. All data comes from data.js (window.ERUC_DATA). */
(function () {
  "use strict";
  const D = window.ERUC_DATA;
  const E = window.ERUC;
  const REF = D.reference;
  const SIG = REF.sigma;
  const HOSPITALS = E.unpackHospitals(D.hospitals);
  const $ = (id) => document.getElementById(id);

  const state = { zip: null, lat: null, lon: null, metro: null, sigma: SIG.default, checked: new Set() };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }
  function fmtMin(m) {
    m = Math.round(m);
    if (m < 60) return m + " min";
    const h = Math.floor(m / 60), r = m % 60;
    return h + " h" + (r ? " " + r + " min" : "");
  }
  function fmtShort(m) {
    m = Math.round(m);
    const h = Math.floor(m / 60), r = m % 60;
    return h ? h + "h" + String(r).padStart(2, "0") : r + "m";
  }
  function title(s) {
    return String(s).toLowerCase().replace(/\b([a-z])/g, (c) => c.toUpperCase());
  }
  function period(m) {
    const p = REF.summary.periods[m];
    return p ? p.start + " to " + p.end : "unknown";
  }
  function footnoteText(codes) {
    if (!codes) return "";
    return String(codes).split(",").map((c) => REF.footnotes[c.trim()]).filter(Boolean).join(" ");
  }

  // ---------- static text from the data ----------
  function fillStatic() {
    document.querySelectorAll(".period-op18b").forEach((el) => (el.textContent = period("OP_18b")));
    document.querySelectorAll(".period-op18b-end").forEach((el) => (el.textContent = REF.summary.periods.OP_18b.end));
    document.querySelectorAll(".period-edv").forEach((el) => (el.textContent = period("EDV")));
    $("n-numeric").textContent = REF.summary.n_op18b_numeric.toLocaleString();
    $("n-na").textContent = REF.summary.n_op18b_not_available.toLocaleString();
    $("n-nozcta").textContent = REF.summary.n_no_zcta_match.toLocaleString();
    $("nat-op18b").textContent = REF.national.OP_18b.score;
    $("hosp-median").textContent = REF.summary.op18b_hospital_quantiles.p50;
    $("built").textContent = REF.built;
  }

  // ---------- checklist ----------
  function buildChecklist() {
    const target = { call911: "list-call911", crisis: "list-call911", er: "list-er", urgent: "list-urgent" };
    E.SYMPTOMS.forEach((s) => {
      const wrap = document.createElement("label");
      wrap.className = "check";
      wrap.innerHTML = '<input type="checkbox" value="' + s.id + '"><span>' + esc(s.label) + "</span>";
      wrap.querySelector("input").addEventListener("change", (ev) => {
        if (ev.target.checked) state.checked.add(s.id); else state.checked.delete(s.id);
        renderVerdict();
        renderResults();
      });
      $(target[s.level]).appendChild(wrap);
    });
  }

  function renderVerdict() {
    const t = E.triage([...state.checked]);
    const v = $("verdict");
    const named = t.hits.filter((h) => h.level !== "urgent").map((h) => h.label.toLowerCase());
    let html = "";
    if (t.level === "call911") {
      html = "<h2>Call 911 now.</h2><p>You checked a sign of a possible emergency (" + esc(named.join("; ")) +
        "). Do not drive yourself. Wait times below do not apply: emergency patients are seen first.</p>" +
        (t.crisis ? "<p>For thoughts of self-harm, the 988 Suicide and Crisis Lifeline is also available, but call 911 first.</p>" : "") +
        '<a class="big-call" href="tel:911">Call 911</a>';
    } else if (t.level === "crisis") {
      html = "<h2>Call or text 988 now.</h2><p>The 988 Suicide and Crisis Lifeline is free, confidential and open 24/7. If you are in danger or have hurt yourself, call 911.</p>" +
        '<a class="big-call" href="tel:988">Call 988</a>';
    } else if (t.level === "er") {
      html = "<h2>Go to an emergency department.</h2><p>You checked: " + esc(named.join("; ")) +
        ". Go to the nearest one, or call 911 if it is getting worse or you cannot get there safely. Do not pick a farther hospital to save a few minutes of median time.</p>";
    } else if (t.level === "urgent") {
      html = "<h2>Urgent care is usually a good fit.</h2><p>Nothing you checked is on the red or amber lists. If one of those signs appears, go to the ER instead. MedlinePlus notes an emergency department can cost 2 to 3 times more than the same care elsewhere.</p>";
    } else {
      html = "<h2>Check anything that applies.</h2><p>If none of the red or amber signs fit and you are unsure, call your doctor's office or a nurse advice line.</p>";
    }
    v.className = "verdict v-" + (t.level === "crisis" ? "call911" : t.level);
    v.innerHTML = html;
    $("results").classList.toggle("demoted", !t.showWaits);
  }

  // ---------- location ----------
  function buildMetros() {
    Object.keys(D.urgentCare).forEach((id) => {
      const m = D.urgentCare[id];
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = m.name;
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", () => { $("zip").value = m.zip; setZip(m.zip); });
      b.dataset.metro = id;
      $("metros").appendChild(b);
    });
  }

  function setZip(raw) {
    const err = $("zip-err");
    const zip = E.normalizeZip(raw);
    if (!zip) { err.textContent = "Enter a 5-digit US ZIP code."; err.hidden = false; return; }
    const loc = D.zcta[zip];
    if (!loc) {
      err.textContent = "ZIP " + zip + " is not in the Census ZIP-area list (it may be a PO-box or business ZIP). Try a nearby residential ZIP.";
      err.hidden = false;
      return;
    }
    err.hidden = true;
    Object.assign(state, { zip: zip, lat: loc[0], lon: loc[1], metro: E.metroFor(D.urgentCare, loc[0], loc[1]) });
    document.querySelectorAll("#metros .chip").forEach((c) =>
      c.setAttribute("aria-pressed", String(c.dataset.metro === state.metro && D.urgentCare[state.metro].zip === zip)));
    renderResults();
    $("results").hidden = false;
  }

  // ---------- results ----------
  // Horizontal positions are percentages, so text never stretches on narrow screens.
  function bandSvg(median, sigma, scaleMax) {
    const y = 18, h = 14, L = 3, R = 3;
    const px = (m) => L + (Math.min(m, scaleMax) / scaleMax) * (100 - L - R);
    const x = (m) => px(m).toFixed(2) + "%";
    const w = (a, b) => (px(b) - px(a)).toFixed(2) + "%";
    const wide = E.lnInterval(median, SIG.high, 0.8);
    const cur = E.lnInterval(median, sigma, 0.8);
    let ticks = "";
    const step = scaleMax > 600 ? 120 : 60;
    for (let t = 0; t <= scaleMax; t += step) {
      ticks += '<line x1="' + x(t) + '" x2="' + x(t) + '" y1="' + (y + h + 2) + '" y2="' + (y + h + 6) + '" stroke="currentColor" opacity=".4"/>' +
        '<text x="' + x(t) + '" y="' + (y + h + 18) + '" text-anchor="middle">' + (t / 60) + "h</text>";
    }
    const label = "Assumed middle 80 percent of visits: " + fmtMin(cur[0]) + " to " + fmtMin(cur[1]) +
      " at sigma " + sigma.toFixed(2) + "; median " + fmtMin(median) + ".";
    return '<svg class="band" role="img" aria-label="' + esc(label) + '">' +
      '<rect x="' + x(wide[0]) + '" y="' + y + '" width="' + w(wide[0], wide[1]) + '" height="' + h + '" rx="3" fill="var(--band)"/>' +
      '<rect x="' + x(cur[0]) + '" y="' + (y + 3) + '" width="' + w(cur[0], cur[1]) + '" height="' + (h - 6) + '" rx="2" fill="var(--band-inner)"/>' +
      '<line x1="' + x(median) + '" x2="' + x(median) + '" y1="' + (y - 4) + '" y2="' + (y + h + 2) + '" stroke="var(--text)" stroke-width="2.5"/>' +
      '<text x="' + x(median) + '" y="' + (y - 7) + '" text-anchor="middle" style="fill:var(--text);font-weight:600">median ' + fmtShort(median) + "</text>" +
      ticks + "</svg>";
  }

  function rank(pct) {
    return pct == null ? "no other hospital to compare" : "shorter than " + Math.round(pct) + "%";
  }

  const EDV_KEY = { low: "OP_18b_LOW_MIN", medium: "OP_18b_MEDIUM_MIN", high: "OP_18b_HIGH_MIN", "very high": "OP_18b_VERY_HIGH_MIN" };

  function hospitalCard(h, scaleMax) {
    const s = state.sigma;
    const addr = esc(title(h.address)) + ", " + esc(title(h.city)) + ", " + esc(h.state) + " " + esc(h.zip);
    const dist = h.miles.toFixed(1) + " mi (ZIP-centroid distance)";
    const tags = '<span class="tag">' + esc(h.type) + "</span>" +
      (h.edv && h.edv !== "Not Available" ? '<span class="tag">' + esc(h.edv) + " ED volume</span>" : "");
    if (h.op18bNum == null) {
      return '<article class="hosp"><div class="hosp-top"><div><h4>' + esc(title(h.name)) + '</h4><div class="meta">' + addr + " · " + dist + "</div>" + tags +
        '</div><div class="median na">Not Available<small>OP-18b</small></div></div>' +
        '<p class="na">CMS footnote: ' + esc(footnoteText(h.op18b_footnote) || "no reason given") + "</p></article>";
    }
    const m = h.op18bNum;
    const cur = E.lnInterval(m, s, 0.8);
    const p4 = E.lnExceed(m, s, 240), p4lo = E.lnExceed(m, SIG.low, 240), p4hi = E.lnExceed(m, SIG.high, 240);
    const pr = (x) => Math.round(100 * x) + "%";
    const se = E.medianSE(m, s, h.op18b_sample);
    const volKey = EDV_KEY[h.edv];
    const volNat = volKey && REF.national[volKey] ? REF.national[volKey].score : null;
    const op18c = /^\d+$/.test(h.op18c) ? fmtMin(Number(h.op18c)) : "Not Available";
    const op22 = /^\d+$/.test(h.op22) ? h.op22 + "%" : "Not Available";
    return '<article class="hosp"><div class="hosp-top"><div><h4>' + esc(title(h.name)) + '</h4><div class="meta">' + addr + " · " + dist +
      (h.phone ? ' · <a href="tel:' + esc(h.phone.replace(/[^\d]/g, "")) + '">' + esc(h.phone) + "</a>" : "") + "</div>" + tags +
      '</div><div class="median">' + fmtMin(m) + "<small>median total visit,<br>discharged patients</small></div></div>" +
      bandSvg(m, s, scaleMax) +
      '<div class="facts">' +
      "<div><b>Middle 80% of visits <span class=\"assume\">assumed</span></b>" + fmtMin(cur[0]) + " – " + fmtMin(cur[1]) + " (σ " + s.toFixed(2) + ")</div>" +
      "<div><b>Chance over 4 h <span class=\"assume\">assumed</span></b>" + pr(p4) + " (σ 0.4–0.8: " + pr(Math.min(p4lo, p4hi)) + "–" + pr(Math.max(p4lo, p4hi)) + ")</div>" +
      "<div><b>Vs. other " + esc(h.state) + " hospitals</b>" + rank(h.pct_shorter_state) + "</div>" +
      "<div><b>Vs. other US hospitals</b>" + rank(h.pct_shorter_nation) + "</div>" +
      (volNat ? "<div><b>US median, " + esc(h.edv) + "-volume EDs</b>" + fmtMin(Number(volNat)) + "</div>" : "") +
      "<div><b>Left before being seen (2024)</b>" + op22 + "</div>" +
      "<div><b>Mental-health visits (OP-18c)</b>" + op18c + "</div>" +
      "<div><b>Cases CMS used</b>" + (h.op18b_sample ? h.op18b_sample.toLocaleString() : "?") + (se ? " (std. error of median ≈ " + Math.round(se) + " min)" : "") + "</div>" +
      "</div>" +
      (h.op18b_footnote ? '<p class="hint">CMS footnote: ' + esc(footnoteText(h.op18b_footnote)) + "</p>" : "") +
      "</article>";
  }

  function urgentCard(p) {
    return '<article class="uc"><h4>' + esc(p.name) + '</h4><div class="meta">' +
      (p.address ? esc(p.address) + " · " : "") + p.miles.toFixed(1) + " mi straight-line</div>" +
      '<div class="meta">Hours (OSM): ' + (p.hours ? esc(p.hours) : "not listed") + "</div>" +
      '<div class="meta"><strong>Wait time: no public data.</strong> <a href="https://www.openstreetmap.org/' + esc(p.osm) + '">OSM entry</a></div></article>';
  }

  function renderResults() {
    if (state.lat == null) return;
    const metroName = state.metro ? D.urgentCare[state.metro].name : null;
    $("place").textContent = "ZIP " + state.zip + (metroName ? " (" + metroName + " demo area)" : "");
    const near = E.nearbyHospitals(HOSPITALS, state.lat, state.lon);
    let scaleMax = 360;
    near.list.forEach((h) => { if (h.op18bNum) scaleMax = Math.max(scaleMax, E.lnInterval(h.op18bNum, SIG.high, 0.8)[1]); });
    scaleMax = Math.min(Math.ceil(scaleMax / 60) * 60, 1200);
    $("hospitals").innerHTML = near.list.map((h) => hospitalCard(h, scaleMax)).join("") ||
      '<p class="na">No hospitals with emergency departments found.</p>';
    $("hidden-note").textContent = near.hiddenNoEd ?
      near.hiddenNoEd + " nearby hospital(s) hidden because CMS lists no emergency services there." : "";
    const uc = $("urgent");
    if (!state.metro) {
      uc.innerHTML = '<p class="na">Urgent-care listings are cached only for the demo areas (Ithaca, New York City, Fremont / Bay Area, Miami, Chicago). Search a map for clinics near you, and call ahead.</p>';
      return;
    }
    const places = E.nearbyUrgentCare(D.urgentCare[state.metro].places, state.lat, state.lon, 15, 8);
    const total = D.urgentCare[state.metro].places.length;
    uc.innerHTML = '<p class="hint">' + total + " urgent-care place(s) tagged in OpenStreetMap for this demo area (snapshot " +
      esc(D.urgentCare[state.metro].osm_timestamp.slice(0, 10)) + "); coverage is incomplete. Showing those within 15 miles.</p>" +
      (places.map(urgentCard).join("") || '<p class="na">None tagged within 15 miles.</p>');
  }

  // ---------- init ----------
  fillStatic();
  buildChecklist();
  buildMetros();
  // Deep links for demos, e.g. index.html#zip=14850&check=cold,sprain&sigma=0.6
  const hash = new URLSearchParams(location.hash.slice(1));
  (hash.get("check") || "").split(",").filter(Boolean).forEach((id) => {
    const box = document.querySelector('.check input[value="' + CSS.escape(id) + '"]');
    if (box) { box.checked = true; state.checked.add(id); }
  });
  const hs = Number(hash.get("sigma"));
  if (hs >= 0.3 && hs <= 1) { state.sigma = hs; $("sigma").value = hs; $("sigma-out").textContent = hs.toFixed(2); }
  renderVerdict();
  if (hash.get("zip")) { $("zip").value = hash.get("zip"); setZip(hash.get("zip")); }
  $("zip-form").addEventListener("submit", (ev) => { ev.preventDefault(); setZip($("zip").value); });
  $("sigma").addEventListener("input", (ev) => {
    state.sigma = Number(ev.target.value);
    $("sigma-out").textContent = state.sigma.toFixed(2);
    renderResults();
  });
})();

/* Pure logic for the page: statistics, distances, symptom triage, lookups.
 * No DOM access here, so the same file is unit-tested under Node. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ERUC = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ---------- normal distribution ----------
  // Inverse CDF: Acklam's rational approximation (relative error < 1.2e-9).
  function normInv(p) {
    if (!(p > 0 && p < 1)) throw new RangeError("p must be in (0, 1)");
    const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2,
      1.38357751867269e2, -3.066479806614716e1, 2.506628277459239];
    const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2,
      6.680131188771972e1, -1.328068155288572e1];
    const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838,
      -2.549732539343734, 4.374664141464968, 2.938163982698783];
    const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996,
      3.754408661907416];
    const lo = 0.02425, hi = 1 - lo;
    let q, r;
    if (p < lo) {
      q = Math.sqrt(-2 * Math.log(p));
      return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    }
    if (p > hi) {
      q = Math.sqrt(-2 * Math.log(1 - p));
      return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    }
    q = p - 0.5;
    r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
      (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }

  // Complementary error function, Chebyshev fit (fractional error < 1.2e-7).
  function erfc(x) {
    const z = Math.abs(x);
    const t = 1 / (1 + 0.5 * z);
    const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 +
      t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 +
      t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
    return x >= 0 ? r : 2 - r;
  }
  function normCdf(x) { return 0.5 * erfc(-x / Math.SQRT2); }

  // ---------- lognormal with median pinned at the CMS value ----------
  function lnQuantile(median, sigma, p) {
    if (!(median > 0) || sigma < 0) throw new RangeError("bad lognormal parameters");
    return median * Math.exp(sigma * normInv(p));
  }
  function lnExceed(median, sigma, t) {
    if (t <= 0) return 1;
    if (sigma === 0) return median > t ? 1 : 0;
    return 1 - normCdf((Math.log(t) - Math.log(median)) / sigma);
  }
  function lnInterval(median, sigma, coverage) {
    const a = (1 - coverage) / 2;
    return [lnQuantile(median, sigma, a), lnQuantile(median, sigma, 1 - a)];
  }
  // Large-sample SE of a sample median under the lognormal: m*sigma*sqrt(pi/(2n)).
  function medianSE(median, sigma, n) {
    if (!(n > 0)) return null;
    return median * sigma * Math.sqrt(Math.PI / (2 * n));
  }

  // ---------- geography ----------
  function haversineMiles(lat1, lon1, lat2, lon2) {
    const R = 3958.8, rad = Math.PI / 180;
    const dp = (lat2 - lat1) * rad, dl = (lon2 - lon1) * rad;
    const a = Math.sin(dp / 2) ** 2 +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dl / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function normalizeZip(input) {
    const m = String(input || "").trim().match(/^(\d{5})(?:-\d{4})?$/);
    return m ? m[1] : null;
  }

  function unpackHospitals(packed) {
    return packed.rows.map(function (r) {
      const o = {};
      packed.cols.forEach(function (c, i) { o[c] = r[i]; });
      o.op18bNum = /^\d+(\.\d+)?$/.test(o.op18b) ? Number(o.op18b) : null;
      return o;
    });
  }

  // Hospitals with an emergency department, sorted by ZIP-centroid distance.
  function nearbyHospitals(hospitals, lat, lon, opts) {
    const o = Object.assign({ radius: 30, max: 8, minCount: 3 }, opts || {});
    const withD = [];
    let hiddenNoEd = 0;
    hospitals.forEach(function (h) {
      if (h.lat == null || h.lon == null) return;
      const d = haversineMiles(lat, lon, h.lat, h.lon);
      if (h.emergency_services !== "Yes") { if (d <= o.radius) hiddenNoEd++; return; }
      withD.push(Object.assign({ miles: d }, h));
    });
    withD.sort(function (a, b) { return a.miles - b.miles || a.name.localeCompare(b.name); });
    let list = withD.filter(function (h) { return h.miles <= o.radius; }).slice(0, o.max);
    if (list.length < o.minCount) list = withD.slice(0, o.minCount);
    return { list: list, hiddenNoEd: hiddenNoEd };
  }

  function metroFor(urgentCare, lat, lon, marginDeg) {
    const m = marginDeg == null ? 0.05 : marginDeg;
    for (const id of Object.keys(urgentCare)) {
      const b = urgentCare[id].bbox; // [s, w, n, e]
      if (lat >= b[0] - m && lat <= b[2] + m && lon >= b[1] - m && lon <= b[3] + m) return id;
    }
    return null;
  }

  function nearbyUrgentCare(places, lat, lon, radius, max) {
    return places.map(function (p) {
      return Object.assign({ miles: haversineMiles(lat, lon, p.lat, p.lon) }, p);
    }).filter(function (p) { return p.miles <= (radius || 15); })
      .sort(function (a, b) { return a.miles - b.miles; })
      .slice(0, max || 8);
  }

  // ---------- symptom checklist ----------
  // Paraphrased from MedlinePlus, "When to use the emergency room - adult":
  // https://medlineplus.gov/ency/patientinstructions/000593.htm
  const SYMPTOMS = [
    { id: "chest", level: "call911", label: "Chest pain or pressure, or pain spreading to the arm or jaw" },
    { id: "stroke", level: "call911", label: "Sudden weakness or drooping on one side, or suddenly unable to speak, see or walk" },
    { id: "breathing", level: "call911", label: "Severe shortness of breath, choking, or stopped breathing" },
    { id: "unresponsive", level: "call911", label: "Passed out, fainted, or a seizure lasting over a minute" },
    { id: "headinjury", level: "call911", label: "Head, neck or spine injury with confusion, fainting, numbness or loss of movement" },
    { id: "allergy", level: "call911", label: "Severe allergic reaction: swelling, hives and trouble breathing" },
    { id: "selfharm", level: "crisis", label: "Thinking about hurting yourself or others" },
    { id: "bleeding", level: "er", label: "Heavy bleeding, a deep wound, or a serious burn" },
    { id: "fracture", level: "er", label: "Possible broken bone with deformity, bone through skin, or loss of movement" },
    { id: "headache", level: "er", label: "Sudden, unusual or very bad headache, or sudden confusion" },
    { id: "fever_stiff", level: "er", label: "High fever with headache and stiff neck, or fever that medicine does not bring down" },
    { id: "vomit_blood", level: "er", label: "Coughing or vomiting blood, or vomiting / diarrhea that will not stop" },
    { id: "poison", level: "er", label: "Poisoning, overdose, or breathed in smoke or fumes" },
    { id: "severe_pain", level: "er", label: "Severe pain anywhere, or dizziness or weakness that does not go away" },
    { id: "cold", level: "urgent", label: "Cold, flu, sore throat, earache, or a low-grade fever" },
    { id: "sprain", level: "urgent", label: "Sprain, strain, or back pain after a minor injury" },
    { id: "cut", level: "urgent", label: "Minor cut that may need stitches, or a minor burn" },
    { id: "rash", level: "urgent", label: "A limited rash, or a minor eye irritation or injury" },
    { id: "uti", level: "urgent", label: "Painful urination or other mild infection symptoms" },
  ];
  const RANK = { none: 0, urgent: 1, er: 2, crisis: 3, call911: 4 };

  function triage(checkedIds) {
    const set = new Set(checkedIds || []);
    let level = "none";
    const hits = [];
    SYMPTOMS.forEach(function (s) {
      if (set.has(s.id)) {
        hits.push(s);
        if (RANK[s.level] > RANK[level]) level = s.level;
      }
    });
    // A crisis item alongside a physical emergency still means 911 first.
    const crisis = hits.some(function (s) { return s.level === "crisis"; });
    return { level: level, crisis: crisis, hits: hits, showWaits: level === "urgent" || level === "none" };
  }

  return {
    normInv: normInv, normCdf: normCdf, lnQuantile: lnQuantile, lnExceed: lnExceed,
    lnInterval: lnInterval, medianSE: medianSE, haversineMiles: haversineMiles,
    normalizeZip: normalizeZip, unpackHospitals: unpackHospitals,
    nearbyHospitals: nearbyHospitals, metroFor: metroFor, nearbyUrgentCare: nearbyUrgentCare,
    SYMPTOMS: SYMPTOMS, triage: triage,
  };
});

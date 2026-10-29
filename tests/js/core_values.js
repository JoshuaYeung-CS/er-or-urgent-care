// Prints core.js results for a grid of inputs so pytest can compare with Python.
"use strict";
const E = require(process.argv[2]);
const out = { quantile: [], exceed: [], se: [], miles: null, triage: {}, zip: [] };
for (const m of [60, 148, 244]) {
  for (const s of [0.3, 0.6, 0.9]) {
    for (const p of [0.01, 0.1, 0.5, 0.9, 0.99]) out.quantile.push([m, s, p, E.lnQuantile(m, s, p)]);
    for (const t of [60, 240, 480]) out.exceed.push([m, s, t, E.lnExceed(m, s, t)]);
    out.se.push([m, s, 400, E.medianSE(m, s, 400)]);
  }
}
out.miles = E.haversineMiles(40.7128, -74.006, 41.8781, -87.6298);
const cases = { none: [], uc: ["cold", "sprain"], er: ["cold", "bleeding"], e911: ["sprain", "chest"],
  crisis: ["selfharm"], both: ["selfharm", "stroke"] };
for (const k of Object.keys(cases)) out.triage[k] = E.triage(cases[k]);
out.zip = ["14850", " 02139 ", "94539-1234", "1485", "abcde", ""].map(E.normalizeZip);
out.symptoms = E.SYMPTOMS;
process.stdout.write(JSON.stringify(out));

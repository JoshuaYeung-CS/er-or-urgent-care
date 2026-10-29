// Runs site/data.js + core.js + app.js against a tiny fake DOM and prints a JSON
// summary of what the page rendered. Usage: node app_smoke.js <site_dir> <hash>
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const siteDir = process.argv[2];
const hash = process.argv[3] || "";
const html = fs.readFileSync(path.join(siteDir, "index.html"), "utf8");

function makeEl(id) {
  const listeners = {};
  const classes = new Set();
  const el = {
    id, hidden: false, value: "", checked: false, textContent: "", className: "", dataset: {},
    _children: [], _html: "",
    get innerHTML() { return this._html; },
    set innerHTML(v) {
      this._html = v;
      const m = /<input type="checkbox" value="([^"]+)">/.exec(v);
      if (m) { this._input = makeEl(null); this._input.value = m[1]; inputs.push(this._input); }
    },
    classList: {
      toggle(c, on) { if (on) classes.add(c); else classes.delete(c); },
      contains(c) { return classes.has(c); },
    },
    setAttribute(k, v) { this["attr_" + k] = v; },
    addEventListener(t, fn) { (listeners[t] = listeners[t] || []).push(fn); },
    dispatch(t, ev) { (listeners[t] || []).forEach((fn) => fn(Object.assign({ target: el, preventDefault() {} }, ev))); },
    appendChild(c) { this._children.push(c); return c; },
    querySelector(sel) { return sel === "input" ? this._input : null; },
  };
  return el;
}

const inputs = [];
const byId = {};
for (const m of html.matchAll(/<[a-z]+[^>]*\bid="([^"]+)"[^>]*>/g)) {
  byId[m[1]] = makeEl(m[1]);
  byId[m[1]].hidden = /\shidden[\s>]/.test(m[0]);
}

const document = {
  getElementById: (id) => byId[id] || null,
  createElement: () => makeEl(null),
  querySelectorAll: (sel) => (sel === "#metros .chip" ? byId.metros._children : []),
  querySelector: (sel) => {
    const m = /value="([^"]+)"/.exec(sel);
    return m ? inputs.find((i) => i.value === m[1]) || null : null;
  },
};
const ctx = {
  window: {}, document, location: { hash }, URLSearchParams, CSS: { escape: (s) => s },
  console, Set, Number, String, Math, Object, JSON,
};
ctx.window = ctx;
ctx.self = ctx;
vm.createContext(ctx);
for (const f of ["data.js", "core.js", "app.js"]) {
  vm.runInContext(fs.readFileSync(path.join(siteDir, f), "utf8"), ctx, { filename: f });
}

const before = byId.hospitals.innerHTML;
byId.sigma.value = "0.9";
byId.sigma.dispatch("input", { target: { value: "0.9" } });
const after = byId.hospitals.innerHTML;

process.stdout.write(JSON.stringify({
  verdictClass: byId.verdict.className,
  verdict: byId.verdict.innerHTML,
  hospitals: before,
  hospitalsAfterSigma: after,
  sigmaOut: byId["sigma-out"].textContent,
  urgent: byId.urgent.innerHTML,
  place: byId.place.textContent,
  resultsHidden: byId.results.hidden,
  demoted: byId.results.classList.contains("demoted"),
  zipError: byId["zip-err"].hidden ? "" : byId["zip-err"].textContent,
  checklistCount: inputs.length,
  metroChips: byId.metros._children.length,
}));

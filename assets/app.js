/* ============================================================================
   Macro Impact Dashboard — renderer (no dependencies, works from file://)
   ========================================================================== */
(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";
  var VBW = 540, VBH = 210;                 // internal SVG coordinate system
  var M = { top: 12, right: 54, bottom: 22, left: 46 };
  var PW = VBW - M.left - M.right;          // plot width
  var PH = VBH - M.top - M.bottom;          // plot height

  var DATA = window.MACRO_DATA;

  // ---- helpers -------------------------------------------------------------
  function el(tag, attrs, text) {
    var e = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }
  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function parseDate(s) { return Date.parse(s + "T00:00:00Z"); }

  function fmtNum(v, dec) {
    return v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }
  function valueSuffix(ind) { return ind.unit === "%" ? "%" : ind.unit === "M" ? "M" : "K"; }
  function deltaSuffix(ind) { return ind.unit === "%" ? "pp" : ind.unit === "M" ? "M" : "K"; }
  function fmtValue(v, ind, forceSign) {
    var s = fmtNum(v, ind.decimals) + valueSuffix(ind);
    if (forceSign && v > 0) s = "+" + s;
    return s;
  }
  var SIGNED = { nfp: true, retail: true };  // figures reported as a change

  function fmtMonthYear(ts) {
    var d = new Date(ts);
    return d.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
  }
  function fmtFullDate(ts) {
    var d = new Date(ts);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
  }

  // "nice" axis: return {min,max,ticks[]}
  function niceScale(lo, hi, count) {
    if (lo === hi) { lo -= 1; hi += 1; }
    var span = hi - lo;
    var raw = span / (count || 4);
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var norm = raw / mag;
    var step = (norm >= 5 ? 5 : norm >= 2 ? 2 : norm >= 1 ? 1 : 0.5) * mag;
    var nmin = Math.floor(lo / step) * step;
    var nmax = Math.ceil(hi / step) * step;
    var ticks = [];
    for (var t = nmin; t <= nmax + step * 1e-6; t += step) ticks.push(+t.toFixed(6));
    return { min: nmin, max: nmax, ticks: ticks };
  }

  // ---- one chart -----------------------------------------------------------
  function buildChart(ind) {
    var pts = ind.points.map(function (p) { return { t: parseDate(p.d), v: p.v, d: p.d }; });
    var xs = pts.map(function (p) { return p.t; });
    var vs = pts.map(function (p) { return p.v; });
    var t0 = xs[0], t1 = xs[xs.length - 1];
    var vmin = Math.min.apply(null, vs), vmax = Math.max.apply(null, vs);

    // include zero baseline when the data straddles it (change / rate figures)
    var lo = vmin, hi = vmax;
    var zeroInside = vmin < 0 && vmax > 0;
    if (zeroInside) { lo = Math.min(0, vmin); hi = Math.max(0, vmax); }
    var pad = (hi - lo) * 0.08 || 1;
    var sc = niceScale(lo - pad, hi + pad, 4);

    var x = function (t) { return M.left + (t - t0) / (t1 - t0) * PW; };
    var y = function (v) { return M.top + (sc.max - v) / (sc.max - sc.min) * PH; };

    var svg = el("svg", { viewBox: "0 0 " + VBW + " " + VBH, preserveAspectRatio: "none",
      role: "img", "aria-label": ind.name + " from " + ind.range.from + " to " + ind.range.to });

    // gridlines + y ticks
    sc.ticks.forEach(function (tv) {
      if (tv < sc.min - 1e-9 || tv > sc.max + 1e-9) return;
      var yy = y(tv);
      var isZero = Math.abs(tv) < 1e-9 && zeroInside;
      svg.appendChild(el("line", { class: isZero ? "g-base" : "g-grid",
        x1: M.left, x2: M.left + PW, y1: yy, y2: yy }));
      svg.appendChild(el("text", { class: "g-tick", x: M.left - 7, y: yy + 3.5, "text-anchor": "end" },
        fmtNum(tv, sc.ticks.some(function (q) { return q % 1 !== 0; }) ? ind.decimals : 0)));
    });

    // x (year) ticks
    var y0 = new Date(t0).getUTCFullYear() + 1, y1 = new Date(t1).getUTCFullYear();
    var years = [];
    for (var yr = y0; yr <= y1; yr++) years.push(yr);
    var xstep = years.length > 7 ? 2 : 1;
    years.forEach(function (yr, i) {
      if (i % xstep !== 0 && i !== years.length - 1) return;
      var tx = Date.UTC(yr, 0, 1);
      if (tx < t0 || tx > t1) return;
      svg.appendChild(el("text", { class: "g-tick", x: x(tx), y: VBH - 6, "text-anchor": "middle" }, "'" + String(yr).slice(2)));
    });

    // area wash (down to zero when present, else to plot floor)
    var floorV = zeroInside ? 0 : sc.min;
    var areaD = "M" + x(pts[0].t) + " " + y(pts[0].v);
    for (var a = 1; a < pts.length; a++) areaD += " L" + x(pts[a].t) + " " + y(pts[a].v);
    areaD += " L" + x(pts[pts.length - 1].t) + " " + y(floorV) + " L" + x(pts[0].t) + " " + y(floorV) + " Z";
    svg.appendChild(el("path", { class: "g-area", d: areaD }));

    // line
    var lineD = "M" + x(pts[0].t) + " " + y(pts[0].v);
    for (var b = 1; b < pts.length; b++) lineD += " L" + x(pts[b].t) + " " + y(pts[b].v);
    svg.appendChild(el("path", { class: "g-line", d: lineD }));

    // end dot + end label
    var last = pts[pts.length - 1];
    svg.appendChild(el("circle", { class: "g-enddot", cx: x(last.t), cy: y(last.v), r: 4 }));
    svg.appendChild(el("text", { class: "g-endlabel", x: x(last.t) + 8, y: y(last.v) + 3.5, "text-anchor": "start" },
      fmtValue(last.v, ind, SIGNED[ind.id])));

    // hover layer
    var cross = el("line", { class: "g-cross", y1: M.top, y2: M.top + PH });
    var hdot = el("circle", { class: "g-hoverdot", r: 4 });
    svg.appendChild(cross); svg.appendChild(hdot);
    var hit = el("rect", { class: "g-hit", x: 0, y: 0, width: VBW, height: VBH });
    svg.appendChild(hit);

    var wrap = h("div", "chart");
    wrap.appendChild(svg);
    var tip = h("div", "tooltip");
    var tipDate = h("div", "tt-date"); var tipVal = h("div", "tt-val");
    tip.appendChild(tipDate); tip.appendChild(tipVal);
    wrap.appendChild(tip);

    function nearest(px) {
      var lo2 = 0, hi2 = pts.length - 1;
      var target = t0 + (px - M.left) / PW * (t1 - t0);
      while (hi2 - lo2 > 1) { var mid = (lo2 + hi2) >> 1; if (pts[mid].t < target) lo2 = mid; else hi2 = mid; }
      return (target - pts[lo2].t) < (pts[hi2].t - target) ? lo2 : hi2;
    }
    function onMove(evt) {
      var r = svg.getBoundingClientRect();
      var cx = evt.touches ? evt.touches[0].clientX : evt.clientX;
      var px = (cx - r.left) / r.width * VBW;
      var i = nearest(px); var p = pts[i];
      var gx = x(p.t), gy = y(p.v);
      cross.setAttribute("x1", gx); cross.setAttribute("x2", gx); cross.style.opacity = 1;
      hdot.setAttribute("cx", gx); hdot.setAttribute("cy", gy); hdot.style.opacity = 1;
      tipDate.textContent = fmtFullDate(p.t);
      tipVal.textContent = fmtValue(p.v, ind, SIGNED[ind.id]);
      tip.style.left = (gx / VBW * r.width) + "px";
      tip.style.top = (gy / VBH * r.height) + "px";
      tip.style.opacity = 1;
    }
    function onLeave() { cross.style.opacity = 0; hdot.style.opacity = 0; tip.style.opacity = 0; }
    svg.addEventListener("mousemove", onMove);
    svg.addEventListener("mouseleave", onLeave);
    svg.addEventListener("touchstart", onMove, { passive: true });
    svg.addEventListener("touchmove", onMove, { passive: true });
    svg.addEventListener("touchend", onLeave);

    return wrap;
  }

  // ---- impact badge (ascending bars; fill count = impact tier) -------------
  function impactBadge(impact) {
    var high = impact === "high";
    var filled = high ? 3 : 2;
    var b = h("span", "impact " + (high ? "high" : "medium"));
    var svg = el("svg", { width: 13, height: 11, viewBox: "0 0 13 11" });
    [[0, 7], [5, 4], [10, 1]].forEach(function (p, i) {
      svg.appendChild(el("rect", { x: p[0], y: p[1], width: 3, height: 11 - p[1], rx: 0.7,
        fill: "currentColor", "fill-opacity": i < filled ? 1 : 0.28 }));
    });
    b.appendChild(svg);
    b.appendChild(document.createTextNode(high ? "HIGH IMPACT" : "MEDIUM IMPACT"));
    return b;
  }

  // ---- delta pill ----------------------------------------------------------
  function deltaPill(ind) {
    if (ind.prev == null) return null;
    var diff = ind.latest.value - ind.prev;
    var suffix = deltaSuffix(ind);
    var dir = diff > 0 ? "up" : diff < 0 ? "down" : "flat";
    var arrow = diff > 0 ? "▲" : diff < 0 ? "▼" : "—";
    var cls;
    if (diff === 0 || ind.good === "neutral") cls = "flat";
    else { var isGood = (ind.good === "up" && diff > 0) || (ind.good === "down" && diff < 0); cls = dir + (isGood ? "-good" : "-bad"); }
    var pill = h("span", "delta " + cls);
    pill.textContent = arrow + " " + fmtNum(Math.abs(diff), ind.decimals) + " " + suffix;
    return pill;
  }

  // ---- card ----------------------------------------------------------------
  function buildCard(ind) {
    var card = h("div", "card");

    var head = h("div", "card-head");
    head.appendChild(h("h3", "card-title", ind.name));
    head.appendChild(impactBadge(ind.impact));
    card.appendChild(head);

    card.appendChild(h("p", "blurb", ind.blurb));

    var stat = h("div", "stat");
    stat.appendChild(h("span", "value", fmtValue(ind.latest.value, ind, SIGNED[ind.id])));
    var pill = deltaPill(ind); if (pill) stat.appendChild(pill);
    stat.appendChild(h("span", "asof", "as of " + fmtMonthYear(parseDate(ind.latest.date))));
    card.appendChild(stat);

    var chartHost = h("div", "view-chart");
    chartHost.appendChild(buildChart(ind));
    card.appendChild(chartHost);

    var tableHost = h("div", "view-table hidden");
    tableHost.appendChild(buildTable(ind));
    card.appendChild(tableHost);

    var foot = h("div", "card-foot");
    foot.appendChild(h("span", null, ind.freq + " · " + ind.source));
    var fred = h("span", null, "FRED: ");
    fred.appendChild(h("code", null, ind.fred_label));
    foot.appendChild(fred);
    card.appendChild(foot);

    return card;
  }

  // ---- table (accessible alternative) --------------------------------------
  function buildTable(ind) {
    var wrap = h("div", "table-wrap");
    var t = h("table", "data");
    var cap = h("caption", null, ind.name + " — " + ind.unit);
    t.appendChild(cap);
    var thead = h("thead"); var tr = h("tr");
    tr.appendChild(h("th", null, "Date")); tr.appendChild(h("th", null, "Value (" + ind.unit + ")"));
    thead.appendChild(tr); t.appendChild(thead);
    var tb = h("tbody");
    // most recent first, cap rows for readability
    var rows = ind.points.slice().reverse().slice(0, 36);
    rows.forEach(function (p) {
      var r = h("tr");
      r.appendChild(h("td", null, fmtFullDate(parseDate(p.d))));
      r.appendChild(h("td", null, fmtNum(p.v, ind.decimals)));
      tb.appendChild(r);
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    if (ind.points.length > 36) wrap.appendChild(h("p", "hint", "Showing 36 most recent of " + ind.points.length + " observations."));
    return wrap;
  }

  // ---- boot ----------------------------------------------------------------
  function boot() {
    // meta line
    document.getElementById("gen-date").textContent = fmtFullDate(parseDate(DATA.generated));
    var span = DATA.indicators[0].range;
    document.getElementById("range-line").textContent = span.from.slice(0, 4) + "–" + DATA.indicators.reduce(function (m, i) { return i.range.to > m ? i.range.to : m; }, "0").slice(0, 4);

    // group indicators into category sections (order = first appearance)
    var host = document.getElementById("sections");
    var order = [], groups = {};
    DATA.indicators.forEach(function (ind) {
      if (!groups[ind.cat]) { groups[ind.cat] = []; order.push(ind.cat); }
      groups[ind.cat].push(ind);
    });
    order.forEach(function (cat) {
      var list = groups[cat];
      var sec = h("section", "section");
      var shead = h("div", "section-head");
      shead.appendChild(h("h2", "section-title", cat));
      shead.appendChild(h("span", "section-count", list.length + (list.length > 1 ? " indicators" : " indicator")));
      sec.appendChild(shead);
      var grid = h("div", "grid");
      list.forEach(function (ind) { grid.appendChild(buildCard(ind)); });
      sec.appendChild(grid);
      host.appendChild(sec);
    });

    // view toggle
    var views = document.querySelectorAll("#view-toggle button");
    views.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.dataset.view;
        views.forEach(function (b) { b.setAttribute("aria-pressed", b === btn); });
        document.querySelectorAll(".view-chart").forEach(function (n) { n.classList.toggle("hidden", mode !== "chart"); });
        document.querySelectorAll(".view-table").forEach(function (n) { n.classList.toggle("hidden", mode !== "table"); });
      });
    });

    // theme toggle
    var order = ["auto", "light", "dark"];
    var tbtn = document.getElementById("theme-btn");
    var cur = 0;
    function apply() {
      var m = order[cur];
      if (m === "auto") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", m);
      tbtn.textContent = "Theme: " + m.charAt(0).toUpperCase() + m.slice(1);
    }
    tbtn.addEventListener("click", function () { cur = (cur + 1) % order.length; apply(); });
    apply();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();

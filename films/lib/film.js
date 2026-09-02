/* films/lib/film.js — the deterministic film runtime.
 *
 * A film is a pure function of time. It declares its metadata, reads its
 * numbers from films/data/facts.json (never retyped), and draws frame t onto a
 * canvas. The renderer drives window.__film.seek(t) and captures pixels; the
 * browser preview merely plays that same function on a clock.
 *
 * Query parameters
 *   capture=1        no playback; the host seeks
 *   format=master    1920×1080 (default) | vertical 1080×1920 | square 1080×1080
 *   t=12.5           preview a single moment
 *   guides=1         draw safe areas (never in a capture)
 */
(function () {
  'use strict';

  const Q = new URLSearchParams(location.search);
  const CAPTURE = Q.get('capture') === '1';
  const FORMATS = { master: [1920, 1080], vertical: [1080, 1920], square: [1080, 1080] };
  const FORMAT = FORMATS[Q.get('format')] ? Q.get('format') : 'master';

  const TOK = {
    bg: '#0B0F0A', surface: '#11150F', ink: '#EDE8DA', muted: '#9AA391',
    gold: '#C9A15E', evidence: '#7FC4CF', review: '#E9A23B', invalid: '#E4796F',
    line: '#232A20', lineStrong: '#39422F', paper: '#EDE8DA', paperInk: '#14170F',
    paperLine: '#C2BAA2', paperMuted: '#565E4E'
  };
  const FONT = { serif: "'Fraunces'", sans: "'Instrument Sans'", mono: "'Fragment Mono'" };

  /* ---- pure helpers ---------------------------------------------------- */
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const k = (t, a, b) => clamp((t - a) / (b - a), 0, 1);
  const eo3 = u => 1 - Math.pow(1 - u, 3);
  const eo5 = u => 1 - Math.pow(1 - u, 5);
  const ei3 = u => u * u * u;
  const eio = u => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
  const lerp = (a, b, u) => a + (b - a) * u;
  const sm = (t, a, b, e) => (e || eio)(k(t, a, b));
  // visible window with fade in (fi) and fade out (fo); 0 outside [a,b]
  const win = (t, a, b, fi, fo) => sm(t, a, a + (fi == null ? 0.4 : fi)) * (1 - sm(t, b - (fo == null ? 0.4 : fo), b));
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function shuffled(arr, seed) {
    const r = mulberry32(seed), a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }
  const pct = (x, d) => (100 * x).toFixed(d == null ? 0 : d) + '%';
  const hexA = (hex, a) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  };

  /* ---- state ---------------------------------------------------------- */
  const FILM = { meta: null, facts: null, spec: null, L: null, overflows: [], ready: false, used: new Set() };
  let cv, g;

  function fontString(o) {
    const fam = FONT[o.font || 'sans'];
    return `${o.style || ''} ${o.weight || 400} ${o.size}px ${fam}`.trim();
  }

  /* text with overflow accounting; returns width drawn */
  function text(ctx, s, x, y, o) {
    o = o || {};
    s = String(s);
    ctx.save();
    ctx.font = fontString(o);
    ctx.fillStyle = o.color || TOK.ink;
    ctx.textAlign = o.align || 'left';
    ctx.textBaseline = o.baseline || 'alphabetic';
    if (o.alpha != null) ctx.globalAlpha *= clamp(o.alpha, 0, 1);
    let w;
    if (o.track) {
      const tr = o.track * o.size;
      const widths = [...s].map(ch => ctx.measureText(ch).width);
      w = widths.reduce((a, b) => a + b, 0) + tr * (widths.length - 1);
      let x0 = x;
      if (ctx.textAlign === 'center') x0 = x - w / 2;
      else if (ctx.textAlign === 'right') x0 = x - w;
      ctx.textAlign = 'left';
      [...s].forEach((ch, i) => { ctx.fillText(ch, x0, y); x0 += widths[i] + tr; });
    } else {
      w = ctx.measureText(s).width;
      ctx.fillText(s, x, y);
    }
    ctx.restore();
    if (o.maxW && w > o.maxW + 0.5 && (o.alpha == null || o.alpha > 0.01)) {
      FILM.overflows.push({ text: s, width: Math.round(w), maxW: Math.round(o.maxW) });
    }
    return w;
  }
  function measure(ctx, s, o) { ctx.save(); ctx.font = fontString(o); const w = ctx.measureText(String(s)).width; ctx.restore(); return w; }
  /* word-wrap into lines that fit maxW */
  function wrap(ctx, s, maxW, o) {
    const words = String(s).split(/\s+/), lines = []; let cur = '';
    for (const w of words) {
      const trial = cur ? cur + ' ' + w : w;
      if (measure(ctx, trial, o) <= maxW || !cur) cur = trial; else { lines.push(cur); cur = w; }
    }
    if (cur) lines.push(cur);
    return lines;
  }
  function paragraph(ctx, s, x, y, o) {
    const lines = wrap(ctx, s, o.maxW, o), lh = o.lineHeight || o.size * 1.4;
    lines.forEach((ln, i) => text(ctx, ln, x, y + i * lh, Object.assign({}, o, { maxW: o.maxW + 4 })));
    return lines.length * lh;
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function dashRect(ctx, x, y, w, h, color, dash, width) {
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width || 2; ctx.setLineDash(dash || [10, 7]);
    ctx.strokeRect(x, y, w, h); ctx.restore();
  }
  function line(ctx, x0, y0, x1, y1, color, width, dash) {
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width || 1; if (dash) ctx.setLineDash(dash);
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); ctx.restore();
  }
  function disc(ctx, x, y, r, color, alpha) {
    ctx.save(); if (alpha != null) ctx.globalAlpha *= alpha; ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }
  function ring(ctx, x, y, r, color, width, alpha) {
    ctx.save(); if (alpha != null) ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = width || 2;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  }
  /* a kicker: short gold rule + mono label — the site's own idiom */
  function kicker(ctx, s, x, y, o) {
    o = o || {}; const size = o.size || 20, color = o.color || TOK.gold;
    ctx.save(); if (o.alpha != null) ctx.globalAlpha *= clamp(o.alpha, 0, 1);
    line(ctx, x, y - size * 0.35, x + size * 1.8, y - size * 0.35, color, 2);
    text(ctx, s, x + size * 2.6, y, { font: 'mono', size, color, track: 0.08, maxW: o.maxW });
    ctx.restore();
  }
  /* a rubber stamp: rotated boxed mono label */
  function stamp(ctx, s, x, y, o) {
    o = o || {}; const size = o.size || 22, color = o.color || TOK.review, ang = o.angle == null ? -0.06 : o.angle;
    ctx.save(); if (o.alpha != null) ctx.globalAlpha *= clamp(o.alpha, 0, 1);
    ctx.translate(x, y); ctx.rotate(ang);
    const w = measure(ctx, s, { font: 'mono', size }) + size * 1.2, h = size * 1.9;
    ctx.strokeStyle = color; ctx.lineWidth = Math.max(2, size * 0.12); ctx.strokeRect(-w / 2, -h / 2, w, h);
    text(ctx, s, 0, size * 0.36, { font: 'mono', size, color, align: 'center' });
    ctx.restore();
    return w;
  }
  /* the locator line every factual film ends on: claim ids + reproduction command */
  function locator(ctx, L, lines, alpha) {
    if (alpha <= 0.001) return;
    const size = Math.round(L.u * 20), maxW = L.W - 2 * L.m;
    // each declared line wraps to the frame; the last declared line (the URL) is gold
    const out = [];
    lines.forEach((s, i) => wrap(ctx, s, maxW, { font: 'mono', size }).forEach(ln => out.push([ln, i === lines.length - 1])));
    const y0 = L.H - L.m - (out.length - 1) * size * 1.7;
    out.forEach(([s, gold], i) => text(ctx, s, L.cx, y0 + i * size * 1.7, {
      font: 'mono', size, color: gold ? TOK.gold : TOK.muted, align: 'center', alpha, maxW: maxW + 4
    }));
  }
  /* the object ledger strip: what kind of thing is on screen */
  function ledgerTag(ctx, L, kind, note, alpha, side, place) {
    if (alpha <= 0.001) return;
    // master: a right-side tag keeps to 62% of the width so it never crosses a top-left kicker;
    // vertical: the tag sits in a band above the locator, where no film draws content
    const size = Math.round(L.u * 17), maxW = (!L.vertical && side === 'right') ? Math.round((L.W - 2 * L.m) * 0.62) : L.W - 2 * L.m;
    const s = note ? `${kind} · ${note}` : kind;
    const x = side === 'right' && !L.vertical ? L.W - L.m : L.m;
    if (L.vertical) side = 'left';
    // wraps to as many lines as the frame needs; tracking is measured into the wrap
    const o = { font: 'mono', size, track: 0.06 };
    const fits = str => { ctx.save(); ctx.font = fontString(o); const w = [...str].reduce((a, ch) => a + ctx.measureText(ch).width, 0) + o.track * size * (str.length - 1); ctx.restore(); return w <= maxW; };
    const words = s.split(/\s+/), lines = []; let cur = '';
    for (const w of words) { const trial = cur ? cur + ' ' + w : w; if (fits(trial) || !cur) cur = trial; else { lines.push(cur); cur = w; } }
    if (cur) lines.push(cur);
    const y0 = (L.vertical && place !== 'top') ? L.H - L.m - 190 * L.u : L.m + size * 0.2;
    lines.forEach((ln, i) => text(ctx, ln, x, y0 + i * size * 1.5, Object.assign({ color: TOK.muted, align: side === 'right' ? 'right' : 'left', alpha, maxW: maxW + 4 }, o)));
  }

  function layout(W, H) {
    const vertical = H > W, m = Math.round(Math.min(W, H) * 0.06);
    const u = vertical ? W / 1080 : Math.min(W / 1920, H / 1080);
    const L = { W, H, vertical, square: W === H, m, u, cx: W / 2, cy: H / 2, format: FORMAT };
    L.safe = { x: m, y: m, w: W - 2 * m, h: H - 2 * m };
    // the 9:16 centre column a vertical crop of the master would keep
    const sw = vertical ? W : Math.round(H * 9 / 16);
    L.social = { x: Math.round((W - sw) / 2), y: 0, w: sw, h: H };
    return L;
  }

  function guides(ctx, L) {
    ctx.save(); ctx.setLineDash([8, 6]); ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(127,196,207,.6)'; ctx.strokeRect(L.safe.x, L.safe.y, L.safe.w, L.safe.h);
    ctx.strokeStyle = 'rgba(233,162,59,.6)'; ctx.strokeRect(L.social.x, L.social.y, L.social.w, L.social.h);
    ctx.restore();
  }

  /* ---- facts access with usage accounting ------------------------------ */
  function fact(id) {
    const f = FILM.facts.facts[id];
    if (!f) throw new Error(`film reads unbound fact ${id}`);
    FILM.used.add(id);
    return f.value;
  }
  function factKind(id) { const f = FILM.facts.facts[id]; if (!f) throw new Error(`unbound fact ${id}`); return f.kind; }

  /* ---- define ---------------------------------------------------------- */
  async function define(spec) {
    FILM.spec = spec;
    const [W, H] = FORMATS[FORMAT];
    const stage = document.getElementById('stage') || (() => { const d = document.createElement('div'); d.id = 'stage'; document.body.appendChild(d); return d; })();
    stage.style.width = W + 'px'; stage.style.height = H + 'px';
    cv = document.createElement('canvas'); cv.width = W; cv.height = H; stage.appendChild(cv);
    g = cv.getContext('2d', { alpha: false });
    FILM.L = layout(W, H);
    FILM.meta = {
      id: spec.id, title: spec.title, duration: spec.duration, fps: spec.fps || 30,
      format: FORMAT, width: W, height: H, poster_t: spec.poster_t == null ? spec.duration / 2 : spec.poster_t,
      claim_frames: spec.claimFrames || [], facts: []
    };
    // fonts first, so the very first frame is set in the vendored faces
    await Promise.all([
      document.fonts.load("400 20px 'Fraunces'"), document.fonts.load("600 20px 'Fraunces'"),
      document.fonts.load("italic 400 20px 'Fraunces'"),
      document.fonts.load("400 20px 'Instrument Sans'"), document.fonts.load("500 20px 'Instrument Sans'"),
      document.fonts.load("400 20px 'Fragment Mono'")
    ]);
    const res = await fetch(new URL('../data/facts.json', location.href).href);
    if (!res.ok) throw new Error('facts.json not reachable: ' + res.status);
    FILM.facts = await res.json();
    if (spec.setup) spec.setup({ fact, factKind, L: FILM.L, TOK });
    FILM.meta.facts = [...FILM.used].sort();
    FILM.ready = true;
    if (!CAPTURE) preview();
    else seek(Number(Q.get('t') || 0));
  }

  function seek(t) {
    t = clamp(Number(t), 0, FILM.spec.duration);
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.globalAlpha = 1;
    g.fillStyle = TOK.bg; g.fillRect(0, 0, FILM.L.W, FILM.L.H);
    FILM.spec.render(t, g, FILM.L, { fact, factKind, TOK });
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1;
    if (Q.get('guides') === '1' && !CAPTURE) guides(g, FILM.L);
    FILM.t = t;
  }

  function preview() {
    const stage = document.getElementById('stage');
    const fit = () => {
      const s = Math.min(innerWidth / FILM.L.W, innerHeight / FILM.L.H);
      stage.style.transform = `scale(${s})`;
      stage.style.left = ((innerWidth - FILM.L.W * s) / 2) + 'px';
      stage.style.top = ((innerHeight - FILM.L.H * s) / 2) + 'px';
    };
    addEventListener('resize', fit); fit();
    const hud = document.createElement('div'); hud.id = 'hud'; document.body.appendChild(hud);
    if (Q.get('t') != null) { seek(Number(Q.get('t'))); hud.textContent = `${FILM.meta.id} · t=${Q.get('t')}s`; return; }
    let t0 = null;
    const loop = ts => {
      if (t0 === null) t0 = ts;
      const t = (ts - t0) / 1000;
      seek(Math.min(t, FILM.spec.duration));
      hud.textContent = `${FILM.meta.id} · ${t.toFixed(1)}s / ${FILM.spec.duration}s · click to replay`;
      if (t < FILM.spec.duration) requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
    addEventListener('click', () => { t0 = null; requestAnimationFrame(loop); });
  }

  window.Film = {
    define, TOK, FONT,
    H: { clamp, k, eo3, eo5, ei3, eio, lerp, sm, win, mulberry32, shuffled, pct, hexA,
         text, measure, wrap, paragraph, roundRect, dashRect, line, disc, ring, kicker, stamp, locator, ledgerTag }
  };
  window.__film = {
    get ready() { return FILM.ready; },
    get meta() { return FILM.meta; },
    seek,
    overflows() { const o = FILM.overflows.slice(); return o; },
    resetOverflows() { FILM.overflows.length = 0; },
    factsUsed() { return [...FILM.used].sort(); }
  };
})();

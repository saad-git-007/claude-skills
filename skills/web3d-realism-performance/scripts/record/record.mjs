// Deterministic screen recorder for a browser app (WebGL included): frame-exact video on a slow or shared GPU.
//
//   node record.mjs --script clip.mjs --out frames [--base http://127.0.0.1:4173] [--fps 30] [--w 1920 --h 1080]
//                   [--dsf 2] [--limit seconds] [--shots 1.5,4] [--nosave]
//
// How it works: after the page has loaded, rAF, performance.now, Date.now, setTimeout/setInterval and every running CSS /
// Web Animations animation are driven by ONE virtual clock that advances exactly 1/fps per output frame. After each step
// the frame is screenshotted. Render speed therefore only changes how long the recording takes, never how it looks:
// no dropped frames, no dt spikes, UI transitions and canvas motion stay in step. (CDP Page.startScreencast and
// real-time screen grabs record whatever the GPU managed, which on an iGPU at 1080p is 13-30 fps with jitter.)
//
// Headless Chrome draws no mouse pointer, so a fake one (arrow + click ripple) is injected. Mouse events are still
// real CDP input events, so :hover states, clicks, drags and wheel handlers behave exactly as for a person.
//
// clip.mjs default-exports the shot list (all times in seconds of video):
//   {
//     duration: 20,
//     url: '/?quality=high',                       // appended to --base
//     ready: 'window.__ready === true',            // expression that is true once the first frames are drawn
//     loaderGone: '.loader.off',                   // optional CSS selector to wait for (loading screen finished)
//     settleMs: 3000,                              // real time to wait after that, before the virtual clock starts
//     hide: '.fps-overlay',                        // optional CSS to hide things
//     async setup(page) {},                        // runs once after ready (define window helpers, hide UI, ...)
//     async start(page) {},                        // runs right when the virtual clock starts (reset an intro to t=0, ...)
//     cursor: [{ t: 0, at: [1500, 900] }, { t: 2, at: '.button' }, { t: 3, at: { call: 'pickMarker', arg: 'Peak', aim: '.dot' } }],
//     events: [{ kind: 'click', t: 2.1 }, { kind: 'down', t: 4 }, { kind: 'up', t: 5 },
//              { kind: 'wheel', t: 6, t1: 7, dy: -600 }, { kind: 'eval', t: 1, fn: (a) => {...}, args: [1] },
//              { kind: 'fn', t: 1, fn: async page => {} }],
//     zoom: [{ t: 0, z: 1 }, { t: 2, z: 2.4, at: '.toolbar' }, { t: 4, z: 1 }],   // punch-in on an element (crops the screenshot)
//     async frame(page, T, frameIndex) {},         // per-frame hook, e.g. drive a free camera along a path
//   }
// `at` targets: [x, y] | 'css selector' | { sel, aim } | { call: 'windowFnName', arg, aim } (window fn returns an Element;
// aim = child selector whose centre to use). A target re-resolves every frame, so the pointer follows things that move.
// Cursor keys ease between each other (smoothstep-in-out; `linear: true` for drags); two equal consecutive targets =
// dwell while following the target. Render the UI at dsf 2-3 and crop: zoomed text stays sharp.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const A = process.argv.slice(2);
const opt = (k, d) => { const i = A.indexOf('--' + k); return i >= 0 ? A[i + 1] : d; };
const FPS = +opt('fps', 30), W = +opt('w', 1920), H = +opt('h', 1080), DSF = +opt('dsf', 1);
const BASE = opt('base', 'http://127.0.0.1:4173'), OUT = opt('out', './frames');
const LIMIT = +opt('limit', 0), NOSAVE = A.includes('--nosave');
const SHOTS = opt('shots', '').split(',').filter(Boolean).map(Number);
const script = (await import(pathToFileURL(path.resolve(opt('script'))).href)).default;

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME || '/usr/bin/google-chrome', headless: 'new', protocolTimeout: 1800000, defaultViewport: null,
  args: ['--use-gl=angle', '--use-angle=gl-egl', '--enable-gpu', '--ignore-gpu-blocklist', '--no-sandbox', `--window-size=${W},${H}`, '--hide-scrollbars'],
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: DSF });
page.on('pageerror', e => console.log('pageerror', String(e).slice(0, 300)));
page.on('console', m => { if (m.type() === 'error') console.log('console.error', m.text().slice(0, 200)); });

// ---- refuse to record on a software renderer: it "works" but never finishes loading a real scene (see preflight/gpu-check.mjs)
const gl = await page.evaluate(() => { const g = document.createElement('canvas').getContext('webgl2'); const e = g?.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'no webgl2'; });
console.log('renderer:', gl);
if (/llvmpipe|swiftshader|software|no webgl2/i.test(gl)) { console.error('Software rendering: fix GPU access first (scripts/preflight/gpu-check.mjs).'); await browser.close(); process.exit(2); }

await page.evaluateOnNewDocument(() => {
  const realRAF = window.requestAnimationFrame.bind(window), realCAF = window.cancelAnimationFrame.bind(window);
  const realNow = performance.now.bind(performance), realDate = Date.now.bind(Date);
  const realST = window.setTimeout.bind(window), realCT = window.clearTimeout.bind(window);
  const realSI = window.setInterval.bind(window), realCI = window.clearInterval.bind(window);
  let virt = false, vt = 0, date0 = 0, id = 1e9;
  const rafQ = [], timers = new Map();
  window.__realRAF = realRAF;
  performance.now = () => (virt ? vt : realNow());
  Date.now = () => (virt ? date0 + vt : realDate());
  window.requestAnimationFrame = cb => { if (!virt) return realRAF(cb); rafQ.push({ id: ++id, cb }); return id; };
  window.cancelAnimationFrame = i => { const k = rafQ.findIndex(r => r.id === i); if (k >= 0) rafQ.splice(k, 1); else realCAF(i); };
  window.setTimeout = (fn, ms = 0, ...a) => { if (!virt || typeof fn !== 'function') return realST(fn, ms, ...a); timers.set(++id, { fn, due: vt + Math.max(0, +ms || 0), a, every: 0 }); return id; };
  window.setInterval = (fn, ms = 0, ...a) => { if (!virt || typeof fn !== 'function') return realSI(fn, ms, ...a); const e = Math.max(1, +ms || 1); timers.set(++id, { fn, due: vt + e, a, every: e }); return id; };
  window.clearTimeout = i => { if (timers.has(i)) timers.delete(i); else realCT(i); };
  window.clearInterval = i => { if (timers.has(i)) timers.delete(i); else realCI(i); };

  // Take over every running CSS / WAAPI animation: pause it and set currentTime from the virtual clock each step.
  // (Animations paused by the page itself are left alone; finished ones are finish()ed so their promises resolve.)
  const track = new WeakMap(), ignore = new WeakSet();
  function sync(tBase) {
    for (const a of document.getAnimations()) {
      if (ignore.has(a)) continue;
      const ps = a.playState; let s = track.get(a);
      if (s && ps === 'paused' && s.rate === a.playbackRate) {
        const ct = s.base + (vt - s.t0) * s.rate, end = a.effect ? a.effect.getComputedTiming().endTime : Infinity;
        if ((s.rate > 0 && ct >= end) || (s.rate < 0 && ct <= 0)) { a.finish(); track.delete(a); } else a.currentTime = ct;
        continue;
      }
      if (ps === 'finished' || ps === 'idle') continue;
      if (ps === 'paused' && !s) { ignore.add(a); continue; }
      s = { t0: tBase, base: +a.currentTime || 0, rate: a.playbackRate }; track.set(a, s); a.pause();
      const ct = s.base + (vt - s.t0) * s.rate; if (ct !== s.base) a.currentTime = ct;
    }
  }
  function runTimers() {
    for (let g = 0; g < 1000; g++) {
      let best = null, bid = 0;
      for (const [i, t] of timers) if (t.due <= vt && (!best || t.due < best.due)) { best = t; bid = i; }
      if (!best) return;
      if (best.every) best.due += best.every; else timers.delete(bid);
      try { best.fn(...best.a); } catch (e) { console.error(e); }
    }
  }
  window.__virtOn = () => { vt = realNow(); date0 = realDate() - vt; virt = true; };
  window.__vstep = ms => {
    const prev = vt; vt += ms;
    runTimers(); sync(prev);                                   // timers, then animations, then rAF: the browser's own order
    for (const r of rafQ.splice(0)) { try { r.cb(vt); } catch (e) { console.error(e); } }
    sync(vt);                                                  // animations created by the callbacks start paused at 0
  };
  window.__vt = () => vt;

  // ---- fake pointer + click ripple
  window.__cursor = { x: -100, y: -100, el: null };
  window.__cur = (x, y, down) => {
    let c = window.__cursor.el;
    if (!c) {
      c = document.createElement('div');
      c.style.cssText = 'position:fixed;left:0;top:0;width:32px;height:32px;z-index:2147483647;pointer-events:none;will-change:transform;transform-origin:4px 3px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.45))';
      c.innerHTML = '<svg width="32" height="32" viewBox="0 0 32 32"><path d="M5 3 L5 24 L10.4 19.2 L14 27.4 L17.6 25.8 L14 17.8 L21.4 17.6 Z" fill="#fff" stroke="#1b1b1f" stroke-width="1.6" stroke-linejoin="round"/></svg>';
      document.body.appendChild(c); window.__cursor.el = c;
    }
    window.__cursor.x = x; window.__cursor.y = y;
    c.style.transform = `translate(${x - 4}px,${y - 3}px) scale(${down ? 0.86 : 1})`;
  };
  window.__ripple = (x, y) => {
    const r = document.createElement('div');
    r.style.cssText = `position:fixed;left:${x - 26}px;top:${y - 26}px;width:52px;height:52px;border-radius:50%;z-index:2147483646;pointer-events:none;border:3px solid rgba(255,255,255,.95);box-shadow:0 0 14px rgba(255,255,255,.5)`;
    document.body.appendChild(r);
    r.animate([{ transform: 'scale(.25)', opacity: 0.95 }, { transform: 'scale(1)', opacity: 0 }], { duration: 520, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'forwards' }).finished.then(() => r.remove());
  };
});

// ------------------------------------------------------------------ load
const t0 = Date.now(), L = m => console.log(((Date.now() - t0) / 1000).toFixed(1) + 's', m);
await page.goto(BASE + (script.url || '/'), { waitUntil: 'domcontentloaded', timeout: 900000 });
await page.waitForFunction(script.ready || 'true', { timeout: 1500000, polling: 500 });
L('ready');
if (script.hide) await page.addStyleTag({ content: `${script.hide}{display:none!important}` });
if (script.setup) await script.setup(page);
if (script.loaderGone) await page.waitForSelector(script.loaderGone, { timeout: 120000 }).catch(() => L('loader wait timed out'));
await new Promise(r => setTimeout(r, script.settleMs ?? 3000));
await page.evaluate(() => window.__virtOn());
if (script.start) await script.start(page);
await new Promise(r => setTimeout(r, 400));                    // let already-scheduled real callbacks drain into the virtual queue

// ------------------------------------------------------------------ timeline
const total = LIMIT || script.duration, nFrames = Math.round(total * FPS), dtMs = 1000 / FPS;
const ease = u => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
const easeIO = u => (u <= 0 ? 0 : u >= 1 ? 1 : u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);

const resolve = async tgt => {
  if (Array.isArray(tgt)) return tgt;
  if (typeof tgt === 'function') return await tgt(page);
  const spec = typeof tgt === 'string' ? { sel: tgt } : tgt;
  return page.evaluate(s => {
    const el = s.call ? window[s.call]?.(s.arg) : document.querySelector(s.sel);
    if (!el) return null;
    const box = (s.aim ? el.querySelector(s.aim) : null) || el, r = box.getBoundingClientRect();
    return r.width || r.height ? [r.left + r.width / 2, r.top + r.height / 2] : null;
  }, spec);
};

const keys = script.cursor.map(k => ({ ...k, pos: null }));
const zkeys = (script.zoom || [{ t: 0, z: 1 }]).map(k => ({ ...k, pos: null }));
const events = script.events.map(e => ({ ...e, done: false }));
let cursorPos = null, lastSent = null, down = false;

async function placeCursor(T) {
  let i = keys.findIndex(k => k.t >= T); if (i < 0) i = keys.length - 1;
  const k1 = keys[i]; let p;
  if (i === 0) p = await resolve(k1.at);
  else {
    const k0 = keys[i - 1];
    if (k0.at === k1.at && !Array.isArray(k1.at)) {             // dwell: keep following a moving target
      const q = await resolve(k1.at); if (q) { if (T >= k1.t && !k1.pos) k1.pos = q; p = q; }
    }
    if (!p) {
      const p0 = k0.pos || await resolve(k0.at) || cursorPos, p1 = await resolve(k1.at) || p0;
      const u = (T - k0.t) / Math.max(1e-6, k1.t - k0.t), e = k1.linear ? Math.min(1, Math.max(0, u)) : easeIO(u);
      p = [p0[0] + (p1[0] - p0[0]) * e, p0[1] + (p1[1] - p0[1]) * e];
      if (T >= k1.t && !k1.pos) k1.pos = p1;
    }
  }
  if (!p) return;
  cursorPos = p;
  if (!lastSent || Math.abs(lastSent[0] - p[0]) > 0.05 || Math.abs(lastSent[1] - p[1]) > 0.05) { await page.mouse.move(p[0], p[1]); lastSent = p; }
  await page.evaluate((x, y, d) => window.__cur(x, y, d), p[0], p[1], down);
}

async function runEvents(T, prevT) {
  for (const e of events) {
    if (e.kind === 'wheel') {                                   // spread dy over [t, t1] with a smoothstep profile
      const a = Math.max(prevT, e.t), b = Math.min(T, e.t1);
      if (b > a) { const dy = e.dy * (ease((b - e.t) / (e.t1 - e.t)) - ease((a - e.t) / (e.t1 - e.t))); if (Math.abs(dy) > 0.01) await page.mouse.wheel({ deltaY: dy }); }
      continue;
    }
    if (e.done || T + 1e-9 < e.t) continue;
    e.done = true;
    if (e.kind === 'down') { if (cursorPos) await page.evaluate((x, y) => window.__ripple(x, y), cursorPos[0], cursorPos[1]); await page.mouse.down(); down = true; }
    else if (e.kind === 'up') { await page.mouse.up(); down = false; }
    else if (e.kind === 'click') {                              // press+release in ONE frame: a target that moves between the two would miss
      if (cursorPos) { await page.evaluate((x, y) => window.__ripple(x, y), cursorPos[0], cursorPos[1]); await page.mouse.click(cursorPos[0], cursorPos[1]); }
    } else if (e.kind === 'eval') await page.evaluate(e.fn, ...(e.args || []));
    else if (e.kind === 'fn') await e.fn(page);
  }
}

async function zoomAt(T) {                                      // -> { z, cx, cy }
  const c = async k => (k.at ? await resolve(k.at) : null) || [W / 2, H / 2];
  let i = zkeys.findIndex(k => k.t >= T);
  if (i < 0) { const k = zkeys[zkeys.length - 1]; return { z: k.z, cx: (await c(k))[0], cy: (await c(k))[1] }; }
  const k1 = zkeys[i];
  if (i === 0) { const p = await c(k1); return { z: k1.z, cx: p[0], cy: p[1] }; }
  const k0 = zkeys[i - 1], e = easeIO((T - k0.t) / Math.max(1e-6, k1.t - k0.t));
  const p0 = k0.pos || (k0.pos = await c(k0)), p1 = k1.at ? await c(k1) : p0;   // a key without a target keeps the centre
  return { z: k0.z + (k1.z - k0.z) * e, cx: p0[0] + (p1[0] - p0[0]) * e, cy: p0[1] + (p1[1] - p0[1]) * e };
}
const clipFor = ({ z, cx, cy }) => z < 1.002 ? undefined : (w => (h => ({ x: Math.min(W - w, Math.max(0, cx - w / 2)), y: Math.min(H - h, Math.max(0, cy - h / 2)), width: w, height: h, scale: z }))(H / z))(W / z);

fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(OUT, { recursive: true });
const tStart = Date.now(); let prevT = -1 / FPS;
for (let f = 0; f < nFrames; f++) {
  const T = f / FPS;
  if (script.frame) await script.frame(page, T, f);
  await placeCursor(T);
  await runEvents(T, prevT);
  await page.evaluate(ms => window.__vstep(ms), dtMs);
  await page.evaluate(() => new Promise(r => window.__realRAF(() => window.__realRAF(r))));   // let the compositor present it
  const clip = clipFor(await zoomAt(T));
  if (!NOSAVE) await page.screenshot({ path: `${OUT}/f${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 95, captureBeyondViewport: false, ...(clip ? { clip } : {}) });
  if (SHOTS.some(s => Math.abs(s - T) < 0.5 / FPS)) await page.screenshot({ path: `${OUT}/shot_${T.toFixed(2)}.png`, captureBeyondViewport: false, ...(clip ? { clip } : {}) });
  prevT = T;
  if (f % 60 === 0) L(`frame ${f}/${nFrames} T=${T.toFixed(2)}s  ${((Date.now() - tStart) / 1000 / (f + 1)).toFixed(2)} s/frame`);
}
L('done');
await browser.close();

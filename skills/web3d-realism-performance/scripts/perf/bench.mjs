// Frame-time benchmark of the 3D lab on the GPU (Chrome, ANGLE on EGL), with lossless screenshots for the visual diff.
//   Template from a three.js project: expects window.__lab = { frame, camera, controls, seek, hold, renderer, callbacks,
//   state.ready }; adapt the hooks and the pose list. Start the app (npm run dev or any server), then
//   BASE=http://127.0.0.1:5173 env -u DISPLAY node scripts/perf/bench.mjs <outdir> [rounds=2]   (QUERY=baked=0 adds ?baked=0)
// Every ambient motion is pinned at t = 40 s and the flight frozen at fixed times, so two runs of the same code give
// identical images. For each pose the lab's own frame() runs with the render forced, then a 1-pixel readPixels waits
// for the GPU: cpu = frame() on the main thread (app update + three.js submission), total = until the GPU has finished.
// Medians of 40 frames after 6 warm-up frames; rounds repeat the pose list and are averaged. Writes <outdir>/bench.json
// and <outdir>/<pose>.png. Needs a GPU: with software WebGL the numbers mean nothing.
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
const require = createRequire(new URL('../../package.json', import.meta.url));
const { chromium } = require('playwright');
const [out, roundsArg] = process.argv.slice(2);
const BASE = process.env.BASE || 'http://127.0.0.1:5173', rounds = Number(roundsArg || 2);
const W = Number(process.env.W || 1920), H = Number(process.env.H || 1080);
// Flight times (tour, frozen) and explore poses: orbit from the sea and the west, out of the front, over the canopy.
const explore = {
  oSea: { p: [0, 7, -36], target: [0, 1.2, 0] }, oWest: { p: [-33, 6, -17], target: [0, 1.2, 0] },
  fLand: { p: [0, 3.2, 6], target: [0, 3.7, 40] }, fHigh: { p: [0, 28, -14], target: [0, 22.98, 19.63] },
};
const poses = process.env.POSES ? process.env.POSES.split(',') : ['t0.5', 't2.0', 't3.4', 't4.8', 't7', 't13', 't19', 't24.5', 't30', 'oSea', 'oWest', 'fLand', 'fHigh'];
mkdirSync(out, { recursive: true });
const t0 = Date.now();
const browser = await chromium.launch({ headless: true, ...(existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {}), args: ['--no-sandbox', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--enable-gpu'] });
const page = await (await browser.newContext({ viewport: { width: W, height: H } })).newPage();
page.on('pageerror', e => console.log('pageerror', e.message));
await page.goto(`${BASE}/${process.env.QUERY ? '?' + process.env.QUERY : ''}`);
await page.waitForFunction(() => window.__lab && window.__lab.state.ready, null, { timeout: 300000 });
const ready = (Date.now() - t0) / 1000;
await page.addStyleTag({ content: '.site-header,.intro-copy,.bottom-dock,.zone-nav,.scene-label,.hotspots,.world-shade,.loading-badge,.ambient-grain,.lab-entry,.part-position,.pin-position,.hotspot{visibility:hidden!important}' });
await page.evaluate(() => { const l = window.__lab; l.hold(true); l.callbacks.forEach(f => f(40)); l.camera.clearViewOffset(); l.camera.updateProjectionMatrix(); });
const frameAt = shot => page.evaluate(shot => {
  const l = window.__lab;
  if (shot.t !== undefined) { l.seek(shot.t); l.hold(true); }
  else { l.transition = undefined; l.state.mode = 'explore'; Object.assign(l.controls, { maxDistance: 400, minDistance: 0, minPolarAngle: 0, maxPolarAngle: Math.PI }); l.camera.position.set(...shot.p); l.controls.target.set(...shot.target); l.controls.update(); l.camera.lookAt(...shot.target); }
  l.camera.clearViewOffset(); l.camera.updateProjectionMatrix(); l.lastPaint = 0; l.dirty = true;
}, shot).then(() => page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r))))));
const res = {};
try {
  for (let r = 0; r < rounds; r++) for (const name of poses) {
    await frameAt(name.startsWith('t') ? { t: Number(name.slice(1)) } : explore[name]);
    const m = await page.evaluate(({ warm, n }) => {
      const l = window.__lab, gl = l.renderer.getContext(), px = new Uint8Array(4);
      const one = () => { cancelAnimationFrame(l.animation); l.lastPaint = 0; l.dirty = true; const a = performance.now(); l.frame(a); cancelAnimationFrame(l.animation); const b = performance.now(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); return [b - a, performance.now() - a]; };
      for (let i = 0; i < warm; i++) one();
      const cpu = [], tot = []; for (let i = 0; i < n; i++) { const [x, y] = one(); cpu.push(x); tot.push(y); }
      l.animation = requestAnimationFrame(l.frame);
      const med = a => { const s = [...a].sort((p, q) => p - q); return s[s.length >> 1]; };
      return { cpu: med(cpu), total: med(tot), calls: l.renderer.info.render.calls, tris: l.renderer.info.render.triangles };
    }, { warm: 6, n: 40 });
    if (r === 0) { await page.evaluate(() => new Promise(q => requestAnimationFrame(() => requestAnimationFrame(q)))); await page.screenshot({ path: `${out}/${name}.png` }); }
    (res[name] ??= []).push(m);
  }
} finally { await browser.close(); }
const avg = k => a => a.reduce((s, x) => s + x[k], 0) / a.length;
const perPose = Object.fromEntries(Object.entries(res).map(([k, a]) => [k, { cpu: +avg('cpu')(a).toFixed(3), total: +avg('total')(a).toFixed(3), calls: a[0].calls, tris: a[0].tris }]));
const vals = Object.values(perPose), mean = k => +(vals.reduce((s, x) => s + x[k], 0) / vals.length).toFixed(3);
const summary = { when: new Date().toISOString(), W, H, rounds, readySeconds: ready, frameMs: mean('total'), cpuMs: mean('cpu'), gpuMs: +(mean('total') - mean('cpu')).toFixed(3), perPose };
writeFileSync(`${out}/bench.json`, JSON.stringify(summary, null, 1));
console.log(JSON.stringify({ frameMs: summary.frameMs, cpuMs: summary.cpuMs, gpuMs: summary.gpuMs, readySeconds: ready }));

// Lightmap step 1 of 3: export the lab as Cycles will see it.
//   npm run dev   (in another terminal), then
//   TMPDIR=/dev/shm node scripts/lightmap/export.mjs <workdir> [base-url]
// Opens the lab in headless Chrome, lets it load, puts it in its explore state (doors and roof open) and writes
// <workdir>/scene.json + scene.bin: every visible mesh in world space, tagged as a lightmap `target` (the list
// CommandWorld.lightmapTargets() returns, so the runtime finds the same meshes), an `emitter` (screens, light strips)
// or an `occluder` (models, plants, everything else that blocks or bounces light), with its material and the lights.
// Target geometry keeps three.js's own vertex order, which is how the baked second UV set finds its way back.
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const [out, base = 'http://127.0.0.1:5173'] = process.argv.slice(2);
if (!out) { console.error('usage: node scripts/lightmap/export.mjs <workdir> [base-url]'); process.exit(1); }
mkdirSync(out, { recursive: true });
// GPU when there is one (much faster); the export itself does not depend on the renderer.
const browser = await chromium.launch({ headless: true, ...(existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {}), args: ['--no-sandbox', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--enable-gpu'] });
try {
  const page = await (await browser.newContext({ viewport: { width: 800, height: 450 } })).newPage();
  page.on('pageerror', e => console.log('pageerror', e.message));
  // Without the current bake: it rebuilds the targets' geometry, and the new bake must match the code's own.
  await page.goto(base + '/?baked=0');
  await page.waitForFunction(() => window.__lab?.state.ready, null, { timeout: 300000 });
  // Explore mode shows the architecture open (doors in their pockets, roof folded into the eave).
  await page.evaluate(() => window.__lab.go('terminal', true));
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const { json, b64 } = await page.evaluate(() => {
    const l = window.__lab, scene = l.scene;
    scene.updateMatrixWorld(true);
    const list = l.lightmapTargets(), targets = new Set(list);
    const chunks = [], meshes = []; let offset = 0;
    const put = arr => { const at = offset; chunks.push(arr); offset += arr.byteLength; return at; };
    const lin = c => [c.r, c.g, c.b];
    // Average colour of a texture (linear), and its alpha as a small PNG when it has cut-outs.
    const avgCache = new Map();
    const average = tex => {
      if (!tex?.image) return null; if (avgCache.has(tex)) return avgCache.get(tex);
      const c = document.createElement('canvas'); c.width = c.height = 16; const g = c.getContext('2d');
      let v = null;
      try { g.drawImage(tex.image, 0, 0, 16, 16); const d = g.getImageData(0, 0, 16, 16).data; let r = 0, gg = 0, b = 0, a = 0;
        for (let i = 0; i < d.length; i += 4) { const w = d[i + 3] / 255; r += d[i] * w; gg += d[i + 1] * w; b += d[i + 2] * w; a += w; }
        const s2l = x => { x /= 255; return x <= .04045 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); };
        v = a ? (tex.colorSpace === 'srgb' ? [r / a, gg / a, b / a].map(s2l) : [r / a / 255, gg / a / 255, b / a / 255]) : [0, 0, 0];
      } catch { v = null; }
      avgCache.set(tex, v); return v;
    };
    const alphaCache = new Map();
    const alphaPng = tex => {
      if (!tex?.image) return null; if (alphaCache.has(tex)) return alphaCache.get(tex);
      const w = Math.min(512, tex.image.width), h = Math.min(512, tex.image.height), c = document.createElement('canvas'); c.width = w; c.height = h;
      c.getContext('2d').drawImage(tex.image, 0, 0, w, h); const url = c.toDataURL('image/png'); alphaCache.set(tex, url); return url;
    };
    const hidden = o => { for (let p = o; p; p = p.parent) if (!p.visible) return true; return false; };
    const dynamic = o => { for (let p = o; p; p = p.parent) { if (p.userData.bake) return false; if (p.userData.dynamic) return true; } return false; };
    let n = 0;
    scene.traverse(o => {
      if (!o.isMesh || o.isInstancedMesh || hidden(o)) return;
      const m = Array.isArray(o.material) ? o.material[0] : o.material, g = o.geometry, name = o.name || o.parent?.name || '';
      let role = targets.has(o) ? 'target' : 'occluder', mat = null, crop = 0;
      if (name === 'Sky' || name === 'Ocean' || name === 'Clouds' || name.startsWith('Cloud')) return;
      if (name === 'Headland terrain') { crop = 90; mat = { color: [.045, .06, .025], roughness: 1, metalness: 0 }; }
      else if (m.isMeshStandardMaterial) {
        const e = lin(m.emissive).map(x => x * m.emissiveIntensity), em = m.emissiveMap ? average(m.emissiveMap) : null;
        const emission = em ? e.map((x, i) => x * em[i]) : e;
        const tint = m.map ? average(m.map) : null, col = lin(m.color).map((x, i) => x * (tint ? tint[i] : 1));
        mat = { color: col, roughness: m.roughness, metalness: m.metalness, emission, opacity: m.opacity };
        if (role !== 'target' && Math.max(...emission) >= .5) role = 'emitter';
        // Blended without a texture: glass, fluids, and the roof's frame straps (their shader folds them into the eave
        // and fades them out, so their geometry here is the closed roof). Blended with a texture: cut-out leaves.
        if (m.transparent && !(m.map && m.map.image)) return;
        if ((m.transparent || m.alphaTest > 0) && m.map && g.attributes.uv) mat.alpha = alphaPng(m.map);
      } else if (m.isMeshBasicMaterial) {
        // Unlit: opaque ones are displays (the Digital Field); blended ones are effects and the logo decal.
        if (m.transparent) return;
        const tint = m.map ? average(m.map) : [1, 1, 1];
        mat = { color: [0, 0, 0], roughness: 1, metalness: 0, emission: lin(m.color).map((x, i) => x * tint[i]) }; role = 'emitter';
      } else if (m.isShaderMaterial) {
        // The architecture's light lines (uBase x a per-vertex gain) emit; its glass is left out (light passes).
        if (m.transparent || !m.uniforms?.uBase) return;
        const gain = g.attributes.aGain; let k = 1; if (gain) { k = 0; for (let i = 0; i < gain.count; i++) k += gain.getX(i); k /= gain.count; }
        mat = { color: [0, 0, 0], roughness: 1, metalness: 0, emission: [.114, .905, 1].map(x => Math.pow(x, 2.2) * m.uniforms.uBase.value * k) }; role = 'emitter';
      } else return;
      const pos = g.attributes.position, nor = g.attributes.normal, uv = g.attributes.uv, e = o.matrixWorld.elements;
      const inv = o.matrixWorld.clone().invert().transpose().elements; // normals: inverse transpose
      let index = g.index ? Array.from({ length: g.index.count }, (_, i) => g.index.getX(i)) : Array.from({ length: pos.count }, (_, i) => i);
      const P = new Float32Array(pos.count * 3), N = new Float32Array(pos.count * 3);
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        P[i * 3] = e[0] * x + e[4] * y + e[8] * z + e[12]; P[i * 3 + 1] = e[1] * x + e[5] * y + e[9] * z + e[13]; P[i * 3 + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
        if (nor) { const a = nor.getX(i), b = nor.getY(i), c = nor.getZ(i); let u = inv[0] * a + inv[4] * b + inv[8] * c, v = inv[1] * a + inv[5] * b + inv[9] * c, w = inv[2] * a + inv[6] * b + inv[10] * c; const L = Math.hypot(u, v, w) || 1; N[i * 3] = u / L; N[i * 3 + 1] = v / L; N[i * 3 + 2] = w / L; }
      }
      if (crop) { const keep = []; for (let t = 0; t < index.length; t += 3) { let ok = true; for (let k = 0; k < 3; k++) { const j = index[t + k]; if (Math.hypot(P[j * 3], P[j * 3 + 2]) > crop) ok = false; } if (ok) keep.push(index[t], index[t + 1], index[t + 2]); } index = keep; }
      if (!index.length) return;
      const rec = { id: n++, name: name.slice(0, 80), role, material: mat, doubleSided: m.side === 2, vertices: pos.count, triangles: index.length / 3,
        position: put(P), normal: nor ? put(N) : -1, index: put(new Uint32Array(index)) };
      if (mat.alpha && uv) { const U = new Float32Array(uv.count * 2); for (let i = 0; i < uv.count; i++) { U[i * 2] = uv.getX(i); U[i * 2 + 1] = uv.getY(i); } rec.uv = put(U); }
      if (role === 'target') { rec.target = list.indexOf(o); rec.sig = l.lightmapSignature(o); }
      meshes.push(rec);
    });
    const lights = [];
    scene.traverse(o => {
      if (!o.isLight || hidden(o)) return; const p = o.getWorldPosition(new o.position.constructor());
      const rec = { type: o.type, position: p.toArray(), color: lin(o.color), intensity: o.intensity };
      if (o.isPointLight) Object.assign(rec, { distance: o.distance, decay: o.decay });
      if (o.isDirectionalLight) rec.target = o.target.getWorldPosition(new o.position.constructor()).toArray();
      if (o.isHemisphereLight) rec.ground = lin(o.groundColor);
      lights.push(rec);
    });
    const buf = new Uint8Array(offset); let at = 0; for (const c of chunks) { buf.set(new Uint8Array(c.buffer, c.byteOffset, c.byteLength), at); at += c.byteLength; }
    let s = ''; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return { json: { meshes, lights, targets: targets.size }, b64: btoa(s) };
  });
  writeFileSync(join(out, 'scene.bin'), Buffer.from(b64, 'base64'));
  writeFileSync(join(out, 'scene.json'), JSON.stringify(json));
  const count = r => json.meshes.filter(m => m.role === r);
  for (const r of ['target', 'emitter', 'occluder']) console.log(r, count(r).length, 'meshes', count(r).reduce((a, m) => a + m.triangles, 0), 'triangles');
  console.log('lights', json.lights.length, 'targets listed', json.targets);
} finally { await browser.close(); }

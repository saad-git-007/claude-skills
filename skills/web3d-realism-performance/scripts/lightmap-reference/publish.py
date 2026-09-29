#!/usr/bin/env python3
"""Lightmap step 3 of 3: encode the bake for the browser.

usage: publish.py <workdir> [repo]      (repo defaults to the current directory)
Reads <workdir>/natural-<a>.npy, lamps-<a>.npy, ao-<a>.npy (bake.py), uv2.json and scene.json (export.mjs). Writes
  public/assets/lightmaps/natural-<a>-<hash>.webp, lamps-...webp (2048, and -1k at 1024), ao-...webp (1024),
  public/assets/lightmaps/uv2-<hash>.bin   gzip; per target: source vertex per new vertex, triangles, lightmap UV
  public/assets/lightmaps/probe-<hash>.hdr the reflection probe (panorama, Radiance RGBE), weighed with the gains
  src/lightmaps.json                       the manifest (ships with the code, so code and bake always agree)
Light maps hold irradiance as sRGB-encoded fractions of a per-map range (the GPU decodes sRGB to linear before
filtering); names carry a content hash because /assets files keep their names under a daily cache check.
"""
import sys, os, json, hashlib, glob
import numpy as np
from PIL import Image

work = sys.argv[1]
repo = sys.argv[2] if len(sys.argv) > 2 else '.'
out = os.path.join(repo, 'public/assets/lightmaps')
os.makedirs(out, exist_ok=True)
for old in glob.glob(os.path.join(out, '*.webp')) + glob.glob(os.path.join(out, '*.bin')) + glob.glob(os.path.join(out, '*.hdr')): os.remove(old)
uv2 = json.load(open(os.path.join(work, 'uv2.json')))
scene = json.load(open(os.path.join(work, 'scene.json')))
sig = {m['id']: m['sig'] for m in scene['meshes'] if m['role'] == 'target'}

def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= .0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - .055)
def half(x):
    h, w = x.shape[:2]
    return x.reshape(h // 2, 2, w // 2, 2, -1).mean((1, 3))
def write(arr8, stem, quality):
    # Blender's first pixel row is the bottom; image files start at the top.
    im = Image.fromarray(np.ascontiguousarray(arr8[::-1]))
    tmp = os.path.join(out, stem + '.tmp.webp'); im.save(tmp, 'WEBP', quality=quality, method=6)
    digest = hashlib.sha256(open(tmp, 'rb').read()).hexdigest()[:8]
    return tmp, digest

atlases = []
for a in range(uv2['atlases']):
    maps = {k: np.load(os.path.join(work, f'{k}-{a}.npy')).astype(np.float32) for k in ('natural', 'lamps', 'ao')}
    cover = maps['natural'][..., 3] > .5
    entry = {'range': {}}
    files = []
    for k in ('natural', 'lamps'):
        rgb = maps[k][..., :3]
        # The range clips the brightest 0.05% of covered texels (the sources' own hot spots).
        peak = float(np.percentile(rgb[cover].max(-1), 99.95)) if cover.any() else 1.0
        rng = float(f'{max(peak, 1e-3):.2g}')
        entry['range'][k] = rng
        for suffix, img in (('', rgb), ('-1k', half(rgb))):
            enc = (srgb(img / rng) * 255 + .5).astype(np.uint8)
            tmp, digest = write(enc, f'{k}-{a}{suffix}', 92)
            files.append((tmp, k, suffix))
    ao = half(maps['ao'][..., :1]).repeat(3, -1)
    enc = (np.clip(ao, 0, 1) * 255 + .5).astype(np.uint8)
    files.append((write(enc, f'ao-{a}', 90)[0], 'ao', ''))
    # One hash per atlas for its files, so the full-size and -1k names stay in step.
    h = hashlib.sha256(b''.join(open(t, 'rb').read() for t, *_ in files)).hexdigest()[:8]
    for tmp, k, suffix in files:
        final = f'{k}-{a}-{h}{suffix}.webp'; os.replace(tmp, os.path.join(out, final))
        if not suffix: entry[k] = final
    atlases.append(entry)
    print(f'atlas {a}: natural range {entry["range"]["natural"]}, lamps range {entry["range"]["lamps"]}')

# Per target: source vertex minus own index (mostly 0), triangle indices as differences from the previous one (Int32
# both), then UVs in eighths of a texel (Uint16). Gzipped: the first two streams almost vanish.
UV_STEPS = uv2['size'] * 8
blob = bytearray(); meshes = []
def put(arr):
    while len(blob) % 4: blob.append(0)
    at = len(blob); blob.extend(arr.tobytes()); return at
for t in uv2['targets']:
    src = np.array(t['src'], np.int64); index = np.array(t['index'], np.int64); uv = np.array(t['uv'], np.float64).reshape(-1, 2)
    meshes.append({'sig': sig[t['id']], 'atlas': t['atlas'], 'verts': len(src), 'tris': len(index) // 3,
                   'src': put((src - np.arange(len(src))).astype(np.int32)), 'index': put(np.diff(index, prepend=0).astype(np.int32)),
                   'uv': put(np.round(np.clip(uv, 0, 1) * UV_STEPS).astype(np.uint16))})
# The reflection probe: lit surfaces at the same gains as the maps, emitters as they are, and where the panorama saw
# sky, the site's own sky (skyColor() in src/landscape.ts, sun disc included). Written as Radiance RGBE with RLE.
gain = {'natural': 1, 'lamps': 1}
path = os.path.join(repo, 'src/lightmaps.json')
if os.path.exists(path):
    try: gain = json.load(open(path))['gain']
    except Exception: pass
def sky(h, w):
    sun = np.array([.38, .075, -.92]); sun /= np.linalg.norm(sun)
    u = (np.arange(w) + .5) / w; v = 1 - (np.arange(h) + .5) / h
    U, V = np.meshgrid(u, v); phi = (U - .5) * 2 * np.pi; th = (V - .5) * np.pi
    d = np.stack([np.cos(phi) * np.cos(th), np.sin(th), np.sin(phi) * np.cos(th)], -1)
    y = np.maximum(d[..., 1], 0); hs = sun[[0, 2]] / np.linalg.norm(sun[[0, 2]])
    dxz = d[..., [0, 2]] + 1e-5; dxz = dxz / np.linalg.norm(dxz, axis=-1, keepdims=True)
    toward = np.maximum((dxz * hs).sum(-1), 0)[..., None]
    mix = lambda a, b, t: a + (b - a) * t
    ss = lambda e0, e1, x: (lambda t: t * t * (3 - 2 * t))(np.clip((x - e0) / (e1 - e0), 0, 1))
    c = mix(mix(np.array([.50, .46, .66]), np.array([1.0, .50, .24]), toward ** 2.2), mix(np.array([.20, .27, .58]), np.array([.75, .42, .40]), toward ** 3.5 * .7), ss(0, .14, y)[..., None])
    c = mix(c, np.array([.03, .07, .22]), ss(.12, .75, y)[..., None])
    s = np.maximum((d * sun).sum(-1), 0)[..., None]
    return c + np.array([1.0, .52, .22]) * s ** 5 * .5 + np.array([1.0, .75, .45]) * s ** 50 * .9 + np.array([1.0, .88, .66]) * ss(.9993, .9996, s) * 16
def write_hdr(img, name):
    h, w, _ = img.shape; m = img.max(-1); e = np.ceil(np.log2(np.maximum(m, 1e-32))); e = np.where(m < 1e-32, -128, e)
    mant = np.where(m[..., None] < 1e-32, 0, img / np.exp2(e)[..., None] * 256)
    rgbe = np.concatenate([np.clip(mant, 0, 255).astype(np.uint8), (e + 128).clip(0, 255).astype(np.uint8)[..., None]], -1)
    buf = bytearray(b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n' + f'-Y {h} +X {w}\n'.encode())
    for row in rgbe:
        buf += bytes([2, 2, w >> 8, w & 255])
        for c in range(4):
            data = row[:, c]; i = 0
            while i < w:
                run = 1
                while i + run < w and run < 127 and data[i + run] == data[i]: run += 1
                if run > 2: buf += bytes([128 + run, data[i]]); i += run; continue
                j = i
                while j < w and j - i < 128 and not (j + 2 < w and data[j] == data[j + 1] == data[j + 2]): j += 1
                buf += bytes([j - i]) + bytes(data[i:j]); i = j
    open(os.path.join(out, name), 'wb').write(buf)
probe = None
if os.path.exists(os.path.join(work, 'probe-natural.npy')):
    pn, pl = np.load(os.path.join(work, 'probe-natural.npy')), np.load(os.path.join(work, 'probe-lamps.npy'))
    alpha = pn[..., 3:4]
    img = pn[..., :3] * gain['natural'] + (pl[..., :3] - pl[..., 4:7]) * gain['lamps'] + pl[..., 4:7] + (1 - alpha) * sky(*pn.shape[:2])
    tmp = f'probe.tmp.hdr'; write_hdr(np.maximum(img, 0).astype(np.float32), tmp)
    probe = f'probe-{hashlib.sha256(open(os.path.join(out, tmp), "rb").read()).hexdigest()[:8]}.hdr'; os.replace(os.path.join(out, tmp), os.path.join(out, probe))
    print(f'probe {probe}: gains {gain}')

import gzip
data = gzip.compress(bytes(blob), 9, mtime=0)
bin_name = f'uv2-{hashlib.sha256(data).hexdigest()[:8]}.bin'
open(os.path.join(out, bin_name), 'wb').write(data)
# Hand-tuned gains are kept across re-bakes (change them in src/lightmaps.json, then run this again for the probe).
manifest = {'version': 1, 'base': '/assets/lightmaps/', 'atlases': atlases, 'gain': gain, 'bin': bin_name, 'uvSteps': UV_STEPS, 'probe': probe, 'meshes': meshes}
json.dump(manifest, open(path, 'w'), separators=(',', ':'))
print(f'{len(meshes)} surfaces, {len(data) / 1e3:.0f} kB of UVs (gzip), {len(atlases)} atlas(es) -> {out}')

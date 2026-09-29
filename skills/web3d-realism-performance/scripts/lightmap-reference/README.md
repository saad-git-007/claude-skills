# Lightmap pipeline: reference implementation

Copied from a working three.js project (September 2026, three.js 0.180, Blender 5.2.1). They are specific to that
scene, so read them as a worked example and port the parts you need. Don't run them unchanged.

| File | Role | Project-specific parts to replace |
|---|---|---|
| `export.mjs` | Playwright + GPU Chrome: loads the app with `?baked=0`, writes `scene.json` + `scene.bin` | `window.__lab`, `lightmapTargets()`, `lightmapSignature()`, the "explore/open" state setup, terrain crop |
| `bake.py` | Headless Blender: builds the scene, second UV set (weld + KEY layer, Smart UV, weights, own packer), Cycles bakes (natural, lamps, AO; margin 0 + dilate), OIDN denoise, irradiance calibration, reflection-probe panoramas | label-based weights (`Observatory lens`, `Expanded glass pavilion`), probe position, cove light |
| `lights.json` | Light rig: sun, sky, point-light gain, emitter gains | all values |
| `publish.py` | WebP maps (+ half size), gzipped UV binary, RGBE probe, manifest | `sky()` is a numpy port of the app's sky shader; replace with yours |
| `lightmap.ts` | Runtime: signature matching, geometry rebuild with `uv1`, material patch | none beyond the manifest path and how targets are collected |

Commands used there:

```bash
npm run dev -- --port 5199 --strictPort                                             # app, in another terminal
TMPDIR=/dev/shm env -u DISPLAY node scripts/lightmap/export.mjs ../lightmap-work http://127.0.0.1:5199
blender -b --factory-startup --python scripts/lightmap/bake.py -- ../lightmap-work   # --samples 128 --size 2048
python3 scripts/lightmap/publish.py ../lightmap-work .
```

Debug options in `bake.py`: `--only <target ids>`, `--stop pack` (saves `pack.blend` after packing), `--stop maps`
(skips the bakes, renders only the probe); `LM_DEBUG=1` logs per-object weights and island counts.

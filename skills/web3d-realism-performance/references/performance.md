# Performance: measuring and the techniques that paid off

## Contents
1. Measuring (benchmark, visual diff, A/B, noise)
2. Draw order and overdraw
3. Skipping work in shaders (with code)
4. Shadows
5. Draw calls and CPU
6. Resolution and frame pacing
7. Vegetation cost
8. Tried and dropped
9. Numbers from one project, for calibration

## 1. Measuring

**Benchmark.** Expose the app's frame function and camera on `window` in dev (for example `window.__lab = { frame,
camera, controls, seek, hold, renderer }`). For each fixed pose:

```js
const one = () => {
  cancelAnimationFrame(app.animation);            // stop the app's own loop
  app.dirty = true; const a = performance.now();
  app.frame(a);                                   // app update + three.js submission (CPU)
  const b = performance.now();
  gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);   // waits for the GPU to finish
  return [b - a, performance.now() - a];          // cpu, total
};
// 6 warm-up frames, then the median of 40; mean over poses = the headline number
```

Record `renderer.info.render.calls` and `.triangles` per pose too. Take a screenshot per pose in the first round.

**Poses.** Cover what users see: the start of any intro flight, each point of interest, wide orbit views, and the
worst case (looking across the most geometry or foliage). Thirteen poses was enough to be representative.

**Determinism.** Before measuring, pin every time-driven thing (`callbacks.forEach(f => f(40))` or equivalent) and
hold the animation. Check it: the same build rendered twice must give SSIM 1.0000.

**Visual diff** (`scripts/perf/compare.py`): mean absolute difference as % of full scale, share of pixels off by more
than 8/255, SSIM. Budget used: mean under 1% and SSIM at least 0.99 per pose. Most kept optimisations changed
nothing measurable (worst 0.024%).

**Noise.** Quiet machine: about 0.6% run to run. With a remote desktop or another browser busy, single runs moved by
several per cent and one unbalanced comparison read -14% that was noise. Use alternating order-balanced pairs
(`scripts/perf/ab.sh`); report medians; re-measure the ends of a long pass back to back.

**Headless GPU on Linux:** `chromium.launch({ executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox',
'--use-angle=gl-egl', '--ignore-gpu-blocklist', '--enable-gpu'] })`, run with `env -u DISPLAY`. Run GPU checks one at
a time; two at once distort each other.

## 2. Draw order and overdraw

three.js draws opaque objects sorted by `renderOrder`, then by material id (creation order), then front to back by
distance. Early depth testing only saves a pixel if what covers it was drawn *first*.

- Draw big background surfaces last: the scene contents at 0, forest 1, terrain 2, sea 3, sky 5.
- Sky dome: in its vertex shader set `gl_Position.z = gl_Position.w` (far plane), keep `depthTest: true`,
  `depthWrite: false`, and draw it last. Only uncovered pixels shade.
- Surfaces that cover others (a desk inset over the desk, a screen face over its bezel, a floor over the base's top)
  should use a material created earlier, or `renderOrder = -1`.
- A 9 km sea plane shaded under everything was a 4-8% frame cost by itself.

## 3. Skipping work in shaders

Patch three.js shader chunks once at startup, and make every patch *throw* if the text it replaces is missing, so a
three.js upgrade cannot silently drop it:

```ts
let chunk = THREE.ShaderChunk.lights_fragment_begin;
const patch = (from: string | RegExp, to: string) => {
  const next = chunk.replace(from, to);
  if (next === chunk) throw new Error('lights_fragment_begin patch did not apply');
  chunk = next;
};
// A light behind the surface (or out of range: directLight.visible is false) adds exactly nothing.
patch('IncidentLight directLight;', `IncidentLight directLight;
#ifdef STANDARD
#define FACES_LIGHT ( max( dot( geometryNormal, directLight.direction ), dot( geometryClearcoatNormal, directLight.direction ) ) > 0.0 )
#else
#define FACES_LIGHT true
#endif`);
patch(/RE_Direct\( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight \);/g,
  'if ( directLight.visible && FACES_LIGHT ) RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );');
THREE.ShaderChunk.lights_fragment_begin = chunk;
```

Other exact skips that paid off: terrain splat layers with zero weight (and triplanar reads under 0.2% weight);
fragments of clouds or blended leaves that contribute nothing (`if (alpha < 1.0/255.0) discard;`); explicit-mip
`textureLod` for impostor atlases (helped on Intel GPUs).

Per-material patches go in `onBeforeCompile`. If you also set a global `Material.prototype.onBeforeCompile`, a
material with its own hook must call the prototype's first, and give each patched variant a
`customProgramCacheKey`.

## 4. Shadows

- Update shadow maps explicitly (`renderer.shadowMap.autoUpdate = false`, set `needsUpdate` when lights or casters
  move). Beware: forcing shadow updates from animation code once left a mesh's GPU geometry stale.
- Exact soft-shadow early-out: after each shadow render, build two small maps holding the min and max depth over each
  PCF footprint (a 4x4 texelFetch pass). In `shadowmap_pars_fragment`, a pixel nearer than the min is fully lit and
  one beyond the max fully shadowed; the 16 taps run only in penumbrae. -2 to -6% at interior views; the ceiling
  (shadows off) was -7%.
- With baked light, static surfaces no longer need real-time shadows from static lights at all.

## 5. Draw calls and CPU

- `mergeStatic()` after construction: merge static meshes by material, baking transforms. Anything animated must be
  marked (`userData.dynamic = true`) before, or it stops moving with its group. Inside a moving group, batch its own
  meshes and keep the group rigid.
- Loaded glTF: batch by material; standard materials that differ only in base colour share one material with the
  colour folded into vertex colours. Keep a "parts" option for models whose meshes are looked up by name later.
- Flat transparent panes (glass) can be merged per sector, not globally, so transparent sorting still works.
- Per frame: no allocations, no DOM style writes unless the value changed, no React state updates unless something
  the UI shows changed.

## 6. Resolution and frame pacing

- Budget the drawing buffer in megapixels per quality level, not DPR alone (phones report DPR 3-4).
- Adaptive quality must ignore loading, hidden tabs, dialogs and paused frames, or it downgrades for no reason.
- A 30 fps limiter must carry the remainder forward, or it produces uneven frame times that look like overload.
- Anisotropic filtering: cap at 8x.

## 7. Vegetation cost

- Octahedral impostors (a few baked views per species, blended per pixel with a parallax step) on one InstancedMesh
  per species. Cards screen-parallel and pushed half a crown toward the camera, so overlapping crowns never cut each
  other along a straight line. Per-pixel depth output would be more correct but cost 13-16 ms a frame.
- Software WebGL (tests) should get a light variant; a software frame of the full forest took ~6 s.
- Half-size atlases for touch devices.

## 8. Tried and dropped

| Idea | Result |
|---|---|
| Depth pre-pass + EQUAL colour pass for alpha-tested foliage | Slower (15.9 vs 14.5 ms) and not identical: coverage needs all texture reads, so pass 1 repeats most of the work |
| Forest drawn in distance bands across species | No gain |
| Single-view impostor shading from 110 m instead of 170 m | -0.6%, SSIM 0.933: visibly worse |
| Tighter 16-sided tree cards | Card area only 2% smaller; no measurable gain |
| Plain PCF instead of soft PCF | No gain worth the look |
| Strict front-to-back opaque sorting | No gain over renderOrder + material order |
| Freezing static matrices (`matrixAutoUpdate = false`) | 0.06 ms |
| In-browser cube-camera capture for reflections | +8 s load (second shader variant per material) |

## 9. Numbers from one project, for calibration

Intel Iris Xe, 1920x1080, 13 poses: 17.8 to 13.9 ms mean frame (GPU 14.8 to 11.3, CPU 3.07 to 2.60), draw calls at
wide views 367 to 248, worst visual change 0.024%. Per iteration: terrain after the lab 4.1%; sea after the terrain
and sky last 7.9%; forest shader 2.2%; batching 0.7% (CPU -16%); terrain skips 2.6%; light skips + covering surfaces
first 6.8%; shadow early-out 2.0%; discard empty fragments 1.1%; DOM writes on change 2.0%.

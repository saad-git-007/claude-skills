---
name: web3d-realism-performance
description: How to make a real-time browser 3D scene (three.js, React Three Fiber, CesiumJS, WebGL/WebGPU) look more photorealistic while keeping or improving its frame time. Covers measuring frame time and visual change, cheap wins (draw order, batching, skipping work in shaders), baked lighting (Cycles lightmaps on a second UV set, a baked reflection probe), PBR textures, impostors for vegetation, glTF asset optimisation, and CAD-accurate models repeated many times (light copies, full detail on demand). Use this whenever the user wants a web 3D scene to look better, more realistic or more "premium", wants it faster or smoother, or mentions frame rate, draw calls, jank, GPU cost, lightmaps, light baking, Blender baking, global illumination, shadows, reflections, environment maps, PBR materials, tree or forest rendering, CAD or datasheet-accurate models, level of detail, soft or blurry 3D on phones, or wants a scene optimised "without losing quality", even if they don't name any of these techniques.
---

# Photorealism and performance for web 3D scenes

Lessons from building and tuning a three.js portfolio scene (a glass pavilion on a sea cliff, a forest, about 250
draw calls): 11 measured optimisation iterations cut mean frame time by 22% with no visible change, and a Cycles light
bake added soft bounce light for +3% frame time. The two goals are not in conflict as often as it seems. Most of the
real cost in a typical scene is wasted work (pixels shaded and then painted over, lights evaluated where they add
nothing), and most of the realism comes from light that can be computed once, offline, instead of every frame.

## The working loop

Everything below depends on being able to answer two questions with numbers: *did this make it faster?* and *did the
image change?* Set that up before touching the scene, because intuition about GPU cost is wrong surprisingly often
(in the project, a depth pre-pass, strict front-to-back sorting and plain PCF shadows all looked like wins and were not).

1. **Make the scene deterministic.** Pin every animation (wind, water, clouds, rotating props) to a fixed time before
   measuring. Unpinned tree sway alone made identical code differ by 2% SSIM.
2. **Benchmark fixed poses on a real GPU.** Headless Chrome with a GPU: `--use-angle=gl-egl --ignore-gpu-blocklist
   --enable-gpu` (Linux) and `env -u DISPLAY` so it uses EGL rather than a virtual X display. Software WebGL
   (SwiftShader, llvmpipe, Playwright's default) says nothing about GPU cost. For each pose, run the app's own frame
   function with the render forced, then a 1-pixel `readPixels` to wait for the GPU; take the median of ~40 frames
   after a few warm-ups. `scripts/perf/bench.mjs` is a template.
3. **Diff the images.** Lossless screenshots of the same poses; per pose, mean absolute difference and SSIM against a
   baseline. A budget such as "mean diff under 1%, SSIM at least 0.99" makes "without losing quality" checkable.
   `scripts/perf/compare.py`.
4. **Alternate A/B on a noisy machine.** Background load moves single runs by several per cent. Run baseline and
   candidate in alternating, order-balanced pairs (prev/cand, then cand/prev) and compare medians. An unbalanced
   2-pair run once read -14% that was pure noise. `scripts/perf/ab.sh`.
5. **One change per iteration**, kept only if faster *and* within the visual budget; commit each kept one separately
   with its measured gain in the message. A stopping rule (for example "five iterations in a row under 5%") keeps the
   pass from turning into endless polishing.
6. **Look at it.** Render the key views before and after, side by side, and actually look: tests cannot see a
   blotchy bake, a floating cable or a wrong reflection. Send the comparison to the user.

## Where frame time usually goes, and the fixes that paid off

In rough order of payoff in the project. Details, code and the rejected ideas are in
`references/performance.md`; read it before optimising.

- **Draw order (overdraw).** The biggest wins were not shader tuning: large, expensive surfaces (terrain, sea plane,
  full-screen sky) were drawn *before* the objects covering them, so their pixels were shaded and then overwritten.
  Draw big background surfaces last (`renderOrder`), put the sky at the far plane with depth testing so only
  uncovered pixels shade, and make covering surfaces draw before what they hide. three.js sorts opaque objects by
  `renderOrder`, then *material creation order*, then distance, so creation order is a lever too. Worth 4-8% each.
- **Skip work that adds exactly nothing.** A light out of range or behind the surface still runs its full BRDF and
  shadow taps in three.js; a patched `lights_fragment_begin` skips it. Soft shadows can skip all their taps where a
  min/max depth map proves the pixel fully lit or fully shadowed. Terrain splatting can skip zero-weight layers.
  Transparent effects can `discard` fragments that contribute nothing.
- **Draw calls (CPU).** Merge static meshes by material once after construction; fold per-object base colours into
  vertex colours so near-identical materials share one; batch loaded glTF models by material. Create each material
  once and share it: a material created inside a loop can never be batched. 367 to 248 draw calls, CPU -16%.
- **Per-frame JS garbage and DOM writes.** Write styles to HTML overlays (labels, pins) only when the value changes.
- **Resolution policy.** Cap the drawing buffer in pixels (for example 5 MP on "High", 1.5 MP on "Performance")
  rather than trusting `devicePixelRatio` on phones, and keep a frame limiter's remainder so a 30 fps cap does not
  read as slow frames. CesiumJS has the opposite default: it draws in CSS pixels, so a 3× phone renders about a
  ninth of its pixels and looks soft. Scale `resolutionScale` by DPR on touch screens, capped at 3
  (`references/cesium-and-cad-models.md` §2).
- **Detail on demand for repeated models.** A full CAD model on each of 171 repeated parts cost +50% frame time and
  +340 MB. A 1-2k-triangle light version on every copy, plus the full one on the single copy a close-up view frames
  (loaded in the background), cost nothing measurable. A single instance needs no light version at all.

## Photorealism per millisecond

What made the biggest visual difference for the least runtime cost (details in `references/realism.md`):

1. **Baked global illumination** (the big one). Real-time lights cannot give soft bounce light, contact darkening or
   area-light falloff at browser budgets. Bake them with Blender's Cycles path tracer into lightmaps on a second UV
   set, and at runtime take the baked surfaces' *diffuse* light from the maps while real-time lights still add
   specular highlights. It even removes per-pixel light loops from those surfaces. Full pipeline and its traps:
   `references/lightmaps.md`; working reference scripts in `scripts/lightmap-reference/`.
2. **A matching environment for reflections.** Render an equirectangular probe of the lit scene in the same bake and
   use it as `scene.environment`, so metal and glass reflect the actual room and sky instead of an unrelated HDRI.
   Don't capture a cube map in the browser at load: every material compiled a second shader variant and cost 8 s.
3. **Real PBR maps where the eye lands.** Roughness variation is what makes concrete, wood and lacquer read as real;
   a flat roughness value reads as plastic. CC0 sources (Poly Haven, ambientCG) are good; set colour maps to sRGB and
   data maps (normal, roughness) to linear.
4. **Impostors for vegetation** instead of cross-plane cards: octahedral views baked from real tree models, blended
   per pixel, lit at runtime from baked normals. Thousands of convincing trees for a few milliseconds.
5. **Tone mapping, sun and sky consistency.** One sun direction and colour used by the sky shader, the bake rig and
   the real-time light; mismatches are what make a scene look composited.

## When baking light, keep albedo in the material

Baking "colour without light" (albedo) into the atlas is usually the wrong trade on the web: the atlas has a few
centimetres per texel, while the material's own textures are much sharper and tile. Bake *irradiance* with the
surface colour divided out (Cycles DIFFUSE pass with direct + indirect, colour off), and multiply by the material
colour at runtime. The surface keeps its sharp detail and its PBR reflections, and the same bake survives colour
tweaks.

## Before you finish

- Frame time measured on the GPU against the baseline, with the per-pose table; visual diff within budget, or the
  intended change shown in side-by-side renders.
- Load cost reported: extra download (desktop and phone), texture memory, time to first frame.
- Guards in place so the optimisation cannot silently rot: shader chunk patches throw if the chunk text changed;
  a test fails when baked geometry no longer matches the bake. That test does not notice a changed light, emitter
  or occluder: re-bake after those too (lightmaps.md, section 7).
- The re-bake / re-measure commands written down in the project's docs, since the next person to change geometry
  needs them.

## Related skill

UI on top of the scene (HTML labels and cards over the canvas, camera flights, scrubbable progress, loading badges,
transitions into and out of the 3D view) is covered by the `web-ui-motion` skill.

## Reference files

- `references/performance.md`: measuring, draw order, batching, shader patches (with code), shadows, resolution
  policy, tried-and-dropped list.
- `references/lightmaps.md`: the Cycles lightmap and reflection-probe pipeline end to end, runtime shader patch,
  signature matching, and every bug hit along the way.
- `references/cesium-and-cad-models.md`: light/full model pairs with measured costs, per-asset triangle budgets,
  CesiumJS resolution and primitive/render-loop/harness traps, CAD models from datasheets in headless Blender, and
  why effects sized in screen space fade out at distance.
- `references/realism.md`: materials, environment, vegetation impostors, glTF optimisation, review renders.
- `scripts/perf/`: `bench.mjs` (fixed-pose GPU benchmark), `compare.py` (visual diff), `ab.sh` (alternating A/B).
  Templates: adapt the pose list and the app hooks (`window.__lab`-style) to the project.
- `scripts/lightmap-reference/`: the project's `export.mjs`, `bake.py`, `publish.py` and `lightmap.ts`. They are
  specific to that scene; read them as a working example and adapt rather than run as-is.

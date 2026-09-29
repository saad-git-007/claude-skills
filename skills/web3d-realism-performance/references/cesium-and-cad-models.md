# CesiumJS scenes and CAD-accurate models: detail on demand

From a second project: a CesiumJS view of large wheeled machinery over real terrain (a steel structure up to
~500 m long, with 170+ copies of one small hanging part plus a few one-off assemblies), used on desktops and on phones
outdoors. The models were built in headless Blender from manufacturer datasheets and photos. Measurements used an
Intel Iris Xe (Vulkan) and SwiftShader in a harness that did not use Cesium ion. What transfers to any engine is §1 (detail on
demand) and §4 (CAD from datasheets). §2 and §3 are Cesium-specific.

## Contents
1. Detail on demand: a light model everywhere, the full model only where the camera is
2. Resolution: Cesium's default is the opposite trap from three.js
3. Cesium traps (primitives, render loop, harness)
4. CAD-accurate models from datasheets in headless Blender
5. Effects sized in screen space fail at distance

## 1. Detail on demand

The question is always "the real model, but it is repeated 170 times". Measure three versions before choosing:

| Asset (worst case: 171 copies of the repeated part) | Tris each | Frame time | Extra memory |
|---|---|---|---|
| Primitive placeholders | small | baseline | 0 |
| Light model on every copy | 1,000-2,000 | within noise | +5.6 MB |
| Full model on every copy | 56,000-83,000 | **+50% GPU, 3× SwiftShader** | **+340 MB** |
| Light everywhere + full on ONE close-up copy | as light | within noise | +3 MB, open +34 ms |
| One 26k-tri one-off assembly | 26,000 | not measurable | +0.9 MB |

Rules that came out of it:
- **Build two versions from the same source file**: a light one (about 1-2k tris, colour parts merged, silhouette
  and the parts people recognise kept) and a full one. Compare them side by side in Blender at the distance the
  light one is seen from, before exporting.
- **The full model goes only where a view needs it** (a close-up camera preset). Start loading it in
  the background when the 3D view opens, without waiting for it. Place it if it has arrived by the time the view
  builds; otherwise swap it in when it arrives, and rebuild only the one span or group it belongs to. If the fetch
  fails, everything stays light.
- **A single instance needs no light version.** One 26k-triangle one-off assembly cost nothing measurable. Levels of detail pay
  off only on repeated parts.
- **Give the loader a triangle budget per asset** (for example 2,500 per copy, 120,000 for the detail model) and
  refuse anything over it, so a bad re-export can't put 80k triangles on every copy.
- **Merge repeated parts per group and per colour.** All copies on one section of the structure become one instance per colour, which is
  what kept the light version free.
- A distant repeated detail (wires, small fittings) is fine as a light mesh everywhere (+2.9 MB, not measurable). The
  full version on the one box in the close-up cost about 1.5 ms, inside the noise, so it was kept.

## 2. Resolution: Cesium's default is the opposite trap

`performance.md` §6 warns about phones reporting DPR 3-4. Cesium does the reverse: with
`useBrowserRecommendedResolution` (on by default) it draws in **CSS pixels**, so a 3× phone renders about a ninth of
its real pixels and everything looks soft. Quality presets that only budget effects (particles, FXAA) don't fix it.
```js
const TOUCH_PIXEL_RATIO_CAP = 3;
function screenPixelRatio() {
  const q = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)');   // guarded: headless stubs lack it
  return q && q.matches ? Math.min(Math.max(devicePixelRatio || 1, 1), TOUCH_PIXEL_RATIO_CAP) : 1;
}
viewer.resolutionScale = (cameraMoving ? q.motionResolution : 1) * screenPixelRatio();
```
- Only touch screens get this: desktops keep 1.0, so there is no performance change there.
- Watch for DPR changes (a window dragged to another screen, a zoom) with a `(resolution: Ndppx)` media query that is
  re-armed at the new value after each change.
- Keep a lower resolution while the camera moves (0.85 here), multiplied on top.
- The project owner confirmed the fix on a physical phone: the 3D view went from soft to sharp. If panning feels
  heavy on a weaker phone, lower the cap to 2 before touching anything else.

## 3. Cesium traps

- **A `Primitive` with a single `GeometryInstance` ignores the instance's `modelMatrix`** and uses the primitive's.
  Bake the transform into the vertices, or set it on the primitive.
- **In request-render mode, `viewer.render()` skips frames** unless `scene.requestRender()` was called. A benchmark
  that doesn't call it measures nothing.
- **Stopping the render loop before rebuilding a primitive** means the new primitive never becomes ready. Rebuild
  first, then pause.
- **Coarse terrain while loading:** right after switching location, sampled heights can be about 140 m off until the
  tiles refine. Anything fitted to the ground (feet, wheels) must ignore readings more than a tolerance
  (10 m here) off the refined profile, or the model folds into the ground.
- **Camera presets that re-frame as the ground refines** have to stop at the first user input (`pointerdown`, `wheel`,
  `keydown`). A screenshot harness has to send a `wheel` event before moving the camera itself, or the preset pulls
  it back.
- **Billed imagery:** a harness mode that doesn't use ion tiles makes renders and benchmarks free and repeatable.
  Never open an ion session just to take review screenshots.
- **A `file://` harness** needs `--allow-file-access-from-files` for WebGL textures to load.
- **WebDriver `execute_script`** has a 30 s default script timeout and a 120 s client read timeout; long benchmarks
  must return early and poll.
- **Snapshot the static files into the benchmark run**, so edits made during a long A/B run don't leak into it.
- **Harness hooks can fake a regression.** A hook that froze one effect's clock (scan beams) let the live clock hide
  the beams in the "before" shot, and the comparison showed a difference the code never had. Freeze every clock the
  shot depends on, or none.
- **Headless runtime tests on a bare `window` stub:** guard every `matchMedia` call, or add `matchMedia` to the stub.

## 4. CAD-accurate models from datasheets (headless Blender)

- **Script the build** (`build_*.py` run by `blender -b --factory-startup --python`), driven by a table of the
  datasheet's dimensions, with a `measure()` function that prints each model dimension next to the sheet's value.
  Manufacturer sheets often contradict themselves. One sheet could not be satisfied in full: most dimensions
  agreed within 0.3 in, three did not, and the drawing was not to scale (62 px/in along one axis against 58.6 along
  another). Record which figures you chose and why, so nobody re-derives them.
- **Scale everything from one number** (`TOTAL_MM`) when the photo's proportions and the owner's stated size differ.
- **Re-exports can silently lose detail.** The working `.blend` had lost its boolean cutter objects, so headless
  exports quietly dropped the outlet pockets and side holes with no error. Check each part's triangle count against a
  known value after every export.
- **Export in the engine's own part format** (a JS global per asset with named colour parts, moving groups, pivots,
  and important points such as an outlet) rather than only a GLB, so the runtime can merge, animate and aim
  parts without searching a node tree.
- **Owner requests beat the photo:** a number printed on a part, loose wires, a handle — remove them when asked, in
  both versions.
- **Render review images with Khronos PBR Neutral**, not AgX, when colours matter: AgX washed a saturated yellow part
  code to cream.
- **Blender MCP:** a render longer than about 2 minutes times out the socket ("No data received") while Blender
  keeps going. Run long renders headless (`blender -b file.blend --python-expr …`).
- **Keep build and export scripts in the repo** and the renders, `.blend` and GLB files in a gitignored render folder
  with a README (measured dimensions, triangle counts, what was changed at the owner's request).

## 5. Effects sized in screen space fail at distance

A scanning-grid effect took its cell size from the ground area one screen pixel covers. Up close that was fine. Far
away, the narrow wedge it was drawn on (2-10 m wide) held only one or two 6-12 m cells, each lit 36% of the time,
so distant scans looked flat. The fix was to lay out the grid in the effect's own coordinates (a fan of 5-8 columns
by 9-14 rows per wedge), merge cells with distance but never below 2×3, flicker tiny wedges harder, and give every
wedge a 1-pixel frame. When a feature is only 5-10 px tall on screen, the frame and the flicker are what can still be
seen; say so rather than promising the grid.

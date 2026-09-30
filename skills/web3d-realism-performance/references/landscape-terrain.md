# Landscape scenes: real terrain, procedural relief, matching photographs

From a third project: a photoreal, real-time recreation of a real valley (Moraine Lake, Banff: a lake under a ring of
3,000 m peaks, about 16 km across) in three.js r186, running on phones and laptops. What transfers to any
"real place from elevation data" scene. Numbers are from that project and are there for calibration.

## Contents
1. Data to mesh
2. Procedural relief on top of a coarse DEM, and how it goes wrong
3. Land cover: forest, snow, treeline
4. Shader features that only a few triangles need (program variants)
5. Matching reference photographs
6. Licence of reference photographs
7. Things that looked like bugs and were settings

## 1. Data to mesh

- **Elevation:** a national bare-earth DEM (here NRCan MRDEM-30, 30 m). Reproject once, offline, into a local
  azimuthal-equidistant frame centred on the hero feature (x east, z south, y up, metres), so float precision is fine
  everywhere and every tool (bake, mesh, POIs, camera paths) shares one frame. Two rasters: a wide one (16 km at
  2048²) and a fine inset (2.5 m/pixel, 1024²) around the hero area. Write the frame into a contract document all
  modules read.
- **Hero feature outlines** (shoreline, a boulder mound, forest edge) are traced from satellite imagery, not guessed
  from the DEM: a 30 m DEM cannot resolve them. Bake land cover to a small RGBA mask (R forest, G talus, B snow,
  A cliff) that the terrain shader reads.
- **Mesh:** a polar grid centred on the hero point with adaptive rings (dense near the camera's usual place, coarse
  far), built in chunks. Heights and normals come from a worker pool. A separate coarser mesh is what the planar
  reflection pass draws (about 4× fewer triangles, invisible in a mirror).
- **Sky/terrain draw order** and overdraw rules are in `performance.md` §2; a terrain this big makes them matter.

## 2. Procedural relief on top of a coarse DEM, and how it goes wrong

A 30 m DEM is smooth at the scale people look at from a canoe. Adding relief in the vertex stage (fall-line gullies,
cliff-band strata, horns, crenellated crests) is what makes peaks look like rock, and it is easy to ruin:

- **Needles and towers.** Sharpening terms added to a height that is already near the summit produce spikes metres
  tall on single vertices. Bound every added term *relative to the base height above the local base*:
  total drop capped at `capK·(capY − y0 + cap0)`, sharpening capped at `taperK·(capY − y0 + taper0)`, strata faded in
  with `smoothstep(0, stFade, capY − y0)`, and keep an apex guard so the summit is never lowered below its neighbours.
  (Project values: capK 0.55, taperK 0.8, stFade 60 m.)
- **Stray peaks** are the same bug seen from the side: a duplicate summit next to the real one. Check each named peak
  against photographs from the same viewpoint (§5) rather than from above.
- **Expose every tunable through a URL override** (`?rp=name:value,…`, forwarded to the worker) so a look can be
  iterated in seconds without a rebuild. Keep the defaults in one object.
- Relief computed per vertex in a worker stays off the frame time; measure load time instead.

## 3. Land cover: forest, snow, treeline

- **Trees on summits** are the classic giveaway. Thin trees by a *position hash* between two elevations
  (`TREELINE = [430, 545]` here) so the treeline is ragged, not a ruler edge; skip at push time but still consume the
  random stream, so adding the rule does not reshuffle every other tree. Stunt trees (scale 0.58) on hostile ground
  such as a boulder mound, and keep dead snags away from a dock.
- **Summit snow** as a product of smooth terms: elevation with noise breakup, a slope term (`smoothstep` of the
  blended normal's y), and a low-frequency noise gate. If summits look like smooth white domes, tighten the
  thresholds and let rock show through on steep faces.
- **Chromatic aberration** in the post pass made magenta speckle on snow against dark rock; expose the strength as a
  uniform (`?ca=`) and keep it low.

## 4. Shader features that only a few triangles need (program variants)

A rubble-and-boulder shading block for one small hero feature was added to the terrain fragment shader and cost
**+4.6% GPU for every pixel of every frame**: the program got heavier for all pixels, not just the ones that use the
block. Fix, worth copying:

- Wrap the feature's GLSL in `#ifdef FEATURE` and build **two** `ShaderMaterial`s from the same source that share one
  `uniforms` object.
- While building the mesh, route the triangles that overlap the feature's rectangle into their own chunk and give it
  the `FEATURE` variant. Everything else keeps the lean program.
- Result: the regression vanished (total for the whole look pass was +1.4% against the previous deployment).
- Compile both variants up front (`renderer.compileAsync`, also with the clip plane the reflection pass uses) so
  nothing compiles while the camera flies.

**Measure with fixed-camera poses.** An A/B on the intro flight path read as a change because the path itself had
changed between builds; fixed poses (rock face, feature, wall, wide) gave the true number. Also pass a fixed pixel
ratio (`?q=1`) so dynamic resolution (which reacts within half a second) cannot hide or fake a difference.

## 5. Matching reference photographs

The workflow that converged, in order:

1. **Recover the camera.** Find the photograph's position and orientation by fitting the DEM's shoreline outline and
   its skyline to the photo (overlay the predicted skyline on the photo, iterate on position, azimuth, pitch, field
   of view). Use that pose as a fixed test view and as the start of the intro flight.
2. **Compare peak by peak** from that pose: the same crop from the render and the photo, side by side, one sentence of
   difference per peak (too pale, too smooth, too much snow, wrong horn). Do this with parallel agents, each owning one
   area (mountains and snow, the dock and canoes, the hero mound), each in its own worktree; the integrator merges and
   re-checks every view, because fixes for one peak leaked into another (stray towers, trees on summits).
3. **Fix the biggest visible difference first** (rock tone and darkness, jaggedness, snow pattern), re-render the same
   poses, repeat. Stop when remaining differences are only what the data cannot give (a 30 m DEM cannot be a 1 m one).
4. **Tell the user what is still different.** Here: peaks paler and smoother than dark rugged photo rock, one summit a
   narrower horn than the photograph's pyramid, lake less vivid than the photo. Performance measured only on a laptop
   iGPU, not on the target phone.

## 6. Licence of reference photographs

Crediting a photograph is not permission to use it. Keep reference photographs out of the repository and out of
`public/` (a gitignored `data/refs/` folder), ship only images you hold rights to or that carry an open licence, credit
each one where it appears and in the README, and list the shipped ones as excluded from the code licence. Record
photographers named in EXIF. Tell the owner plainly when a shipped image's source offers no reuse licence.

## 7. Things that looked like bugs and were settings

- A scene that never finishes loading in headless Chrome: it was the software renderer, not the scene
  (`scripts/preflight/gpu-check.mjs`; `performance.md` §1).
- Frame rates of 13-50 fps in headless tests on a laptop iGPU are normal and noisy; judge by GPU timer queries, not by
  fps (`performance.md` §1).
- An intro flight that looks different between builds changes every benchmark that rides it.

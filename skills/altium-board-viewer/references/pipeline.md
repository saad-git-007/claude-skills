# Pipeline internals

## Data flow

```
.PrjPcb ──build.py (altium_monkey)──► work/build/data.json + layers.json
                                           │
                     make2d.py + assets/viewer_template.html ──► <name>_viewer.html  (data + layers embedded)
                                           │
              make_pdf.py (reads the viewer HTML, prints with Chrome) ──► <name>_board.pdf
              fetch_models.py ──► work/models/{kicad,maker,third_party}
              conv3d.py (OCP) ──► work/out3d/{models,placements,sources,report}.json
              make3d.py + assets/viewer3d_template.html + vendor three.js ──► <name>_3D.html
```

The 2D viewer HTML is the hand-off format: the PDF, model fetch and 3D steps all read the board from it.

## altium_monkey (calls used)

- `AltiumDesign.from_prjpcb(path)`, `.load_pcbdoc()`, `.get_pcb_project_parameters()`
- `pcb.to_layer_svgs(PcbSvgRenderOptions(visible_layers=[PcbLayer.TOP, …], drill_hole_mode="overlay"), params)`
  keyed by names like `TOP`, `TOP_OVERLAY`, `MULTI_LAYER` (`PcbLayer.TOP_OVERLAY`, not `TOPOVERLAY`).
- `pcb.to_board_outline_svg()`; `pcb.board.outline.vertices` (`x_mils`, `y_mils`)
- `pcb.components`, `pcb.component_bodies` (`component_index`, `outline`, `standoff_height_mils`,
  `overall_height_mils`, `body_color_3d` BGR int), `pcb.get_component_primitives(i)["pads"]`,
  `pcb.get_component_pick_place_center_mils(i, origin_relative=False)`
- SVG frame: `x = (x_mil - min_x) * 0.0254`, `y = (max_y - y_mil) * 0.0254` (mm, Y down). The renderer's viewBox
  can span metres; crop to the outline (build.py does).
- Match the outline with `<path d="`: a looser regex catches `id="scene"`.

## 2D viewer

- Layer fragments are gzip+base64 in `<script type="application/json" id="layerdata">`, decoded in the browser
  with `DecompressionStream`. CSS recolours each layer by overriding SVG presentation attributes via `--c`.
- Selection: `fit2d(true, playRing)`: frame the whole board, then play the ring (`#ring`: halo, track, comet,
  ping, plus a `#ringTag` label). `updateRing()` runs in `applyVB()` so the ring follows pan and zoom.
- Phones: `scrollIntoView` scrolls the whole page; scroll inside the list element instead.

## PDF

Stdlib HTML → `chrome --headless=new --print-to-pdf`. The zone grid is 3×3 with 4 mm overlap; labels are kept
horizontal (rotated text extracts reversed and isn't searchable). Fonts load from Google Fonts at print time.

## 3D conversion (conv3d.py, cadquery-ocp 8)

- STEP → GLB with `STEPCAFControl_Reader` + `RWGltf_CafWriter` (keeps XCAF colours), Z-up, mm.
  OCP 8 names: `OCP.collections.IndexedDataMap_TCollection_AsciiString_TCollection_AsciiString`,
  `TopoDS.Face(...)` (not `Face_s`), `Bnd_Box.CornerMin()/CornerMax()`.
- Tessellation: linear deflection `max(0.02, diag * 0.006)`, angular 0.8. Finer looks the same and lags.
- KiCad models: rotation from the `.kicad_mod` pin 1 and pad centroid vs the board pads.
- Maker models: try 24 rotations, score lead/leg positions against pad centres from the TOPSOLDER and DRILLS
  fragments. Seating: SMD = lowest point on the board; THT = first height with geometry away from the pads
  (otherwise a relay sits on its corner legs, or a part floats on its pins).
- `stacked`: a board mounted upside down above a socket (Raspberry Pi on a 2×20 header), flipped about X.

## 3D performance (measured: 430 parts, ~21 ms a frame orbiting, 3 s load)

The first version drew one mesh per CAD face: tens of thousands of draw calls, unusable when panning.

1. Merge each GLB's primitives **per colour** into one geometry.
2. One `InstancedMesh` per model × colour (146 resistors = 1–2 draws); `frustumCulled = false`.
3. Render on demand: a `dirty` flag, set by `controls.addEventListener("change", …)` (otherwise wheel zoom
   doesn't redraw) and by UI actions.
4. Picking: ray against per-part `Box3`s, not triangles.
5. `renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5))`.
6. Highlights: rebuild small extra meshes for the selection instead of recolouring instances.
7. `focusOn()` keeps the board-level camera distance (no zoom-in on select); `#fit3d` resets the view.

three.js is pinned to r128: the last release with `examples/js` (non-module) OrbitControls and GLTFLoader that
inline into a single offline HTML.

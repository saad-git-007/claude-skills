# Baked light: Cycles lightmaps and a reflection probe for a three.js scene

## Contents
1. What to bake, and what not to
2. Pipeline overview (export, bake, publish, runtime)
3. Step 1: export the scene from the browser
4. Step 2: bake in headless Blender
5. Step 3: publish for the web
6. Step 4: runtime (shader patch, code)
7. Keeping bake and code in step
8. Bugs hit, and their fixes
9. Cost of the finished result

Working reference implementation: `../scripts/lightmap-reference/` (export.mjs, bake.py, publish.py, lightmap.ts).

## 1. What to bake, and what not to

- **Targets** (receive baked light): static, opaque, standard-material surfaces: floors, walls, furniture, frames,
  signs. Not animated groups, not glass, not self-lit screens, and usually not detailed loaded models (they keep
  real-time light and the environment probe; their UVs are rarely lightmap-friendly).
- **Occluders** (cast shadows and bounce light in the bake, not baked themselves): models, plants (with alpha
  textures), terrain near the scene.
- **Emitters**: self-lit surfaces (screens, light strips), with an emission gain for the bake if they must light
  their surroundings.
- **Maps per atlas**: `natural` (sun + sky with all bounces), `lamps` (the scene's own lights and emitters), `ao`
  (occlusion within about 1 m, half size; used to dim reflections). Separate natural and lamp maps let you rebalance
  them at runtime with two gains, without re-baking.
- **Not albedo.** Bake irradiance with the surface colour divided out and keep the material's own maps: they are far
  sharper than an atlas at ~2.5 cm per texel, and PBR reflections stay intact.

## 2. Pipeline overview

```
browser (?baked=0) --export.mjs--> scene.json + scene.bin (world-space meshes, roles, materials, lights, signatures)
headless Blender   --bake.py-----> natural/lamps/ao .npy (float), uv2.json (per-corner lightmap UVs), probe .npy
python             --publish.py--> WebP maps (full and half size), gzipped UV binary, probe .hdr, manifest .json
browser            --lightmap.ts-> finds each target by signature, rebuilds its geometry with uv1, patches its material
```

Exporting from the running app (rather than rebuilding the scene in Blender by hand) guarantees the bake sees exactly
the geometry the browser draws, in the same vertex order.

## 3. Export

- Load the app with baking disabled (`?baked=0`) and in its "fully open" state (doors, roofs in the pose most users
  see). Exporting with the bake applied produced mismatched geometry.
- Walk the scene: world-space positions (`applyMatrix4(mesh.matrixWorld)`; use `.elements` when serialising a
  matrix, or you get NaNs), normals, index, uv (for alpha-tested occluders, plus the alpha texture), material colour,
  roughness, metalness, emission. Skip transparent materials without a texture (glass, fading straps).
- Record lights: point lights (position, intensity in candela, distance, decay), the sun direction and colour.
- Record a **signature** per target: vertex and index counts, world bounding box and 8 sample vertices, in
  millimetres. The runtime matches on this.
- Crop the terrain to the area that matters (90 m worked); the rest is wasted bake time.
- Run the exporter on the GPU browser (see performance.md) so it is fast.

## 4. Bake (headless Blender, `blender -b --factory-startup --python bake.py -- <workdir>`)

**Build the scene.** Create meshes from the export (three.js Y-up to Blender Z-up). Drop degenerate triangles from
occluders (Blender segfaulted setting custom normals on them); for targets, split repeated vertices instead so the
triangle count still matches. Give targets Blender's own normals (`shade_smooth`) rather than three.js's
interpolated ones: interpolated normals across big flat faces baked a sawtooth where light grazes them. Set
`shadow_terminator_geometry_offset = 1.0` and `shadow_terminator_shading_offset ≈ 0.15` for low-poly cylinders.

**Second UV set.**
1. Weld each target (remove doubles) on a copy, keeping a per-loop KEY (a UV layer holding the original triangle *
   3 + corner, and the target id): UV layers are the one loop attribute that survives welding and joining.
2. Smart UV Project (angle limit ~60°, margin 0, no scale to bounds).
3. Weight each face by importance: floor-level undersides and faces buried inside other geometry almost nothing
   (0.02; test with one scene-wide `BVHTree`: a short ray hitting something within 5 mm, or hitting a back face,
   means hidden), downward faces lower, metal less (it shows little diffuse light: .25 + .75 * (1 - metalness)),
   floors more, far architecture less. `scene.ray_cast` per face was far too slow; build one BVHTree.
4. Size each island by sqrt(area * weight / uv area); split long thin strips and sparse rings so they pack well;
   enforce a minimum of about 3 texels across (sub-texel bevel islands bled).
5. Pack with your own shelf packer (binary-search the scale, with padding of a few texels). Blender's `pack_islands`
   left islands outside 0-1 and collapsed thousands of tiny ones.
6. Copy the UVs back to the original topology by KEY.

**Light rig.** Sun as a Blender sun lamp (strength in W/m², a small angle like 0.8° for soft edges); sky as a world
shader that reproduces the app's sky colour function (port it to numpy/nodes so they match); point lights as spheres
(W = 4π · cd), small radius; emitters at their emission times a gain.

**Bake.** Cycles, CPU is fine (128 samples, 2048 atlas: ~10 minutes on a laptop i7). Passes:
`bake(type='DIFFUSE', pass_filter={'DIRECT','INDIRECT'})` with colour off, once with only natural light on and once
with only the lamps; `bake(type='AO')` with distance ~1 m at a quarter of the samples.

**Margin: bake with `margin=0` and dilate yourself.** With many objects baking into one image, Cycles grows each
object's islands against that object's mask alone, so a neighbour's margin overwrites texels another object already
baked (triangular colour patches, especially with EXTEND margins). After the bake, fill empty texels (alpha 0) from
their filled neighbours for ~16 iterations in numpy, then denoise. Keep alpha as bake coverage.

**Denoise** with OpenImageDenoise through the compositor of a throwaway scene (image node, Denoise node, render,
save EXR, read back).

**Calibrate to irradiance.** Cycles' diffuse bake is not in the renderer's units: bake a white plane under a sun of
strength 1 at normal incidence and read the value (0.3683 in Blender 5.2), then scale every map by its inverse.

**Reflection probe.** Render an equirectangular panorama (panoramic camera, `film_transparent`, Emit pass on) from a
point above the scene's centre, once per light group, as multilayer EXR (Blender 5.x: set `media_type =
'MULTI_LAYER_IMAGE'` before `file_format = 'OPEN_EXR_MULTILAYER'`; passes come out as separate EXR parts, read them
with OpenImageIO). Rotate the camera 90° about X and remap columns to three.js's equirect layout.

## 5. Publish

- Maps as sRGB-encoded fractions of a per-map range (the 99.95th percentile of covered texels, so hot spots clip
  instead of crushing everything else). The GPU decodes sRGB before filtering, which spends the 8 bits where the eye
  needs them. WebP quality ~92; also write half-size versions for phones. AO at half size is plenty.
- UVs: per target, the source vertex per new vertex (delta-coded), the index (delta-coded) and UVs quantised to 1/8
  texel as Uint16, all gzipped; the browser inflates with `DecompressionStream('gzip')`. ~400 kB for 87k triangles.
- Probe: combine the passes with the same gains as the maps, add the app's own sky where the panorama saw sky, write
  Radiance RGBE with RLE (`.hdr`, loads with `RGBELoader`). Note: some hosts (Cloudflare) send no content type for
  `.hdr`; the loader does not care.
- Content-hash every file name, and put the manifest in the source tree so code and bake always ship together.

## 6. Runtime (three.js)

For each target whose signature matches a manifest entry: rebuild the geometry with the baked vertex order and a
`uv1` attribute, clone its material once per (material, atlas), and patch the clone:

```ts
function bakedMaterial(source: THREE.MeshStandardMaterial, [natural, lamps, ao]: THREE.Texture[], range, gain) {
  const m = source.clone();
  m.lightMap = natural; m.lightMapIntensity = range.natural * gain.natural;   // textures: channel = 1 (uv1), sRGB
  const u = { lampMap: { value: lamps }, lampIntensity: { value: range.lamps * gain.lamps }, bakedAoMap: { value: ao } };
  m.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, u);
    shader.fragmentShader = 'uniform sampler2D lampMap,bakedAoMap;uniform float lampIntensity;\n' + shader.fragmentShader
      // real-time lights keep their specular highlights but add no diffuse: the maps hold it, with shadows and bounces
      .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\nreflectedLight.directDiffuse=vec3(0.0);')
      .replace('#include <lights_fragment_maps>', `vec3 baked=texture2D(lightMap,vLightMapUv).rgb*lightMapIntensity
          +texture2D(lampMap,vLightMapUv).rgb*lampIntensity;
        #if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
          irradiance=vec3(0.0); iblIrradiance+=baked;      // through three.js's energy-conserving IBL path
        #else
          irradiance=baked;
        #endif
        #if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
          radiance+=getIBLRadiance(geometryViewDir,geometryNormal,material.roughness);
        #endif`)
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>
        #if defined( USE_ENVMAP ) && defined( STANDARD )
          reflectedLight.indirectSpecular*=computeSpecularOcclusion(saturate(dot(geometryNormal,geometryViewDir)),
            texture2D(bakedAoMap,vLightMapUv).r,material.roughness);
        #endif`);
  };
  m.customProgramCacheKey = () => 'baked-light';
  return m;
}
```

Check that every `#include` you replace exists and throw otherwise. Don't try to replace `NUM_POINT_LIGHTS` tokens:
three.js substitutes them before `onBeforeCompile` sees the shader. Attach any extra textures (roughness, normal) to
the source material *before* cloning. Use the probe as `scene.environment` at intensity 1; keep the old HDRI only
for the `?baked=0` path.

Gains: tune natural and lamp gains by rendering the key views at a grid of values and matching the pre-bake
brightness per view (within about ±10%), then let the bake's softer light stand.

## 7. Keeping bake and code in step

- The manifest lists each target's signature; the runtime counts matched and missed surfaces and exposes them (for
  example `app.lightmaps = { count, missed }`); a surface that no longer matches simply keeps real-time light.
- A test loads the page and asserts `missed === 0` and `count === manifest.meshes.length`, and that every map, the UV
  file and the probe return 200 and are not an HTML fallback page. Any geometry change then fails the test until
  someone re-bakes, which is the point.
- Document the three commands (export, bake, publish) and the time they take.

## 8. Bugs hit, and their fixes

| Symptom | Cause | Fix |
|---|---|---|
| NaN positions in the export | serialised a Matrix4 object instead of `.elements` | use `.elements` |
| Blender segfault in `normals_split_custom_set` | degenerate triangles | drop them (occluders) or split repeated vertices (targets) |
| Hours of ray casting | `scene.ray_cast` per face | one `BVHTree.FromPolygons` for the scene |
| Tiny islands collapsed, UVs outside 0-1 | Blender's island packer | own shelf packer; KEY layer to copy UVs back |
| Sawtooth along grazing light under signs | three.js interpolated normals on big flat faces | Blender normals + shadow terminator offsets |
| Bleeding at bevels | sub-texel islands | minimum 3 texels per island |
| Triangular orange/teal patches on one panel | Cycles per-object bake margin overwrote neighbours in the shared atlas | `margin=0`, dilate empty texels yourself |
| Blotchy metal band, washed-out soffit | a hidden "cove" ring light in the bake | removed it; bake what the scene really has |
| 27 surfaces missed after re-bake | exported with the bake already applied | export with `?baked=0` |
| Closed roof straps in the bake | exporter included transparent helper meshes | skip transparent materials without a texture |
| Green tint in reflections | probe placed over a green emissive field | move the probe; bake it with the scene |
| +8 s load | cube-camera capture in the browser compiled second shader variants | bake the probe offline |

To debug a bake artefact: crop the float map at the face's UV rectangle, rasterise every triangle's UVs over that
region (from the published UV file *and* from the bake .blend), and check the face's weight and texel count. That
separates packing, weighting and bake causes in minutes.

## 9. Cost of the finished result (one project)

31 target meshes (87k triangles), one 2048 atlas at ~2.6 cm per texel. Frame time +3.4% (12.5 to 13.0 ms), ready
time +0.8 s, download +1.6 MB desktop / +1.1 MB phone (half-size maps), ~48 MB texture memory. Bake ~10 minutes on
a laptop CPU, full pipeline ~13 minutes.

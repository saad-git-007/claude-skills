# Realism: materials, environment, vegetation, assets, review

## Contents
1. Materials and textures
2. Light, sky and environment
3. Water
4. Vegetation (impostors)
5. glTF assets
6. Reviewing the look

## 1. Materials and textures

- Roughness variation sells realism more than colour detail. A flat `roughness: 0.6` reads as plastic; a real
  roughness map (raise its contrast if the source is subtle) makes concrete, stone and wood read as real.
- Sources: Poly Haven and ambientCG (CC0). Download diffuse, normal and roughness at 1-2k, convert to WebP.
- Colour spaces: diffuse/albedo `THREE.SRGBColorSpace`; normal, roughness, metalness, AO linear (the default).
- Normal maps: Poly Haven ships `nor_gl` (OpenGL, +Y up; right for three.js) and `nor_dx`; use `nor_gl` or flip
  green. Keep `normalScale` modest (0.5-1) on hard surfaces.
- Tile with `wrapS = wrapT = RepeatWrapping` and a repeat that gives a believable real-world scale (floor tiles, wood
  grain width). Set anisotropy (up to 8) on anything seen at grazing angles, especially floors.
- Wood: a real veneer photo (for example a smoked black oak) beats a procedural one; lacquer = `MeshPhysicalMaterial`
  with `clearcoat` ~0.8, clearcoat roughness ~0.2.
- With baked light, attach these maps before the bake clones the material (see lightmaps.md), and remember the
  material colour multiplies the baked irradiance.
- Record every asset's source and licence (and modifications, for CC BY) where the project keeps credits.

## 2. Light, sky and environment

- One sun: the same direction and colour in the sky shader, the real-time directional light, the bake rig, the
  impostor bakes and the canopy shading. Mismatched suns are what make a scene look composited.
- The environment map drives reflections and ambient light for everything not baked. An HDRI of an unrelated place
  makes metal reflect the wrong world; a probe baked from the scene itself (lightmaps.md) reflects the real room.
  Low-resolution environments are fine: they feed blurred PMREM lighting (a 512x256 HDR was enough).
- Emissive surfaces (screens, strips) look right when they also light their surroundings; in a bake they can, as
  emitters with a gain.
- Warm task lights under signs, cool daylight from outside: colour contrast between light sources is a large part of
  the "photographed" look.

## 3. Water

A large ocean plane looked convincing with: Schlick Fresnel with F0 = 0.02, sky reflection by the view direction,
Blinn-Phong sun lobes (a broad one and a tight one) for glitter, and a fade to the horizon colour with distance.
Draw it after the terrain (performance.md).

## 4. Vegetation (impostors)

Cross-plane tree cards look fake from most angles. What worked:

- Bake hemi-octahedral impostors from real tree models in headless Blender (EEVEE on the GPU, about a minute per tree
  with `env -u DISPLAY` so it uses EGL): albedo+alpha and normal atlases for a set of view directions.
- At runtime, one InstancedMesh per species; per pixel, blend the three nearest baked views with one parallax step;
  light from the baked normals with the scene's sun; alpha-to-coverage edges; foliage photo detail where magnified.
- Place trees deterministically (seeded), each with its own sunlit height; keep crowns away from camera paths.
- A canopy "fill" under the crowns for dense forest: its face shaded as the dark interior (shaded undersides,
  trunks), never the foliage photo, which on a steep face reads as a hedge wall. Start it inside the forest edge so
  the edge trees stand in front of it.
- A distant canopy texture rendered once on the GPU at load (crowns, their shading and shadows for the fixed sun).
- Half-size atlases on phones and on a "Performance" setting.

## 5. glTF assets

- Optimise every model: `gltf-transform optimize in.glb out.glb --compress meshopt --texture-compress webp
  --texture-size 512 --simplify true --simplify-ratio 0.6 --simplify-error 0.0008` (register three's
  `MeshoptDecoder`). Or `webp`, `dedup`, `prune`, `quantize` steps separately (KHR_mesh_quantization loads natively).
  One project halved its model download this way (8.5 to 4.2 MB).
- `optimize` merges plain materials into palettes and renames them: find meshes by mesh name, not material name, and
  pass `--palette false` if colours must stay editable.
- Blender GLB export: `use_active_scene=True`; `use_selection` alone once pulled in objects from other scenes and
  tripled the file size. Check orientation (front facing the camera) and scale after import.
- Screens inside models: map a canvas texture to the mesh named `Screen` (or equivalent) rather than hunting
  materials.

## 6. Reviewing the look

- Render the same fixed views before and after on the GPU (1280x720 is enough for review), compose them side by side
  with labels, and look at each one. Check mean brightness per view against the baseline (0.95-1.10 is a sane band
  after a lighting change).
- Look specifically for: blotches or patches on large flat panels (bake margins, UV density), light leaking at
  corners, sawtooth along grazing light, floating objects, reflections of the wrong thing, crushed blacks.
- Check a phone viewport too (half-size maps, different framing).
- Send the renders to the user; realism is their call, and they will spot things tests cannot.

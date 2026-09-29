# Lightmap step 2 of 3: unwrap, pack and bake in Cycles (about 20 minutes on the dev laptop's CPU).
#   blender -b --factory-startup --python scripts/lightmap/bake.py -- <workdir> [--samples 128] [--size 2048] [--texel 0.025]
# Reads <workdir>/scene.json + scene.bin (export.mjs) and the light rig (lights.json), builds the lab in Blender
# (three.js y-up becomes Blender z-up), gives every lightmap target a second UV set packed into atlases (as many as
# `texel`, the target size of a texel in metres, needs), bakes and denoises, and writes per atlas, as float16 NumPy:
#   natural-<a>.npy  sun and sky, direct and bounced (diffuse irradiance, the surface's own colour divided out)
#   lamps-<a>.npy    the room's own lights: point lights, the desk lamp, screens, light strips and the cove light
#   ao-<a>.npy       ambient occlusion within 1 m (the runtime dims reflections with it)
# (alpha: 1 where something was baked), probe-natural.npy and probe-lamps.npy (the reflection probe, below), and
# uv2.json: per target, the vertex split and UVs that publish.py packs.
# --only <ids> limits the targets, --stop pack stops after packing (saving pack.blend) and --stop maps skips the
# three bakes, for quick experiments.
import bpy, bmesh, json, math, sys, os, time
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
work = argv[0]
opt = {'samples': 128, 'size': 2048, 'texel': 0.025, 'only': '', 'stop': ''}
for i, a in enumerate(argv):
    if a.startswith('--'): opt[a[2:]] = type(opt.get(a[2:], ''))(argv[i + 1])
SIZE, SAMPLES, TEXEL = int(opt['size']), int(opt['samples']), float(opt['texel'])
t0 = time.time()
def log(*a): print(f'[{time.time() - t0:7.1f}s]', *a, flush=True)

scene_json = json.load(open(os.path.join(work, 'scene.json')))
rig = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lights.json')))
# Cycles' diffuse bake (surface colour divided out) reads 0.3683 under a sun of strength 1 at normal incidence; the
# browser wants irradiance (that sun = 1), so the light maps are scaled by this.
TO_IRRADIANCE = 1 / 0.3683
blob = open(os.path.join(work, 'scene.bin'), 'rb').read()
def arr(offset, count, dtype, width):
    return np.frombuffer(blob, dtype=dtype, count=count * width, offset=offset).reshape(count, width)
# three.js (x, y, z) -> Blender (x, -z, y)
def to_blender(v): return np.stack([v[:, 0], -v[:, 2], v[:, 1]], axis=1)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
cy = scene.cycles
cy.device = 'CPU'
cy.samples = SAMPLES
cy.use_denoising = False
cy.max_bounces = 6; cy.diffuse_bounces = 4; cy.glossy_bounces = 2; cy.transmission_bounces = 2; cy.transparent_max_bounces = 8
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.sample_clamp_indirect = 6.0
cy.min_light_bounces = 2  # dark surfaces: no Russian roulette on the first bounces (less noise after dividing out albedo)
scene.render.threads_mode = 'AUTO'

# ---------------- materials ----------------
def principled(name, m, emission_on=True):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    c = m.get('color', [.5, .5, .5])
    bsdf.inputs['Base Color'].default_value = (*c, 1)
    bsdf.inputs['Roughness'].default_value = max(.05, m.get('roughness', .5))
    # Keep some diffuse on every surface so the diffuse bake has something to divide by.
    bsdf.inputs['Metallic'].default_value = min(.9, m.get('metalness', 0))
    e = m.get('emission', [0, 0, 0])
    for rule in rig['emitters']:
        if max(e) > 1e-4 and np.linalg.norm(np.array(e) - rule['near']) < .1 * np.linalg.norm(rule['near']): e = [x * rule['gain'] for x in e]
    if emission_on and max(e) > 1e-4:
        k = max(e); bsdf.inputs['Emission Color'].default_value = (*[x / k for x in e], 1); bsdf.inputs['Emission Strength'].default_value = k
    mat['emission'] = list(e); mat['estrength'] = max(e)
    return mat

def alpha_texture(mat, data_url, name):
    import base64
    png = base64.b64decode(data_url.split(',', 1)[1]); path = os.path.join(work, f'alpha-{name}.png')
    open(path, 'wb').write(png)
    img = bpy.data.images.load(path); img.colorspace_settings.name = 'sRGB'
    nt = mat.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UV'
    nt.links.new(uv.outputs['UV'], tex.inputs['Vector']); nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])

# ---------------- geometry ----------------
objects = {}
for rec in scene_json['meshes']:
    if opt['only'] and rec['role'] == 'target' and str(rec['id']) not in opt['only'].split(','): continue
    P = to_blender(arr(rec['position'], rec['vertices'], np.float32, 3))
    I = arr(rec['index'], rec['triangles'], np.uint32, 3).astype(np.int64)
    # Blender faces cannot use a vertex twice. Occluders drop such (zero-area) triangles; targets must keep every
    # triangle in order, so their repeated corners get copies of the vertex (`dup` maps a copy back to the original).
    bad = (I[:, 0] == I[:, 1]) | (I[:, 1] == I[:, 2]) | (I[:, 0] == I[:, 2])
    dup = []
    if bad.any() and rec['role'] != 'target': I = I[~bad]
    elif bad.any():
        I = I.copy(); base_n = len(P)
        for t in np.where(bad)[0]:
            for k in (1, 2):
                if I[t, k] in I[t, :k]: dup.append(int(I[t, k])); I[t, k] = base_n + len(dup) - 1
        P = np.concatenate([P, P[dup]])
    me = bpy.data.meshes.new(f"{rec['role']}-{rec['id']}")
    me.vertices.add(len(P)); me.vertices.foreach_set('co', P.ravel())
    me.loops.add(len(I) * 3); me.loops.foreach_set('vertex_index', I.ravel().astype(np.int32))
    me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, len(I) * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    # Targets bake with Blender's own normals (flat where three.js left triangles unwelded, as on the rounded boxes;
    # smooth across shared vertices, as on cylinders and revolves): three.js's interpolated normals across a big flat
    # face tilt in and out of light that grazes it, which baked a sawtooth under the sign light bars.
    if rec['role'] == 'target': me.shade_smooth()
    elif rec['normal'] >= 0:
        N = to_blender(arr(rec['normal'], rec['vertices'], np.float32, 3))
        if dup: N = np.concatenate([N, N[dup]])
        me.normals_split_custom_set_from_vertices([tuple(n) for n in N])
    if 'uv' in rec:
        U = arr(rec['uv'], rec['vertices'], np.float32, 2)
        if dup: U = np.concatenate([U, U[dup]])
        uvl = me.uv_layers.new(name='UV'); uvl.data.foreach_set('uv', U[I.ravel()].ravel())
    ob = bpy.data.objects.new(me.name, me); scene.collection.objects.link(ob)
    mat = principled(me.name, rec['material'])
    if rec['material'].get('alpha'): alpha_texture(mat, rec['material']['alpha'], rec['id'])
    me.materials.append(mat)
    ob['role'] = rec['role']; ob['rid'] = rec['id']; ob['label'] = rec['name']; ob['nsrc'] = rec['vertices']; ob['dup'] = dup
    # Smooth-shaded low-poly cylinders and revolves: without these offsets Cycles shades their facets' shadow
    # terminator as a sawtooth.
    ob.shadow_terminator_geometry_offset = 1.0; ob.shadow_terminator_shading_offset = .15
    objects[rec['id']] = ob
targets = [ob for ob in objects.values() if ob['role'] == 'target']
log('built', len(objects), 'objects,', len(targets), 'targets')

# ---------------- second UV set: weld, unwrap, weight, pack ----------------
# The runtime geometry is three.js's (often unwelded: rounded boxes are triangle soup), so unwrapping happens on a
# welded copy that remembers, per loop, which face and corner it came from; the UVs are then copied back per corner.
def weights_for(ob, bm):
    # Texel importance per face: undersides at floor level and faces buried under other geometry get almost none,
    # desk undersides a third, the floor extra, and metal and the far-off architecture less.
    bsdf = next(n for n in ob.data.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    # Metal shows little diffuse light, so baked detail on it is barely seen: density follows how diffuse it is.
    base = .25 + .75 * (1 - bsdf.inputs['Metallic'].default_value)
    lab = ob['label']
    if lab.startswith('Observatory lens'): base *= .55
    if lab == 'Expanded glass pavilion' and bsdf.inputs['Roughness'].default_value > .6: base *= 1.8
    w = {}
    for f in bm.faces:
        c = f.calc_center_median(); n = f.normal
        k = base
        if n.z < -.5 and c.z < .3: k = .02
        elif c.z < -.8: k = .02
        elif c.z < -.1 and math.hypot(c.x, c.y) < 12.45: k = .02  # under the pavilion floor
        elif n.z < -.5 and c.z < 3.0: k = base * .35
        else:
            # Hidden: pressed against another surface, or inside a solid (the ray meets a face from behind).
            loc, hn, _, dist = bvh.ray_cast(c + n * 1e-4, n, 2.0)
            if loc is not None and (dist < .005 or hn.dot(n) > 0): k = .02
        w[f.index] = k
    if os.environ.get('LM_DEBUG'):
        by = {}
        for f in bm.faces: by[w[f.index]] = by.get(w[f.index], 0) + f.calc_area()
        log('  weights', lab[:20], {round(k, 3): round(v, 1) for k, v in by.items()})
    return w

# One ray-tracing structure over the whole scene, for the covered-face test above.
from mathutils.bvhtree import BVHTree
_v, _f, _n = [], [], 0
for ob in objects.values():
    me = ob.data; co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co)
    vi = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
    _v.append(co.reshape(-1, 3)); _f.append(vi.reshape(-1, 3) + _n); _n += len(me.vertices)
bvh = BVHTree.FromPolygons(np.concatenate(_v).tolist(), np.concatenate(_f).tolist(), all_triangles=True)
del _v, _f
log('bvh built')

welded = []; targets_by_weld = []
for ob in targets:
    bm = bmesh.new(); bm.from_mesh(ob.data)
    # KEY (a UV layer, the one kind of loop data that survives welding and joining): the loop's index in the
    # three.js topology (triangle * 3 + corner) in x, and later the target it belongs to in y.
    kl = bm.loops.layers.uv.new('KEY')
    for f in bm.faces:
        for k, loop in enumerate(f.loops): loop[kl].uv = (f.index * 3 + k, 0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    me = bpy.data.meshes.new(ob.name + '-weld'); bm.to_mesh(me); bm.free()
    wo = bpy.data.objects.new(me.name, me); scene.collection.objects.link(wo); wo['src'] = ob.name
    welded.append(wo); targets_by_weld.append(ob)
log('welded')

bpy.ops.object.select_all(action='DESELECT')
for wo in welded: wo.select_set(True)
bpy.context.view_layer.objects.active = welded[0]
for wo in welded: wo.data.uv_layers.active = wo.data.uv_layers.new(name='LM')
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
log('unwrapped')

# Islands, texel density and packing. Blender's own packer dropped thousands of tiny islands (collapsing them), so
# islands are sized and placed here: each island gets atlas area in proportion to its surface area times its
# importance, then a shelf packer places the bounding boxes (rotated to lie flat) at the largest scale that fits.
def islands(bm, uvl):
    # faces connected through shared UV coordinates at shared vertices
    parent = {f.index: f.index for f in bm.faces}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) < 2: continue
        for i in range(1, len(lf)):
            a, b = lf[0], lf[i]
            ok = True
            for v in e.verts:
                ua = next(l[uvl].uv for l in a.loops if l.vert == v); ub = next(l[uvl].uv for l in b.loops if l.vert == v)
                if (ua - ub).length > 1e-6: ok = False; break
            if ok: parent[find(a.index)] = find(b.index)
    groups = {}
    for f in bm.faces: groups.setdefault(find(f.index), []).append(f)
    return list(groups.values())

records = {}  # welded object name -> list of [loop indices, uv in weighted metres]
area_total = 0.0
per_object_area = {}
for wo in welded:
    src = bpy.data.objects[wo['src']]
    bm = bmesh.new(); bm.from_mesh(wo.data); bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv['LM']
    w = weights_for(src, bm)
    recs = []; a_obj = 0.0
    for isl in islands(bm, uvl):
        k = max(w[f.index] for f in isl)
        loops = np.array([l.index for f in isl for l in f.loops])
        uv = np.array([l[uvl].uv[:] for f in isl for l in f.loops], np.float64)
        t = uv.reshape(-1, 3, 2)
        a_uv = np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1]) - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1])).sum() / 2
        a3 = sum(f.calc_area() for f in isl)
        scale = math.sqrt(a3 * k / a_uv) if a_uv > 1e-14 and a3 > 1e-10 else 0.0
        uv = (uv - uv.min(0)) * scale
        recs.append([loops, uv]); a_obj += a3 * k
    bm.free()
    records[wo.name] = recs; per_object_area[wo.name] = a_obj; area_total += a_obj
    if os.environ.get('LM_DEBUG'): log('weighted', src['label'][:30], len(wo.data.polygons), 'faces', len(recs), 'islands', f'{a_obj:.1f} m2')
# How many atlases at the requested texel size, packing about 60% full; biggest objects first into the emptiest.
capacity = (SIZE * TEXEL) ** 2 * .6
n_atlas = max(1, math.ceil(area_total / capacity))
log(f'weighted area {area_total:.0f} m2 -> {n_atlas} atlas(es) of {SIZE}px at {TEXEL*100:.1f} cm')
bins = [[] for _ in range(n_atlas)]; load = [0.0] * n_atlas
for wo in sorted(welded, key=lambda o: -per_object_area[o.name]):
    i = load.index(min(load)); bins[i].append(wo); load[i] += per_object_area[wo.name]
PAD = 4 / SIZE  # atlas units between islands: 2 texels each side at full size, 1 at the -1k size
MIN = 3 / SIZE  # every island at least 3 texels across (a bevel narrower than a texel would bake no texel of its own)

def sparse_split(loops, uv, small):
    # Islands that fill little of their box (rings: an unrolled soffit or beam top) waste the atlas; cut them into
    # quadrants, recursively, until each piece is reasonably solid or small.
    t = uv.reshape(-1, 3, 2); lo = uv.min(0); wh = uv.max(0) - lo
    area = np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1]) - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1])).sum() / 2
    if len(t) < 2 or max(wh) < small or area > .35 * wh[0] * wh[1]: return [(loops, uv)]
    c = t.mean(1) - lo; q = ((c[:, 0] > wh[0] / 2).astype(int) + 2 * (c[:, 1] > wh[1] / 2)).repeat(3)
    if len(np.unique(q)) < 2: return [(loops, uv)]
    return [p for i in range(4) if (q == i).any() for p in sparse_split(loops[q == i], uv[q == i], small)]

def shelf(boxes, S):
    # Shelves with the space beside each shelf's first (tallest) box packed again as smaller shelves, recursively:
    # plain shelves waste the height beside a big island such as the floor. boxes: (w, h), tallest first.
    # Returns positions, or None if they do not fit at scale S.
    dims = [(max(w * S, MIN) + PAD, max(h * S, MIN) + PAD) for w, h in boxes]
    pos = [None] * len(dims); min_w = min(d[0] for d in dims)
    def fill(order, x0, y0, x1, y1):
        # Place what fits in the rectangle, tallest first; return the indices left over, in order.
        if not order or x1 - x0 < min_w or y1 - y0 < dims[order[-1]][1]: return order
        left = []; y = y0; i = 0
        while i < len(order):
            if y1 - y < dims[order[-1]][1]: return left + order[i:]
            k = order[i]; W, H = dims[k]
            if W > x1 - x0 or H > y1 - y: left.append(k); i += 1; continue
            pos[k] = (x0, y); rest = fill(order[i + 1:], x0 + W, y, x1, y + H)
            y += H; order = rest; i = 0
        return left
    return pos if not fill(list(range(len(dims))), 0.0, 0.0, 1.0, 1.0) else None

for a, group in enumerate(bins):
    items = []
    # Long strips (a ring beam unrolls to 70 m) would set the scale on their own: cut them into pieces no longer than
    # a quarter of the atlas's side (a seam across a strip is hard to see).
    side = math.sqrt(sum(per_object_area[wo.name] for wo in group) / .7)
    for wo in group:
        bpy.data.objects[wo['src']]['atlas'] = a
        for loops, uv in records[wo.name]:
            wh = uv.max(0) if len(uv) else np.zeros(2)
            if wh[1] > wh[0]: uv = np.stack([uv[:, 1], wh[0] - uv[:, 0]], 1); wh = wh[::-1]
            n = int(math.ceil(wh[0] / (side / 4))) if wh[0] > side / 4 and wh[0] > 3 * wh[1] else 1
            if n > 1:
                cu = uv.reshape(-1, 3, 2)[:, :, 0].mean(1); part = np.minimum((cu / wh[0] * n).astype(int), n - 1).repeat(3)
                pieces = [(loops[part == i], uv[part == i]) for i in range(n) if (part == i).any()]
            else: pieces = [(loops, uv)]
            pieces = [q for pl, pu in pieces for q in sparse_split(pl, pu, side / 24)]
            for pl, pu in pieces:
                pu = pu - pu.min(0); pwh = pu.max(0)
                items.append((max(pwh[0], 1e-4), max(pwh[1], 1e-4), wo.name, (pl, pu)))
    items.sort(key=lambda it: -it[1])
    boxes = [(w, h) for w, h, *_ in items]
    lo, hi = 0.0, 4.0 / math.sqrt(max(sum(w * h for w, h in boxes), 1e-9))
    for _ in range(18):
        mid = (lo + hi) / 2
        if shelf(boxes, mid): lo = mid
        else: hi = mid
    S = lo; pos = shelf(boxes, S)
    used = sum(w * h for w, h in boxes) * S * S
    for (w, h, name, (loops, uv)), (x, y) in zip(items, pos):
        # Narrow islands are stretched across to the minimum (a lightmap may be anisotropic).
        sx, sy = max(w * S, MIN) / (w * S), max(h * S, MIN) / (h * S)
        rec_uv = uv * S * np.array([sx, sy]) + np.array([x + PAD / 2, y + PAD / 2])
        wo = bpy.data.objects[name]; lm = wo.data.uv_layers['LM']
        buf = np.zeros(len(wo.data.loops) * 2, np.float32); lm.data.foreach_get('uv', buf); buf = buf.reshape(-1, 2)
        buf[loops] = rec_uv; lm.data.foreach_set('uv', buf.ravel())
    log(f'atlas {a}: {len(group)} objects, {len(items)} islands, {used * 100:.0f}% used, {1 / (S * SIZE) * 100:.2f} cm per texel at weight 1')

if opt['stop'] == 'pack': bpy.ops.wm.save_as_mainfile(filepath=os.path.join(work, 'pack.blend')); log('stopping after pack'); sys.exit(0)
# Copy the packed UVs back to the three.js topology, corner by corner (KEY.x is the original loop).
for wo, ob in zip(welded, targets_by_weld):
    wm, me = wo.data, ob.data
    uv_src = np.zeros((len(wm.loops), 2), np.float32); wm.uv_layers['LM'].data.foreach_get('uv', uv_src.ravel())
    key = np.zeros((len(wm.loops), 2), np.float32); wm.uv_layers['KEY'].data.foreach_get('uv', key.ravel())
    out = np.full((len(me.loops), 2), -1.0, np.float32); out[np.round(key[:, 0]).astype(np.int64)] = uv_src
    # Faces the weld collapsed (zero area, never seen): borrow any UV of the same vertex, else the atlas corner.
    missing = np.where(out[:, 0] < 0)[0]
    if len(missing):
        vi = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
        known = {}
        for li in range(len(me.loops)):
            if out[li, 0] >= 0: known.setdefault(vi[li], out[li])
        for li in missing: out[li] = known.get(vi[li], np.zeros(2, np.float32))
    lm = me.uv_layers.new(name='LM'); lm.data.foreach_set('uv', out.ravel())
    me.uv_layers.active = lm
    bpy.data.objects.remove(wo)
log('uv2 copied back')

# ---------------- lights ----------------
def sky_image(w=1024, h=512):
    # Port of skyColor() in src/landscape.ts, without the sun's disc (the sun lamp below carries that light).
    sun = np.array([.38, .075, -.92]); sun /= np.linalg.norm(sun)
    u = (np.arange(w) + .5) / w; v = (np.arange(h) + .5) / h
    U, V = np.meshgrid(u, v)
    phi = (.5 - U) * 2 * math.pi; th = (V - .5) * math.pi
    bx, by, bz = np.cos(phi) * np.cos(th), np.sin(phi) * np.cos(th), np.sin(th)
    d = np.stack([bx, bz, -by], -1)  # three.js direction
    y = np.maximum(d[..., 1], 0)
    hs = sun[[0, 2]] / np.linalg.norm(sun[[0, 2]])
    dxz = d[..., [0, 2]] + 1e-5; dxz = dxz / np.linalg.norm(dxz, axis=-1, keepdims=True)
    toward = np.maximum((dxz * hs).sum(-1), 0)[..., None]
    mix = lambda a, b, t: a + (b - a) * t
    ss = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
    horizon = mix(np.array([.50, .46, .66]), np.array([1.0, .50, .24]), toward ** 2.2)
    mid = mix(np.array([.20, .27, .58]), np.array([.75, .42, .40]), toward ** 3.5 * .7)
    c = mix(horizon, mid, ss(0, .14, y)[..., None])
    c = mix(c, np.array([.03, .07, .22]), ss(.12, .75, y)[..., None])
    s = np.maximum((d * sun).sum(-1), 0)[..., None]
    c = c + np.array([1.0, .52, .22]) * s ** 5 * .5 + np.array([1.0, .75, .45]) * s ** 50 * .9
    img = bpy.data.images.new('sky', w, h, float_buffer=True)
    px = np.concatenate([c, np.ones((h, w, 1))], -1).astype(np.float32)
    img.pixels.foreach_set(px.ravel()); return img

world = bpy.data.worlds.new('sky'); scene.world = world
wn = world.node_tree.nodes; bg = next(n for n in wn if n.type == 'BACKGROUND')
env = wn.new('ShaderNodeTexEnvironment'); env.image = sky_image(); world.node_tree.links.new(env.outputs['Color'], bg.inputs['Color'])
SUN = Vector((.38, -(-.92), .075)).normalized()  # Blender coords of the three.js sunDir
sun_data = bpy.data.lights.new('sun', 'SUN'); sun_data.energy = rig['sun']['strength']; sun_data.angle = math.radians(rig['sun']['angle'])
sun_data.color = tuple(rig['sun']['color'])
sun_ob = bpy.data.objects.new('sun', sun_data); scene.collection.objects.link(sun_ob)
sun_ob.rotation_euler = (-SUN).to_track_quat('-Z', 'Y').to_euler()

lamps = []
for L in scene_json['lights']:
    if L['type'] != 'PointLight': continue
    p = L['position']; ld = bpy.data.lights.new('lamp', 'POINT')
    # three.js candela -> Cycles watts (irradiance I/d^2 on both sides)
    ld.energy = 4 * math.pi * L['intensity'] * rig['pointLights']['gain']; ld.color = tuple(L['color'])
    ld.shadow_soft_size = rig['pointLights']['smallRadius'] if L['intensity'] < 3 else rig['pointLights']['radius']
    lo = bpy.data.objects.new('lamp', ld); lo.location = (p[0], -p[2], p[1]); scene.collection.objects.link(lo); lamps.append(lo)

# The cove: a thin emitting ring (bake only) just inside and under the ring beam.
cv = rig['cove']
if cv['strength'] > 0:
    bpy.ops.mesh.primitive_torus_add(major_radius=cv['radius'], minor_radius=cv['tube'], major_segments=192, minor_segments=8, location=(0, 0, cv['height']))
    cove = bpy.context.active_object; cove.name = 'cove'
    cmat = bpy.data.materials.new('cove'); cbs = next(n for n in cmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    cbs.inputs['Base Color'].default_value = (0, 0, 0, 1)
    cmat['emission'] = [c * cv['strength'] for c in cv['color']]; cmat['estrength'] = cv['strength']
    cbs.inputs['Emission Color'].default_value = (*cv['color'], 1); cbs.inputs['Emission Strength'].default_value = cv['strength']
    cove.data.materials.append(cmat); cove['role'] = 'light'

def natural(on):
    sun_ob.hide_render = not on; bg.inputs['Strength'].default_value = rig['sky']['strength'] if on else 0.0
def lamps_on(on):
    for lo in lamps: lo.hide_render = not on
    for mat in bpy.data.materials:
        if 'emission' not in mat.keys() or not mat.node_tree: continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf and max(mat['emission']) > 1e-4:
            bsdf.inputs['Emission Strength'].default_value = mat['estrength'] if on else 0.0

# ---------------- bake ----------------
atlases = sorted({ob['atlas'] for ob in targets})
def bake(kind):
    imgs = {a: bpy.data.images.new(f'{kind}-{a}', SIZE, SIZE, float_buffer=True, alpha=True) for a in atlases}
    for img in imgs.values(): img.generated_color = (0, 0, 0, 0)
    for ob in targets:
        # Each target gets its own material copy holding its atlas image as the active bake node.
        mat = ob.data.materials[0]
        nt = mat.node_tree
        node = nt.nodes.get('LMBAKE') or nt.nodes.new('ShaderNodeTexImage'); node.name = 'LMBAKE'
        uvn = nt.nodes.get('LMUV') or nt.nodes.new('ShaderNodeUVMap'); uvn.name = 'LMUV'; uvn.uv_map = 'LM'
        nt.links.new(uvn.outputs['UV'], node.inputs['Vector'])
        node.image = imgs[ob['atlas']]; nt.nodes.active = node; node.select = True
    bpy.ops.object.select_all(action='DESELECT')
    for ob in targets: ob.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    # No margin from Cycles: it grows each object's islands against that object alone, so with every target in one
    # image a neighbour's margin painted over texels already baked (triangular patches on a large sign panel). The
    # margin is grown afterwards over empty texels only (dilate).
    b = scene.render.bake; b.margin = 0; b.use_clear = True; b.target = 'IMAGE_TEXTURES'
    if kind == 'ao':
        world.light_settings.distance = 1.0
        bpy.ops.object.bake(type='AO', margin=0, use_clear=True)
    else:
        b.use_pass_direct = True; b.use_pass_indirect = True; b.use_pass_color = False
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=0, use_clear=True)
    log('baked', kind)
    for a, img in imgs.items():
        dilate(img)
        px = denoise(img, f'{kind}-{a}')
        if kind != 'ao': px[..., :3] *= TO_IRRADIANCE
        np.save(os.path.join(work, f'{kind}-{a}.npy'), px.astype(np.float16))
    log('denoised', kind)

# Grows every island by up to 16 texels into empty space (alpha 0): each empty texel next to filled ones takes their
# mean. The islands keep their own texels, and filtering and mipmaps at their edges see their light, not black.
# Alpha stays the coverage of the bake itself.
def dilate(img, steps=16):
    w, h = img.size; px = np.zeros(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    rgb = px[..., :3] * (px[..., 3:] > .5); have = (px[..., 3] > .5).astype(np.float32)
    for _ in range(steps):
        s = np.zeros_like(rgb); n = np.zeros_like(have)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            s += np.roll(rgb * have[..., None], (dy, dx), (0, 1)); n += np.roll(have, (dy, dx), (0, 1))
        grow = (have == 0) & (n > 0)
        if not grow.any(): break
        rgb[grow] = s[grow] / n[grow][:, None]; have[grow] = 1
    px[..., :3] = rgb; img.pixels.foreach_set(px.ravel())

# Intel Open Image Denoise, through the compositor of a throwaway empty scene (rendering it costs next to nothing).
def denoise(img, name):
    w, h = img.size
    sc = bpy.data.scenes.new('denoise'); sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.device = 'CPU'
    sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    tree = bpy.data.node_groups.new('denoise', 'CompositorNodeTree'); sc.compositing_node_group = tree
    tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    src = tree.nodes.new('CompositorNodeImage'); src.image = img
    dn = tree.nodes.new('CompositorNodeDenoise'); out = tree.nodes.new('NodeGroupOutput')
    tree.links.new(src.outputs['Image'], dn.inputs['Image']); tree.links.new(dn.outputs['Image'], out.inputs[0])
    sc.render.use_compositing = True; sc.render.image_settings.file_format = 'OPEN_EXR'
    bpy.ops.render.render(write_still=False, scene=sc.name)
    path = os.path.join(work, f'{name}.exr')
    bpy.data.images['Render Result'].save_render(path, scene=sc)
    back = bpy.data.images.load(path); px = np.zeros(w * h * 4, np.float32); back.pixels.foreach_get(px)
    raw = np.zeros(w * h * 4, np.float32); img.pixels.foreach_get(raw)
    bpy.data.images.remove(back); bpy.data.scenes.remove(sc)
    # Alpha from the raw bake: 0 where nothing was baked (the margin included).
    return np.concatenate([px.reshape(h, w, 4)[..., :3], raw.reshape(h, w, 4)[..., 3:]], -1)

for ob in objects.values(): ob.select_set(False)
if opt['stop'] != 'maps':  # --stop maps: skip the three bakes (to test the probe)
    natural(True); lamps_on(False); bake('natural')
    natural(False); lamps_on(True); bake('lamps')
    natural(True); lamps_on(False)
    cy.samples = max(32, SAMPLES // 4); bake('ao')

# ---------------- reflection probe ----------------
# An equirectangular panorama from above the open roof, as the scene environment (reflections and the models' ambient
# light). Rendered twice with the sky transparent, so publish.py can weigh it like the maps: lit surfaces times the
# natural and lamp gains, emitters as they are (Emit pass), and the visible sky from skyColor().
PROBE = (0.0, -1.5, 8.0)  # Blender coordinates of three.js (0, 8, 1.5)
def panorama(kind):
    cam = bpy.data.cameras.new('probe'); cam.type = 'PANO'; cam.panorama_type = 'EQUIRECTANGULAR'
    co = bpy.data.objects.new('probe', cam); scene.collection.objects.link(co); scene.camera = co
    co.location = PROBE; co.rotation_euler = (math.radians(90), 0, 0)  # centre of the image = +Y, +X at 3/4, +Z up
    r = scene.render; r.resolution_x, r.resolution_y, r.resolution_percentage = 512, 256, 100; r.film_transparent = True
    r.use_compositing = False; scene.compositing_node_group = None
    vl = scene.view_layers[0]; vl.use_pass_emit = True
    cy.use_denoising = True; cy.samples = SAMPLES
    r.image_settings.media_type = 'MULTI_LAYER_IMAGE'; r.image_settings.file_format = 'OPEN_EXR_MULTILAYER'; r.filepath = os.path.join(work, f'probe-{kind}.exr')
    bpy.ops.render.render(write_still=True)
    import OpenImageIO as oiio
    # Each pass is its own part of the file: find it by channel name.
    inp = oiio.ImageInput.open(r.filepath); parts = {}; n = 0
    while inp.seek_subimage(n, 0):
        parts[inp.spec().channelnames[0].split('.')[1]] = inp.read_image(format='float'); n += 1
    inp.close()
    comb = parts['Combined']; emit = parts['Emission'][..., :3]
    # To three.js's equirect layout (u = atan2(z, x) / 2pi + .5 in its own axes): a column remap.
    w = comb.shape[1]; phi = ((np.arange(w) + .5) / w - .5) * 2 * math.pi
    ub = (.5 + np.arctan2(np.cos(phi), -np.sin(phi)) / (2 * math.pi)) * w - .5
    cols = np.mod(np.round(ub).astype(int), w)
    np.save(os.path.join(work, f'probe-{kind}.npy'), np.concatenate([comb[:, cols], emit[:, cols]], -1).astype(np.float32))
    bpy.data.objects.remove(co)
natural(True); lamps_on(False); panorama('natural')
natural(False); lamps_on(True); panorama('lamps')
log('probe rendered')

# ---------------- second UV set for the browser ----------------
uv2 = []
for ob in targets:
    me = ob.data
    vi = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
    dup = list(ob['dup'])
    if dup: vi = np.where(vi >= ob['nsrc'], np.array([0] + dup)[np.clip(vi - ob['nsrc'] + 1, 0, None)], vi)
    uv = np.zeros((len(me.loops), 2), np.float32); me.uv_layers['LM'].data.foreach_get('uv', uv.ravel())
    q = np.round(uv * 65535).astype(np.int64)
    keys = vi.astype(np.int64) * (1 << 34) + q[:, 0] * (1 << 17) + q[:, 1]
    uniq, first, inverse = np.unique(keys, return_index=True, return_inverse=True)
    uv2.append({'id': ob['rid'], 'atlas': ob['atlas'], 'src': vi[first].tolist(), 'uv': uv[first].round(6).ravel().tolist(), 'index': inverse.tolist()})
json.dump({'size': SIZE, 'atlases': len(atlases), 'targets': uv2}, open(os.path.join(work, 'uv2.json'), 'w'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(work, 'bake.blend'))
log('done')

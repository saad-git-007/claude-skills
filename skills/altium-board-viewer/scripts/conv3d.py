"""Convert STEP models to compact coloured meshes and compute a placement for every component.

Inputs : the 2D viewer HTML (board data + layer SVG), <work>/models/{kicad,maker,third_party}.
Output : <work>/out3d/models.json, placements.json, sources.json, report.json
Run with the 3D venv python (cadquery-ocp + numpy), see setup.sh --3d.
"""
from __future__ import annotations

import base64, gzip, json, math, re, sys
from pathlib import Path

import numpy as np
import OCP.collections as OC
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.IFSelect import IFSelect_RetDone
from OCP.Message import Message_ProgressRange
from OCP.RWGltf import RWGltf_CafWriter
from OCP.RWMesh import RWMesh_CoordinateSystem_Zup
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from itertools import permutations, product

sys.path.insert(0, str(Path(__file__).parent))
from kicad_map import kicad_for  # noqa: E402
import cfg  # noqa: E402

VIEWER = cfg.VIEWER
KICAD = cfg.MODELS / "kicad"
MAKER = cfg.MODELS / "maker"
THIRD = cfg.MODELS / "third_party"
OUT = cfg.OUT3D
OUT.mkdir(parents=True, exist_ok=True)

# Maker STEP files by footprint (board.json "maker_map": footprint -> STEP basename, or [basename, extra deg]).
MAKER_MAP = {k: (tuple(v) if isinstance(v, list) else (v, 0)) for k, v in cfg.MAKER_MAP.items()}
ROT_OVERRIDE: dict[str, float] = cfg.ROT_OVERRIDE

# ---------- board data from viewer ----------
src = VIEWER.read_text()
D = json.loads(re.search(r'id="data">(.*?)</script>', src, re.S).group(1).replace("<\\/", "</"))
LZ = json.loads(re.search(r'id="layerdata">(.*?)</script>', src, re.S).group(1).replace("<\\/", "</"))
B = D["board"]
mask = gzip.decompress(base64.b64decode(LZ["TOPSOLDER"])).decode()
drills = gzip.decompress(base64.b64decode(LZ["DRILLS"])).decode()
NUM = re.compile(r"-?\d+\.?\d*")


def to_board(x, y):  # svg mm -> board frame (mm, Y up, origin lower-left of outline)
    return x - B["x"], B["y"] + B["h"] - y


def elem_center(line: str):
    a = {k: v for k, v in re.findall(r'\b(x|y|width|height|cx|cy|d|transform)="([^"]*)"', line)}
    if "cx" in a:
        px, py = float(a["cx"]), float(a["cy"])
    elif "width" in a and "x" in a:
        px, py = float(a["x"]) + float(a["width"]) / 2, float(a["y"]) + float(a["height"]) / 2
    elif "d" in a:
        n = [float(v) for v in NUM.findall(a["d"])]
        xs, ys = n[0::2], n[1::2]
        px, py = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    else:
        return None
    t = a.get("transform", "")
    m = re.match(r"rotate\((-?[\d.]+) (-?[\d.]+) (-?[\d.]+)\)", t)
    if m:
        ang, ox, oy = math.radians(float(m.group(1))), float(m.group(2)), float(m.group(3))
        dx, dy = px - ox, py - oy
        px, py = ox + dx * math.cos(ang) - dy * math.sin(ang), oy + dx * math.sin(ang) + dy * math.cos(ang)
    return px, py


PADS: dict[int, dict[str, list]] = {}
HOLES: set[int] = set()
for frag in (mask, drills):
    for line in frag.split("\n"):
        m = re.search(r'data-component-index="(\d+)"', line)
        if not m or 'data-primitive="pad' not in line:
            continue
        num = (re.search(r'data-pad-designator="([^"]*)"', line) or [None, ""])[1]
        if 'data-primitive="pad-hole"' in line:
            HOLES.add(int(m.group(1)))
        c = elem_center(line)
        if c:
            PADS.setdefault(int(m.group(1)), {}).setdefault(num, []).append(to_board(*c))


def pad_info(i):
    p = PADS.get(i, {})
    pts = [np.mean(v, axis=0) for k, v in p.items() if k]
    if not pts:
        return None, None
    cen = np.mean(pts, axis=0)
    p1 = np.mean(p["1"], axis=0) if "1" in p else None
    return cen, p1


# ---------- KiCad footprint parsing ----------
def kicad_fp(name):
    t = (KICAD / f"{name}.kicad_mod").read_text()
    pads = {}
    for m in re.finditer(r'\(pad\s+"([^"]*)"\s+\S+\s+\S+\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)', t):
        if m.group(1):
            pads.setdefault(m.group(1), []).append((float(m.group(2)), -float(m.group(3))))  # model frame: Y up
    pts = [np.mean(v, axis=0) for v in pads.values()]
    off = re.search(r"\(model[\s\S]*?\(offset\s*\(xyz\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", t)
    rot = re.search(r"\(model[\s\S]*?\(rotate\s*\(xyz\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", t)
    return {"cen": np.mean(pts, axis=0) if pts else np.zeros(2), "p1": np.mean(pads["1"], axis=0) if "1" in pads else None,
            "offset": [float(v) for v in off.groups()] if off else [0, 0, 0],
            "rotate": [float(v) for v in rot.groups()] if rot else [0, 0, 0]}


# ---------- STEP -> GLB ----------
GLB = OUT / "glb"; GLB.mkdir(exist_ok=True)


def step_to_glb(path: Path, out: Path):
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader(); r.SetColorMode(True); r.SetNameMode(False)
    if r.ReadFile(str(path)) != IFSelect_RetDone or not r.Transfer(doc):
        raise RuntimeError(f"cannot read {path}")
    shape = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).GetOneShape()
    box = Bnd_Box(); BRepBndLib.AddOptimal_s(shape, box, False, False)
    pa, pb = box.CornerMin(), box.CornerMax()
    x0, y0, z0, x1, y1, z1 = pa.X(), pa.Y(), pa.Z(), pb.X(), pb.Y(), pb.Z()
    diag = math.dist((x0, y0, z0), (x1, y1, z1))
    BRepMesh_IncrementalMesh(shape, max(.02, diag * .006), False, .8, True)  # light meshes for smooth viewing
    w = RWGltf_CafWriter(TCollection_AsciiString(str(out)), True)
    cs = w.ChangeCoordinateSystemConverter()
    cs.SetInputLengthUnit(0.001); cs.SetOutputLengthUnit(0.001)
    cs.SetInputCoordinateSystem(RWMesh_CoordinateSystem_Zup); cs.SetOutputCoordinateSystem(RWMesh_CoordinateSystem_Zup)
    if not w.Perform(doc, OC.IndexedDataMap_TCollection_AsciiString_TCollection_AsciiString(), Message_ProgressRange()):
        raise RuntimeError("glb export failed")
    verts = []
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face(ex.Current()); loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            tr = loc.Transformation()
            for n in range(1, tri.NbNodes() + 1):
                q = tri.Node(n).Transformed(tr); verts.append((q.X(), q.Y(), q.Z()))
        ex.Next()
    V = np.array(verts)
    if len(V) > 6000:
        V = V[np.random.default_rng(1).choice(len(V), 6000, replace=False)]
    VERTS[path.stem] = V
    return np.array([x0, y0, z0]), np.array([x1, y1, z1])


VERTS: dict[str, np.ndarray] = {}
ROTS = []
for perm in permutations(range(3)):
    for signs in product((1, -1), repeat=3):
        M = np.zeros((3, 3))
        for r_, (c_, s_) in enumerate(zip(perm, signs)):
            M[r_, c_] = s_
        if round(np.linalg.det(M)) == 1:
            ROTS.append(M)


def seat_z(P, lo, hi, pads, tht):
    """SMD: lowest point touches the board.  THT: body starts at the first height with geometry away from every pad."""
    if not tht or not len(pads):
        return lo[2]
    z = lo[2]
    while z < hi[2]:
        sl = P[(P[:, 2] >= z) & (P[:, 2] < z + 0.3)]
        if len(sl):
            d = np.linalg.norm(sl[:, None, :2] - pads[None, :, :], axis=2).min(1)
            if (d > 1.6).mean() > 0.25:
                return z
        z += 0.15
    return lo[2]


def fit_orientation(V, pads, bcen, bd, top_h, tht):
    """Try all 24 axis-aligned orientations; keep the one whose legs/leads land on the real pads."""
    best = None
    for M in ROTS:
        P = V @ M.T
        lo, hi = P.min(0), P.max(0)
        t = np.array([bcen[0] - (lo[0] + hi[0]) / 2, bcen[1] - (lo[1] + hi[1]) / 2, 0.0])
        P0 = P + t
        t[2] = -seat_z(P0, P0.min(0), P0.max(0), pads, tht)
        P = P + t
        below = P[P[:, 2] < -0.4]
        contact = below if len(below) >= 12 else P[P[:, 2] < P[:, 2].min() + 0.25]
        if len(pads):
            d = np.linalg.norm(contact[:, None, :2] - pads[None, :, :], axis=2)
            score = np.minimum(d.min(1), 4).mean() + np.minimum(d.min(0), 4).mean()
        else:
            score = 0.0
        score += 0.15 * np.abs((hi - lo)[:2] - bd).sum() + (0 if len(below) >= 12 else 0.5)
        if best is None or score < best[0]:
            best = (score, M, t)
    return best


# ---------- placements ----------
models, place, report = {}, [], {"kicad": {}, "maker": {}, "box": []}
model_meta = {}


def get_model(key: str, path: Path):
    if key not in model_meta:
        out = GLB / f"{key}.glb"
        lo, hi = step_to_glb(path, out)
        model_meta[key] = (lo, hi)
        models[key] = base64.b64encode(gzip.compress(out.read_bytes(), 9)).decode()
        print(f"  glb {key}: {out.stat().st_size // 1024} KB")
    return model_meta[key]


def rot2(v, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])


for c in D["comps"]:
    i, des, fp = c["i"], c["d"], c["fp"]
    pcen, pp1 = pad_info(i)
    body = [p for s in c["s"] for p in s["p"]]
    bx = [to_board(*p) for p in body] if body else [to_board(c["bb"][0], c["bb"][1]), to_board(c["bb"][2], c["bb"][3])]
    bmin, bmax = np.min(bx, 0), np.max(bx, 0)
    bcen = (bmin + bmax) / 2
    top_h = max((s["z1"] for s in c["s"]), default=1.0)
    theta = c["rot"]
    entry = None
    mk = MAKER_MAP.get(fp)
    mpath = None
    if mk:
        for d in (MAKER, THIRD):
            if (d / f"{mk[0]}.step").exists():
                mpath = d / f"{mk[0]}.step"; break
    kt = kicad_for(des, fp)
    try:
        if mpath and mpath.exists():
            get_model(mk[0], mpath)
            pads = np.array([np.mean(v, axis=0) for k, v in PADS.get(i, {}).items() if k]) if PADS.get(i) else np.zeros((0, 2))
            score, M, t = fit_orientation(VERTS[mpath.stem], pads, bcen, bmax - bmin, top_h, i in HOLES)
            extra = ROT_OVERRIDE.get(des, 0)
            if extra:  # manual turn about the part's body centre
                a_ = math.radians(extra); Rz = np.array([[math.cos(a_), -math.sin(a_), 0], [math.sin(a_), math.cos(a_), 0], [0, 0, 1]])
                M = Rz @ M
                t = np.array([*(rot2(t[:2] - bcen, extra) + bcen), t[2]])
            entry = {"m": mk[0], "x": float(t[0]), "y": float(t[1]), "z": float(t[2]), "r": 0.0, "R": [round(float(v), 3) for v in M.flatten()], "fit": round(float(score), 3)}
            report["maker"].setdefault(mk[0], []).append(des)
        elif kt and (KICAD / f"{kt.split(':')[1]}.step").exists():
            name = kt.split(":")[1]
            get_model(name, KICAD / f"{name}.step")
            f = kicad_fp(name)
            best = None
            for k in range(4):
                th = theta + 90 * k
                if pp1 is not None and f["p1"] is not None:
                    t = pp1 - rot2(f["p1"], th)
                else:
                    t = (pcen if pcen is not None else bcen) - rot2(f["cen"], th)
                mapped = rot2(f["cen"], th) + t
                ref = pcen if pcen is not None else bcen
                err = float(np.linalg.norm(mapped - ref)) + 0.001 * k
                if best is None or err < best[0]:
                    best = (err, th, t)
            th = best[1] + ROT_OVERRIDE.get(des, 0)
            t = best[2]
            entry = {"m": name, "x": t[0], "y": t[1], "z": 0.0, "r": th, "off": f["offset"], "rot3": f["rotate"], "err": round(best[0], 3)}
            report["kicad"].setdefault(name, []).append(des)
    except Exception as e:  # noqa: BLE001
        print("model fail", des, e)
    if entry is None:
        report["box"].append(des)
        continue
    entry.update({"i": i})
    entry = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in entry.items()}
    place.append(entry)

    # Boards mounted upside down above a socket (board.json "stacked"), e.g. a Raspberry Pi on a 2x20 header.
    for st in cfg.STACKED:
        sp = THIRD / st["step"]
        if not (re.search(st["footprint"], fp) and sp.exists()):
            continue
        key = Path(st["step"]).stem
        lo, hi = get_model(key, sp)
        mc = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2]); md = np.array([hi[0] - lo[0], hi[1] - lo[1]])
        bd = bmax - bmin
        th = theta if abs(abs(rot2(md, theta)) - bd).sum() <= abs(abs(rot2(md, theta + 90)) - bd).sum() else theta + 90
        th += float(st.get("rot", 0))
        # flipped about the model X axis: (x, y, z) -> (x, -y, -z)
        mcf = np.array([mc[0], -mc[1]])
        t = bcen - rot2(mcf, th)
        place.append({"m": key, "x": round(float(t[0]), 4), "y": round(float(t[1]), 4), "z": round(top_h + float(lo[2]) + float(st.get("gap", 0)), 4), "r": th, "flip": 1, "i": i})
        report["maker"][key] = [des]

for p in place:
    if "fit" in p:
        print("  fit", D["comps"][[c["i"] for c in D["comps"]].index(p["i"])]["d"], p["fit"], p["R"])
big = [p for p in place if p.get("err", 0) > 0.6]
print("placed", len(place), "| box", len(report["box"]), "| large fit error:", [(D["comps"][[c["i"] for c in D["comps"]].index(p["i"])]["d"], p["err"]) for p in big][:20])
(OUT / "models.json").write_text(json.dumps(models, separators=(",", ":")))
(OUT / "placements.json").write_text(json.dumps(place, separators=(",", ":")))
SRC_TXT = {**cfg.MAKER_SOURCES, **{Path(s["step"]).stem: s.get("source", "Third-party model") for s in cfg.STACKED}}
sources = {}
for p in place:
    t = SRC_TXT.get(p["m"], "Manufacturer model" if (MAKER / (p["m"] + ".step")).exists() else f"KiCad library: {p['m']}")
    sources[p["i"]] = (sources[p["i"]] + " + " + t) if p["i"] in sources else t
(OUT / "sources.json").write_text(json.dumps(sources))
(OUT / "report.json").write_text(json.dumps(report, indent=1))
print("models.json", (OUT / "models.json").stat().st_size // 1024, "KB")

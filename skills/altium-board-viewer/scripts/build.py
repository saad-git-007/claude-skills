"""Extract board outline, layer SVGs and components from an Altium project with altium_monkey.
Output: <work>/build/data.json, layers.json, frag_*.svgfrag.  Run with the altium venv python."""
from __future__ import annotations

import base64, csv, gzip, json, re, sys, zipfile
from pathlib import Path

from altium_monkey import AltiumDesign, PcbLayer, PcbSvgRenderOptions

import sys as _s; _s.path.insert(0, str(Path(__file__).resolve().parent))
import cfg  # noqa: E402
PRJ, BOM, PNP, OUT = cfg.PRJ, cfg.BOM, cfg.PNP, cfg.BUILD
MIL = 0.0254

LAYERS = [  # key, label, PcbLayer
    ("BOTTOM", "Bottom copper", PcbLayer.BOTTOM),
    ("MID2", "Inner 2", PcbLayer.MID2),
    ("MID1", "Inner 1", PcbLayer.MID1),
    ("TOP", "Top copper", PcbLayer.TOP),
    ("BOTTOMSOLDER", "Bottom pads", PcbLayer.BOTTOM_SOLDER),
    ("TOPSOLDER", "Top pads", PcbLayer.TOP_SOLDER),
    ("DRILLS", "Drills", None),
    ("TOPOVERLAY", "Silkscreen", PcbLayer.TOP_OVERLAY),
]


def read_bom() -> tuple[dict, set, str]:
    if not BOM or not BOM.exists():
        return {}, set(), ""
    if BOM.suffix.lower() == ".csv":
        rows = [[x.strip() for x in r] for r in csv.reader(open(BOM, encoding="utf-8", errors="ignore"))]
        return parse_bom_rows(rows)
    z = zipfile.ZipFile(BOM)
    ss = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    import html
    ss = [html.unescape(s) for s in ss]
    rows = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read("xl/worksheets/sheet1.xml").decode(), re.S):
        out = []
        for a, v in re.findall(r"<c ([^>]*?)(?:/>|>(.*?)</c>)", row, re.S):
            m = re.search(r"<v>(.*?)</v>", v or "")
            s = m.group(1) if m else ""
            if 't="s"' in a and s:
                s = ss[int(s)]
            out.append(s.strip())
        rows.append(out)
    return parse_bom_rows(rows)


def parse_bom_rows(rows: list[list[str]]) -> tuple[dict, set, str]:
    """Column positions, header rows and the NNP marker come from board.json."""
    k = cfg.BOM_COLS
    width = max(k.values()) + 1
    title = " ".join(x for x in rows[0] if x) if rows else ""
    bom, nnp = {}, set()
    for r in rows[cfg.BOM_HEADER_ROWS:]:
        r = (r + [""] * width)[:width]
        cell = r[k["refs"]]
        refs = [t.strip() for t in re.split(r"[,; ]+", cell) if re.match(r"^[A-Z]+\d+$", t.strip())]
        entry = {"item": r[k["item"]], "name": r[k["name"]], "mpn": r[k["mpn"]], "mfr": r[k["mfr"]]}
        if cfg.NNP_MARKER and cfg.NNP_MARKER in (r[k["item"]], r[k["name"]], r[k["mpn"]]):
            nnp |= set(refs)
            continue
        for t in refs:
            bom[t] = entry
        for des, text in cfg.BOM_ALIAS.items():  # parts listed by description instead of designator
            if text in cell:
                bom[des] = entry
    return bom, nnp, title


def scene_inner(svg: str) -> str:
    i = svg.find('<g id="scene">')
    j = svg.rfind("</g>")
    body = svg[i + len('<g id="scene">'): j] if i >= 0 else svg
    return re.sub(r"<metadata.*?</metadata>", "", body, flags=re.S).strip()


def gz64(s: str) -> str:
    return base64.b64encode(gzip.compress(s.encode(), 9)).decode()


def kind_of(des: str, fp: str, comment: str) -> str:
    p = re.sub(r"[^A-Z]", "", des.split()[0].upper())
    f = (fp + " " + comment).upper()
    if p == "RLY": return "relay"
    if p == "MDLE": return "module"
    if p == "C" and "ALUM" in f: return "ecap"
    if p == "C": return "cap"
    if p == "R": return "res"
    if p in ("LED",) or "LTST" in f or comment.lower() == "green": return "led"
    if p == "J": return "conn"
    if p in ("U", "Q", "OPTO", "Y"): return "ic"
    if p == "D": return "diode"
    if p == "L": return "ind"
    if p in ("TP", "TPG"): return "tp"
    if p == "MH": return "hole"
    if p == "SW": return "sw"
    return "other"


DEFAULT_H = {"res": .35, "cap": .5, "led": .8, "ic": 1.1, "diode": 1.2, "tp": 2.5, "ind": 6.1, "conn": 8.5, "other": 1.0, "sw": 3.5}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    design = AltiumDesign.from_prjpcb(PRJ)
    pcb = design.load_pcbdoc()
    params = design.get_pcb_project_parameters()
    bom, nnp, bom_title = read_bom()
    pnp = {}
    if PNP and PNP.exists():
        rows = list(csv.reader(open(PNP, encoding="utf-8", errors="ignore")))
        start = next((n + 1 for n, r in enumerate(rows) if r and r[0].strip().lower() == "designator"), 1)
        pnp = {r[0]: r for r in rows[start:] if len(r) > cfg.PNP_COMMENT_COL}

    # Board outline (mils) and the renderer's mil -> svg-mm transform.
    ov = pcb.board.outline.vertices
    ox = [v.x_mils for v in ov]; oy = [v.y_mils for v in ov]
    osvg = pcb.to_board_outline_svg()
    pts = [tuple(map(float, p)) for p in re.findall(r"(-?[\d.]+) (-?[\d.]+)", re.search(r'<path d="([^"]+)"', osvg).group(1))]
    sx0 = min(p[0] for p in pts); sy0 = min(p[1] for p in pts)
    min_x = min(ox) - sx0 / MIL
    max_y = max(oy) + sy0 / MIL
    X = lambda x: (x - min_x) * MIL
    Y = lambda y: (max_y - y) * MIL
    outline_path = re.search(r'<path d="([^"]+)"', osvg).group(1)
    bx0, by0 = X(min(ox)), Y(max(oy))
    bw, bh = (max(ox) - min(ox)) * MIL, (max(oy) - min(oy)) * MIL
    outline_pts = [[round(X(v.x_mils), 3), round(Y(v.y_mils), 3)] for v in ov]

    # Layer SVG fragments.
    opts = PcbSvgRenderOptions(
        visible_layers=[l for _, _, l in LAYERS if l is not None],
        precision=3, show_board_outline=False, drill_hole_mode="overlay",
        drill_hole_overlay_opacity=1.0, drill_hole_overlay_color="#000000",
    )
    svgs = pcb.to_layer_svgs(opts, params)
    print("rendered:", list(svgs))
    frags = {}
    for key, label, layer in LAYERS:
        src = None
        for k in svgs:
            if re.sub(r"[^A-Z0-9]", "", k.upper()) == key:
                src = svgs[k]
        if src is None:
            print("missing layer", key); continue
        frags[key] = scene_inner(src)
        print(f"  {key}: {len(frags[key])//1024} KB")

    # Components.
    comps = []
    bodies_by = {}
    for b in pcb.component_bodies:
        bodies_by.setdefault(b.component_index, []).append(b)
    for i, c in enumerate(pcb.components):
        des = c.designator
        row = pnp.get(des)
        comment = row[cfg.PNP_COMMENT_COL] if row else (getattr(c, "comment", "") or "")
        fp = c.footprint or (row[1] if row else "")
        b = bom.get(des)
        try:
            px, py = pcb.get_component_pick_place_center_mils(i, origin_relative=False)
        except Exception:
            px, py = c.get_x_mils(), c.get_y_mils()
        k = kind_of(des, fp, comment)
        shapes = []
        for body in bodies_by.get(i, []):
            poly = [[round(X(v.x_mils), 3), round(Y(v.y_mils), 3)] for v in body.outline]
            if len(poly) < 3: continue
            z0 = max(body.standoff_height_mils * MIL, 0.0)
            z1 = max(body.overall_height_mils, body.model_extruded_max_z / 10000.0) * MIL
            if z1 <= z0 + 0.05: z1 = z0 + DEFAULT_H.get(k, 1.0)
            col = body.body_color_3d
            rgb = None if col in (8421504, 0) else "#%02x%02x%02x" % (col & 255, (col >> 8) & 255, (col >> 16) & 255)
            shapes.append({"p": poly, "z0": round(z0, 3), "z1": round(z1, 3), "c": rgb})
        # Pad bounding box (used for 2D highlight and fallback 3D box).
        xs, ys = [], []
        try:
            prims = pcb.get_component_primitives(i)
            for pad in prims.get("pads", []):
                pxm, pym = pad.x / 10000.0, pad.y / 10000.0
                w = max(pad.top_width, pad.bot_width, pad.hole_size) / 10000.0
                h = max(pad.top_height, pad.bot_height, pad.hole_size) / 10000.0
                r = max(w, h) / 2
                xs += [pxm - r, pxm + r]; ys += [pym - r, pym + r]
        except Exception as e:  # noqa: BLE001
            print('prims fail', des, e)
        for s in shapes:
            for x, y in s["p"]:
                xs.append(x / MIL + min_x); ys.append(max_y - y / MIL)
        if xs:
            bb = [round(X(min(xs)), 3), round(Y(max(ys)), 3), round(X(max(xs)), 3), round(Y(min(ys)), 3)]
        else:
            bb = [round(X(px) - 1, 3), round(Y(py) - 1, 3), round(X(px) + 1, 3), round(Y(py) + 1, 3)]
        if not shapes and k not in ("hole",):
            x0, y0, x1, y1 = bb
            shapes.append({"p": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "z0": 0, "z1": DEFAULT_H.get(k, 1.0), "c": None, "fallback": True})
        comps.append({
            "i": i, "d": des, "fp": fp.split(":")[-1], "cm": comment, "k": k,
            "x": round(X(px), 3), "y": round(Y(py), 3),
            "xm": round(px - min(ox), 1), "ym": round(py - min(oy), 1),
            "rot": round(c.get_rotation_degrees() % 360, 1),
            "side": "Bottom" if str(c.get_layer_normalized() if hasattr(c, "get_layer_normalized") else c.layer).upper().startswith("BOT") else "Top",
            "nnp": des in nnp, "bom": b, "bb": bb, "s": shapes,
        })

    def sortkey(c):
        m = re.match(r"([A-Za-z ]*?)(\d+)$", c["d"].replace(" ", ""))
        return (m.group(1), int(m.group(2))) if m else (c["d"], 0)
    comps.sort(key=sortkey)

    data = {
        "title": f"{cfg.TITLE} {cfg.REV}".strip(),
        "bomTitle": bom_title,
        "board": {"x": round(bx0, 3), "y": round(by0, 3), "w": round(bw, 3), "h": round(bh, 3),
                  "path": outline_path, "pts": outline_pts, "thick": cfg.THICK},
        "layers": [{"key": k, "label": lbl} for k, lbl, _ in LAYERS if k in frags],
        "comps": comps,
    }
    (OUT / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    (OUT / "layers.json").write_text(json.dumps({k: gz64(v) for k, v in frags.items()}))
    for k, v in frags.items():
        (OUT / f"frag_{k}.svgfrag").write_text(v)
    print("components:", len(comps), "nnp:", sum(c["nnp"] for c in comps),
          "fallback boxes:", sum(1 for c in comps if any(s.get("fallback") for s in c["s"])))
    print("board mm:", bw, bh)


if __name__ == "__main__":
    main()

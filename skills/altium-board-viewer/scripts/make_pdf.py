"""Build the assembly PDF (overview + zoomed zone pages) from the data embedded in the viewer HTML.

Needs only the Python standard library and Google Chrome:
    python3 make_pdf.py
"""
from __future__ import annotations

import base64, datetime, gzip, html, json, re, subprocess, tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cfg  # noqa: E402
VIEWER, PDF = cfg.VIEWER, cfg.PDF
COLS, ROWS = 3, 3          # zone grid
OVERLAP = 4.0              # mm shared between neighbouring zones

src = VIEWER.read_text()
D = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', src, re.S).group(1).replace("<\\/", "</"))
LZ = json.loads(re.search(r'<script type="application/json" id="layerdata">(.*?)</script>', src, re.S).group(1).replace("<\\/", "</"))
FR = {k: gzip.decompress(base64.b64decode(v)).decode() for k, v in LZ.items()}
B, comps = D["board"], D["comps"]
NUM = re.compile(r"-?\d+\.?\d*")


def elem_lines(frag: str) -> tuple[str, str, list[str]]:
    """Split a layer fragment into its opening <g>, closing </g> and one string per child element."""
    lines = frag.strip().split("\n")
    return lines[0], lines[-1], lines[1:-1]


def bbox_of(line: str):
    vals = []
    for m in re.finditer(r'\b(d|x|y|cx|cy|x1|y1|x2|y2|width|height|r|points)="([^"]*)"', line):
        vals.append((m.group(1), [float(v) for v in NUM.findall(m.group(2))]))
    xs, ys = [], []
    a = dict(vals)
    if "d" in a or "points" in a:
        seq = a.get("d") or a.get("points")
        xs += seq[0::2]; ys += seq[1::2]
    if "cx" in a:
        r = (a.get("r") or [0])[0]
        xs += [a["cx"][0] - r, a["cx"][0] + r]; ys += [a["cy"][0] - r, a["cy"][0] + r]
    if "x" in a and "y" in a:
        w = (a.get("width") or [0])[0]; h = (a.get("height") or [0])[0]
        xs += [a["x"][0], a["x"][0] + w]; ys += [a["y"][0], a["y"][0] + h]
    if "x1" in a:
        xs += a["x1"] + a.get("x2", []); ys += a["y1"] + a.get("y2", [])
    if not xs or not ys:
        return None
    pad = 3.0 if "transform=" in line else 0.5
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


LAYERS = {}
for k in ("TOPSOLDER", "TOPOVERLAY", "DRILLS"):
    head, tail, items = elem_lines(FR[k])
    LAYERS[k] = (head, tail, [(bbox_of(i), i) for i in items])


def layers_in(x0, y0, x1, y1) -> str:
    out = []
    for k, (head, tail, items) in LAYERS.items():
        kept = [s for bb, s in items if bb is None or (bb[2] >= x0 and bb[0] <= x1 and bb[3] >= y0 and bb[1] <= y1)]
        out.append(f'<g class="L L-{k}">{head}{"".join(kept)}{tail}</g>')
    return "".join(out)


zw, zh = B["w"] / COLS, B["h"] / ROWS
ZONES = []
for r in range(ROWS):
    for c in range(COLS):
        name = f"{'ABC'[r]}{c + 1}"
        x0 = B["x"] + c * zw - OVERLAP; y0 = B["y"] + r * zh - OVERLAP
        ZONES.append({"name": name, "x0": x0, "y0": y0, "x1": x0 + zw + 2 * OVERLAP, "y1": y0 + zh + 2 * OVERLAP})


def zone_of(cmp) -> str:
    c = min(COLS - 1, max(0, int((cmp["x"] - B["x"]) // zw)))
    r = min(ROWS - 1, max(0, int((cmp["y"] - B["y"]) // zh)))
    return f"{'ABC'[r]}{c + 1}"


def labels(scale: float, link: bool, area=None) -> str:
    out = []
    for c in comps:
        x0, y0, x1, y1 = c["bb"]
        if area and not (x1 >= area[0] and x0 <= area[2] and y1 >= area[1] and y0 <= area[3]):
            continue
        w, h = x1 - x0, y1 - y0
        fs = max(.6, min(1.5, w * .32, max(w, h) * .3)) if scale == 1.0 else max(1.0, min(1.6, max(w, h) * .45))
        cls = "lbl n" if c["nnp"] else "lbl"
        t = f'<text x="{c["x"]}" y="{c["y"]}" font-size="{fs:.2f}" class="{cls}">{html.escape(c["d"])}</text>'
        if c["nnp"]:
            out.append(f'<rect x="{x0}" y="{y0}" width="{max(w, .4)}" height="{max(h, .4)}" class="nnpr"/>')
        out.append(f'<a href="#zone-{zone_of(c)}">{t}</a>' if link else t)
    return "".join(out)


def grid_overlay() -> str:
    g = []
    for i in range(1, COLS):
        x = B["x"] + i * zw; g.append(f'<line x1="{x}" y1="{B["y"] - 3}" x2="{x}" y2="{B["y"] + B["h"] + 3}" class="grid"/>')
    for i in range(1, ROWS):
        y = B["y"] + i * zh; g.append(f'<line x1="{B["x"] - 3}" y1="{y}" x2="{B["x"] + B["w"] + 3}" y2="{y}" class="grid"/>')
    for z in ZONES:
        cx = (z["x0"] + z["x1"]) / 2; cy = (z["y0"] + z["y1"]) / 2
        g.append(f'<a href="#zone-{z["name"]}"><text x="{cx}" y="{cy}" class="zname">{z["name"]}</text></a>')
    return "".join(g)


def locator(active: str) -> str:
    cells = []
    for z in ZONES:
        x0 = max(z["x0"] + OVERLAP, B["x"]); y0 = max(z["y0"] + OVERLAP, B["y"])
        on = z["name"] == active
        cells.append(f'<a href="#zone-{z["name"]}"><rect x="{x0}" y="{y0}" width="{zw}" height="{zh}" class="cell{" on" if on else ""}"/>'
                     f'<text x="{x0 + zw / 2}" y="{y0 + zh / 2}" class="cname{" on" if on else ""}">{z["name"]}</text></a>')
    return (f'<svg class="loc" viewBox="{B["x"] - 2} {B["y"] - 2} {B["w"] + 4} {B["h"] + 4}">'
            f'<path d="{B["path"]}" class="locb"/>{"".join(cells)}</svg>')


fitted = sum(1 for c in comps if not c["nnp"])
today = datetime.date.today().isoformat()
m = 4
overview = f'''<section class="page" id="overview">
  <div class="head">
    <div><p class="eyebrow">Top assembly · {today}</p><h1>{html.escape(cfg.TITLE)} <em>{html.escape(cfg.REV)}</em></h1></div>
    <div class="stats">
      <div class="stat"><strong>{len(comps)}</strong><span>Parts</span></div>
      <div class="stat"><strong>{fitted}</strong><span>Fitted</span></div>
      <div class="stat"><strong>{len(comps) - fitted}</strong><span>NNP</span></div>
      <div class="stat"><strong>{B["w"]:.0f}×{B["h"]:.0f}</strong><span>mm · 4 layers</span></div>
    </div>
  </div>
  <svg class="asm" viewBox="{B["x"] - m} {B["y"] - m} {B["w"] + 2 * m} {B["h"] + 2 * m}" xmlns="http://www.w3.org/2000/svg">
    <path d="{B["path"]}" class="sub"/>{layers_in(-1e9, -1e9, 1e9, 1e9)}<path d="{B["path"]}" class="edge"/>
    {grid_overlay()}<g>{labels(1.0, True)}</g>
  </svg>
  <div class="legend"><span><i style="background:#c9c2b3"></i>Pads</span><span><i style="background:#a9a294"></i>Silkscreen</span>
    <span class="k-f">R1</span><span>Fitted</span><span class="k-n">U3</span><span>Not normally populated (NNP)</span>
    <span class="hint">Click a part or zone letter to open its zoomed page · Ctrl+F a designator to find it</span></div>
</section>'''

zone_pages = []
for z in ZONES:
    area = (z["x0"], z["y0"], z["x1"], z["y1"])
    inzone = sorted({c["d"] for c in comps if zone_of(c) == z["name"]})
    zone_pages.append(f'''<section class="page" id="zone-{z["name"]}">
  <div class="head">
    <div><p class="eyebrow"><a href="#overview">← Overview</a> · Zone</p><h1>Zone <em>{z["name"]}</em></h1>
      <p class="sub-t">{len(inzone)} parts in this zone</p></div>
    {locator(z["name"])}
  </div>
  <svg class="zone" viewBox="{z["x0"]} {z["y0"]} {z["x1"] - z["x0"]} {z["y1"] - z["y0"]}" xmlns="http://www.w3.org/2000/svg">
    <path d="{B["path"]}" class="sub"/>{layers_in(*area)}<path d="{B["path"]}" class="edge"/>
    <g>{labels(2.0, False, area)}</g>
  </svg>
</section>''')

css = """
@page { size: 11in 17in; margin: 12mm 12mm 12mm; }
:root { --text:#1c1a16; --text-2:#4a453c; --muted:#625b4e; --gold:#735719; --line:rgba(28,26,22,.14); --danger:#a83226; }
* { box-sizing: border-box; }
body { margin:0; color:var(--text); font:400 9.5pt/1.45 Inter, system-ui, sans-serif; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
a { color: inherit; text-decoration: none; }
.page { break-after: page; height: 405mm; display: flex; flex-direction: column; }
.page:last-child { break-after: auto; }
.eyebrow { font:650 7.5pt/1 "JetBrains Mono", monospace; letter-spacing:.14em; text-transform:uppercase; color:var(--gold); margin:0 0 6px; }
.eyebrow a { color: var(--gold); }
h1 { font:500 30pt/1 Fraunces, Georgia, serif; letter-spacing:-.02em; margin:0; }
h1 em { font:italic 30pt/1 "Instrument Serif", serif; color:var(--gold); }
.sub-t { margin:6px 0 0; color:var(--muted); font-size:9pt; }
.head { display:flex; justify-content:space-between; align-items:flex-end; gap:20px; padding-bottom:10px; border-bottom:1px solid var(--line); margin-bottom:10px; }
.stats { display:flex; gap:22px; }
.stat strong { display:block; font:500 18pt/1 Fraunces, serif; font-variant-numeric:tabular-nums; }
.stat:first-child strong { color:var(--gold); }
.stat span { font:650 6.5pt/1 Inter; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }
.asm, .zone { width:100%; flex:1; min-height:0; display:block; }
.sub { fill:#fbf8f1; } .edge { fill:none; stroke:#1c1a16; stroke-width:.3; }
.zone .edge { stroke-width:.2; }
.L [fill]:not([fill="none"]) { fill:var(--c); } .L [stroke]:not([stroke="none"]) { stroke:var(--c); }
.L-TOPSOLDER { --c:#c9c2b3; } .L-TOPOVERLAY { --c:#a9a294; } .L-DRILLS { --c:#ffffff; }
.lbl { font-family:"JetBrains Mono", monospace; font-weight:600; fill:#1f3f8f; text-anchor:middle; dominant-baseline:central; paint-order:stroke; stroke:#fbf8f1; stroke-width:.12px; }
.lbl.n { fill:var(--danger); font-style:italic; }
.nnpr { fill:rgba(168,50,38,.07); stroke:var(--danger); stroke-width:.15; stroke-dasharray:.6 .4; }
.grid { stroke:var(--gold); stroke-width:.25; stroke-dasharray:2 1.4; opacity:.7; }
.zname { font:500 18px Fraunces, serif; fill:var(--gold); opacity:.18; text-anchor:middle; dominant-baseline:central; }
.legend { display:flex; flex-wrap:wrap; gap:6px 16px; font-size:8pt; color:var(--text-2); margin-top:6px; align-items:center; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }
.k-f { color:#1f3f8f; font:600 8pt "JetBrains Mono"; } .k-n { color:var(--danger); font:italic 600 8pt "JetBrains Mono"; }
.hint { margin-left:auto; color:var(--muted); }
.loc { width:34mm; height:37mm; flex:none; }
.locb { fill:#f1ece0; stroke:#1c1a16; stroke-width:1; }
.cell { fill:transparent; stroke:rgba(115,87,25,.35); stroke-width:.8; } .cell.on { fill:rgba(115,87,25,.85); }
.cname { font:600 22px "JetBrains Mono"; fill:var(--muted); text-anchor:middle; dominant-baseline:central; } .cname.on { fill:#fffdf8; }
"""

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{D["title"]}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Instrument+Serif:ital@1&family=Inter:wght@400;550;650&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{css}</style></head><body>{overview}{"".join(zone_pages)}</body></html>'''

with tempfile.TemporaryDirectory() as tmp:
    page = Path(tmp) / "report.html"
    page.write_text(doc)
    subprocess.run([cfg.chrome_bin(), "--headless=new", "--no-first-run", f"--user-data-dir={tmp}/prof",
                    "--no-pdf-header-footer", "--virtual-time-budget=20000", f"--print-to-pdf={PDF}", f"file://{page}"],
                   check=True, capture_output=True, timeout=300)
print(PDF, PDF.stat().st_size // 1024, "KB")

#!/usr/bin/env python3
"""Plan-first layout for Canva rebuilds: validate editability/hierarchy, then emit edit-design ops.

  layout_plan.py check plan.json           # report problems (exit 1 if any ERROR)
  layout_plan.py ops plan.json PAGE_ID     # print insert/add_text operations JSON, in layer order

Plan format (coordinates in Canva page pixels; list order == bottom-to-top layer order):
{
  "page": {"w": 816, "h": 1056, "margin": 40},
  "elements": [
    {"name": "header_band", "kind": "rect", "role": "background", "x": 0, "y": 0, "w": 816, "h": 340, "color": "#1E2766"},
    {"name": "header_texture", "kind": "image", "role": "decor", "asset": "MAH...", "x": 0, "y": 0, "w": 816, "h": 340,
     "opacity": 0.08, "transparent": true, "alt": "Star pattern"},
    {"name": "card1", "kind": "rect", "role": "container", "x": 40, "y": 552, "w": 232, "h": 210, "color": "#FFFFFF",
     "radius": 14, "stroke": "#DCE0F5", "stroke_weight": 1.5},
    {"name": "gold_ring", "kind": "ring", "role": "decor", "x": 456, "y": 20, "w": 320, "h": 320, "stroke": "#E6C27A", "stroke_weight": 2},
    {"name": "icon", "kind": "path", "role": "content", "x": 63, "y": 455, "w": 18, "h": 18, "d": "M...", "vb": [24, 24], "color": "#E6C27A"},
    {"name": "hero", "kind": "image", "role": "content", "asset": "MAH...", "x": 466, "y": 30, "w": 300, "h": 300, "transparent": true, "alt": "..."},
    {"name": "title", "kind": "text", "role": "text", "text": "Title", "x": 40, "y": 150, "w": 420, "size": 50, "line_height": 1.05}
  ]
}
kinds: rect | circle | ring | path | image | text.   roles: background | decor | container | content | text.
"transparent": true on images whose pixels are mostly see-through (cut-outs, textures).
Text height is estimated (chars * 0.58 * size per line, bold sans); pass "h" to override.
"""
import json
import math
import sys

CHAR_W = 0.58  # average glyph width / font size for bold sans; serif display ~0.52


def text_h(e):
    if "h" in e:
        return e["h"]
    size, lh = e.get("size", 16), e.get("line_height", 1.4)
    lines = 0
    for para in e["text"].split("\n"):
        lines += max(1, math.ceil(len(para) * CHAR_W * size / e["w"]))
    return lines * size * lh


def box(e):
    h = text_h(e) if e["kind"] == "text" else e["h"]
    return (e["x"], e["y"], e["x"] + e["w"], e["y"] + h)


def inter(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def area(a):
    return (a[2] - a[0]) * (a[3] - a[1])


def contains(outer, inner, tol=1):
    return (outer[0] <= inner[0] + tol and outer[1] <= inner[1] + tol and
            outer[2] >= inner[2] - tol and outer[3] >= inner[3] - tol)


def check(plan):
    pg = plan["page"]
    els = plan["elements"]
    m = pg.get("margin", 40)
    out = []
    err = lambda s: out.append("ERROR  " + s)
    warn = lambda s: out.append("WARN   " + s)
    boxes = [box(e) for e in els]
    first_text = next((i for i, e in enumerate(els) if e["kind"] == "text"), len(els))

    for i, e in enumerate(els):
        b = boxes[i]
        n = e.get("name", f"#{i}")
        # Layer order: text on top of everything.
        if e["kind"] != "text" and i > first_text:
            err(f"{n}: non-text element placed after text starts; move it below all text so it can't sit on top of a text box")
        # Page bounds.
        if b[0] < -0.5 or b[1] < -0.5 or b[2] > pg["w"] + 0.5 or b[3] > pg["h"] + 0.5:
            warn(f"{n}: extends outside the page {tuple(round(v) for v in b)}")
        # Margins for content.
        if e.get("role") in ("text", "content", "container") and (b[0] < m - 0.5 or b[2] > pg["w"] - m + 0.5):
            warn(f"{n}: breaks the {m}px side margin (x {round(b[0])}-{round(b[2])})")
        if e["kind"] == "text" and e.get("size", 16) < 9:
            warn(f"{n}: {e.get('size')}px text is too small to read in print")

    for i, a in enumerate(els):
        for j in range(i + 1, len(els)):
            b = els[j]
            na, nb = a.get("name", f"#{i}"), b.get("name", f"#{j}")
            ov = inter(boxes[i], boxes[j])
            if not ov:
                continue
            # Text must never overlap text: both become hard to click and read.
            if a["kind"] == "text" and b["kind"] == "text":
                err(f"text boxes overlap: {na} / {nb} ({int(ov)} px²) - move one or shorten/widen")
                continue
            if b["kind"] == "text":
                continue  # text over a shape/image is the intended pattern
            # A later non-text element hides an earlier element completely -> earlier one can't be clicked.
            if contains(boxes[j], boxes[i]):
                opaque = b["kind"] in ("rect", "circle", "path") and b.get("opacity", 1) >= 0.99
                same = area(boxes[j]) <= area(boxes[i]) * 1.05
                if same:
                    err(f"{nb} sits exactly on top of {na}: {na} can't be selected. Merge them (e.g. bake the backdrop "
                        f"colour into the image) or drop the redundant one")
                elif opaque:
                    err(f"{nb} (opaque) completely hides {na}")
                elif a.get("role") == "background" and b.get("role") == "decor":
                    warn(f"{nb} overlays background {na}: clicks on the band select {nb}. Prefer ONE layer per band "
                         f"(bake texture/glow + colour into a single image) or tell the user to lock both")
                else:
                    warn(f"{nb} fully covers {na}'s area; {na} is only selectable through the Layers panel")
            elif b.get("role") == "decor" and a["kind"] != "text" and ov > 0.5 * area(boxes[i]):
                warn(f"decor {nb} covers most of {na}; consider moving the decor lower in the stack")
    return out


def ops(plan, page_id):
    res = []
    for e in plan["elements"]:
        k = e["kind"]
        base = {"page_id": page_id, "top": e["y"], "left": e["x"]}
        if k in ("rect", "circle", "ring", "path"):
            if k == "rect":
                d, vb = f"M0 0 L{e['w']} 0 L{e['w']} {e['h']} L0 {e['h']} Z", [e["w"], e["h"]]
            elif k in ("circle", "ring"):
                d, vb = "M0 50 A50 50 0 1 1 100 50 A50 50 0 1 1 0 50 Z", [100, 100]
            else:
                d, vb = e["d"], e["vb"]
            op = {"type": "insert_shape", **base, "width": e["w"], "height": e["h"], "path": d,
                  "view_box_width": vb[0], "view_box_height": vb[1]}
            if k != "ring":
                op["color"] = e["color"]
            for src, dst in (("radius", "corner_rounding"), ("stroke", "stroke_color"),
                             ("stroke_weight", "stroke_weight"), ("opacity", "opacity")):
                if src in e:
                    op[dst] = e[src]
            res.append(op)
        elif k == "image":
            op = {"type": "insert_fill", **base, "width": e["w"], "height": e["h"], "asset_type": "image",
                  "asset_id": e["asset"], "alt_text": e.get("alt", e.get("name", "image"))}
            if "opacity" in e:
                op["opacity"] = e["opacity"]
            res.append(op)
        elif k == "text":
            res.append({"type": "add_text", **base, "width": e["w"], "text": e["text"]})
    return res


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "ops"):
        print(__doc__)
        return 2
    plan = json.load(open(sys.argv[2]))
    if sys.argv[1] == "check":
        issues = check(plan)
        print("\n".join(issues) if issues else "OK: no overlap or layering problems found")
        return 1 if any(i.startswith("ERROR") for i in issues) else 0
    print(json.dumps(ops(plan, sys.argv[3]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

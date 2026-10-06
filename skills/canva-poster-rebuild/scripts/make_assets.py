#!/usr/bin/env python3
"""Asset helpers for rebuilding a flat poster in Canva.

Import as a module (python3 -c "import sys; sys.path.insert(0, '<skill>/scripts'); from make_assets import *")
or run the CLI:

  make_assets.py crop SRC OUT x0 y0 x1 y1 [--scale N] [--nearest] [--knockout]
  make_assets.py circle SRC OUT SIZE [--bg #E9ECFC] [--zoom 1.1] [--offset-y 14]
  make_assets.py pattern OUT W H [--cell 96]
  make_assets.py glow OUT W H CX CY R [--rgb 110,128,230] [--alpha 150]
  make_assets.py dots OUT W H [--rgb 244,196,214]
  make_assets.py sample SRC x,y [x,y ...]
  make_assets.py band OUT W H [--base #1E2766] [--pattern 0.08] [--glow cx,cy,r]   # one flattened band image

Render at 2x the Canva element size for crisp output (e.g. 816x340 element -> 1632x680 PNG).
"""
import argparse
import math
import sys

from PIL import Image, ImageDraw, ImageFilter


def knockout_white(im, hard=245, soft=225):
    """Near-white -> transparent, with a soft ramp so edges stay smooth."""
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            m = min(r, g, b)
            if m >= hard:
                px[x, y] = (r, g, b, 0)
            elif m >= soft:
                px[x, y] = (r, g, b, int(a * (hard - m) / (hard - soft)))
    return im


def crop(src, box, scale=1, nearest=False, knockout=False):
    im = Image.open(src).convert("RGBA").crop(box)
    if knockout:
        im = knockout_white(im)
    if scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)),
                       Image.NEAREST if nearest else Image.LANCZOS)
    return im


def circle_clip(im, size, bg=None, zoom=1.0, offset=(0, 0)):
    """Place `im` on a square canvas (optionally filled with bg) and clip to a circle.
    zoom>1 lets the circle edge hide flat crop edges of the artwork."""
    canvas = Image.new("RGBA", (size, size), bg or (0, 0, 0, 0))
    w = int(size * zoom * im.width / max(im.width, im.height))
    h = int(size * zoom * im.height / max(im.width, im.height))
    art = im.convert("RGBA").resize((w, h), Image.LANCZOS)
    canvas.alpha_composite(art, ((size - w) // 2 + offset[0], (size - h) // 2 + offset[1]))
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    canvas.putalpha(Image.composite(canvas.getchannel("A"), Image.new("L", (size, size), 0),
                                    m.resize((size, size), Image.LANCZOS)))
    return canvas


def star_pattern(w, h, cell=96, width=2):
    """8-point star lattice, white lines on transparent. Use at element opacity ~0.08."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    r = cell * 0.42
    for gy in range(-1, h // cell + 2):
        for gx in range(-1, w // cell + 2):
            cx, cy = gx * cell + (cell // 2 if gy % 2 else 0), gy * cell
            for rot in (0, 45):
                pts = [(cx + r * math.cos(math.radians(rot + 45 + 90 * k)),
                        cy + r * math.sin(math.radians(rot + 45 + 90 * k))) for k in range(4)]
                dr.line(pts + [pts[0]], fill=(255, 255, 255, 255), width=width)
            q = r * 0.35
            dr.ellipse((cx - q, cy - q, cx + q, cy + q), outline=(255, 255, 255, 255), width=width)
    return im


def glow(w, h, cx, cy, r, rgb=(110, 128, 230), alpha=150):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for rr in range(r, 0, -4):
        a = int(alpha * (1 - rr / r) ** 1.6)
        dr.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(*rgb, a))
    return im.filter(ImageFilter.GaussianBlur(20))


def band(w, h, base="#1E2766", pattern_alpha=0.08, glow_at=None, glow_r=None, glow_rgb=(110, 128, 230)):
    """One flattened background band: solid colour + optional glow + faint star pattern.
    Using a single image per band keeps clicks from landing on a texture layer."""
    im = Image.new("RGBA", (w, h), _rgb(base))
    if glow_at:
        im.alpha_composite(glow(w, h, glow_at[0], glow_at[1], glow_r or h, glow_rgb))
    if pattern_alpha:
        p = star_pattern(w, h)
        p.putalpha(p.getchannel("A").point(lambda a: int(a * pattern_alpha)))
        im.alpha_composite(p)
    return im.convert("RGB")


def dot_grid(w, h, rgb=(244, 196, 214), step=42):
    """Dots that grow/darken toward the bottom-right."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for y in range(20, h, step):
        for x in range(20, w, step):
            t = (x / w) * 0.7 + (y / h) * 0.3
            rr = 4 + 12 * t
            dr.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(*rgb, int(60 + 170 * t)))
    return im


def _rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crop"); c.add_argument("src"); c.add_argument("out")
    for k in ("x0", "y0", "x1", "y1"):
        c.add_argument(k, type=int)
    c.add_argument("--scale", type=float, default=1); c.add_argument("--nearest", action="store_true")
    c.add_argument("--knockout", action="store_true")
    ci = sub.add_parser("circle"); ci.add_argument("src"); ci.add_argument("out"); ci.add_argument("size", type=int)
    ci.add_argument("--bg"); ci.add_argument("--zoom", type=float, default=1.0); ci.add_argument("--offset-y", type=int, default=0)
    pa = sub.add_parser("pattern"); pa.add_argument("out"); pa.add_argument("w", type=int); pa.add_argument("h", type=int)
    pa.add_argument("--cell", type=int, default=96)
    g = sub.add_parser("glow"); g.add_argument("out")
    for k in ("w", "h", "cx", "cy", "r"):
        g.add_argument(k, type=int)
    g.add_argument("--rgb", default="110,128,230"); g.add_argument("--alpha", type=int, default=150)
    d = sub.add_parser("dots"); d.add_argument("out"); d.add_argument("w", type=int); d.add_argument("h", type=int)
    d.add_argument("--rgb", default="244,196,214")
    s = sub.add_parser("sample"); s.add_argument("src"); s.add_argument("points", nargs="+")
    b = sub.add_parser("band"); b.add_argument("out"); b.add_argument("w", type=int); b.add_argument("h", type=int)
    b.add_argument("--base", default="#1E2766"); b.add_argument("--pattern", type=float, default=0.08)
    b.add_argument("--glow", help="cx,cy,r in output pixels")
    a = p.parse_args()
    if a.cmd == "band":
        g_ = [int(v) for v in a.glow.split(",")] if a.glow else None
        band(a.w, a.h, a.base, a.pattern, g_[:2] if g_ else None, g_[2] if g_ else None).save(a.out)
        print("wrote", a.out)
        return 0

    if a.cmd == "crop":
        crop(a.src, (a.x0, a.y0, a.x1, a.y1), a.scale, a.nearest, a.knockout).save(a.out)
    elif a.cmd == "circle":
        circle_clip(Image.open(a.src), a.size, _rgb(a.bg) if a.bg else None, a.zoom, (0, a.offset_y)).save(a.out)
    elif a.cmd == "pattern":
        star_pattern(a.w, a.h, a.cell).save(a.out)
    elif a.cmd == "glow":
        glow(a.w, a.h, a.cx, a.cy, a.r, tuple(int(v) for v in a.rgb.split(",")), a.alpha).save(a.out)
    elif a.cmd == "dots":
        dot_grid(a.w, a.h, tuple(int(v) for v in a.rgb.split(","))).save(a.out)
    elif a.cmd == "sample":
        im = Image.open(a.src).convert("RGB")
        for pt in a.points:
            x, y = (int(v) for v in pt.split(","))
            print(pt, "#%02x%02x%02x" % im.getpixel((x, y)))
    if a.cmd not in ("sample",):
        print("wrote", a.out)


if __name__ == "__main__":
    sys.exit(main())

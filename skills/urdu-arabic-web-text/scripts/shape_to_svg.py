#!/usr/bin/env python3
"""Shape a fixed Arabic or Urdu phrase with HarfBuzz and write it as a single-path SVG.

Usage:
  python3 shape_to_svg.py FONT.ttf|otf "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ" OUT.svg [--pad 60]

Use it for phrases that must look identical on every browser (Safari drops some Qur'anic fonts' marks), such as
the Bismillah on a home page. Show the SVG as a CSS mask so it takes the theme colour:

  .bismillah { aspect-ratio: W / H; background-color: currentColor;
    -webkit-mask: url(/img/bismillah.svg) center / contain no-repeat; mask: url(/img/bismillah.svg) center / contain no-repeat; }

and give the element role="img", lang="ar" and aria-label with the real text. W and H are printed below.

Needs: pip install uharfbuzz fonttools
"""
import sys

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

args = [a for a in sys.argv[1:]]
pad = 60
if "--pad" in args:
    i = args.index("--pad")
    pad = int(args[i + 1])
    del args[i:i + 2]
if len(args) != 3:
    sys.exit(__doc__)
font_path, text, out = args

face = hb.Face(hb.Blob.from_file_path(font_path))
font = hb.Font(face)
buf = hb.Buffer()
buf.add_str(text)
buf.guess_segment_properties()
hb.shape(font, buf, {})

tt = TTFont(font_path)
glyph_set = tt.getGlyphSet()
order = tt.getGlyphOrder()
pen = SVGPathPen(glyph_set, ntos=lambda v: "%d" % round(v))
bounds = BoundsPen(glyph_set)
x = 0
# HarfBuzz returns RTL runs in visual order (left to right), so glyphs can be laid out with a running x.
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    name = order[info.codepoint]
    t = (1, 0, 0, -1, x + pos.x_offset, -pos.y_offset)  # flip y: font units grow up, SVG grows down
    glyph_set[name].draw(TransformPen(pen, t))
    glyph_set[name].draw(TransformPen(bounds, t))
    x += pos.x_advance

if bounds.bounds is None:
    sys.exit("Nothing was drawn: does the font cover this text?")
x0, y0, x1, y1 = bounds.bounds
w, h = round(x1 - x0 + 2 * pad), round(y1 - y0 + 2 * pad)
vb = f"{round(x0 - pad)} {round(y0 - pad)} {w} {h}"
with open(out, "w", encoding="utf-8") as fh:
    fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"><path d="{pen.getCommands()}"/></svg>')
print(f"{out}: viewBox {vb}  ->  aspect-ratio: {w} / {h};")

#!/usr/bin/env python3
"""Cut an Arabic-script font down to the glyphs a set of strings really uses, then prove the cut is safe.

Usage:
  python3 subset_font.py FONT.ttf|otf OUT.woff2 STRINGS.json|STRINGS.txt

STRINGS: a JSON list of strings, or a text file with one string per line. Include every phrase the page shows,
exactly as rendered (after any display-only replacements such as U+06E4 -> U+0653).

Why not plain `pyftsubset --text=`: Nastaliq and Qur'anic fonts build words through chains of contextual
substitutions and ligatures. The final glyphs are not enough; the subset must keep the intermediate glyphs the
lookups pass through, or some words shape differently. This script records the HarfBuzz buffer after every
lookup, also shapes with common features switched off, and finally checks every string shapes identically
(same glyph names and positions) with the cut. "mismatched 0 of N" means safe.

Needs: pip install uharfbuzz fonttools brotli
"""
import json
import sys

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont

if len(sys.argv) != 4:
    sys.exit(__doc__)
SRC, OUT, STRS = sys.argv[1:4]

raw = open(STRS, encoding="utf-8").read()
try:
    strings = json.loads(raw)
except json.JSONDecodeError:
    strings = [line.strip() for line in raw.splitlines() if line.strip()]
if not strings:
    sys.exit("No strings to keep.")

data = open(SRC, "rb").read()
font = hb.Font(hb.Face(data))
order = TTFont(SRC).getGlyphOrder()
gids = set()

VARIANTS = [{}, {"rlig": False}, {"calt": False}, {"rlig": False, "calt": False},
            {"rlig": False, "calt": False, "fina": False, "medi": False, "init": False}]


def trace(s, feats):
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()

    def on_message(_msg):
        gids.update(i.codepoint for i in buf.glyph_infos)
        return True

    buf.set_message_func(on_message)
    hb.shape(font, buf, feats)
    gids.update(i.codepoint for i in buf.glyph_infos)


for s in strings:
    for v in VARIANTS:
        trace(s, v)

glyphs = sorted({order[g] for g in gids if g < len(order)} | ({".notdef", "space"} & set(order)))
opts = subset.Options()
opts.layout_closure = False
opts.layout_features = ["*"]
opts.hinting = False
opts.glyph_names = True
opts.notdef_outline = True
opts.name_IDs = ["*"]
opts.name_legacy = True
sub = subset.Subsetter(opts)
sub.populate(glyphs=glyphs, unicodes=[ord(c) for c in set("".join(strings))])
f = TTFont(SRC)
sub.subset(f)
f.flavor = "woff2"
f.save(OUT)

# Verify with an uncompressed copy of the cut.
tmp = OUT + ".check.ttf"
f2 = TTFont(OUT)
f2.flavor = None
f2.save(tmp)
font2 = hb.Font(hb.Face(open(tmp, "rb").read()))
order2 = TTFont(tmp).getGlyphOrder()


def shaped(fnt, ordr, s):
    b = hb.Buffer()
    b.add_str(s)
    b.guess_segment_properties()
    hb.shape(fnt, b, {})
    return [(ordr[i.codepoint], p.x_advance, p.x_offset, p.y_offset) for i, p in zip(b.glyph_infos, b.glyph_positions)]


bad = [s for s in strings if shaped(font, order, s) != shaped(font2, order2, s)]
import os
os.remove(tmp)
print(f"{OUT}: {os.path.getsize(OUT) / 1024:.0f} KB, glyphs {len(glyphs)}, mismatched {len(bad)} of {len(strings)}")
for s in bad[:10]:
    print("  differs:", s)
sys.exit(1 if bad else 0)

"""Contrast and depth-ladder checks for a surface system. Pure stdlib.

    python3 check_contrast.py surfaces.css           # check the tokens and dark grounds in a stylesheet
    python3 check_contrast.py pair '#5b6b84' '#f1f5fa'
    python3 check_contrast.py stack '#90a2bd' '#0c1124' 'rgba(255,255,255,.05)' 'rgba(139,92,246,.22)'
    python3 check_contrast.py oklch '#e9eef6' '#ffffff'

`stack` = text colour, base ground, then every gradient layer at its PEAK alpha where it sits behind text (the
corner of a radial bloom, the top of a sheen), bottom to top. That composite is what the text is really read
against; checking only the base colour is how muted text ends up at 3.9:1 in a glowing corner.

Targets: body and muted text ≥ 4.5:1; large text (≥ 24 px, or ≥ 19 px bold) and graphics, icons, borders that carry
meaning ≥ 3:1. Depth ladder: neighbouring grounds ≥ ~0.02 OKLCH L apart in light themes (with a shadow or line
helping), ≥ ~0.05 in dark, where shadows vanish.
"""

from __future__ import annotations

import re
import sys


def parse(color: str) -> tuple[float, float, float, float]:
    c = color.strip().lower()
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return r, g, b, a
    m = re.fullmatch(r"rgba?\(([^)]*)\)", c)
    if m:
        parts = [p for p in re.split(r"[\s,/]+", m.group(1)) if p]
        r, g, b = (float(p) / 255 for p in parts[:3])
        a = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1) if len(parts) > 3 else 1.0
        return r, g, b, a
    raise ValueError(f"unsupported colour: {color!r} (use #hex or rgb()/rgba())")


def over(top: tuple, bottom: tuple) -> tuple:
    """Source-over compositing in sRGB space, which is what browsers do for these layers."""
    a = top[3] + bottom[3] * (1 - top[3])
    if a == 0:
        return 0.0, 0.0, 0.0, 0.0
    mix = lambda i: (top[i] * top[3] + bottom[i] * bottom[3] * (1 - top[3])) / a
    return mix(0), mix(1), mix(2), a


def composite(base: str, *layers: str) -> tuple:
    result = parse(base)
    for layer in layers:
        result = over(parse(layer), result)
    return result


def _linear(u: float) -> float:
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple) -> float:
    r, g, b = (_linear(u) for u in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: tuple, bg: tuple) -> float:
    if fg[3] < 1:
        fg = over(fg, bg)
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def oklch_l(rgb: tuple) -> float:
    r, g, b = (_linear(u) for u in rgb[:3])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    return 0.2104542553 * l ** (1 / 3) + 0.7936177850 * m ** (1 / 3) - 0.0040720468 * s ** (1 / 3)


def hexof(rgb: tuple) -> str:
    return "#" + "".join(f"{round(u * 255):02x}" for u in rgb[:3])


# ── Stylesheet mode ─────────────────────────────────────────────────────────────────────────────────────────────

def blocks(css: str) -> dict[str, dict[str, str]]:
    """Custom properties per selector block, for the blocks that define tokens."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out: dict[str, dict[str, str]] = {}
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*--[^{}]*)\}", css):
        props = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body))
        out.setdefault(" ".join(selector.split()), {}).update({k: v.strip() for k, v in props.items()})
    return out


SOLID = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))$")

TEXT_PAIRS = [  # (text token, ground token, minimum)
    ("--text", "--page", 4.5), ("--text", "--surface", 4.5), ("--text", "--card", 4.5), ("--text", "--well", 4.5),
    ("--muted", "--page", 4.5), ("--muted", "--surface", 4.5), ("--muted", "--card", 4.5), ("--muted", "--well", 4.5),
    ("--muted-strong", "--card", 4.5), ("--accent", "--surface", 3.0), ("--accent", "--card", 3.0),
    ("--on-accent", "--accent", 4.5), ("--on-accent", "--accent-deep", 4.5), ("--accent", "--accent-soft", 4.5),
]
LADDER = [("--surface", "--card"), ("--card", "--page"), ("--card", "--well")]  # a well sits inside a card

# Where text can sit on each dark ground, as (label, base, layers at peak). Keep in step with the stylesheet.
GROUND_PEAKS = {
    "cosmic": [("top-right bloom", "#0c1124", ["rgba(255,255,255,.05)", "rgba(139,92,246,.22)"]),
               ("bottom-left bloom", "#0a0f20", ["rgba(34,211,238,.15)"])],
    "aurora": [("top-left bloom", "#0b1428", ["rgba(59,130,246,.24)"]),
               ("bottom-right bloom", "#0b1428", ["rgba(20,184,166,.18)"])],
    "twilight": [("top-left corner", "#1e2a66", [])],
    "glass-edge": [("top edge", "#16244a", ["rgba(255,255,255,.06)"])],
}


def check_stylesheet(path: str) -> int:
    found = blocks(open(path, encoding="utf-8").read())
    light = next((v for k, v in found.items() if k == ":root"), {})
    dark = {**light, **next((v for k, v in found.items() if "data-theme" in k and "dark" in k and "data-ground" not in k), {})}
    failures = 0
    for name, tokens in (("light", light), ("dark", dark)):
        print(f"\n{name} theme")
        for fg, bg, minimum in TEXT_PAIRS:
            a, b = tokens.get(fg, ""), tokens.get(bg, "")
            if not (SOLID.match(a) and SOLID.match(b)):
                continue
            ratio = contrast(parse(a), parse(b))
            ok = ratio >= minimum
            failures += not ok
            print(f"  {'ok ' if ok else 'LOW'} {fg:>14} on {bg:<13} {ratio:5.2f}:1  (min {minimum})")
        for upper, lower in LADDER:
            a, b = tokens.get(upper, ""), tokens.get(lower, "")
            if SOLID.match(a) and SOLID.match(b):
                step = oklch_l(parse(b)) - oklch_l(parse(a))
                print(f"      ladder {upper} → {lower}: {abs(step):.3f} OKLCH L {'darker' if step < 0 else 'lighter' if step > 0 else 'SAME'}")
    muted = dark.get("--muted", "#90a2bd")
    print("\ndark grounds: --muted at each gradient peak")
    for ground, peaks in GROUND_PEAKS.items():
        for label, base, layers in peaks:
            bg = composite(base, *layers)
            ratio = contrast(parse(muted), bg)
            ok = ratio >= 4.5
            failures += not ok
            print(f"  {'ok ' if ok else 'LOW'} {ground:<10} {label:<18} {hexof(bg)}  {ratio:5.2f}:1")
    print("\nfrosted glass (72% surface fill) over a saturated violet backdrop: secondary text")
    for name, tokens in (("light", light), ("dark", dark)):
        surface = parse(tokens.get("--surface", "#ffffff"))
        fill = f"rgba({round(surface[0]*255)},{round(surface[1]*255)},{round(surface[2]*255)},.72)"
        bg = composite("#8b5cf6", fill)
        ratio = contrast(parse(tokens.get("--muted-strong", "#475569")), bg)
        ok = ratio >= 4.5
        failures += not ok
        print(f"  {'ok ' if ok else 'LOW'} {name:<6} --muted-strong on {hexof(bg)}  {ratio:5.2f}:1")
    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1].endswith(".css"):
        return check_stylesheet(argv[1])
    if len(argv) == 4 and argv[1] == "pair":
        print(f"{contrast(parse(argv[2]), parse(argv[3])):.2f}:1")
        return 0
    if len(argv) >= 4 and argv[1] == "stack":
        bg = composite(argv[3], *argv[4:])
        print(f"text {argv[2]} on {hexof(bg)} (composited): {contrast(parse(argv[2]), bg):.2f}:1")
        return 0
    if len(argv) >= 3 and argv[1] == "oklch":
        for c in argv[2:]:
            print(f"{c}: L {oklch_l(parse(c)):.3f}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

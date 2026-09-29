# Theme gallery: complete, proven directions to start from

Each theme below was built and reviewed on a real product. Pick one as a starting direction and change the accent
hue; don't mix the grounds of two themes on one screen. The CSS for the first two lives in `../assets/surfaces.css`
(open `../assets/showcase.html` and switch the theme and ground to see them).

## 1. Clean light (operations / SaaS)

Near-white grounds stepping down as they recede, 1 px lines, E1/E2 shadows, a cobalt accent.

| Token | Value | Role |
|---|---|---|
| `--page` | `#e9eef6` | page, a cool grey-blue |
| `--surface` | `#ffffff` | panels |
| `--card` | `#f1f5fa` | cards in panels (+ top-lit tint, E1) |
| `--well` | `#e8edf5` | inputs, plots, tracks |
| `--text` / `--muted` / `--muted-strong` | `#0f172a` / `#5b6b84` / `#475569` | |
| `--accent` → `--accent-deep` | `#2563eb` → `#1d4fd8` | primary face gradient |

Character: calm, dense, readable for hours. Colour comes only from the accent, tone washes on stat tiles, status
badges and the selected card's edge bloom.

## 2. Dark with lit panels (four grounds)

Base: page `#050810`, surface `#121b2e`, card/well `#1e2a45`, text `#e7edf8`, muted `#90a2bd`, accent `#6c9aff`.
Panels then wear one ground (`data-ground` on `<html>`):

| Ground | Look | Brightest point behind text | Muted text there |
|---|---|---|---|
| **Cosmic** (the owner's pick) | violet bloom top-right, cyan bloom bottom-left, ink-navy base, full glass lift (rims, inner band, lip, indigo under-glow) | `#312b5b` | 4.98:1 |
| Aurora | blue glow top-left, teal glow bottom-right, deep navy | `#172e59` | 5.13:1 |
| Twilight | one strong diagonal, indigo `#1e2a66` → ink `#080c1c` | `#1e2a66` | 5.13:1 |
| Glass edge | navy `#16244a` falling to `#0b1226`, top sheen, luminous edge | `#243155` | 4.91:1 |

Cosmic and Glass edge carry the most "glass"; Twilight is the most dramatic; Aurora the most colourful. The
numbers are from `check_contrast.py` on the shipped values. Aurora, Twilight and Glass edge were rebuilt from the
project's render notes (described colours and peaks) and re-measured, not copied from shipped CSS.

## 3. Liquid glass (frosted, over a vivid ambient)

From a portfolio site with a full-screen 3D scene: cobalt and cyan light behind frosted panels. Its taste is
near-future sci-fi; use it when the brief is close to that. The frosted panels sit over a colourful ambient, which
is the one place blur earns its cost.

### Tokens

```css
:root{
 --accent:#a1f7ff;                               /* cyan: active states, progress, focus */
 --muted:#bacdea;
 --line:rgba(177,216,255,.22);
 --glass-edge:rgba(201,233,255,.3);
 --glass-shadow:inset 0 1px 0 rgba(232,251,255,.2),0 8px 32px rgba(0,8,50,.2);
 color:#eff7ff; background:#070e31;
}
body{
 background:
  radial-gradient(ellipse at 84% 18%,rgba(92,240,246,.62),transparent 32%),
  radial-gradient(ellipse at 63% 40%,rgba(16,164,224,.52),transparent 38%),
  radial-gradient(ellipse at 9% 8%,rgba(47,77,235,.85),transparent 52%),
  radial-gradient(ellipse at 95% 88%,rgba(45,71,213,.8),transparent 52%),
  linear-gradient(145deg,#071032 8%,#102777 50%,#091437 85%);
 background-attachment:fixed;
}
.glass{                                          /* header, panels, docks */
 background:linear-gradient(115deg,rgba(32,63,130,.65),rgba(12,25,72,.72));
 border:1px solid var(--glass-edge);
 backdrop-filter:blur(18px) saturate(145%); -webkit-backdrop-filter:blur(18px) saturate(145%);
 box-shadow:var(--glass-shadow);
}
.pill-active{                                    /* the gliding nav pill */
 background:linear-gradient(135deg,rgba(139,237,255,.28),rgba(142,165,255,.16));
 box-shadow:inset 0 1px 0 rgba(209,252,255,.28),inset 0 0 0 1px rgba(188,235,255,.17);
}
::selection{background:#a1f7ff;color:#071d4a}
```

### Type and details

- Manrope (variable) for display and body, IBM Plex Mono for small uppercase labels ("eyebrows"), with generous
  letter spacing on the mono labels.
- Nameplates in the 3D scene: lacquered walnut with sand-coloured etched lettering, a thin cyan inlay; warm materials
  next to the cool UI keep it from feeling cold.
- Static `backdrop-filter` on small, fixed panels over the 3D canvas was fine; never animate it.

### What the owner cared about

Concise copy, readable sizes on phones (body at least 14-15 px, dates 12 px), a realistic scene under a sci-fi UI,
and seeing a render of every visual change before it shipped.

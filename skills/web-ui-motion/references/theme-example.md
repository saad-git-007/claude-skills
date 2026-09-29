# Example theme: "liquid glass" (cobalt and cyan)

One project's look, recorded as a worked example of a coherent theme; it is that site's taste. Use it only when a
user asks for this style or something close (near-future sci-fi, glassy panels, soft glow).

## Tokens

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

## Type and details

- Manrope (variable) for display and body, IBM Plex Mono for small uppercase labels ("eyebrows"), with generous
  letter spacing on the mono labels.
- Nameplates in the 3D scene: lacquered walnut with sand-coloured etched lettering, a thin cyan inlay; warm materials
  next to the cool UI keep it from feeling cold.
- Static `backdrop-filter` on small, fixed panels over the 3D canvas was fine; never animate it.

## What the owner cared about

Concise copy, readable sizes on phones (body at least 14-15 px, dates 12 px), a realistic scene under a sci-fi UI,
and seeing a render of every visual change before it shipped.

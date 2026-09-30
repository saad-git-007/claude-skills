---
name: web-ui-surfaces
description: "A proven visual system for polished web UI at rest: depth ladders (light and dark), wells vs raised controls, gradient rules (px-sized blooms, colour over brightness, contrast at the brightest point), dark panels lifted by light (rims, inner band, under-glow), glass (gradient glass vs frosted, with measured fills), and recipes for primary/secondary buttons, cards, selected and alert states, stat tiles, segmented controls, fields, badges and tables. Ships a themeable surfaces.css (light, dark, four dark grounds), a showcase page and a contrast/ladder checker. Use whenever the user wants a website or app to look more polished, premium, modern or \"less flat\", asks for gradients, glassmorphism, glowing or lifted cards, nicer buttons, a dark theme, a colour palette or design tokens, or starts a new site and wants it to look good, even if they don't name any of these."
---

# Web UI surfaces: depth, gradients, glass and components

Distilled from a production operations app whose look was rebuilt in several rounds: grounds re-spaced by measured
lightness, a dark theme chosen by its owner from three rounds of rendered variants (four subtle options rejected as
"they all look pretty same", then bolder families, then a crossing of the two they liked), and every text colour
checked against every ground and gradient peak by tests. A portfolio site's frosted-glass theme is included as a
second, contrasting direction. The main lesson: **polish is mostly depth and restraint, measured.** Surfaces that
step apart by the right amount, one accent doing one job, gradients kept to corners and edges, and a press state on
everything you can press.

## The rules (why each exists)

1. **Depth is a ladder of grounds spaced by OKLCH lightness**, not hexes that look different on one monitor. Light
   themes step *down* as surfaces recede (~0.02-0.03 L, helped by lines and soft shadows); dark themes step *up* as
   they nest (~0.06-0.09 L), because shadows vanish on near-black. Old steps of 1.05:1 read as flat in both.
2. **You read through wells; you press raised things.** Inputs, plots, tracks and table heads recede; buttons and
   dropdown triggers stand proud. A dropdown styled as a well looked disabled.
3. **One token, one depth; one colour, one job.** A token painting both cards and wells made depth undefined; one blue
   painting heading, value, stroke, dot and button made nothing stand out.
4. **Gradients: px-sized, hue not brightness, corners and edges, measured at the peak.** A `%` glow spread behind a
   nested card and sank it; a brighter ground flips nesting; a sheen on a bloom took muted text to 3.9:1 until halved.
5. **On near-black, lift is light:** a bright top rim, a light band inside the top edge, a dark bottom rim, a
   luminous lip and a coloured under-glow. Remove one and the panel sinks.
6. **Split `background-color` (state) from `background-image` (tint/gradient)** on every raised surface. A shorthand
   in a state rule erases the gradient.
7. **Glass comes from edges first.** Gradient glass (sheen, luminous edge, rims) works anywhere at no cost. Frosted
   glass only over something worth blurring, small, fixed, never animated, and with enough fill: 58% left muted text
   at 3.1:1; 72% plus stronger secondary text measured 5.3:1.
8. **Every control answers a press; disabled looks inert.** Primary: accent face gradient + accent-tinted shadow,
   lift on hover, sink on press. Secondary: surface + tint + strong line, recesses instantly. One primary per view.
9. **Contrast is checked, not eyeballed:** text ≥ 4.5:1 and meaningful graphics ≥ 3:1 on *every* ground it can land
   on, including washes, selected states and gradient peaks, and on both ends of a gradient button face.
10. **Render variants and let the owner choose;** make them bold enough to tell apart; judge subtle effects at 2×.

## Workflow for a new site or app

1. Pick a direction from `references/theme-gallery.md` (clean light, dark with lit panels, liquid glass), or define
   one: the page ground, one accent (plus a deeper partner for gradients), tones for status.
2. Copy `assets/surfaces.css`, rename classes to the project's, set the accent, and run
   `python3 assets/check_contrast.py <your.css>`. Fix every LOW before designing further.
3. Build pages from the component recipes (`references/components.md`); gradients and glass from
   `references/gradients-and-glass.md`; depth and colour roles from `references/depth-and-color.md`.
4. For anything taste-driven (a dark ground, a hero treatment), render 3-5 named variants of a real screen and ask
   (`references/process.md`). Open `assets/showcase.html` for a quick look at every component in both themes.
5. Apply the theme before first paint, review both themes at desktop and 390 px with real data, and check hover in a
   browser that has hover (headless Chrome doesn't).
6. Motion (entrances, pills that glide, drawers, loaders) is a separate skill: `web-ui-motion`.

## Rejected, and why (so it doesn't get re-proposed)

- **Subtle variants of the same idea** (four darker navies): owners can't tell them apart. Vary hue, direction, lift.
- **Brighter panels for "pop" in dark mode:** they flip nesting (cards look sunken). Use hue blooms and rim light.
- **%-sized glows on panels:** they scale with the element and leak behind nested content.
- **Wide selected-state blooms:** at 60% width the bloom went under meta text (3.85:1). End it at ~12%.
- **Grey shadows under saturated buttons:** they look dirty. Tint the shadow with the button's hue.
- **Sheen on every button:** glitter. One primary action per view (maybe two or three special entry points).
- **Animated blur or gradients:** they cost frames. Paint is free at rest; animate transform and opacity only.
- **Frosted glass by default:** it needs something behind it, costs GPU, and its contrast depends on what passes
  behind. Gradient glass got the owner's pick.
- **Recessed (well-styled) dropdown buttons:** read as disabled.
- **A rose red for small status signals:** reads pink at 9 px; use a true red token, same in both themes.

## Reference files

- `references/depth-and-color.md`: the ladder with measured L values, wells vs raised, shadows per theme, the
  five-part dark lift, colour roles and overload, contrast targets and where to measure, colours for data.
- `references/gradients-and-glass.md`: the gradient rules, recipes (tone wash, corner blooms, edge bands, button
  face, brand mark, sheen), stacking and state, gradient vs frosted glass (measured fills), ambient page light.
- `references/components.md`: buttons (table), cards and their states, panels, stat tiles, segmented controls,
  fields (16 px, native select popups), badges, tables, dialogs, each with its trap.
- `references/process.md`: rendering named variants for the owner, making it regression-proof, rendering and
  review traps (theme before first paint, headless hover, native popups), what owners asked for.
- `references/theme-gallery.md`: three complete directions with tokens and measured peaks.
- `assets/surfaces.css`: the whole system, generic class names, light + dark + four dark grounds.
- `assets/showcase.html`: every component in one page; `?theme=dark&ground=aurora` to switch from the URL.
- `assets/check_contrast.py`: checks a stylesheet's text/ground pairs, ladder steps, dark-ground peaks and frosted
  glass; also `pair`, `stack` (composite layers at their peak) and `oklch` modes.

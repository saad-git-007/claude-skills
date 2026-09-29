# Gradients and glass

## Contents
1. The gradient rules
2. Recipes: washes, blooms, sheens, edge bands, faces
3. Stacking and state
4. Glass: gradient glass vs frosted glass
5. Ambient page light

## 1. The gradient rules

1. **Size gradients in px, not %.** A `%`-sized glow scales with the element: on a 2,000 px panel it spread hundreds
   of pixels down behind a nested card and made it look sunken. `radial-gradient(520px 320px at 100% 0%, …)`
   keeps the light in the corner on a 90 px tile and a 2,000 px panel alike.
2. **Colour carries the pop, not brightness.** A ground brighter than the cards nested in it flips them from raised
   to recessed. Peaks should change hue (violet, cyan) at a lightness close to the base.
3. **Glows peak where text is sparse**: panel corners, the header band, the leading edge of a card. Never centre a
   bloom behind body copy.
4. **Measure text at the brightest point** of the stacked layers (`check_contrast.py stack`). A glassy sheen stacked
   on a violet bloom dropped muted text to 3.9:1 in a corner; halving the sheen and trimming the bloom brought every
   peak to ≥ 4.7:1. A draft "Aurora" failed at 4.3:1 behind panel subtitles and was dimmed before anyone saw it.
5. **Decorative texture behind text is a local bright speck.** A sparse starfield option was kept faint and flagged
   as the busiest choice for that reason.
6. **Static paint is free.** Gradients cost nothing at rest; animating them (or `filter`/`backdrop-filter`) is what
   costs frames. Keep motion to transform and opacity.

## 2. Recipes

**Tone wash** (a stat tile carries a whisper of its icon's hue, so four tiles read as four at a glance):
```css
.tile.tone-green { background-image: linear-gradient(135deg, var(--green-soft), transparent 65%); }
.tile.tone-green .tile-icon { background: var(--green-soft); color: var(--green); }
```

**Corner blooms** (a dark panel ground; px-sized, low alpha, hue not brightness):
```css
background-image:
  linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,0) 110px),        /* glassy top sheen */
  radial-gradient(520px 320px at 100% 0%, rgba(139,92,246,.22), transparent 70%),   /* violet, top right */
  radial-gradient(560px 360px at 0% 100%, rgba(34,211,238,.15), transparent 70%),   /* cyan, bottom left */
  linear-gradient(180deg, #0c1124, #0a0f20);                                        /* ink-navy base */
```

**Edge band for state** (from the edge that carries meaning, narrow enough to stay off the text):
```css
.card.is-alert    { background-image: linear-gradient(90deg, var(--orange-soft), transparent 55%); }
.card.is-selected { background-image: linear-gradient(90deg, color-mix(in srgb, var(--accent) 16%, transparent), transparent 12%);
                    box-shadow: inset 3px 0 0 var(--accent), var(--shadow-e1); }
```
The selected bloom first ran to 60% and dragged muted meta text to 3.85:1. It now ends at 12%, hugging the bar.

**Button face**: a diagonal between the accent and a deeper accent (`linear-gradient(135deg, var(--accent),
var(--accent-deep))`) plus a 1 px inner top highlight (`inset 0 1px 0 rgba(255,255,255,.22)`) and a shadow
**tinted with the accent**. A grey shadow under a saturated button looks dirty. Check `--on-accent` against **both
ends** of the face: dark text on a dark-theme face passed at the light end and failed (4.45:1) at the deep end.

**Brand mark / avatar**: two-hue diagonal + inner top highlight + a small tinted drop glow. At avatar size, prefer
radial blobs to a conic sweep (a conic centre reads as a pinwheel seam at ~22 px).

**Sheen** (a diagonal highlight swept once on hover): on the one primary action per view, maybe two or three
special entry points. On every control it reads as glitter. It's visible only ~20-130 ms into a 600 ms sweep, so
review it frame by frame, not with one screenshot.

## 3. Stacking and state

- **Split `background-color` (state) from `background-image` (tint, wash, bloom).** State rules move only the
  colour; a `background:` shorthand in a hover rule silently erases the gradient. Treat the shorthand on these
  elements as a bug.
- **Tie-breaks by order.** When alert and selected combine, the later rule wins; put selected after alert on
  purpose, and write it down.
- **Layer washes on top of grounds.** A tile's tone wash is its own `background-image` layer above the ground, so
  changing the ground doesn't lose the tones.
- Restate the lift in hover: `box-shadow: var(--panel-shadow), var(--shadow-glow)`. Replacing the shadow with only a
  glow drops the rims and the panel appears to sink on hover.

## 4. Glass

**Gradient glass (preferred):** no blur, works on any background, costs nothing.
- A slightly translucent surface fill (~92%), a top sheen (`rgba(255,255,255,.10)` fading within ~90 px), a
  luminous edge (the accent mixed into the line colour at ~38%), a bright top rim and a dark bottom rim.
- The owner's final pick in the project (the "Cosmic" ground) is gradient glass: after three rounds of renders, the
  "glass" they asked for came from rims, an inner light band and an under-glow, with no blur at all.

**Frosted glass (`backdrop-filter`):** only where there's something worth blurring behind it (photography, a 3D
canvas, a colourful ambient), only on small, fixed panels, and never animated (blur is re-computed every frame
anything behind it moves).
- **Blur averages the backdrop; it doesn't neutralise it.** Over a saturated violet bloom, a 58% surface fill left
  muted text at 3.1:1 (light) and 3.8:1 (dark). A **72% fill** plus `--muted-strong` for secondary text measured
  5.3:1 and 7.1:1. Check against the most saturated colour that can pass behind the panel.
- Always provide the opaque fallback in the base rule and add blur under `@supports (backdrop-filter: blur(1px))`.
- `saturate(145%)` with the blur keeps the colour behind lively instead of grey.
- For a whole theme built on frosted glass, see `theme-gallery.md` ("Liquid glass").

## 5. Ambient page light

One or two very large (900-1,100 px), very faint (7-10% alpha) blooms behind everything, `background-attachment:
fixed`, mixed from the accent and one neighbouring hue. It keeps a flat page from feeling dead without competing
with the panels. Keep it under the panels' own light; if you can point at the bloom, it's too strong.

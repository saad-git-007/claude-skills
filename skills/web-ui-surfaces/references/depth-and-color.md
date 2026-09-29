# Depth and colour: the ladder, wells, lift, and colour roles

## Contents
1. The depth ladder (light and dark are opposites)
2. Wells vs raised: what recedes and what stands proud
3. Shadows per theme, and lift by light on near-black
4. Colour roles and tokens
5. Contrast targets and where to measure them
6. Colours for data (charts, lanes, series)

## 1. The depth ladder

Every screen has 3-4 grounds: page, panel, card inside a panel, well inside a card. Users read depth from the
**lightness difference** between neighbours, so space them by measured OKLCH L, not by picking hex values that look
different on your monitor.

| Ground | Light theme | L | Dark theme | L |
|---|---|---|---|---|
| panel (surface) | `#ffffff` | 1.000 | `#121b2e` | ~0.22 |
| card, nested in a panel | `#f1f5fa` | 0.969 | `#1e2a45` | ~0.29 |
| page | `#e9eef6` | 0.948 | `#050810` | ~0.13 |
| well, inside a card | `#e8edf5` | 0.945 | = card | |

- **Light and dark encode depth in opposite directions.** In light, everything is near-white, so grounds step
  **down** as they recede and shadows plus 1 px lines help. In dark, shadows vanish on near-black, so nesting steps
  **up**: a card is lighter than its panel, and a well inside a card steps up exactly like the card did.
- **Step sizes that read:** light ~0.02-0.03 OKLCH L *with* a line and a soft shadow; dark ~0.06-0.09 (the old dark
  ladder's ~0.04 steps made cards invisible against the page, and plots invisible inside cards).
- **One token must not paint two depths.** The original light theme used one "soft surface" for raised cards *and*
  recessed wells, so depth read as undefined. Split them (`--card` and `--well`).
- Check any ladder with `../assets/check_contrast.py` (it prints each step).

## 2. Wells vs raised

The rule that settled every argument: **you read *through* wells; you *press* raised things.**
- Wells: text inputs, search fields, plot areas, segmented-control tracks, table heads, media placeholders, switch
  tracks, code blocks.
- Raised: buttons, dropdown triggers, chips you tap, cards you open.
- A dropdown button styled as a well read as **disabled** (an owner reported it as "washed out"). Dropdown triggers
  get control chrome: surface + tint + the strong line colour, like secondary buttons.
- A well's text still needs 4.5:1; wells are the grounds where muted text most often fails.

## 3. Shadows per theme, and lift by light

- **Light:** E1 (resting card) = contact line + soft ambient: `0 1px 2px rgba(15,23,42,.05), 0 2px 8px -2px
  rgba(15,23,42,.06)`. E2 (panel) `0 6px 18px rgba(15,23,42,.06)`. E3 (dialog) `0 14px 34px rgba(15,23,42,.10)`.
  Hover promotes a card to an accent-tinted glow, not a bigger grey shadow.
- **Dark:** contact shadow only (`0 1px 2px rgba(0,0,0,.45)`); ambient shadows are invisible on near-black.
- **Lift on near-black comes from light.** A dark panel whose fill is only ~0.04 L off the page stands off by:
  1. a bright top rim: `inset 0 1px 0 rgba(255,255,255,.26)`;
  2. a light band just inside the top edge: `inset 0 14px 22px -16px rgba(170,195,255,.22)`;
  3. a dark bottom rim: `inset 0 -1px 0 rgba(0,0,0,.45)`, plus faint side rims;
  4. a luminous lip under the bottom edge: `0 2px 0 -1px rgba(160,190,255,.14)`;
  5. a deep drop shadow **and** a coloured under-glow: `0 26px 50px -18px rgba(0,0,0,.9), 0 18px 42px -16px
     rgba(99,102,241,.42)`.
  Remove any one and the panel sinks into the page. The first two attempts were too faint to see at 1×; judge lift
  at 2× before showing anyone.
- **The top-lit tint** on light cards: `linear-gradient(180deg, rgba(255,255,255,.55), <line colour at 16%>)` as
  `background-image`. It gives form without adding separation.

## 4. Colour roles and tokens

- **Define roles, not paint.** `--text`, `--muted`, `--muted-strong`, `--accent`, `--accent-soft` (a tinted
  background), `--accent-line` (a tinted border), `--on-accent` (text on accent), tones with `-soft` pairs for badges
  and icon chips, `--line`, `--line-strong` (control borders).
- **Avoid role overload.** One blue once painted a section's heading, its value, the chart stroke, the dots and the
  button at the same time, so nothing stood out. Give each element one job: headings `--muted-strong` (uppercase,
  small, with a colour chip if needed), values `--text`, the series its own hue, buttons `--muted` at rest.
- **Glows mix from tokens**: `color-mix(in srgb, var(--accent) 22%, transparent)`. One definition then serves both
  themes; dark just uses hotter percentages (22% → 30%).
- **A signal colour that must read as itself at 8-10 px** (a red count badge, a live lamp) gets its own token, and
  can be identical in both themes. A rose "red" (`#e11d48`) read pink on a 9 px lamp; `#dc2626` reads red and clears
  4.8:1 under white text.
- **A recolour touches every file that paints it.** A lamp's fill lived in one stylesheet and its glow in another;
  changing one gave a red lamp in a pink halo. Grep for every use of a token's old value.
- Mark theme-invariant tokens with a comment, so someone doesn't "fix" the duplicate.

## 5. Contrast targets and where to measure

- Body and muted text ≥ 4.5:1; large text and meaningful graphics (icons, focus rings, chart strokes, input borders
  that are the only affordance) ≥ 3:1.
- **Measure against every ground the text can land on**, not just the page: card, well, selected card, alert wash,
  and **the brightest point of every gradient behind it** (§ gradients). Nudging a ground changes every text colour
  drawn on it. A ground retune once took `--muted` to 4.35:1 on cards and a chart hue to 2.92:1; both had to be
  re-darkened.
- `check_contrast.py stack <text> <base> <layer@peak>...` composites the layers the way the browser does.
- Muted text that passes everywhere: light `#5b6b84` (4.60-5.41:1 on the ladder above), dark `#90a2bd`.
- Colours that libraries draw outside CSS (map markers, canvas charts) can't read `var()`: keep a hand-synced copy
  and a comment pointing at the token.

## 6. Colours for data

- Choose series colours with a validator, not by eye: each ≥ 3:1 against the ground it is drawn on, and pairwise
  distinct under normal vision (ΔE ≥ ~15) **and** simulated protanopia/deuteranopia (ΔE ≥ ~8).
- Blue + cyan as neighbours failed normal-vision separation (ΔE 13.8). Blue, green and orange-red passed (worst pair
  ΔE 8.4 protan, 21.6 normal). Tuned hexes: light `#2a78d6`, `#199e70`, `#dd5826`.
- Colour is never the only signal: every series carries a text label and its value.
- A series colour is tuned against its ground; change the ground and re-check the series.

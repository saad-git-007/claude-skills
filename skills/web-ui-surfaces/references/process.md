# Process: getting to a look the owner loves, and proving it holds

## 1. Render named variants; let the owner pick

Visual taste is the owner's call, and words like "premium", "glassy" or "bounce" mean different things to
different people. What worked:
- **Render 4-5 named variants** of the same real screen (not a mock-up), side by side, same crop: "1 · Aurora",
  "2 · Twilight indigo", "3 · Deep ocean", "4 · Nebula", "5 · Glass edge". Put a table in a README: what each is,
  its brightest point, and muted-text contrast there.
- **Make round 1 bold enough to tell apart.** Four subtle darker navies were rejected: "they all look pretty same,
  I want something that bounces". Variants should differ in kind (hue, direction, lift), not in a few hex steps.
- **Iterate on what they liked.** Round 2 → they liked Glass edge and Nebula → round 3 crossed them (Glass lift,
  Nebula glass, Cosmic, Deep nebula, Starfield) → Cosmic was picked. Keep the earlier picks in each new round as
  references.
- **Show subtle effects at 2×.** A crop at 2× of the lift, beside the previous round's, is what made the difference
  visible. Twice the first cut of an effect was too faint to see at 1×.
- **Ask the scope question with the pick:** which surfaces follow (panels, tiles, dialogs, command palette)?
- After implementing, **pixel-diff the real app against the chosen render** (0.0% here), so what ships is what was
  picked.

## 2. Build it so it can't silently regress

- Tokens in one place, each with a comment saying *why* its value is what it is (the contrast it protects, the step
  it keeps). The next person to "tweak" a colour needs to know what they are about to break.
- Tests that measure, not tests that check presence:
  - ground steps: OKLCH L difference between neighbouring tokens above a floor;
  - text on every ground (and gradient peak) ≥ 4.5:1;
  - the dark lift present in the panel's **computed** `box-shadow`;
  - no horizontal page overflow at 320, 360, 390 and 412 px with real, long data.
- `check_contrast.py` in CI, or its logic ported into the suite.

## 3. Rendering and review traps

- **Apply the theme before first paint** (a tiny inline script in `<head>` reading the saved choice or
  `prefers-color-scheme`). If the theme is set after load, every control's colour transition plays from the other
  theme's values: users see a fade on each load, and a screenshot caught buttons mid-fade looking washed out.
- **Theme switches:** add a class that sets `transition: none` for two frames around the swap, so the page changes in
  one step instead of every control fading on its own clock. The same applies to screenshot scripts that flip themes.
- **Headless Chrome reports `(hover: none)`**, so hover styles in `@media (hover: hover)` never apply in headless
  screenshots or tests. Launch with
  `--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4` to review
  hover states.
- **Native popups** (select lists, date pickers) don't appear in headless screenshots: use a headful browser (under
  Xvfb on a server) and grab the screen.
- **Transitions still running** make colour reads flaky: freeze transitions (`* { transition: none !important }`)
  before reading computed colours.
- **Real data for layout review:** long names, big numbers, empty states. Short fixture names hide ellipsis and
  wrapping bugs.
- Review both themes, desktop and a 390 px phone, and at least one "busy" screen (tables, forms), not just the hero.

## 4. What owners actually asked for (useful defaults)

- Stronger than you think: every "subtle" first pass was sent back as invisible.
- Colour over brightness: they liked hue blooms (violet, cyan), not lighter panels.
- Leave recognisable anchors alone: the KPI tiles at the top stayed exactly as they were.
- Readable text everywhere is non-negotiable: contrast regressions were caught in review and fixed before any render
  was shown, so the choice was only ever between readable options.

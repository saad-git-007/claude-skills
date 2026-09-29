# Components: the recipes, with their traps

All of these are implemented in `../assets/surfaces.css` and shown in `../assets/showcase.html`.

## Buttons

| | Face | Border | Rest shadow | Hover | Press |
|---|---|---|---|---|---|
| Primary | `135deg` accent → accent-deep, 1 px inner top highlight | none | tinted with the accent | lift 1 px, shadow grows | sink (`scale .98`, no lift), shadow collapses to a tight glow |
| Secondary | surface + top-lit tint | `--line-strong` | none | accent border + text, compact glow | recess instantly: well fill, accent line |
| Icon | as secondary, square 40 px | `--line-strong` | none | accent | `scale .94` |

- **One primary per view.** Two gradient buttons side by side compete; the second is secondary.
- **Press is faster and firmer than hover** (~70 ms in, a spring out over ~260 ms). Animate `translate`/`scale`, so
  a control's own transform survives.
- **A button that navigates never shows its spring-back** (the view swaps first), so the press itself must carry
  the feedback: the secondary button's fill recesses instantly on `:active`.
- **Disabled must look inert:** opacity .55, no lift, no shadow, default cursor. Otherwise a slow request reads as a
  click that did nothing and invites a second click.
- Minimum height 40 px (44 px for touch-first products); focus is an instant 3 px ring in the accent at ~22-30%,
  never animated.
- Remove the mobile tap flash (`-webkit-tap-highlight-color: transparent`) only when every control has its own press
  state.

## Cards

- **Resting:** `--card` fill + top-lit tint image + 1 px line + E1.
- **Hover (interactive cards only):** accent border, fill to `--surface`, compact accent glow plus a faint inset
  ring, 1 px lift. Put hover rules inside `@media (hover: hover)` so touch screens don't get stuck hover states.
- **Selected:** accent-soft fill, a 3 px inset accent bar, and a bloom from that edge ending at 12%.
- **Alert / needs attention:** a warm wash from the leading edge to 55%, border mixed 45% toward the warm tone.
- **Long titles:** `min-width: 0` on the flex child and ellipsis on the title. A `nowrap` title otherwise sets the
  card's minimum width and widens the page on phones.
- **Hover glow and card edge:** if a card has a custom edge (a dark ground's luminous border), the hover rule must
  restate it; a generic hover border drops the ground's look.

## Panels

- Surface fill (or a dark ground image), 1 px edge, E2 (or the dark lift), 12 px radius, 20-22 px padding, a
  title 17 px and a muted subtitle 13.5 px.
- In dark themes, choose one ground per product (`theme-gallery.md`). Consider which surfaces **don't** get it:
  in the project, stat tiles kept the plain surface with their tone washes, because the owner wanted "the four
  cards at the top left alone", and modals kept theirs.

## Stat tiles (KPIs)

- A 40 px icon chip in the tone's soft/strong pair, a 22 px value (`letter-spacing: -.02em`), a 13 px muted label,
  a 135° tone wash to 65%.
- **All values the same size:** "10 / 53" was the only value with a place to break, so it wrapped while its
  neighbours didn't and read as a different size. Keep values `nowrap` with an ellipsis (plus `min-width: 0` on
  their container), and make room (tighter gap and padding, one column under ~360 px) rather than shrinking
  the text.
- Animate a value change (a count-up) only when the value changed, never on every render.

## Segmented controls and tabs

- Track = a well with a pill radius and 3 px padding; the active segment is the raised pill: accent fill, on-accent
  text, a tinted shadow.
- If the pill glides between segments, make **the pill itself** the selected element (sized from `offset*`, gliding
  `transform` + `width`) and drop the button's own fill once it's shown. A separate fill plus a ring on two clocks
  looked broken. (Motion details: `web-ui-motion`.)
- Use `aria-pressed` (toggle group) or `role="tab"` + `aria-selected` (tabs), and style from that attribute, so the
  look can't drift from the state.

## Fields

- Wells: `--well` fill, 1 px line, 8 px radius, 40 px min height; focus = accent border + ring, instantly.
- **16 px text on phones**, or iOS zooms into the field. Anything sitting beside a 16 px control (a toggle, a
  sibling select) must match, or it looks mismatched.
- **Native select popups:** give `option`/`optgroup` their own `background-color` and `color`. Chrome on
  Windows/Linux paints a white popup for a transparent or dark select while the options inherit light text: white
  on white. Headless screenshots can't see native popups; check in a real (headful) browser.
- Placeholders are hints, not labels: every field has a visible label.

## Badges, dots, counts

- Pill badges: tone-soft fill, tone text, 12 px bold, `nowrap`.
- Count badges: white on the signal red (≥ 4.8:1), min-width 20 px so "3" and "12" are the same shape.
- Status dots: the tone plus a 3 px halo in the same tone at ~22%, so they read on any ground.

## Tables

- **Never transform rows** (sticky heads and horizontal scrollers break). Row hover = accent-soft fill + an inset
  3 px accent bar.
- The head row is a well with small uppercase muted-strong labels and `position: sticky; z-index: 1`.
- Wrap wide tables in their own `overflow-x: auto` container with the border on the container, never the page.

## Dialogs and popovers

- Surface fill, E3 shadow, 12 px radius, a dimmed backdrop. Decide explicitly whether dialogs follow a dark panel
  ground or stay plain. Ask the owner; in the project they stayed plain.
- On phones, cap popovers relative to their container (a map, a panel), not the viewport, and give them their own
  scroll.

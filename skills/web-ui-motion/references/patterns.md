# Pattern catalogue

Code for each is in `../assets/motion-base.css` (numbered sections) and `../assets/motion-helpers.tsx`. Every one was
shipped on a production site and works with reduced motion (it shows the final state).

| # | Pattern | Use it for | Trap |
|---|---|---|---|
| 1 | Orchestrated hero entrance | The first screen: eyebrow, headline word by word (70 ms apart), paragraph, CTA, image, within ~1 s | One entrance per page. `Words` renders presentational spans: give the heading an `aria-label`. Don't wrap words in a block element if a rule like `h1>span{display:block}` exists |
| 2 | Reveal once on scroll (`useReveal`, `[data-reveal]`) | Sections of a long page rising in as they arrive | Only once (unobserve after reveal). Stagger items arriving together by 60 ms, capped at ~7 steps. Threshold .12 and a -6% bottom margin so it fires as the block becomes readable. Add a print rule forcing visibility |
| 3 | Growing native `<details>` | Collapsible lists (publications, past roles) | Only where `interpolate-size` is supported; elsewhere it opens instantly, which is fine. Children can rise in with `--i` |
| 4 | CTA sheen | The single most important action | Two passes after load (delay ~1.3 s), then only on hover/focus. Never loop. Only one element on the page gets it |
| 5 | Circular View Transition (`transitionView(update, button)`) | Switching between whole views (page to app), growing from the pressed control | Check `prefers-reduced-motion` yourself. Never when the old view holds a live WebGL canvas. Wrap the state change in `flushSync` so React commits inside the callback |
| 6 | Staggered re-mount | A caption or dialog whose content changes: parts arrive in reading order, 50 ms apart | Keep the total under ~250 ms or it feels slow on repeat |
| 7 | Segmented-nav pill | Tab bars and docks: one pill glides to the active item | Drive it with `--active` (index) and `--count`; animate `translate`, not `left`. It can follow external state (a guided tour) too |
| 8 | Honest progress | Loading: a bar from real progress (requests finished / requests made) and a small dithered indicator | No fake timers or eased-to-99% bars. `scaleX` not `width`. The indicator is the one loop allowed and stops when loading ends |
| 9 | Selected marker ping | Showing which hotspot/marker is active | Three pings, then rest |
| 10 | Drawer `<dialog>` | Side panels | `@starting-style` + `transition-behavior: allow-discrete` for enter and exit; exit faster (240 ms) than enter (380 ms, drawer easing). Fallback: instant close |
| 11 | Press and arrow micro-interactions | Every button and link | Press `scale: .97` at 120 ms, hover at 200 ms; animate `scale`, not `transform`, so a control's own transform survives. Arrow nudge only with `(hover:hover) and (pointer:fine)` |
| 12 | Text scramble (`Scramble`) | Short mono labels that change (section codes) | Screen readers get the plain text once (`sr-only`), the scramble is `aria-hidden`. Keep it under ~0.8 s and only on change |
| 13 | Data that "settles" | A visual that tells the product story (bars starting as noise and settling into signal, once) | Make the start state visible long enough to be seen (hold ~0.5 s) or the effect happens while still invisible |

## Timing table

| Kind | Duration | Easing |
|---|---|---|
| Press | 80-120 ms | ease |
| Hover | ~150 ms | ease |
| State change (colour, border) | 200 ms | ease |
| Panel / drawer in | 300-400 ms | `cubic-bezier(.32,.72,0,1)` |
| Panel out | ~240 ms | `cubic-bezier(.77,0,.175,1)` |
| Reveal / entrance | 500-700 ms | `cubic-bezier(.16,1,.3,1)` |
| Progress | per update | linear |
| Focus ring | instant | none: never animate focus |

## Porting a library component

Most component libraries (Tailwind + Motion/GSAP) can be ported to a few lines of CSS:
1. Find the component's actual constants: durations, easing curves, offsets, stagger.
2. Rebuild it with CSS keyframes/transitions and the tokens; replace `motion`'s spring with the nearest cubic-bezier.
3. Drop any animated blur or backdrop-filter.
4. Check the licence (see sources.md) and credit substantial ports in the file header.

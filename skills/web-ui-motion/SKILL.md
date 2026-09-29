---
name: web-ui-motion
description: A tested motion and layout system for websites and web apps, covering timing and easing tokens, entrance and scroll reveals, View Transitions, drawers, segmented-nav pills, honest loading progress, micro-interactions, reduced-motion handling, no-scroll layouts that fit every viewport, and HTML overlays and camera flights over a 3D (WebGL/three.js) canvas. Includes a vetted review of twelve UI and motion sources (beui.dev, bencho.dev, aura.build, open-design.ai, typeui.sh and others) with their licences. Use this whenever the user wants to add or polish animations, transitions, hover or press effects, page or view transitions, scroll effects, loaders, a more "premium" or "alive" feel, or wants UI inspiration from component libraries or design galleries, or has layout problems on phones, short laptop screens or landscape, or builds UI over a 3D scene, even if they don't say "motion".
---

# Web UI motion and layout

Distilled from building a portfolio site with a readable résumé page and a full-screen three.js lab: twelve design
and component sites were reviewed, their techniques ported to plain CSS plus four small React helpers (about 3 KB, no
packages), and the result was tested at many viewport sizes and with reduced motion. The main lesson: good motion is a
small, consistent system with a few rules, not a collection of effects. The details below make it repeatable.

## First, decide what motion is for

Motion earns its place when it explains something: where a panel came from, which item is active, that work is
progressing, what the next action is. For each candidate animation, name what it communicates; if the answer is
"it looks cool", it probably belongs in the rejected list below. Also consider the audience: the portfolio's readers
were hiring managers who skim, so scroll hijacking and gimmicks were rejected even though they demo well.

## The rules (why each exists)

1. **The base style is the finished state.** Hidden "from" states live only in keyframes or inside
   `@media (prefers-reduced-motion: no-preference)`. Then reduced motion, old browsers, print and failed JavaScript
   all show a complete interface rather than invisible content.
2. **Entrances use `animation-fill-mode: backwards`, not `forwards`**, and the individual `translate`/`scale`
   properties rather than `transform`. A `forwards` fill or an animated `transform` freezes over the element's own
   hover transform afterwards.
3. **Timing tokens, used everywhere:** press 80-120 ms, hover ~150 ms, state change 200 ms, panels 300-400 ms,
   reveals ~600 ms. Strong ease-out (`cubic-bezier(.16,1,.3,1)`) for entrances; linear only for progress. Exits are
   faster than entrances. These are the values the reviewed sources agree on.
4. **Only transform and opacity animate**, especially over a WebGL canvas. Animated `filter: blur()`,
   `backdrop-filter`, box-shadow or layout properties are what drop frames, and they compete with a 3D renderer.
5. **Nothing decorative loops.** WCAG 2.2.2 requires a pause control for motion longer than five seconds. Attention
   effects run a fixed number of times (two sheen passes, three pings, four pulses) and then rest. A loader may loop
   until loading ends.
6. **Honour `prefers-reduced-motion` in JavaScript too.** View Transitions and requestAnimationFrame effects do not
   check it by themselves.
7. **Progressive enhancement for new platform features** (View Transitions, `@starting-style`,
   `transition-behavior: allow-discrete`, `::details-content`, `interpolate-size`): wrap them in `@supports`, and make
   the fallback the plain, instant version.
8. **Keep the native elements.** `<dialog>` and `<details>` give focus handling and accessibility that library
   replacements reviewed here did worse.

## Workflow

1. Read the existing stylesheets (all of them) before adding a rule, and change a value where it is defined rather
   than stacking overrides.
2. Put tokens and every animation in one motion stylesheet loaded last (template: `assets/motion-base.css`), and
   the few JS helpers in one module (`assets/motion-helpers.tsx`: `useReveal`, `Words`, `Scramble`,
   `transitionView`).
3. Pick patterns from `references/patterns.md`; each has its code, when to use it and its trap.
4. For inspiration from third-party libraries, read `references/sources.md` first: which sources are worth it, which
   licences allow reuse, and why porting the technique usually beats installing the library.
5. Check layout at real sizes (`references/layout-and-3d.md`): short laptop windows and landscape phones break more
   often than narrow phones. Automate it (`assets/layout.spec.example.ts`).
6. Test with reduced motion on, and look at the result in a browser. Send the user screenshots or a short video of
   anything they will judge by eye.

## Rejected, and why (so it doesn't get re-proposed)

- View Transition when *leaving* a view that holds a live WebGL canvas: 1.5-3 s to snapshot, against 21 ms for a
  plain swap. Entering such a view from a plain page is fine.
- Anything that starts a second WebGL context or a permanent animation loop next to a 3D scene: shader backgrounds,
  point-cloud loaders, cursor trails.
- Scroll hijacking (Lenis-style smooth scroll), pinned sections, scroll-scrubbed text: they get in the way of skimming.
- Tilt cards, magnetic buttons, cursor-following borders, gooey effects: per-pointer-move layout reads and SVG
  filters, and a gimmicky tone.
- Blur-in text and letter-by-letter or 3D-flip headlines: animated blur is ruled out over a canvas, and
  per-character spans are noise for screen readers. Word-by-word with `aria-hidden` spans and an `aria-label` is fine.
- Hold-to-confirm, fleeing buttons, marquees: friction, dark-pattern adjacency, endless motion.

## Reference files

- `references/patterns.md`: the pattern catalogue (hero entrance, scroll reveal, growing `<details>`, CTA sheen,
  circular View Transition, drawer dialog, segmented-nav pill, text scramble, honest loader, progress, hotspot ping,
  press and arrow micro-interactions), with code, use and traps.
- `references/sources.md`: the twelve reviewed sites (what each really is, licence, verdict), attribution rules.
- `references/layout-and-3d.md`: no-scroll layouts across viewport heights, the sizes to test, safe areas, and UI
  over a 3D canvas: projected tags, cards kept on screen, camera flights, scrubbable progress, loading, quality menus.
- `references/theme-example.md`: the "liquid glass" cobalt/cyan theme from that project, as one example style.
  It is that site's taste; don't apply it by default.
- `assets/`: `motion-base.css` (tokens + patterns, generic class names), `motion-helpers.tsx` (React helpers, with
  credits), `layout.spec.example.ts` (Playwright no-scroll layout test).

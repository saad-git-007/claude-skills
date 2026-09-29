---
name: web-ui-motion
description: A tested motion and layout system for websites and web apps: timing and easing tokens, entrance and scroll reveals, View Transitions, drawers, gliding pills, honest loaders, micro-interactions, reduced motion, layouts that fit every viewport, UI over a 3D (WebGL/three.js) canvas, motion in live apps that poll or stream (dashboards, AI chat: launcher morph, loading avatar, Send/Stop, citations), and browser-test traps that let motion tests pass without testing. Includes a licence-checked review of twelve UI sources (beui.dev, bencho.dev, aura.build and others). Use whenever the user wants to add or polish animations, transitions, hover or press effects, loaders, a more "premium" or "alive" feel, UI inspiration from component libraries, a chat or assistant panel, or has layout problems on phones, short screens or landscape, or flaky or suspiciously green UI tests, even if they don't say "motion".
---

# Web UI motion and layout

Distilled from building a portfolio site with a readable résumé page and a full-screen three.js lab: twelve design
and component sites were reviewed, their techniques ported to plain CSS plus four small React helpers (about 3 KB, no
packages), and the result was tested at many viewport sizes and with reduced motion. The main lesson: good motion is a
small, consistent system with a few rules, not a collection of effects. The details below make it repeatable.

A second project added what a one-off site never shows: an operations dashboard that re-renders every 10 s (map,
3D view, charts) with a streaming AI chat, about 170 browser tests, and phones in daily field use. Its lessons are in
`references/live-app-patterns.md` and `references/testing-motion.md`.

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
9. **In a live app, nothing replays by accident.** Re-renders, re-applied classes and `display: none` → shown all
   restart CSS animations. Bind entrances to static wrappers or a `.fresh` class that is removed once they have played,
   and pulse on changed *values*, never on render events.
10. **Opaque from the first frame.** A panel, menu or drawer that grows while its content is still transparent shows
   an empty box for 60-90 ms. Reveal with `clip-path` and never fade the shell. Cover late content with a linear veil,
   and film the transition at 0.1× speed before calling it done.

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
6. Test with reduced motion on, and look at the result in a browser. Before trusting a green run, read
   `references/testing-motion.md`: headless Chrome turns off every hover rule, and a skipped browser class can
   still report OK. Send the user screenshots or a short video of
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
- A View Transition for a launcher-to-panel morph over live content: it freezes the map and polling into a snapshot,
  stretches a round button into an ellipse and puts two launchers on screen. Use the clip-path morph instead.
- A spring on a panel's shape (its clip or size): it drags the corner radius around. Springs only on small controls'
  `transform`, and never on opacity, which overshoots past 1 and flickers.
- Fading a drawer or menu panel in: the page ghosts through its rows. Keep it opaque and reveal it with a clip.
- A conic-gradient loading orb: at avatar size its centre reads as a pinwheel seam. Use orbiting radial blobs.

## Reference files

- `references/patterns.md`: the pattern catalogue (hero entrance, scroll reveal, growing `<details>`, CTA sheen,
  circular View Transition, drawer dialog, segmented-nav pill, text scramble, honest loader, progress, hotspot ping,
  press and arrow micro-interactions), with code, use and traps.
- `references/sources.md`: the twelve reviewed sites (what each really is, licence, verdict), attribution rules.
- `references/layout-and-3d.md`: no-scroll layouts across viewport heights, the sizes to test, safe areas, content that
  widens phone pages (`1fr`, nowrap, long tokens, scroll traps), and UI over a 3D canvas: projected tags, cards kept on screen, camera flights, scrubbable progress, loading, quality menus.
- `references/live-app-patterns.md`: apps that poll or stream: poll-safe and once-only entrances, the blank-box
  trap, a chat assistant (launcher morph, streaming orb, phase label, Send/Stop with focus handoff, citations, copy),
  exit animations that keep state synchronous, gliding pills, drawers, third-party widgets, timeline zoom, press
  feedback that survives navigation.
- `references/testing-motion.md`: browser-test traps (tests that pass without testing, tests that fail at random,
  seeing native popups and blank frames, reaching real phone widths).
- `references/theme-example.md`: the "liquid glass" cobalt/cyan theme from that project, as one example style.
  It is that site's taste; don't apply it by default.
- `assets/`: `motion-base.css` (tokens + patterns 1-15, incl. once-only entrance, launcher morph, working orb,
  Send/Stop pop; generic class names), `motion-helpers.tsx` (React helpers, with
  credits), `layout.spec.example.ts` (Playwright no-scroll layout test).

## Related skill

How surfaces look at rest (depth ladders, gradients, glass cards, button and card recipes, contrast checks, and a
gallery of complete themes including this one's "liquid glass") is covered by `web-ui-surfaces`.

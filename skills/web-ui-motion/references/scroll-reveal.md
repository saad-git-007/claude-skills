# Scroll reveal (the mosque site's, exact)

Blocks rise into view once as they arrive: fade from 0, 26 px lower (18 px on phones) and 97.5 % scale, 0.6-0.7 s
strong ease-out, blocks arriving together staggered 80 ms apart (capped at 400 ms). Page headers rise line by line
(70 ms apart) on load, and in-page links scroll smoothly. Shipped on every page of a production site (2026); the owner
asked for it to be reused as is.

## Files (in `assets/scroll-reveal/`)

| File | What it is |
| --- | --- |
| `reveal-head.js` | Tiny head script: sets `html.reveal-on` before first paint, removes it after 2.5 s if the main script never ran. |
| `scroll-reveal.js` | `defer` script: IntersectionObserver, staggered `--rd`, once only, then clears the delay. |
| `scroll-reveal.css` | Hidden state, transitions, page-header rise, smooth anchors, print rule. |
| `example.html` | Demo: serve the folder and scroll. |

## Wiring

```html
<head>
  <script src="/assets/reveal-head.js"></script>          <!-- blocking, before the CSS: no flash -->
  <link rel="stylesheet" href="/assets/scroll-reveal.css">
  <script src="/assets/scroll-reveal.js" defer></script>
</head>
...
<header class="pagehead"><h1>…</h1><p class="lede">…</p></header>
<div class="grid" data-reveal-group> …cards reveal one by one… </div>
<section class="prose" data-reveal> …one block… </section>
```

With a strict CSP, both scripts are external files, so no inline script is needed. The original listed its real
class names (`:is(.grid-cards, .tiles) > *, .mapcard, .prose, .sitefoot`) instead of data attributes; to do that, put
the same list in `SELECTOR` in the JS and in the three CSS selectors.

## What to reveal (and what not)

- Reveal: card grids (children), section titles, maps, long prose, forms, the footer, empty-state messages.
- Don't reveal: the page header (it has its own load rise), navigation, the bottom dock, anything above the fold that
  the visitor needs at once (a live "next prayer" card was fine because it is visible within ~0.1 s), and content
  that re-renders on a poll (see live-app-patterns: it would replay).

## Why each detail

- **Hidden only behind three gates** (motion allowed, `reveal-on`, not yet `.revealed`): reduced motion, no JS,
  a failed script and print all show the full page. The 2.5 s watchdog covers a blocked or broken main script.
- **Class set in `<head>`**: setting it from the deferred script would show blocks, hide them, then reveal them.
- **`translate`/`scale`, not `transform`**, plus `transform` listed with its own 150 ms timing: cards keep their
  hover lift, and it is never delayed by the reveal delay. The delay (`--rd`) is removed on `transitionend` too.
- **rootMargin -8 %, threshold .06**: fires as the block becomes readable, not while it is still behind the dock or
  at the very edge. Stagger resets after a 120 ms pause, so a fresh scroll starts at 0 ms again.
- **Shorter travel on phones** (18 px, .985): 26 px felt like a jump on a 390 px screen.
- **Once only** (`unobserve`): repeated reveals on scroll-up feel like the page is reloading.

## Known edge

A jump far down the page (fast fling, End key, deep anchor) can pass blocks that never intersected during the jump;
they reveal when scrolled back to, which is the intended behaviour. Tests that scroll with one big wheel step will see
them still hidden: scroll in steps, or assert only on what is in view.

## Testing

Playwright in Chromium and WebKit at 390×800: blocks above the fold have opacity 1 after load, blocks below start at
0 and reach 1 after scrolling to them in steps; with `reduced_motion='reduce'`, `reveal-on` is absent and every block
is 1 at once; no page errors.

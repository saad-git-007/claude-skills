# Morphing bottom dock (phone menu)

The exact phone menu from a production mosque website (2026): a floating pill dock at the bottom of the screen
with five captioned shortcuts and a **More** button. Tapping More squeezes the pill, then springs it open into a
panel of rows; closing reverses it. Desktop (≥1021 px) hides it and shows a normal top nav. The owner asked for it
to be rebuilt the same way in future web apps, so reuse these files as they are and change only content and tokens.

**Licence:** a vanilla-JS port of Danny Williams's *Morphing menu* (`MorphingMenu.tsx`), which the user holds a
licence for. Use it only in the user's own projects, and keep the credit line ("Phone menu: adapted from Danny
Williams's Morphing menu, used under the owner's licence") in the README or credits.

## Files (in `assets/morphing-menu/`)

| File | What it is |
| --- | --- |
| `morph-menu.src.js` | The behaviour (ES module source, imports `motion`). Edit this one. |
| `morph-menu.bundle.js` | Pre-built, minified IIFE (15 KB). Drop-in when there's no build step. |
| `morphing-menu.css` | Layout and motion of the component itself (`--mm-*` custom properties). Don't edit; override. |
| `dock-theme.css` | Placement, theme tokens (light + dark), captions under icons, current-page accent, and the production fixes. |
| `example.html` | Working demo: serve the folder and open at phone width. |

Build the bundle from source (pinned versions that are known to work):

```
npm i motion@11.18.2 && npm i -D esbuild
npx esbuild morph-menu.src.js --bundle --minify --format=iife --target=es2019 --outfile=public/assets/morph-menu.js
```

## Wiring it into a page

```html
<link rel="stylesheet" href="/assets/morphing-menu.css" media="(max-width: 1020px)">
<link rel="stylesheet" href="/assets/dock-theme.css">      <!-- or merge into the site stylesheet, after the above -->
...
<div class="mm-dock"> …markup below… </div>
<script src="/assets/morph-menu.js" defer></script>
```

- **Render the markup on the server** (or in the static HTML) so every dock link works before the script loads.
  The script only adds the morph; it never creates links.
- One source of truth for the items, e.g. a list `{ id, href, label, short, icon, dock, external?, img? }`:
  `dock: true` items (max 5) go in the bar with `short` as the caption; the rest become panel rows.
- Set `--mm-count` in `dock-theme.css` to dock items + 1 (More).
- Strict CSP is fine: no inline script or style is needed (the demo's inline bits are only for the demo).

## Markup contract

```html
<div class="mm-dock">
  <nav class="morphing-menu" aria-label="Sections" data-view="collapsed">
    <div class="morphing-menu__shell">
      <div class="morphing-menu__bar">
        <!-- up to 5 shortcuts; current page gets aria-current="page" -->
        <a class="morphing-menu__shortcut" data-menu-item="home" href="/" aria-label="Home" aria-current="page">
          <span class="morphing-menu__icon"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true">…</svg></span>
          <span class="mm-cap" aria-hidden="true">Home</span></a>
        …
        <!-- More: aria-current="true" when the current page is one of the panel rows -->
        <button type="button" class="morphing-menu__shortcut" data-menu-item="more" aria-label="More"
          aria-expanded="false" aria-controls="mm-main">…three dots…<span class="mm-cap" aria-hidden="true">More</span></button>
      </div>
      <div id="mm-main" class="morphing-menu__panel" aria-hidden="true" inert>
        <a class="morphing-menu__row" data-menu-item="news" href="/newsletter">
          <span class="morphing-menu__icon">…svg or <img class="mm-logo" src="…" alt="" width="24" height="24">…</span>
          <span class="morphing-menu__label">Newsletter</span></a>
        <!-- external row: target/rel + arrow -->
        <a class="morphing-menu__row" data-menu-item="partner" href="https://…" target="_blank" rel="noopener">…
          <span class="ext" aria-label="(opens in a new tab)"><svg …><path d="M9 5h10v10"/><path d="M19 5 6 18"/></svg></span></a>
      </div>
    </div>
  </nav>
</div>
```

Every interactive element needs a unique `data-menu-item` (focus is restored by it). Icons are 24-unit line SVGs
(`stroke: currentColor`, width 2); use class `fill` / `nostroke` on parts that should be solid.

## What the script does (so you don't re-derive it)

- Views: `collapsed` ↔ `main`. Opening from the bar: the shell compresses (100 ms, to 280×32) then springs to the
  panel's size (spring 0.4 s, bounce 0.24); rows rise from 48 px with a 20 ms stagger. Closing reverses with a
  smaller bounce. Interrupting cancels the pending phase and starts from the current geometry.
- Reduced motion: every change snaps (no springs, no blur).
- Keyboard: Enter/Space on More opens and focuses the first row; Escape closes and returns focus to More; Tab out
  of the open panel closes it. The hidden layer gets `inert` + `aria-hidden`.
- Tap outside closes; choosing a row closes and then navigates; a page restored from the back/forward cache comes
  back collapsed.
- Mouse hover tooltips only for icon-only shortcuts (captioned ones don't need them).
- **Size is re-measured** on resize, on `load`, and whenever the bar or a panel changes size (ResizeObserver).
  Without this, a script that runs before the stylesheet applies measures the unstyled bar (~2000 px) and the shell
  covers the whole page (seen in WebKit on fast revisits).

## Production fixes baked into `dock-theme.css`

- Opaque surface tokens in both themes; a translucent dock let page content ghost through while it morphed.
- Hidden panel never scrolls (`overflow: hidden` when `aria-hidden="true"`, scrollbars hidden): its resting rows
  sit 16 px low and some phones drew a thin scrollbar line in the dock.
- Logo images in rows use the same 20 px slot as line icons (`scale: 1.2` for visual weight) so labels align.
- `main` gets bottom padding (120 px + safe area) so the last content is never under the dock.
- The `.mm-dock` strip is `pointer-events: none`; only the pill takes taps.
- With cross-document View Transitions, give the dock its own `view-transition-name` and no animation so it stays
  still while the page crossfades.

## Pairing it with the rest of the site

- Desktop: a normal top nav at ≥1021 px; put the same panel items in a "More…" `<details>` dropdown there with a solid
  surface (same `--dock-surface` and `--dock-shadow`), closing on outside click, Escape and link choice.
- Speculation rules: prefetch the dock's internal links eagerly
  (`"selector_matches": ".mm-dock a[href]:not([target])"`) so taps feel instant.
- Don't block pinch zoom on the dock unless the owner asks; if you do, leave maps their own gestures.

## Testing it

Check with Playwright in Chromium **and** WebKit at 390×800: the shell is 348×66 collapsed, grows to the panel size
when More is clicked, and returns to 348×66 after Escape; no page errors; both themes. Load the page ~10 times in a
row (including revisits) and assert the collapsed height every time; that is what catches the measuring bug.

```py
J = "()=>{const s=document.querySelector('.morphing-menu__shell').getBoundingClientRect();return [Math.round(s.width),Math.round(s.height),document.querySelector('.morphing-menu').dataset.view]}"
pg.goto(url); pg.wait_for_timeout(800); assert pg.evaluate(J)[:2] == [348, 66]
pg.click('[data-menu-item="more"]'); pg.wait_for_timeout(1000); assert pg.evaluate(J)[2] == 'main'
pg.keyboard.press('Escape'); pg.wait_for_timeout(1000); assert pg.evaluate(J)[:2] == [348, 66]
```

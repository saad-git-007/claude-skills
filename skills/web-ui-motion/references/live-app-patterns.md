# Motion in a live app: polling dashboards and AI chat

The patterns in `patterns.md` came from a site that renders once. A dashboard that re-renders every few seconds and
a chat that streams tokens break them in ways that don't show in a demo. Everything here was shipped in a Flask +
vanilla JS operations dashboard (10 s polling, Leaflet map, CesiumJS view, a streaming RAG chat) and pinned by
browser tests.

## Contents
1. Entrances that survive polling and re-showing
2. Opaque from the first frame (the blank-box trap)
3. Chat assistant: launcher morph, working orb, Send/Stop, sources
4. Closing: exit animations without breaking state
5. Selected pills, drawers and third-party widgets
6. Timeline zoom by re-windowing
7. Press feedback that survives navigation

## 1. Entrances that survive polling and re-showing

**Three things silently replay an entrance:** a re-render that replaces the element, re-adding a class the element
already has, and `display: none` → shown. The last one is the easiest to miss: hiding an element cancels its CSS
animations, and showing it again starts them over. A chat transcript bound to `.messages > .msg` replayed every
message's entrance each time the panel reopened.

- **Page and tab entrances** belong on static wrappers that the render never replaces (`.view.active > *`). Applying
  `.active` again changes nothing, so the entrance runs only on a real tab switch, not on each poll.
- **Items that arrive once** (messages, alerts, new rows) get a `.fresh` class. The code that creates the item adds
  it, and it is removed once *all* of that item's entrances have finished:
  ```js
  function settleEntrance(el, names) {           // names: Set of this item's entrance keyframe names
    requestAnimationFrame(() => {
      const runs = el.getAnimations({ subtree: true }).filter(a => names.has(a.animationName));
      // A cancelled animation (panel closed mid-entrance) rejects, and allSettled treats that as done too
      Promise.allSettled(runs.map(a => a.finished)).then(() => el.classList.remove('fresh'));
    });
  }
  ```
  Removing the class on the first `animationend` cuts a longer sibling animation short. `animationend` also bubbles
  up from children, so when an element runs two animations, check `event.animationName`.
- **Streaming text:** replace the bubble's children on each token and keep the bubble element itself, so its
  entrance plays once.
- **Pulses on changed data** compare the *values* with the last ones seen (keep a map, and clear it on logout). Never
  pulse on a render event: a forced re-render with unchanged data would flash everything.
- **Arrivals during a poll** go through a pending set that the next render consumes. Cap how many flips animate in
  one poll (a mass reconnect); the cap skips this poll's choreography only and must not clear flashes still pending
  from earlier polls.
- **Skeletons on library containers** (`.map:empty`) set paint properties only: background and an opacity breathe.
  Adding `position` or `overflow` changed the containing block that Leaflet's absolutely positioned panes resolve
  against. Once Leaflet filled the div the rule stopped matching, the panes reflowed, and the tile layer ended up
  12,500 px wide, with a horizontal page scrollbar.
- **No `scale()` in reveal keyframes** for anything a layout test measures: a width read mid-entrance fails at
  random. Use `translate` and `opacity`.

## 2. Opaque from the first frame (the blank-box trap)

This happened three times in one project: a menu unfold, a chat panel morph and a phone nav drawer each showed an
**empty box** for their first 60 to 90 ms. The cause each time was the same: the shell grew with a strong ease-out, so
it was nearly full size early, while its content was still at opacity 0 or waiting on a stagger delay. On screen it
reads as a flash of white.

- Film it rather than guessing. Use CDP `Animation.setPlaybackRate` at 0.1 and a screen recording, or freeze frames
  with `document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; })`.
- Keep the growing surface opaque from its first frame. Reveal it with `clip-path` plus `translate`, and never fade the
  panel itself: a fading drawer let the page show through its rows.
- If the content has to arrive later, cover the gap with a **veil** in the source control's colour. Fade it
  **linearly** over about 70% of the unfold, not with the shell's ease-out, so at 30% the shape still reads as the
  button it came from.
- Stagger delays for rows should follow the reveal front (compute them from the shell's easing curve). A generic
  settle curve left a drawer three-quarters open and empty at 60 ms.
- If a library hides a control's icon when it expands (Leaflet's layers control does), draw a stand-in icon in
  `::after` that fades out over about 150 ms.

## 3. Chat assistant

**Launcher → panel morph with no measuring.** Place the panel so its geometry comes from the same tokens as the
launcher: its right edge is the launcher's right edge, and its bottom sits exactly `dock + gap` above the launcher's
bottom. The panel then starts as a translated, clipped circle, which *is* the launcher:
```css
.chat-panel{
 --morph-dx:0px; --morph-dy:calc(var(--dock) + var(--gap));
 --morph-corner:calc(100% - var(--dock));
 --morph-closed:inset(var(--morph-corner) 0 0 var(--morph-corner) round calc(var(--dock)/2));
 --morph-open:inset(-64px round calc(var(--radius) + 64px));  /* opens past the box: the shadow grows in */
}
@keyframes morph-open{from{transform:translate(var(--morph-dx),var(--morph-dy));clip-path:var(--morph-closed)}
                      to{transform:none;clip-path:var(--morph-open)}}
.chat-panel:not([hidden]){animation:morph-open 300ms var(--ease-out) backwards}
/* Short screens dock the panel BESIDE the launcher, so the circle slides in from the side */
@media (max-height:540px){.chat-panel{--morph-dx:calc(var(--dock) + var(--gap));--morph-dy:0px}}
```
- Don't use a View Transition here. It freezes a live map and any polling into a snapshot for its whole duration,
  stretches the round launcher into an ellipse (snapshots are bitmaps), and shows a second launcher, because the real
  one stays on screen as the toggle.
- Use no overshoot on the shape. A spring on a clip drags the corner radius around, and that is the first thing that
  makes a panel look cheap. Springs are for small controls (a question bubble popping from the composer's corner),
  and only on `transform`: a spring on opacity overshoots past 1 and flickers.
- Close with the reverse morph at about 190 ms with ease-in. The panel is `inert` while it folds, and `hidden` is held
  off by a timer of the same length.
- On short screens (a phone on its side had 86 to 103 px to read in), dock the panel beside the launcher and compact
  the header and composer.

**The avatar is the loading indicator.** The assistant's orb sits still at rest and swirls and breathes only while
an answer streams: `.msg.streaming > .orb` and `.panel.working .header > .orb`. The state is bound to the real stream,
not to a timer. It stops the moment the stream ends, so a transcript of 40 answers has at most one orb moving. Build
the orb from radial gradients, two orbiting light blobs in `::before`, and a glass highlight in `::after`. A conic
sweep was tried and rejected: at about 22 px its centre point reads as a pinwheel seam. Under reduced motion the orb
keeps still, with brighter bands, so the state still shows.

**Before the first token,** show what is happening ("Searching…", then "Reading 4 sources…") from `data-phase`
rather than an empty bubble with a caret. Retrieval plus time to first token can take a second or two, and a blank
bubble reads as a hang.

**Send and Stop share one grid cell.** Swap them with `hidden`, and move focus with the swap. Otherwise a keyboard user
who pressed Send is dropped to `<body>` when the button disappears:
```js
function setStreaming(on) {
  const leaving = on ? send : stop, arriving = on ? stop : send;
  const handOff = document.activeElement === leaving;
  leaving.hidden = true; arriving.hidden = false;
  send.disabled = on;                          // Enter in the box must not queue a second question
  if (handOff) arriving.focus();
  if (!on) send.classList.add('popping');      // Send's return pops; bound to :not([hidden]) it would replay on every panel open
}
send.addEventListener('animationend', e => { if (e.animationName === 'pop-scale') send.classList.remove('popping'); });
```
For the icons, use a paper-plane Send and a filled-square Stop. Give the composer no placeholder when the product
owner asks for an empty box; the accessible name comes from the label, not the placeholder.

**Sources after the answer.** Render citations when the stream finishes, from the server's list of which sources
were cited (or from the `[n]` markers in the text if the stream was cut). Show cited rows first with their exact
position (page, printed page label, line range), then a collapsed "N more searched". The list slides open through
`::details-content` (see `patterns.md` #3). When a citation chip opens it from code, add an `.instant` class that
turns the transition off, because the chip then scrolls to the row, and a list still collapsing would be measured
instead. Also parse grouped citations: models write `[1, 2]`, `[2-4]` and `[1][3]`.

**A copy button on each finished answer** copies the text plus a "Sources:" footnote list, and its tick pops in (a
spring on `scale`). To download a cited image, fetch it, make a blob, then trigger the download. A plain
`<a download>` is ignored cross-origin and would navigate the app away.

## 4. Closing: exit animations without breaking state

- Keep the state change synchronous: remove `.show` straight away, so tests, Escape handlers and focus logic see
  the closed state. Add a `.closing` class that keeps the element visible for the exit animation, removed by a timer,
  which then runs any deferred cleanup (clearing an image `src`, emptying a chart).
- Cancel any pending close at the top of every open function.
- The Escape handler must check `.show` first. Closing a modal that is already hidden adds `.closing` and flashes it
  on screen.
- Under reduced motion, finish the close synchronously. Otherwise the user gets an invisible full-screen click shield
  for the length of the exit.
- **The universal reduced-motion clamp shortens durations but not delays.** A staggered, backwards-filled item sits
  invisible for its whole delay. Add `animation-delay: 0s !important` for staggered groups in the reduced-motion
  block.
- **A third-party widget's close** (Leaflet removing `-expanded`): watch it with a `MutationObserver` and give it a
  `.closing` class for about 170 ms. Observer callbacks run before paint, so there is no flash, and the library's
  handlers are never patched. Test trap: running expand and collapse in one task hands the observer both records at
  once, it does nothing, and a reduced-motion test written that way passes without testing anything.

## 5. Selected pills, drawers and third-party widgets

- **Make the gliding indicator the selected pill itself**, not a ring beside the button's own fill. With two layers on
  two clocks (fill at 150 ms, ring at 250 ms) they visibly disagree. Size the pill from `offsetLeft/Top/Width/Height`
  (whole pixels, unaffected by transforms). `getBoundingClientRect` catches the button mid press spring-back. Glide
  `transform` and `width`: `scaleX` squashes the pill's round ends by about 40%. Once the pill is shown, drop the
  button's own fill with `:has(> .indicator.shown) .active`.
- **The pill glides only after a gesture** (a flag set by the click and read once) and snaps into place on a poll.
  Any handler that moves `.active` without a full render must also sync the pill, or it stays behind until the next
  poll and uses up the next click's glide.
- **Phone nav drawer:** reveal it with `clip-path` and `translate`, keeping it opaque (§2). Swap the ☰ icon for ✕ on
  `aria-expanded`. Put the scrim in `::after` on the drawer's own element, and have the outside-click handler accept a
  click whose target is that element. Every close path (toggle, Escape, picking a view, tapping outside) goes through
  one `closeDrawer()`, so none of them snap shut while the others roll up.
- **Native `<select>` popups:** Chrome on Windows and Linux draws a white popup under a transparent select while the
  options inherit light text. Set `select option, select optgroup { background-color: var(--surface); color: var(--text) }`.

## 6. Timeline zoom by re-windowing

If a chart already draws from a `[from, to]` window over data it has fetched, zooming is just redrawing a narrower
window: no transforms and no re-fetch.
- Wheel or ctrl+wheel (a trackpad pinch) zooms around the pointer, shift+wheel or a sideways wheel pans, and a drag
  pans once zoomed. With two fingers, the time under their midpoint stays put. Double-click, `0` or a "Show all" pill
  resets.
- Set a floor for how far it zooms (for example 10 min, or 3 h for hourly data, so the window can never be empty),
  and fold events from before the window into the opening value, so a step chart doesn't start blank.
- Call `preventDefault` on the wheel only when something changed (or while zoomed). Zooming out at full range must
  fall through, so the dialog can still scroll.
- Clear the tracked pointers on a primary `pointerdown`. A touch that was never released otherwise turns the next
  touch into a phantom pinch.
- An empty zoomed window still takes gestures: draw the "no samples" message inside the same hit area and give it its
  own Show all button.
- On phones, keep `touch-action: pan-y` on the plot, so a vertical swipe still scrolls the page.

## 7. Press feedback that survives navigation

- Press in fast (about 70 ms) and release with a spring (about 260 ms). Where the press navigates, the view swap
  swallows the spring-back, so the press itself has to carry the feedback: sink the surface immediately.
- Haptics: `navigator.vibrate(8)` on a confirm, only on a coarse pointer, and checking reduced motion when it fires
  (read `matchMedia` then, not at load).
- Remove the grey mobile tap flash (`-webkit-tap-highlight-color: transparent`) only once every control has its own
  press state. A test that pairs each `:hover` group with a matching `:active` group keeps that true, including
  controls a library builds (`.leaflet-bar a`).

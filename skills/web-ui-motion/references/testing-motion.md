# Testing motion and layout in a real browser: traps that pass silently

Each item below once let a test go green without checking anything, or made a correct change fail at random. They
come from a Selenium + headless Chrome suite of about 170 browser tests for a dashboard with a lot of motion. They
apply to Playwright as well.

## Tests that pass without testing anything

- **Check the count, not just "OK".** A snap-packaged chromedriver died under a cron-started session's cgroup, the
  suite turned that into a class-level `skipTest`, and it reported `OK (skipped=2)` while 155 of 172 browser tests
  never ran (one skip is counted per class, not per test). Compare the number of tests defined with the number run.
  Point the harness at a non-snap Chrome with environment overrides (`CHROME_BINARY`, `CHROMEDRIVER`).
- **Headless Chrome reports `(hover: none)`**, so every rule inside `@media (hover: hover)` is off and every hover
  assertion passes without testing anything. CDP `Emulation.setEmulatedMedia` cannot emulate `hover`. Either launch
  with `--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4`, or
  copy the stylesheet's own hover rules into an unconditional `<style>` for the test. Either way, add a control
  assertion that the card actually moves on hover.
- **Pin animations by computed style, not by class name.** A selector typo left a badge bump that never ran while its
  `classList` test stayed green. Read `getComputedStyle(el).animationName` or `el.getAnimations()`.
- **Pin behaviour, not the presence of code.** Large search-and-replace edits have silently dropped lines: a guard
  lost its reduced-motion check, and a handler kept only its comment. After a big replacement, look at the body of the
  function that was replaced.
- **Stub streams must honour `AbortSignal`.** A fake streaming `fetch` that ignored the signal meant Stop was never
  actually tested. The stub has to reject with `AbortError` when the signal fires.
- **Empty fixtures hide layout bugs.** A 33-character email address (one unbreakable token) widened a phone page to
  549 px, and the test fixture's short names never showed it. Build layout fixtures from real data, and unlock every
  gated panel: a locked admin panel renders as a lock screen and measures clean.

## Tests that fail at random

- **Transitions still running.** Reading colours right after a theme switch landed mid-transition: the test passed
  alone and failed in the full suite. Inject `* { transition: none !important }` for the read.
- **Entrance animations change geometry.** A modal that scales in gives the wrong rect if measured when it opens.
  Measure right before sending synthetic input.
- **Smooth scrolling.** With `html { scroll-behavior: smooth }`, even `scrollTo(0, 0)` glides. Wait until `scrollY`
  stops changing.
- **Leaflet after a viewport change** must get `map.invalidateSize()`, or popups anchor to the old width.
- **Observer batching.** Two DOM changes in one task reach a `MutationObserver` as one batch (see
  live-app-patterns §4).

## Seeing what users see

- **Native popups** (`<select>` lists) don't appear in headless screenshots. Use headful Chrome under Xvfb and grab
  the screen (`import -window root`).
- **Frame-exact capture of the whole UI** (videos, pixel-stable screenshots of mid-transition states): drive
  rAF, `performance.now`, timers and every animation in `document.getAnimations()` from one virtual clock (pause each
  animation and set `currentTime`; `finish()` at the end), then screenshot per step. Real-time screencasts of a slow
  GPU are jittery and let canvas and DOM drift apart. Working recorder: the `web3d-realism-performance` skill,
  `scripts/record/` and `references/recording-clips.md`. Headless Chrome draws no mouse pointer; inject one.
- **Short effects:** a 600 ms sheen is visible only from about 20 to 130 ms. Take screenshots early, or slow
  everything with CDP `Animation.setPlaybackRate`.
- **Blank frames:** film transitions at 0.1× speed before judging them (live-app-patterns §2).
- **Judge subtle effects at 2× zoom** before handing them over. Twice, a "lift" or glow that looked fine to the
  author was invisible to the owner.
- **Frozen-data renders:** serve the working tree against a copy of the production database made with SQLite
  `backup()`. Import the app without starting its pollers, mint a session cookie from the copy's own secret, and
  raise the staleness threshold, so the renders show real data with no live traffic.

## Reaching real viewport sizes

- Chrome's headless window has a minimum width of 500 px. For phone sizes use `mobileEmulation.deviceMetrics`, or
  retarget the running driver with `Emulation.setDeviceMetricsOverride` and restore it in `finally`. That is also
  the cheapest way to measure 320, 520, 600 and 700 px in one test.
- Device emulation gives **overlay scrollbars**: `scrollbar-gutter: stable` reserves 0 px there but 15 px in a real
  window, so widths measured under emulation come out 15 px too generous.
- If your suite's viewports are 390 px and desktop only, **nothing runs between 390 and 720 px**, and a fixed
  `max-width` rule can pass every test while looking wrong on a small tablet. Test the declared rule across the band.
- An element with `overflow-y: auto` also scrolls sideways (`overflow-x` becomes `auto`), so page-level `scrollWidth`
  checks can't see a sideways drag inside it. Check that scroller's own `scrollWidth`.

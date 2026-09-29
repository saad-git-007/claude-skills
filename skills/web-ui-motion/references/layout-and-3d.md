# Layout across viewports, and UI over a 3D canvas

## Contents
1. Layouts that fit every viewport without scrolling
2. Sizes to test
3. HTML overlays on a 3D scene (projected tags, cards kept on screen)
4. Camera flights and a scrubbable progress bar
5. Loading, quality settings, fullscreen
6. Reduced motion and returning visitors in a 3D experience

## 1. Layouts that fit every viewport

For an app-like screen (fixed header, fixed bottom navigation, content in between), the rule was: navigation and
primary actions are always reachable without scrolling, at any viewport size.

- **Width decides the layout family** (phone portrait, desktop). **Height tiers** then make each family fit:
  - `@media (min-width:701px) and (max-height:689px)`: short laptops (1366x768 with browser chrome): same layout,
    tighter rhythm (smaller headline, less margin).
  - `@media (min-width:701px) and (max-height:600px)`: hide secondary bits (tags, secondary labels).
  - `@media (max-height:520px) and (orientation:landscape)`: phones in landscape, whatever their width: one compact
    row of chrome top and bottom, caption in a left column clamped to 2 lines, the scene full-bleed behind.
  - Keep the tiers last in the cascade so they win.
- Use `100svh` (small viewport height), not `100vh`, on phones, and `env(safe-area-inset-*)` for notches and home
  indicators (`padding: 0 max(18px, env(safe-area-inset-left))`). Add `viewport-fit=cover` to the viewport meta tag.
- A `min-height` bigger than the viewport silently pushes fixed controls under the dock; that broke 1366x768 laptops,
  not only phones.
- Headlines wrap differently at real sizes: at 1920x940 (a 1080p screen with browser chrome) a heading wrapped to four
  lines and covered a button. Cap headline width/size per tier, and test at the user's actual window size when they
  report a layout bug. Ask for a screenshot and window size if you cannot reproduce it (browsers differ: the report
  came from Firefox).
- Automate it: `../assets/layout.spec.example.ts` loads the page at each size (skipping heavy assets) and asserts no
  vertical or horizontal scroll, no overlap between caption, actions, controls and dock, and every key control fully in
  the viewport.

## 2. Sizes to test

| Case | Size |
|---|---|
| Small phone, browser bars showing | 375x548 (mobile, DPR 2) |
| Typical phone | 412x915 (DPR 3), 360x740 |
| Phone in landscape | 844x390 |
| Smallest landscape phone | 568x320 |
| Short laptop window | 1280x600 |
| 1366x768 laptop with browser chrome | 1366x650 |
| 1080p with browser chrome | 1920x940 |
| Tablet / desktop | 1280x900, 960x720 |

Run once with `reducedMotion: 'reduce'` too.

## 3. HTML overlays on a 3D scene

Labels, hotspots and info cards as HTML elements positioned over a WebGL canvas (crisper text, accessible, easy to
style) rather than text in the scene.

- Project each anchor point every frame: `p.project(camera)`, then
  `x = (p.x*.5+.5)*width`, `y = (-p.y*.5+.5)*height`; hide it when `p.z >= 1` (behind the camera) or outside a safe
  rectangle (under the header or the dock).
- Move with `transform: translate(x px, y px)` and toggle `visibility`: never `left/top` (layout).
- **Write styles only when they change.** Cache the last value per element and property:
  ```ts
  private put(el: HTMLElement, prop: string, value: string) {
    let w = this.written.get(el); if (!w) { w = {}; this.written.set(el, w); }
    if (w[prop] === value) return; w[prop] = value; el.style.setProperty(prop, value);
  }
  ```
  Per-frame style writes cost style recalculation for the whole overlay; this saved ~2% frame time.
- Keep an open card on screen: set `--card-x` to `clamp(-24, 12 - x, width - 12 - cardWidth - x)` and open it above
  the tag (`--card-y`) when it would run past the dock; on portrait phones always open upward.
- On phones, turn tags into dots with short-name pills; sort visible tags by screen x and alternate their labels
  below/above so neighbours never collide.
- Show a station's tags only when the camera has arrived there (not during camera moves), so they are tappable.
- Tapping a tag during an automatic tour pauses it; closing the card resumes it (unless the visitor had paused).

## 4. Camera flights and a scrubbable progress bar

- A guided flight as keyframes (time, camera position, look-at target). Where the camera must not stop (an intro
  sweep past several keys), use one **cubic Hermite curve** timed by the keys, with the tangent at each inner key along
  the bisector of the incoming and outgoing chords at the **harmonic mean** of the two speeds: it passes through each
  key smoothly without stopping or bunching up.
  ```ts
  const tangent = (k: number) => {                          // P(k): key position, time(k): key time
    if (k <= 0 || k >= last) return new Vector3();           // start from rest, settle at the last key
    const a = P(k).sub(P(k - 1)), b = P(k + 1).sub(P(k));
    const dir = a.clone().normalize().add(b.clone().normalize());
    const va = a.length() / (time(k) - time(k - 1)), vb = b.length() / (time(k + 1) - time(k));
    return dir.normalize().multiplyScalar(2 * va * vb / (va + vb));
  };
  // Hermite: p = P(i)(2s³-3s²+1) + tangent(i)(s³-2s²+s)h + P(i+1)(3s²-2s³) + tangent(i+1)(s³-s²)h,  h = time(i+1)-time(i)
  ```
- Hold ~2 s at each point of interest (a repeated key) so people can read; ease between stations.
- Owners asked for: no mid-flight pauses during the intro, a slightly closer camera on detailed stations, and the
  flight on every visit (a portfolio's first impression), with replay from the logo.
- The progress bar is a slider: `pointerdown` captures the pointer, holds the flight and seeks; `pointermove` scrubs;
  `pointerup` resumes unless it was paused before. Keyboard: arrows ±1 s, Page Up/Down ±5 s, Home/End. Give it
  `role="slider"` with `aria-valuenow`. Draw its fill with `scaleX`, linear transition.
- Frame-time guard: after a stalled frame (tab switch, dt > 3 s) count it as one frame, or the flight jumps.

## 5. Loading, quality settings, fullscreen

- Loading badge: real progress (requests finished / requests made), a short honest label ("3D scene elements loading
  42%", with "(may take a few seconds)" underneath), and a single indicator loop that ends when loading ends.
- Graphics quality (High / Auto / Performance), fullscreen and help as **one row of three icon buttons** beside the
  primary action; persist the choice in `localStorage` with a versioned key so defaults can be migrated.
- Fullscreen: use the native API where it exists; on iPhone Safari (no element fullscreen) make the experience fill
  the page instead of showing an error. Handle the user leaving fullscreen with Esc.
- Re-frame the camera on resize by checking width **and** height (orientation changes, fullscreen).

## 6. Reduced motion and returning visitors in 3D

- Reduced motion: skip the automatic flight (go straight to its end), stop ambient animation, render only when
  something changes, and skip decorative effects entirely (they cost GPU even when static).
- Render on demand: no idle re-renders when nothing moves (this took idle rendering from constant to zero).
- Keep state-driven scene updates (visibility tied to the current view) separate from ambient animation callbacks, so
  pausing ambient motion never leaves the scene in a wrong state.
- Don't route leaving a WebGL view through a View Transition; don't destroy and rebuild the 3D view when the visitor
  briefly switches to a text view: hide and pause it, so returning is instant.

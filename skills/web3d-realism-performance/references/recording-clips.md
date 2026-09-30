# Recording clips of a live 3D app: frame-exact video on a slow GPU

For demo videos, social posts and changelog clips of a WebGL app with a real UI. Used to produce a 24 s UI walkthrough
and a 33 s cinematic cut of a heavy terrain scene on a laptop iGPU; both came out at a steady 30 fps although the GPU
managed 13-30 fps live. Templates: `scripts/record/` (`record.mjs`, `clip.example.mjs`, `post.py`, `encode.sh`) and
`scripts/preflight/gpu-check.mjs`.

## Contents
1. Why a virtual clock
2. Preflight: a real GPU, or stop
3. Workflow
4. Shot-list craft (pointer, punch-ins, camera paths)
5. Cinematic extras (strips, crossfades, sound)
6. Delivery
7. Traps hit

## 1. Why a virtual clock

Real-time capture (CDP `Page.startScreencast`, a screen grab) records whatever the GPU managed, with jitter and
dropped frames, and UI transitions and the canvas drift apart. Instead, `record.mjs` replaces `requestAnimationFrame`,
`performance.now`, `Date.now`, `setTimeout` and `setInterval` once the app has loaded, and drives **every running
CSS/WAAPI animation** (`document.getAnimations()`: pause, then set `currentTime` from the clock; `finish()` when done)
from one virtual clock that moves exactly 1/fps per output frame. A frame costs as long as it costs
(0.2-0.55 s at 1080p-4K render size on an Iris Xe); the video is perfect regardless. The app's own `dt` is 33 ms every
frame, so simulation (water, boat, time of day) runs at true speed.

Mouse and wheel input are still real CDP input events, so `:hover`, pointer capture, drags and wheel zoom behave as for
a person. Headless Chrome draws no pointer, so an arrow and a click ripple are injected as DOM.

## 2. Preflight: a real GPU, or stop

Run `scripts/preflight/gpu-check.mjs` first (`record.mjs` also refuses software renderers). If Chrome cannot open the
GPU it falls back to llvmpipe *silently*: nothing errors, but the first draw compiles every shader on the CPU and a
heavy scene does not finish loading in 10+ minutes; Chrome's SwiftShader may refuse to create a context at all. On
Linux the usual cause is that nobody is logged into the machine's desktop (it sits at the login screen after a reboot,
you are on SSH), so the ACL on `/dev/dri/renderD128` is not granted. Fix: log in on the desktop, or have the owner run
`sudo setfacl -m u:$USER:rw /dev/dri/renderD128 /dev/dri/card0` (gone at next reboot). Do not apply it yourself
unasked.

## 3. Workflow

1. Write the shot list (`clip.example.mjs`). Give the app a fixed pixel ratio (`?q=1`-style switch) so dynamic
   resolution is off, and hide debug overlays.
2. **Dry run:** `node record.mjs --script clip.mjs --out dry --nosave --shots 1.4,3.6,…`. It renders the whole timeline
   but saves only PNGs at those times (a full dry run of 24 s is about a minute). Tile them into a contact sheet with
   PIL and *look*; fix targets, timings, and anything in the way. Expect 3-5 rounds.
3. **Final render:** `--dsf 2` (3 when punching in 2× or more), `--out frames`. About 4-7 minutes for 24 s. Run it
   detached (`nohup … &`) and wait on the log/output file; never poll with `sleep` chains.
4. `post.py frames small` downscales every frame to 1920×1080 with Lanczos (crops come out at different sizes).
5. `encode.sh small out.mp4 [soundtrack.m4a]`. Verify with `ffprobe`, then make a contact sheet *from the encoded file*
   (`ffmpeg -i out.mp4 -vf "fps=1/2,scale=480:270,tile=4x4" -frames:v 1 sheet.png`) and look at it again.
6. Look at a couple of full-size frames at the zoomed moments: text should be crisp.

## 4. Shot-list craft

- **Pointer:** ease between targets (smoothstep in-out), `linear` for drags, dwell ~0.35 s after a click, and arrive
  0.1 s early. Targets are re-resolved every frame, so the pointer follows things that move with the camera (markers,
  cards). A DOM marker whose button has a zero-size box must be aimed at its dot child (`aim: '.dot'`).
- **Click in one frame** (`kind: 'click'`): press and release in separate frames missed a card's close button because
  the card had moved in between.
- **Pick targets that are really visible:** opacity above 0.5, inside a safe rectangle, not under other UI; choose the
  nearest to the screen centre. Return `null` and the pointer simply stays.
- **Punch-ins on controls** (a toolbar while its buttons are clicked): a `zoom` track crops the screenshot
  (`Page.captureScreenshot` `clip` with `scale`), so nothing in the app changes. Zoom 2.4× on the *whole bar* (labels
  readable) rather than 1.4× on one button; render at `--dsf 3` so the crop is still sharp. Punch in just before the
  click, hold through the last click of a group, release after the state change is visible. A place card: 1.5×.
- **Restarting an intro fly-in** for the take: set its progress back (and mark it active again if it had finished) in
  `start(page)`; first frame is then the opening shot.
- **Free camera paths** (aerial cranes, dives): interpolate each component with a **monotone cubic Hermite**
  (Fritsch-Carlson) in time. Catmull-Rom overshoots between keys and gave an upside-down frame where it dipped below
  the lake. Sample a known-valid path of the app (its own ride) to find safe positions; positions
  inside forest or rock are invalid. A far look-at target keeps the horizon steady.
- Keep the app's real UI in frame for feature demos; hide it (`hide`) for cinematic shots.

## 5. Cinematic extras

- **Same move, different state:** render the identical camera move once per state (time of day), then composite
  vertical strips with PIL and animate the dividers (open from the middle, hold, wipe away). "One valley, four lights"
  costs four short renders of the same move (dsf 1 is enough).
- **Crossfades** between separately rendered sequences: `Image.blend` over 15-18 frames.
- **Overlay captions/titles** are DOM elements animated with `el.animate(...)`; they run on the virtual clock too.
- **Sound** without assets: ffmpeg `lavfi` sines (a few partials + slow `tremolo` + `aecho`) swelling as the piece
  climbs, a band-passed pink-noise whoosh on the fast move, short sine ticks on clicks, plus a recording the app
  already ships under an open licence as the bed. Measure with `volumedetect`: mean around −23 dB, peak under −0.5 dB
  (a first mix at −33 dB was inaudible). Headless audio capture is not needed.

## 6. Delivery

- For X/Twitter and most feeds: landscape 16:9 at 1920×1080, H.264 High, yuv420p, bt709, `+faststart`, 30 fps, AAC track
  (silent if need be). 24-34 s is well inside the limits.
- Upload limits of chat/file tools are often ~30 MB: keep the full-quality master (crf 19, about 12-14 Mbps) and make a
  lighter copy (6-8 Mbps) for sharing inline; tell the user which is which.
- Save next to the project, not in the repository (big binaries), unless asked.

## 7. Traps hit

- `pkill -f "google-chrome"` inside a bash tool call kills the tool's own shell (its command line contains the
  pattern); so do `pgrep -f` wait loops. Kill by PID from `ps -eo pid,args | awk …`, and wait on files.
- Session scratch folders can be wiped (reboot, date change): keep recorder scripts in the repo or a skill, not in `/tmp`.
- Real timers created before the virtual clock starts keep running in real time (a loader's 2 s hold): wait until they
  have fired (`loaderGone`, `settleMs`) before starting.
- A first real-rAF callback still fires after the switch; the recorder waits 400 ms for such callbacks to re-queue.
- Web Animations the page pauses itself are left alone; if a UI animation looks frozen, check it is not paused by design.

# UI and motion sources: what each is really worth

Reviewed September 2026 by reading their code, docs and terms (no demo was watched running). Re-check licences
before copying code; they change.

## The finding that matters most

Almost nothing can be dropped into a project that doesn't already use their stack. The component libraries are
built on **Tailwind plus Motion (Framer Motion) or GSAP**. Installing one component means adding Tailwind, `motion`
(~30 KB+), `clsx` and `tailwind-merge` for effects that are a few lines of CSS. Port the technique and its tuned
constants instead; install the library only if the project already uses that stack.

## The twelve

| Site | What it actually is | Licence / terms | Worth it for |
|---|---|---|---|
| beui.dev (motion) | Copy-paste React library, ~42 motion components, Tailwind v4 + `motion` | MIT (c) 2026 Saurabh Chauhan | **High** as technique: circular View Transition, dock pill, drawer timing, text scramble, scroll reveal, press/arrow micro-interactions, dither loader |
| bencho.dev | ~30 tunable React blocks in **plain CSS**, no Tailwind | Blocks MIT (c) 2026 Lorenzo Cabra; the site itself all rights reserved | **High** fit: two-phase nav indicator, tick-bar progress, label tips, side-panel timing |
| aura.build | AI landing-page builder with public galleries | Gallery code not licensed for reuse; companion repo `MengTo/Skills` is **MIT** | **Medium-high** via the MIT repo: staggered word reveal, timeline reveal, masked gradient border, animation hygiene |
| typeui.sh | Commercial design "skills"; paid animations are prompts, not code | Free `skills/fundamentals` repo is MIT | **Medium**: clearest interaction rules (timing table, instant focus, reduced motion, five-second rule) |
| open-design.ai | Open-source desktop design workspace driving your coding agent | Apache-2.0 repo; marketing site code unlicensed | **Medium**: `[data-reveal]` pattern; `craft/animation-discipline.md` (durations, WCAG 2.2.2, View Transition reduced-motion caveat) |
| styles.refero.design | Gallery of 2,000+ generated DESIGN.md files describing real sites | Reference only; scraping and republishing prohibited | **Medium** as a survey of real durations and easing; no code |
| obsidianui.dev | Landing-page effects: galleries, WebGL shaders, cursor toys; Tailwind + motion/GSAP | MIT, mixed provenance (items derived from Magic UI, React Bits) | **Low**: one CSS button, the sliding tab indicator idea |
| collectui.com | Inspiration gallery, now curating posts from X (not Dribbble); no code | Each work belongs to its designer | **Ideas only**: staged honest loading, segmented progress, rolling labels |
| designmd.me | Paid URL-to-DESIGN.md generator | Terms prohibit automated access | **Low**: one reveal-on-scroll template |
| designmd.supply | MIT URL-to-DESIGN.md generator (Google's format) | MIT | **None**: the format has no vocabulary for motion |
| design-md.hyperbrowser.ai | Bring-your-own-key generator, no gallery | No licence file | **None** |
| neuform.ai | Prompt-to-HTML generator, sibling of Aura | Terms forbid scraping; free tier personal use | **None** beyond Aura |

Google's DESIGN.md format, which four of these generate, has no way to express motion (an open issue says so),
which is why they offered nothing here.

Also useful: Emil Kowalski's drawer easing and interaction writing (MIT code); WCAG 2.2.2 (Pause, Stop, Hide).

## Rules for using them

- Only ideas and ordinary numeric conventions (durations, easings) from sources whose terms don't allow reuse
  (Aura's gallery, Neuform, Refero, designmd.me, collectui, unlicensed marketing pages).
- MIT/Apache code: fine to port; keep the copyright notice with substantial copies and credit ports in the file
  header anyway.
- Never scrape sites whose terms forbid it, and never pull keys or call private backends to get at a gallery's data
  (a research agent once tried; the permission system stopped it).

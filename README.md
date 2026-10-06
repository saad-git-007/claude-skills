# Claude skills

[Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) for Claude Code and claude.ai,
distilled from building a three.js portfolio site, a production operations dashboard (a live map, a CesiumJS 3D
view and a streaming AI chat, used on desktops and field phones) and a print and social admissions poster rebuilt in
Canva. Every rule, number and pitfall in them was measured or hit on one of those projects.

| Skill | What it gives Claude |
|---|---|
| [`web3d-realism-performance`](skills/web3d-realism-performance) | Making a browser 3D scene (three.js, React Three Fiber, CesiumJS, WebGL) look photorealistic while keeping it fast: a measuring workflow (fixed-pose GPU benchmark, image diff, alternating A/B), draw order and overdraw, batching, shader-chunk patches that skip work, baked lighting with Blender Cycles (lightmaps on a second UV set plus a reflection probe), PBR textures, vegetation impostors and glTF optimisation; CAD-accurate models repeated many times (a light copy everywhere, full detail only in close-up, with measured costs), and sharp CesiumJS rendering on phones; real-place landscapes from elevation data (bounded procedural relief, treeline, shader program variants, matching photographs); and frame-exact demo videos of a live WebGL app (virtual-clock recorder, scripted pointer and punch-in zooms, GPU preflight). Includes the benchmark and recorder scripts and a reference lightmap pipeline. |
| [`web-ui-motion`](skills/web-ui-motion) | A motion and layout system for websites: timing and easing tokens, entrance and scroll reveals, View Transitions, drawer dialogs, nav pills, honest loaders and micro-interactions, all with reduced-motion support; layouts that fit every viewport without scrolling; HTML overlays and camera flights over a 3D canvas; motion in live apps that poll or stream (an AI chat's launcher morph, loading avatar and Send/Stop); browser-test traps that let motion tests pass without testing anything; and a licence-checked review of twelve UI and motion sources. Includes a CSS template, React helpers and a Playwright layout test. |
| [`web-ui-surfaces`](skills/web-ui-surfaces) | How polished UI looks at rest: depth ladders spaced by measured lightness (light and dark work in opposite directions), wells vs raised controls, gradient rules (px-sized blooms, colour over brightness, contrast checked at the brightest point), dark panels lifted by light, gradient vs frosted glass with measured fills, and recipes for buttons, cards, selected and alert states, stat tiles, segmented controls, fields, badges and tables. Includes a themeable `surfaces.css` (light, dark and four dark panel grounds), a showcase page and a contrast and depth checker. |
| [`canva-poster-rebuild`](skills/canva-poster-rebuild) | Turning a flat poster or flyer image into a fully editable Canva design through the Canva MCP, with every element directly clickable (text always on top, no element hidden behind another, one background layer per band) and a clean visual hierarchy: a plan-first workflow with a layout checker that flags overlaps and hidden layers before anything is built, asset extraction (white knockout, circle clipping, generated star patterns, glows and flattened band images), Canva edit-API pitfalls (true-pixel rounded corners, outline-only rings, crops that survive image swaps, layer order), an optional redesign recipe (grid, type scale, indigo-and-gold palette, card and footer patterns), real Canva fonts set through Firefox automation on a dedicated control profile, and print PDF / social PNG export with checks. Includes the asset, layout-plan, upload and browser-launcher scripts. |

The skills point to each other. The 3D one covers rendering; the motion one covers how the interface moves,
including UI laid over a 3D scene; the surfaces one covers how it looks at rest.

## Install

**Claude Code** (all projects): copy or symlink a skill folder into `~/.claude/skills/`.

```bash
git clone https://github.com/saad-git-007/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/skills/web3d-realism-performance claude-skills/skills/web-ui-motion claude-skills/skills/web-ui-surfaces \
  claude-skills/skills/canva-poster-rebuild ~/.claude/skills/
```

For a single project, use `<project>/.claude/skills/` instead.

**claude.ai**: download the `.skill` files from the [latest release](https://github.com/saad-git-007/claude-skills/releases/latest)
and upload them in claude.ai's skills settings (skills must be enabled for your account).

Claude loads a skill by itself when a request matches its description; you can also ask for it by name.

## Layout of a skill

```
skills/<name>/
├── SKILL.md       instructions and the when-to-use description (always read first)
├── references/    detail Claude reads when the task needs it
├── scripts/       runnable tools and reference implementations   (web3d-realism-performance, canva-poster-rebuild)
└── assets/        templates to copy into a project               (web-ui-motion, web-ui-surfaces)
```

The scripts and templates come from those projects. Read them as worked examples and adapt the app hooks, selectors
and names to yours.

## Credits

`web-ui-motion/assets/motion-helpers.tsx` adapts techniques from beUI (MIT, (c) 2026 Saurabh Chauhan), the
open-design.ai reveal pattern and MengTo/Skills (MIT), as credited in its header. Sources whose terms don't allow reuse
were used for ideas only; see `web-ui-motion/references/sources.md`.

## Licence

[MIT](LICENSE)

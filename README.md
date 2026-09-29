# Claude skills

[Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) for Claude Code and claude.ai,
distilled from building a three.js portfolio site and a production operations dashboard (a live map, a CesiumJS 3D
view and a streaming AI chat, used on desktops and field phones). Every rule, number and pitfall in them was measured
or hit on one of those projects.

| Skill | What it gives Claude |
|---|---|
| [`web3d-realism-performance`](skills/web3d-realism-performance) | Making a browser 3D scene (three.js, React Three Fiber, CesiumJS, WebGL) look photorealistic while keeping it fast: a measuring workflow (fixed-pose GPU benchmark, image diff, alternating A/B), draw order and overdraw, batching, shader-chunk patches that skip work, baked lighting with Blender Cycles (lightmaps on a second UV set plus a reflection probe), PBR textures, vegetation impostors and glTF optimisation; CAD-accurate models repeated many times (a light copy everywhere, full detail only in close-up, with measured costs), and sharp CesiumJS rendering on phones. Includes the benchmark scripts and a reference lightmap pipeline. |
| [`web-ui-motion`](skills/web-ui-motion) | A motion and layout system for websites: timing and easing tokens, entrance and scroll reveals, View Transitions, drawer dialogs, nav pills, honest loaders and micro-interactions, all with reduced-motion support; layouts that fit every viewport without scrolling; HTML overlays and camera flights over a 3D canvas; motion in live apps that poll or stream (an AI chat's launcher morph, loading avatar and Send/Stop); browser-test traps that let motion tests pass without testing anything; and a licence-checked review of twelve UI and motion sources. Includes a CSS template, React helpers and a Playwright layout test. |

The two skills point to each other. The 3D one covers rendering; the motion one covers the interface, including UI
laid over a 3D scene.

## Install

**Claude Code** (all projects): copy or symlink a skill folder into `~/.claude/skills/`.

```bash
git clone https://github.com/saad-git-007/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/skills/web3d-realism-performance claude-skills/skills/web-ui-motion ~/.claude/skills/
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
├── scripts/       runnable tools and reference implementations   (web3d-realism-performance)
└── assets/        templates to copy into a project               (web-ui-motion)
```

The scripts and templates come from those projects. Read them as worked examples and adapt the app hooks, selectors
and names to yours.

## Credits

`web-ui-motion/assets/motion-helpers.tsx` adapts techniques from beUI (MIT, (c) 2026 Saurabh Chauhan), the
open-design.ai reveal pattern and MengTo/Skills (MIT), as credited in its header. Sources whose terms don't allow reuse
were used for ideas only; see `web-ui-motion/references/sources.md`.

## Licence

[MIT](LICENSE)

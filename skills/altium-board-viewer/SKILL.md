---
name: altium-board-viewer
description: Turn an Altium Designer PCB project (.PrjPcb/.PcbDoc, with an optional BOM .xlsx/.csv and pick-and-place .csv) into a self-contained, searchable 2D board viewer HTML, a printable assembly PDF (overview plus zoomed zone pages, so any part is easy to find on paper) and a 3D viewer HTML with real part models (KiCad library plus free manufacturer STEP files), using wavenumber-eng/altium_monkey. A setup script checks every requirement and installs what is missing (uv, Python 3.12, altium_monkey, cadquery-ocp, three.js), keeps it all in one cache folder and deletes it afterwards. Use whenever the user has an Altium project, Gerber/BOM package or PCB and wants to view, search, share, print, review or render it in 3D, find a component on the board, check the BOM against the layout, or mentions altium_monkey, even if they don't say "viewer".
---

# Altium board viewer

Three outputs from one Altium project, all files that open offline with nothing installed:

| Output | What it is |
|---|---|
| `<name>_viewer.html` (~1 MB) | 2D board: copper, pads, drills, silkscreen layers; search by designator, value, MPN or footprint; detail card; animated gold ring on the selected part; NNP (not placed) parts greyed with a toggle; light/dark theme |
| `<name>_board.pdf` (~3.5 MB, 11×17 in) | Overview page with a zone grid (A1, B2…) whose labels link to zoomed zone pages; every zone page has a locator map. Finding a part = look up its zone, turn to that page |
| `<name>_3D.html` (~3 MB) | Board with real models: orbit, top/flip/reset view, search, part highlight, NNP ghosts, model source per part |

The scripts are in `scripts/`, templates and the example config in `assets/`. Read `references/pipeline.md`
before changing a script, and `references/models.md` before sourcing 3D models.

## 1. Requirements are installed for you

Run `scripts/setup.sh --check` first and show the user what is missing and the disk it needs. Then:

```bash
bash scripts/setup.sh          # 2D + PDF: installs uv (user-local), Python 3.12, altium_monkey venv   (~150 MB)
bash scripts/setup.sh --3d     # also cadquery-ocp + numpy venv and three.js r128 files            (~+650 MB)
bash scripts/setup.sh --clean  # remove venvs, models and build files when done (outputs are kept)
```

- Everything goes in `$ABV_WORK` (default `~/.cache/altium-board-viewer`, or `work_dir` in board.json), never in
  the user's project. Re-running skips what is already there.
- The only thing it will not install is Chrome/Chromium (needs sudo, used only to print the PDF). If it is missing,
  ask the user, then run the command `setup.sh` prints.
- altium_monkey is installed with `uv venv` + `uv pip install`, not the repo's `uv sync`: that needs a newer uv than
  many machines have. The clone is deleted after install.
- **Disk:** if the user says space is tight, tell them the numbers above before starting, and run `--clean` at the end.

## 2. Ask before building (one round, with recommended defaults)

1. **3D detail:** simple extruded shapes, or real models (KiCad library + free manufacturer files, ~1 GB temporary)?
2. **NNP parts:** greyed out with a toggle *(recommended)*, hidden, or shown normally?
3. **PDF:** overview + zoomed zones *(recommended)*; add a component table only if they ask.
4. **Output folder** (default `board_viewer/` next to the project) and title/revision text.

## 3. Run

```bash
cp assets/board.example.json <project>/board_viewer/board.json   # fill in paths, name, title, BOM columns
bash scripts/run.sh <project>/board_viewer/board.json            # 2d + pdf
bash scripts/run.sh <project>/board_viewer/board.json models 3d  # real 3D models
```

`run.sh` calls `setup.sh` itself, so a missing requirement is installed before the step that needs it.
Steps: `2d` (build.py → make2d.py), `pdf` (make_pdf.py), `models` (fetch_models.py), `3d` (conv3d.py → make3d.py).

**board.json** (all paths relative to the file): `project`, `bom`, `pnp`, `name` (file prefix), `title`, `rev`,
`bom_columns` (0-based columns for item/name/mpn/mfr/refs), `bom_header_rows`, `nnp_marker`, `bom_alias`
(designator → text in a refs cell, for parts listed by description), `pnp_comment_col`, `board_thickness`,
`kicad_rules`, `maker_map`, `maker_urls`, `maker_sources`, `rot_override`, `stacked`, `out_dir`, `work_dir`, `chrome`.

First look at the BOM's header rows to set `bom_columns`; after the `2d` step check the printed counts
(components, NNP, fallback boxes) against the BOM and tell the user about mismatches. It is the most useful
review finding (e.g. a capacitor whose catalogue size doesn't fit its footprint, a "vertical" connector whose
model is right-angle).

## 4. 3D models

`fetch_models.py` downloads the KiCad model and footprint for every rule match, plus `maker_urls`, then lists
what is still missing. For each part without a model, see `references/models.md`: free manufacturer download
→ community model → KiCad equivalent → leave as a box and tell the user. **Never** create accounts, log in or
send the user's e-mail anywhere (SnapEDA, Ultra Librarian, SamacSys and most DigiKey/Mouser model links are
login-gated). Download each untrusted file into its own folder.

Orientation is automatic: each maker model is tried in all 24 axis-aligned rotations and scored against the
real pad and drill positions, so through-hole leads go into their holes. If one is still wrong (e.g. a
connector facing inward), add `"rot_override": {"J16": 180}` and re-run `3d`. Check `report.json` in the work
folder: `large fit error` lists parts to look at.

## 5. Verify before reporting

Open each HTML in a real browser (Firefox with the GPU; headless Chrome's software GL is too slow and freezes CSS
animations in screenshots). Check: no console errors; search finds a part and the ring lands on it; NNP toggle;
3D orbit is smooth (aim ≤ 25 ms a frame) and Reset view works; THT parts stand upright; the PDF zone links jump to
the right page. Then report sizes, disk freed and the parts that are boxes or stand-ins.

## Defaults this user asked for (keep them)

- Selecting a part **keeps the whole board in view** and marks it with the animated gold ring; the user zooms
  in themselves. Do not auto-zoom to the part, in 2D or 3D.
- Top copper **blue** (`#3f74d0`), bottom copper **red** (`#c8553d`).
- No 3D inside the 2D viewer; the 3D viewer is its own file, linked from the top bar.
- PDF: no component list; overview + zoomed zones; no 3D page.
- 3D: a labelled gold **Reset view** button; rendering must stay light (see pipeline.md, Performance).
- Look: the `my-design-language` skill if present (jet black, one gold accent, short labels).

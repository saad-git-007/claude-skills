---
name: canva-poster-rebuild
description: Rebuild a flat poster, flyer or social graphic (JPEG/PNG/screenshot) as a fully editable Canva design through the Canva MCP, where every element can be clicked and edited (text always on top, no element hidden behind another) and the visual hierarchy is clean, optionally redesign it to a polished professional standard, set real Canva fonts through Firefox browser automation, and export a print PDF and a high-res social PNG. Use this whenever the user shares an image of a poster/flyer/banner/event graphic and wants it "in Canva", "editable", "recreated", "rebuilt", "redesigned", "made more professional", or wants elements not hidden behind layers — even if they don't say "rebuild". Also use when the user asks to change fonts on a Canva design and the Canva MCP can't do it, or wants a Canva design exported for print and social.
---

# Canva poster rebuild

Turn a flat image into a Canva design where every piece (background block, card, icon, image, text box) is its own element, stacked so text is always on top and nothing important hides behind anything else. Optionally redesign it, set fonts, and export.

The whole job runs through four tool families:
- **Canva MCP** (`mcp__canva__*`): create the design, upload images, add/move/style elements, export.
- **Python + PIL** (Bash): cut images out of the source, make transparent/circular versions, generate decorative textures. `scripts/make_assets.py` has ready helpers.
- **curl**: upload asset bytes to Canva upload URLs (`scripts/upload_to_canva.sh`).
- **Firefox automation** (`mcp__firefox-*`), only for fonts: the Canva MCP cannot set a font family.

Read `references/canva-edit-gotchas.md` before your first `edit-design` call. It lists the API behaviours that cost time in the original session.

## The two things that make this worth doing
Users ask for this because flat or AI-generated designs are painful to edit in Canva. Text hides under shapes, a click grabs a texture instead of the button under it, and there's no obvious structure. Treat these two properties as the deliverable, not side effects:

**1. Every element can be selected and edited directly.**
- Text is the top layer, always. No shape or image is ever stacked above a text box.
- Text boxes never overlap each other.
- No element completely covers another. If two layers would share one footprint (a coloured disc behind a round photo, a texture on a colour band), merge them into one: bake the backdrop colour into the image, or bake texture, glow and colour into a single band image. Otherwise drop the redundant one. One band = one background layer is the ideal.
- Decorative layers (textures, glows, dot grids) sit directly above their band and below every card, image and text box. If a decorative overlay has to stay separate so its colour can still be edited, tell the user to lock the band and its overlay in Canva (Position → Layers → lock), so clicks reach the content.
- Containers (cards, tiles, pills) sit under their own content and never cross into a neighbouring section.

**2. The visual hierarchy is clean and readable at a glance.**
- One grid: consistent side margins and column gutters, with everything snapped to them.
- Distinct type levels: display title, then section labels (small, uppercase, accent colour), then card titles, then body and bullets. Each level keeps one size, weight and colour wherever it appears.
- One accent colour, used sparingly. Repeated items (three programs, three highlights) get identical structure, and their internal parts line up across the row.
- The layer order mirrors this hierarchy: bands → decor → containers → images and icons → text.

Enforce both with a **layout plan**: write the full element list as JSON (bottom-to-top order, coordinates, roles), run `scripts/layout_plan.py check plan.json`, and fix every ERROR before touching Canva. The same plan then generates the insert operations, so what you checked is exactly what gets built.

## Workflow

### 1. Study the source
Read the image. Note its pixel size, the sections from top to bottom, every piece of text (copy it exactly), the colours, and which visuals are raster art (logo, illustration, QR code, ornaments). Sample exact colours with PIL `getpixel` rather than guessing. Text pixels are anti-aliased, so pick a solid area, or take a dark percentile over the text region.

### 2. Extract the raster assets
Crop each visual into its own file with `scripts/make_assets.py`:
- Make white backgrounds transparent (`knockout_white`) for illustrations and ornaments, so they can't block anything behind them.
- Upscale small crops (logo, QR code) with LANCZOS, or NEAREST for QR codes, so they don't look soft.
- If an illustration has a flat-cut edge, clip it into a circle (`circle_clip`, e.g. `--zoom 1.1`) instead of letting the hard edge show. The artwork is centred by default; if the circle clips a head or other key detail at the top, shift it down with `--offset-y` (about +20 to +30 at 600px).
- Recreate decorative textures (dot grids, geometric patterns, glows) as transparent PNGs rather than cropping them out with text baked in.

Look at every generated asset with Read before uploading it.

### 3. Upload the assets
Call `mcp__canva__create-upload-url` once per file. You can call it several times in one turn. Then POST the raw bytes with `scripts/upload_to_canva.sh <file> <url>`. Each response holds a `mediaId`, which is what `insert_fill` and `update_fill` take as `asset_id`. Each URL can be used once.

### 4. Create the base design
Call `mcp__canva__create-design` with a short brief and an explicit format that matches the source's aspect ratio. A portrait 0.773 ratio is "Flyer (Portrait US Letter)", 816×1056. Poll `get-create-design-async-job`, respecting `wait_seconds`. Then call `read-design` with `open_transaction: true` and fields `page_metadata, design_content, thumbnails` to get the page id, its size and the generated elements.

Compute a scale factor (page width ÷ source width) and work in page pixels from then on.

### 5. Write and check the layout plan
Write `plan.json` in the scratchpad (the format is in the docstring of `scripts/layout_plan.py`). List elements bottom to top:

1. **Background bands**: one per section, edge to edge, covering the page's own texture background. When a band has texture or a glow, make it **one flattened image**: `make_assets.py band OUT W H --base '#1E2766' --pattern 0.08 --glow cx,cy,r`, rendered at 2× the element size. In the plan it's `"kind": "image", "role": "background"`. A plain colour band can stay a `rect`, which keeps it recolourable.
2. **Decor**: textures, glows and dot grids, only if they can't be baked into the band. Each separate overlay is a click-trap over its band, and the checker flags it.
3. **Containers**: cards, tiles, pills and rules.
4. **Images and icons**: illustration, logo, QR code, icon shapes.
5. **Text**: every text box, with font size and line height so the checker can estimate its height.

Run `python3 scripts/layout_plan.py check plan.json`. Fix every ERROR. Then read each WARN and either fix it or note that it's intentional (e.g. a 2px optical nudge on a large title).

### 6. Build from the plan
Delete the generated placeholders. Then run `python3 scripts/layout_plan.py ops plan.json <PAGE_ID>` and pass its operations to `edit-design` (`finalize: "keep_open"`), in chunks of about 30. Each new element lands on top of the previous ones, so the plan order becomes the layer order.

Then style the text in a second pass: the add_text results contain each element's `locator_id`, so call `format_text` on each one.

Check the thumbnail after every call. Fix positions with `position_element` and `resize_element`, never by deleting and re-adding, because re-adding puts the element on top. When real text heights in the response differ from the estimate, update the plan and re-run `check`.

### Fixing layers on a design that already exists
Use this when the user (or an earlier pass) has a band built as a colour rectangle plus pattern and glow overlays, or a shape hidden exactly under an image. It works without rebuilding anything else, and keeps the fonts that were set in the browser:

1. Generate the flattened band image(s) with `make_assets.py band`, matching the old colour, glow position and pattern strength so the look doesn't change. Upload them.
2. In one `edit-design` call, delete the old band rectangle, its overlays and any fully hidden duplicate shape, and `insert_fill` the new band image(s) at the same position and size. New inserts land on **top** of everything, covering the whole poster in the thumbnail. That's expected.
3. In a second call, send each new band to the back with `layer_element` `position: "back"`. (The insert's locator id only exists after the first call returns, which is why this takes two calls.) Bands that don't overlap can go back in any order.
4. Confirm in the returned document that the bands are first in the element list and all text is last, and that the thumbnail matches the old look. Then commit.
5. Re-export any PDF or PNG the user already has saved locally, so their files match the design.
6. Tell the user the trade-off: a baked band can't be recoloured with Canva's colour picker. Offer to regenerate it in another colour if they need one.

### 7. Redesigns (when asked for "more professional", "polished" and so on)
Do the design thinking at the plan stage (step 5), not after building. Follow `references/design-recipe.md`, which covers the grid, type scale, palette, section patterns and SVG icon paths that produced the polished result. Keep every piece of the user's copy word-for-word. If you add a label of your own, such as a card tag, tell the user.

### 8. Audit, then save
Before committing, re-read the design (`read-design` with the transaction id, `design_content`) and confirm:
- every `type: "text"` element comes after every non-text element in the list;
- no text box's real height now runs into the next element;
- the final thumbnail matches the plan.

Commit (`finalize: "commit"`) once the user has asked for the design to be built, or has approved the preview. Canva's version history keeps earlier states, so mention it when you overwrite a previous version.

### 9. Fonts (Canva MCP can't do this)
`format_text` has no font-family option, and every `add_text` box gets Canva's default font. To set real fonts, drive the Canva editor in a dedicated, signed-in Firefox control profile that you launch yourself with `scripts/firefox-control-launcher.sh`, never the user's everyday browser. Follow `references/firefox-fonts.md`, which covers connecting to the profile, selecting elements reliably, the font picker and verifying the result. Recommended default pairing: **Playfair Display** for display text (titles, card headings, numbers, quotes) and **Montserrat** for everything else.

### 10. Export
- `get-export-formats` first, then `export-design`.
- **Print**: `{"type":"pdf","export_quality":"pro","size":"letter"}` (or `a4`). Download it with curl into the user's working directory. Verify with `pdfinfo`, `pdffonts` (fonts embedded) and `pdfimages -list` (effective PPI), and render a preview with `pdftoppm` to look at.
- **Social**: `{"type":"png","export_quality":"pro","width":2160,"lossless":true}`.
- Tell the user that API exports have **no bleed or crop marks**. For a print shop, they should use File → Settings → Show print bleed, then Download → PDF Print with "Crop marks and bleed" ticked.

## What to tell the user at the end
- The design link.
- How the layers are organised (bands → decor → cards → images → text). Say plainly whether any element can only be selected through the Layers panel. If you kept a decorative overlay separate, recommend locking it.
- Anything that differs from the source: fonts, gradients that became flat colours, invented labels, a QR code copied from a JPEG (they should test-scan it).
- File paths of the exports, plus any print caveats.

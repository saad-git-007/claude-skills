# Canva MCP edit-design: gotchas learned the hard way

## Layering
- Every insert (`insert_shape`, `insert_fill`, `add_text`) goes on top of everything already on the page, so the order you insert in is the stacking order.
- `layer_element` only offers `front` and `back`. Get the order right as you build instead of fixing it afterwards. The one good use of `back` is replacing a background band after the fact: insert the new band image (it lands on top), then send it `back` in the next call. Each `back` puts that element below everything, including any band sent back earlier, so send bands back in top-to-bottom order if they overlap.
- Separate texture or glow overlays on a band are click-traps: a click on the band selects the overlay. Flatten colour, glow and texture into one band image (`make_assets.py band`) instead.
- Never delete and re-add an element just to move it. Use `position_element` and `resize_element` so it keeps its layer.

## Page and background
- `create-design` with format "Flyer (Portrait US Letter)" gives an 816×1056 page.
- Generated designs often have an image as the page background (e.g. a paper texture) that delete operations can't remove. Cover it with full-bleed rectangles.

## Shapes (`insert_shape`)
- The path uses SVG `d` syntax with only M/L/H/V/C/S/A/Z commands. Q and T are not supported.
- Rectangle: `M0 0 L100 0 L100 100 L0 100 Z` with viewBox 100×100, then set width and height.
- **Rounded corners**: set viewBox equal to the element's pixel size (e.g. path `M0 0 L290 0 L290 38 L0 38 Z`, viewBox 290×38) so `corner_rounding` is in real pixels. For a pill, use rounding = height/2.
- Circle: `M0 50 A50 50 0 1 1 100 50 A50 50 0 1 1 0 50 Z`, viewBox 100×100.
- **Outline-only ring**: leave out `color` and pass `stroke_color` and `stroke_weight`. The fill stays empty.
- Diagonal panels: draw the polygon in a viewBox matching the bounding box, e.g. `M218 0 L381 0 L381 206 L0 206 Z`.
- Simple filled icons (24×24 viewBox) that render well:
  - crescent: `M14.5 3 A9 9 0 1 0 21 15.5 A7 7 0 1 1 14.5 3 Z`
  - hourglass: `M6 2 H18 V4 H17 V6 C17 9 14.5 10.5 13.5 12 C14.5 13.5 17 15 17 18 V20 H18 V22 H6 V20 H7 V18 C7 15 9.5 13.5 10.5 12 C9.5 10.5 7 9 7 6 V4 H6 Z`
  - speech bubble: `M4 3 H20 A2 2 0 0 1 22 5 V15 A2 2 0 0 1 20 17 H10 L5 21 V17 H4 A2 2 0 0 1 2 15 V5 A2 2 0 0 1 4 3 Z`
  - check: `M9 16.2 L4.8 12 L3.4 13.4 L9 19 L21 7 L19.6 5.6 Z`

## Images
- `insert_fill` crops to the frame you give it. Give it the image's true aspect ratio to avoid unwanted cropping.
- **`update_fill` keeps the old frame's crop.** After swapping in an image with a different aspect ratio and resizing the frame, call `crop_media` with `top:0,left:0,width:W,height:H` to reset the crop.
- `opacity` on `insert_fill` sets element opacity, which the user can change later.

## Text
- `add_text` with `width` creates a fixed-width wrapping box. Its default is 16px, black, Canva's default font.
- Format in a **second** call using the locator ids returned by the first.
- `format_text` options: color, font_size, font_weight (normal/bold only), font_style, line_height, text_align, list_level + list_marker (real bullets), link, decoration, strikethrough. There is **no font family and no letter spacing.**
- Estimate line breaks before placing text: bold sans runs about 0.55–0.6 × font size per character. Heights come back in the response; check them and re-position anything that wrapped more than expected.
- Two colours in one heading means two text boxes (e.g. "‘Aisha Academy" in white and "Canada" in periwinkle).
- Superscript honorifics: the Unicode characters `ˢᵃ` work.

## Transactions
- `read-design` with `open_transaction: true` returns a `transaction_id`. All edits use it, and nothing is saved until `finalize: "commit"`.
- Responses are big, because the whole document is echoed back. Batch many operations into one call (30+ is fine).
- After committing, element ids persist, so a later transaction can reference them.

## Uploads
- `create-upload-url` returns a single-use URL. Send it with `curl -X POST -H "Content-Type: application/octet-stream" --data-binary @file URL`. The response is `{"mediaId":"..."}`.

# Design recipe: polished admissions or event poster (US Letter, 816×1056)

Use this when the user asks for a "more professional", "polished" or "senior designer" version. It is a system, not a template. Adapt the palette and sections to the content.

## Principles
- **One grid**: 40px outer margins, a content width of 736, and three columns of 232 with 20px gutters (x = 40, 292, 544).
- **Three zones**: a dark header (about the top third), a white body, and a dark footer. The dark bands frame the page, and the body holds the information.
- **One accent colour** used sparingly (gold): small labels, a pill, icons, numbers and a thin ring. Never on large areas.
- **Hierarchy through size and colour, not boxes everywhere**: small coloured uppercase labels ("PROGRAMS OFFERED") above content, large display type for the title, and quiet grey body text.
- **Repeat structure**: anything that appears three times becomes three identical cards or tiles.
- Keep the user's copy word-for-word. Short uppercase labels can be rephrased only if the meaning is unchanged.

## Palette used (indigo + gold)
| Role | Hex |
|---|---|
| Header/footer base | #1E2766 |
| Mid indigo card | #3A4AA8 |
| Light accent text on dark | #AEB8F5 / #C7CEF5 |
| Tint fills (tiles, requirement card, pills) | #F1F3FD / #EEF0FB / #E9ECFC |
| Hairlines and borders | #DCE0F5 / #E6E9F7 |
| Gold accent | #E6C27A (on dark), #C9A24A / #B8913F (on white) |
| Headings on white | #1E2766 |
| Body text | #2B2F45, secondary #4A4F66 |

Derive an equivalent palette from the source's brand colours: a dark base, a mid tone, a tint, and one warm accent.

## Section patterns (y positions are for 816×1056)
1. **Header 0–340**: navy base, soft glow on the right and a geometric pattern at about 8% strength. Bake all three into **one** band image (`make_assets.py band band_header.png 1632 680 --base '#1E2766' --pattern 0.08 --glow 1320,330,420`; footer: `band band_footer.png 1632 288 --base '#1E2766' --pattern 0.08`), so clicking the header doesn't catch a texture layer. Only keep a separate navy rectangle plus an overlay if the user wants to recolour the band in Canva, and then recommend locking both. Do the same for the illustration: bake its lavender backdrop into the circle-clipped image rather than adding a separate disc behind it. Top-left: the logo on a white circle badge (60px) with a small italic line beside it. Then a gold rule (24×2) plus a gold uppercase label, a two-line title at 50px bold (line 2 in a light tint colour), and a gold pill (290×38, rounding 19) holding a navy 13px bold label. Right side: a circle-clipped illustration (300px) on a lavender circle, with a 320px gold outline ring behind it.
2. **Intro 366**: an 18px bold navy sentence, 560 wide, with an ornament image on the right.
3. **Highlight tiles 432–496**: three tint tiles (rounding 12). Each has a 36px navy circle containing an 18px gold icon, plus a 14px bold label.
4. **Section label 523** plus a hairline running across to the right margin.
5. **Program cards 552–762**: white cards with a 1.5px hairline border and rounding 14. Inside each: a gold number ("01") at 24px, a tint tag pill (104×22) at the top right, the title at 16px bold navy, a hairline divider at a fixed y, then 13px bullets. Keep the dividers aligned across cards even if the titles differ in length.
6. **Requirements card plus quote card 780–896**, side by side at 358 wide each. Requirements: a tint card with a label and bold bullets. Quote: a mid-indigo card with a large gold quote mark, white italic quote and a gold attribution.
7. **Footer 912–1056**: navy plus pattern. Left: a gold label, the website at 30px bold white (link), then a small label and the contact line. Right: the QR code on a white rounded card, with a right-aligned caption to its left.

## Generated textures (see scripts/make_assets.py)
- `star_pattern(w, h)`: an 8-point star lattice in white lines on transparent. Place at element opacity 0.06–0.10.
- `glow(w, h, cx, cy, r, rgb)`: a soft radial bloom, for lifting the area behind a hero image.
- `dot_grid(...)`: fading dots, for lighter, softer designs.

## Fonts (set via Firefox, see firefox-fonts.md)
- Display: Playfair Display, for the title, card titles, numbers and the quote (which becomes Bold Italic automatically).
- Text: Montserrat, for everything else.
- Alternatives: Cormorant Garamond + Lato (more classic), or DM Serif Display + Inter (more modern).
- Montserrat runs about 10% wider than Canva's default font. After switching, re-check long card titles and two-line tiles for overflow.

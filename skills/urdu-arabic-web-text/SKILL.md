---
name: urdu-arabic-web-text
description: "Proven recipe for showing Urdu (Nastaliq) and Arabic (Qur'anic, Naskh) text on websites and web apps so it renders correctly and reads comfortably on every device: font choice per script (Jameel Noori Nastaleeq, Noto Nastaliq Urdu, DigitalKhatt IndoPak, Amiri Quran), the Safari/iPhone traps (Nastaliq unjoined in CoreText, Qur'anic marks dropped), right spacing (word-spacing not letter-spacing, line-height for tall Nastaliq), RTL markup, correct Qur'anic text (shadda + khara alif on Allah, madd sign), font subsetting verified with HarfBuzz, and drawing a fixed phrase such as the Bismillah as an SVG. Use whenever a page shows Urdu, Arabic, Persian or Qur'anic text, an Islamic or mosque site needs Bismillah, prayer names, ayat or hadith, or the user says RTL text looks cramped, cut off, broken, unjoined, has missing dots or vowel marks, or wrong spacing, even if they don't name fonts."
---

# Urdu and Arabic text on the web

Distilled from a production mosque website (Cloudflare Worker, plain HTML/CSS, no framework) whose public pages show
the Bismillah, Arabic prayer names, Qur'anic verses and long Urdu passages from the Promised Messiah (as) and the
Khulafa, in light and dark themes, on phones and desktops. Every rule below fixed a bug the owner actually saw.
The main lesson: **the font, the text and the browser all have to agree, and Safari is the one that disagrees.**
Test there, or hand off a fixed rendering (SVG) when the text never changes.

## The rules (why each exists)

1. **One font per job, by script.** Urdu in Nastaliq (Jameel Noori Nastaleeq; Noto Nastaliq Urdu on Apple), Qur'anic
   Arabic in a Qur'anic font (DigitalKhatt IndoPak for the Indo-Pak style South Asian readers expect; Amiri Quran as a
   fallback). Never set Qur'an in a Nastaliq font or Urdu in a Naskh font: readers notice immediately.
2. **Space words, never letters.** `letter-spacing` breaks the joins of connected scripts. Widen gaps with
   `word-spacing` (`.3em` ≈ one narrow letter was what the owner asked for). Don't `text-transform` or justify-stretch them.
3. **Nastaliq is tall.** It slopes down to the right and stacks dots; give it `line-height: 2.25`–`2.4` and
   padding inside its box, or the dots of one line touch the next and the first line's top gets clipped.
   Qur'anic Arabic with full vowel marks needs ~`2.1`; short labels (prayer names) ~`1.8`.
4. **Bigger than the Latin text around it.** Urdu ~21px desktop / 19px phone; Qur'anic Arabic ~26px / 22px;
   inline labels ~16–19px. At Latin sizes the dots and marks are unreadable.
5. **Mark every block** with `lang` and `dir`: `<p lang="ur" dir="rtl">`, `<p lang="ar" dir="rtl">`. The browser picks
   shaping, line breaking and fonts from `lang`; `dir` sets alignment and punctuation side. Don't use CSS `direction`
   alone.
6. **Safari cannot shape Jameel Noori Nastaleeq** (built for Windows text engines): letters come out unjoined, even
   from the full original font. Apple devices ship Noto Nastaliq Urdu, so switch to it only there with
   `@supports (font: -apple-system-body)` (understood only by WebKit on Apple platforms). Keep Jameel Noori
   elsewhere. Repeat the spacing rules inside that block; the Apple font is wider and taller.
7. **Safari drops DigitalKhatt's marks** (dots and vowels vanish, words look cut off). For a fixed phrase (the
   Bismillah, a logo line) pre-shape it with HarfBuzz into an SVG and show it as a CSS `mask` coloured with
   `currentColor` (`scripts/shape_to_svg.py`). Longer Qur'anic text stays live text; check it on a real iPhone.
8. **Get the text itself right before blaming the font.** "Allah" needs shadda and khara (standing) alif:
   `اللّٰهِ`; without them the owner saw the top of the word as "cut off". See `references/text-correctness.md`.
9. **Subset, then prove the subset.** Full Nastaliq fonts are 5+ MB. Cut to the glyphs the page's strings actually
   produce, tracing every HarfBuzz lookup step so multi-step ligatures keep their intermediate glyphs, and verify that
   every string shapes identically with the subset (`scripts/subset_font.py`). A naive `pyftsubset --text=` cut
   silently loses ligature intermediates. Rebuild the cut whenever wording changes.
10. **Lazy-load by `unicode-range`.** Give each Arabic-script `@font-face` a `unicode-range` so English-only pages never
    download it, and keep a large "full alphabet" cut for user-written text in a separate family used only where such
    text appears.
11. **Self-host and keep the licence.** DigitalKhatt and Amiri are SIL OFL 1.1 (credit them); Jameel Noori Nastaleeq
    is freeware of unclear licence, so ask the owner before shipping it publicly.

## Workflow

1. List every Arabic-script string the site shows and decide per string: Urdu (Nastaliq) or Arabic (Qur'anic or Naskh).
2. Fix the text: marks on Allah, madd sign form for the chosen font, no stray tatweel (`references/text-correctness.md`).
3. Pick fonts and add the CSS from `assets/rtl-text.css` (tokens, `@font-face` with `unicode-range`, the Apple
   override, spacing). Font sources and licences: `references/fonts.md`.
4. Subset each font against the real strings with `scripts/subset_font.py` (needs `pip install uharfbuzz fonttools brotli`);
   it prints `mismatched 0 of N` when the cut is safe.
5. For a fixed heading phrase that must look perfect everywhere, run `scripts/shape_to_svg.py` and use the mask recipe.
6. Test in Chromium and WebKit at 390 px and desktop, both themes; then ask the owner to check one page on a real
   iPhone. Read the testing traps in `references/fonts.md` first: Linux WebKit lacks Apple's Nastaliq font, so its
   screenshots of Urdu look broken even when an iPhone is fine.

## Rejected, and why (so it doesn't get re-proposed)

- `letter-spacing` on Urdu or Arabic: breaks joins. Use `word-spacing`.
- Jameel Noori Nastaleeq on Safari: unjoined letters; no CSS fixes it. Use Noto Nastaliq Urdu there.
- Live DigitalKhatt text for the Bismillah: marks missing on iPhone. Use the pre-shaped SVG mask.
- An `<img>` of the Bismillah: can't follow the theme colour. A mask with `background-color: currentColor` can.
- Google Fonts links for Arabic: a third-party request and often a CSP problem; self-host the subset instead.
- `pyftsubset --text=...` alone for Nastaliq: drops intermediate ligature glyphs, so some words render wrong.
- Mixing Urdu and English in one line without `dir`/`<bdi>`: punctuation and numbers jump to the wrong side.

## Reference files

- `references/fonts.md`: each font (where to get it, licence, size, strengths, known engine bugs), the CSS stack per
  script, `unicode-range`, the Apple override, and testing traps (headless WebKit, blank captures, how to compare).
- `references/text-correctness.md`: Qur'anic text details (Allah, madd U+06E4 vs U+0653, khara alif U+0670), Urdu vs
  Arabic letters (ی/ي, ک/ك, ہ/ه), detecting Arabic-script paragraphs, mixed-direction lines, numerals.
- `assets/rtl-text.css`: drop-in tokens and classes (`.ar`, `.ur`, `.ar-label`, `.bismillah`) with the spacing values above.
- `scripts/subset_font.py`: HarfBuzz-traced subsetter with a shaping-identity check.
- `scripts/shape_to_svg.py`: shape a phrase with HarfBuzz and write a single-path SVG for a CSS mask.

# Fonts for Urdu and Arabic, and how to test them

## The fonts

| Font | Use | Licence | Notes |
| --- | --- | --- | --- |
| **Jameel Noori Nastaleeq** | Urdu body text (Chromium, Firefox, Android, Windows) | Freeware, unclear terms: ask the owner | The look Urdu readers expect. Full font ~5 MB; a cut for a few passages is ~70 KB. **Broken in Safari** (unjoined letters, even from the original file). |
| **Noto Nastaliq Urdu** | Urdu on Apple devices (system font) | SIL OFL 1.1 | Ships with iOS/macOS, so it costs nothing to use there. Wider and taller than Jameel: give it `line-height: 2.4`. Can be self-hosted for other platforms too (large). |
| **DigitalKhatt IndoPak** (QUL resource 568, https://qul.tarteel.ai/resources/font/568) | Qur'anic Arabic, Bismillah, prayer names in Indo-Pak style | SIL OFL 1.1 (Amine Anane / Tarteel) | Beautiful mushaf shaping; a cut for ~40 strings is ~32 KB. **Safari drops its marks** (dots and vowels missing): pre-shape fixed phrases to SVG. Uses U+0653 for the madd sign. |
| **Amiri Quran** | Qur'anic Arabic fallback (Naskh) | SIL OFL 1.1 | Renders well in every engine; less familiar to South Asian readers than Indo-Pak. |
| **Scheherazade New** | General Arabic fallback | SIL OFL 1.1 | Wide character coverage. |

Credit OFL fonts in the README or footer (font name, author, licence, source URL).

## CSS stack

```css
@font-face { font-family: "DigitalKhatt IndoPak"; src: url("/fonts/dk-arabic.woff2") format("woff2");
  font-display: swap; unicode-range: U+0600-06FF, U+0750-077F, U+08A0-08FF, U+FB50-FDFF, U+FE70-FEFF; }
@font-face { font-family: "Noori Passages"; src: url("/fonts/noori-passages.woff2") format("woff2");
  font-display: swap; unicode-range: U+0600-06FF, U+FB50-FDFF, U+FE70-FEFF; }
:root {
  --font-arabic: "DigitalKhatt IndoPak", "Amiri Quran", "Scheherazade New", serif;
  --font-urdu: "Noori Passages", "Jameel Noori Nastaleeq", "Noto Nastaliq Urdu", serif;
}
/* Apple only: Safari can't shape Jameel Noori; the system Nastaliq works. */
@supports (font: -apple-system-body) {
  .ur { font-family: "Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", serif; line-height: 2.4; word-spacing: .3em; }
}
```

- `unicode-range` means a page with no Arabic-script characters never downloads the font.
- Keep two Urdu cuts when admins can type Urdu: a small one for the fixed passages (preloaded on that page with
  `<link rel="preload" as="font" type="font/woff2" crossorigin>`) and a full-alphabet one in a separate family used
  only in the user-content container. The full one then downloads only when such text exists.
- A strict CSP (`style-src 'self'`) is fine: everything is in the stylesheet, nothing inline.

## Spacing values that were approved

| Text | Size (desktop / phone) | line-height | word-spacing |
| --- | --- | --- | --- |
| Urdu passage (Jameel Noori) | 21px / 19px | 2.25 | .3em |
| Urdu passage (Noto Nastaliq on Apple) | same | 2.4 | .3em |
| Urdu in user-written prose | 1.3em | 2.3 | .3em |
| Qur'anic verse (DigitalKhatt) | 26px / 22px | 2.1 | normal |
| Arabic label under an English name | 19px / 16px | 1.8 | normal |

Put passages in a padded box (10px 14px) so the tall first and last lines are never clipped by `overflow: hidden`
on a parent card.

## Testing traps

- **Linux WebKit (Playwright) is not an iPhone.** It lacks Noto Nastaliq Urdu, so the Apple branch falls back to
  Jameel Noori and the Urdu looks unjoined in screenshots even when real iPhones are fine. It also mis-renders
  DigitalKhatt even from the original file. Use it for layout, not for judging Arabic-script shaping; ask the owner
  to check one page on a real iPhone.
- **Blank element screenshots in WebKit** are usually a capture timing problem or something fixed on top (a bottom
  menu, a sticky header). Scroll the element into view, wait ~800 ms, and check `document.elementFromPoint` before
  assuming the text is missing.
- **Compare against the full font.** To prove a subset is safe visually, render the same element twice in Chromium,
  once forcing the full font with an injected style (needs `bypass_csp=True` in the Playwright context), and diff.
- **Check both themes**: gold-on-navy and navy-on-ivory change how thin Nastaliq strokes read.
- **Measure, don't eyeball, overflow**: check that `scrollWidth <= innerWidth` at 320 px; long Urdu words don't break.

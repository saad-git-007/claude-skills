# Getting the text itself right

Many "font bugs" are text bugs. Check these first.

## Qur'anic Arabic

- **Allah** in the Bismillah and in verses: lam, lam with **shadda (U+0651)** and **khara / standing alif (U+0670)**,
  then ha: `اللّٰهِ`. The full Bismillah used in production:
  `بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ`. Without the marks the owner reported the word as "cut off at the top".
- **Madd sign**: sources often use U+06E4 (small high madda); DigitalKhatt IndoPak expects U+0653 (maddah above).
  Convert for display only, keep the source text unchanged:
  `const indoPak = (t) => t.replace(/ۤ/g, 'ٓ');`
- Copy verses from a trusted digital mushaf (QUL / Tanzil) rather than retyping; keep the reference (surah:ayah).
- Don't add or "correct" marks yourself; if a source lacks them, ask the owner which mushaf to follow.

## Urdu vs Arabic letters

Urdu text must use Urdu code points, or Nastaliq fonts pick wrong forms and search breaks:

| Urdu | Arabic look-alike |
| --- | --- |
| ی U+06CC (farsi yeh) | ي U+064A |
| ک U+06A9 (keheh) | ك U+0643 |
| ہ U+06C1 (heh goal) | ه U+0647 |
| ے U+06D2 (yeh barree) | (none) |
| ۔ U+06D4 (full stop) | . |

Arabic quoted inside Urdu keeps Arabic code points; mark it `lang="ar"`.

## Direction and mixing

- Block level: `<p lang="ur" dir="rtl">…</p>`. A whole page in Urdu: `<html lang="ur" dir="rtl">`.
- An English word or number inside Urdu, or an Urdu word inside English: wrap it in `<bdi>` (or `dir="auto"`), so
  punctuation and digits land on the right side.
- Detecting Arabic-script paragraphs in user-written Markdown (used in production): a paragraph is RTL if more than
  half its non-space characters are in U+0600–U+06FF:
  ```ts
  const isArabic = (s: string) => (s.match(/[؀-ۿ]/g)?.length ?? 0) > s.replace(/\s/g, '').length * 0.5;
  ```
  Then render it with `class="ar" lang="ar" dir="rtl"` (or `ur` when the site's language is Urdu).
- Numerals: keep the source's digits. Urdu commonly uses Extended Arabic-Indic digits (۰۱۲۳…, U+06F0–06F9); times
  and dates in an English UI stay Latin.

## Screen readers and decorative renderings

- A phrase drawn as an SVG mask has no text: give the element `role="img"` and `aria-label` with the real Arabic,
  plus `lang="ar"`, e.g. `<p class="bismillah" lang="ar" role="img" aria-label="بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ"></p>`.
- Keep a translation or transliteration nearby for readers who don't read the script.

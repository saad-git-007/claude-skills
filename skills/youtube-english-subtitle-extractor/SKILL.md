---
name: youtube-english-subtitle-extractor
description: Find a YouTube video by title and extract its English subtitles. Prefer the video's English transcript/caption track; use PaddleOCR on the frames only when no English transcript is available.
---

# YouTube English Subtitle Extractor

Use this skill when the user gives a YouTube video title or link and wants its English subtitles or transcript extracted. Search for the video, confirm the intended match from title/channel/duration, and produce a local, timestamped transcript artifact.

## Workflow

1. **Find the right video.** Search YouTube using the supplied title (or resolve the supplied link). If multiple plausible matches remain, show the candidates and ask which one before downloading. Use the user's stated channel, date, or other identifying details when available.
2. **Check for an English transcript before OCR.** First inspect YouTube subtitle tracks with `yt-dlp` (`--list-subs`), including manually provided and auto-generated tracks. If needed, use the available browser-use/browser tools to open the video, expand its description if necessary, select **Show transcript**, and inspect the transcript language. A Bangla, Urdu, or other non-English transcript does not substitute for English captions burned into the image.
3. **Download the video.** By default, save a local copy at a resolution sufficient to read the captions (720p is usually enough). If the user explicitly asks only for a transcript or captions and not a video copy, avoid downloading the video unless needed to access the transcript. If the video is unavailable or access-restricted, report that instead of trying to bypass the restriction.
4. **If English captions/transcript are available, download those too and skip OCR.** Save the English track as VTT (or SRT if VTT is unavailable), and also make a clean timestamped TXT when useful. The video may still be retained as requested, but do not process its frames with OCR when a usable English track was found.
5. **If no English track is available, run PaddleOCR on the video frames.** Reuse the local PaddleOCR environment if present; otherwise create a project-local virtual environment so system Python remains intact. CPU installation can use the user's Paddle CPU wheel index (`https://www.paddlepaddle.org.cn/packages/stable/cpu/`) followed by `paddleocr`. PaddlePaddle 3.2.2 worked with PaddleOCR 3.7.0 here; if a newer Paddle wheel errors during inference, try that compatible version in the isolated environment.
6. **Locate and sample the captions before full OCR.** Inspect representative frames at several points to find the on-screen English text and crop tightly around it. For the 1280×720 MTA video processed in this workspace, the caption region was approximately `x=250..1030, y=530..675`; treat that only as a starting point, not a universal crop. Captions can move or be absent. Sample about once per second for ordinary subtitles, use PaddleOCR on CPU unless a compatible accelerator is actually available, and keep original timestamps. A one-second sampling interval gives approximate boundaries and can miss very brief text.
7. **Create reviewable outputs.** Save a timestamped SRT and readable TXT beside the downloaded video, plus raw OCR observations/confidence when useful. Keep the downloaded video and source caption file. Do not silently “correct” uncertain names or wording; retain the OCR text and call out likely recognition errors. Report which source was used (English transcript versus frame OCR), the sampled timing precision, and links to the output files.

## Caption download example

Use the resolved video URL with `yt-dlp` to list caption tracks, then download only English tracks without downloading media, for example:

```bash
yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs 'en,en.*' --sub-format vtt -o '%(title)s.%(ext)s' VIDEO_URL
```

Inspect the resulting files to confirm that the selected track is English. A YouTube transcript panel may expose text not successfully fetched by `yt-dlp`; when browser-use is available, use the panel and save its transcript with timestamps rather than falling through to OCR prematurely.

## OCR quality

PaddleOCR can read outlined English captions well, but motion, decorative overlays, names, and punctuation can cause errors. Check sample outputs before processing the full video; check the beginning, middle, and end afterward. A raw one-frame-per-second reading is not yet a polished transcript: collapse consecutive duplicate observations into caption intervals, preserve changed captions, and do not merge separate sentences merely because they share a few words. Be transparent that OCR timings are approximate and that the transcript may need spot correction.

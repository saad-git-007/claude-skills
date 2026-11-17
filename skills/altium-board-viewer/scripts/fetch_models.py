"""Download the 3D models the board needs into <work>/models (stdlib only, skips files already there).

  kicad/        KiCad official .step + matching .kicad_mod (pin 1 and pad centre fix the rotation)
  maker/        manufacturer STEP files from board.json "maker_urls" (zip archives are unpacked)
  third_party/  anything you drop in by hand (community models, stacked boards)

Only free, no-login sources. Never send personal details (no e-mail in headers).
"""
from __future__ import annotations

import io, json, re, sys, urllib.error, urllib.request, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cfg  # noqa: E402
from kicad_map import kicad_for, urls  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) board-viewer"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


src = cfg.VIEWER.read_text()
D = json.loads(re.search(r'id="data">(.*?)</script>', src, re.S).group(1).replace("<\\/", "</"))
kdir, mdir, tdir = (cfg.MODELS / n for n in ("kicad", "maker", "third_party"))
for d in (kdir, mdir, tdir):
    d.mkdir(parents=True, exist_ok=True)

need, unmapped = {}, {}
for c in D["comps"]:
    if c["fp"] in cfg.MAKER_MAP:
        continue
    tgt = kicad_for(c["d"], c["fp"])
    if tgt:
        need.setdefault(tgt, []).append(c["d"])
    elif c["k"] not in ("hole", "tp"):
        unmapped.setdefault(c["fp"], []).append(c["d"])

missing = []
for tgt, refs in sorted(need.items()):
    name = tgt.split(":")[1]
    for url, out in zip(urls(tgt), (kdir / f"{name}.step", kdir / f"{name}.kicad_mod")):
        if out.exists():
            continue
        try:
            out.write_bytes(get(url)); print("ok  ", out.name)
        except urllib.error.HTTPError as e:
            missing.append((tgt, e.code, refs[:4])); print("FAIL", e.code, url)

for base, url in cfg.MAKER_URLS.items():
    dest = mdir / f"{base}.step"
    if dest.exists() or (tdir / f"{base}.step").exists():
        continue
    try:
        blob = get(url)
    except urllib.error.HTTPError as e:
        print("FAIL", e.code, url); continue
    if blob[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(blob))
        steps = [n for n in z.namelist() if n.lower().endswith((".step", ".stp"))]
        if not steps:
            print("no STEP inside", url); continue
        blob = z.read(max(steps, key=lambda n: z.getinfo(n).file_size))
    dest.write_bytes(blob); print("ok  ", dest.name, len(blob) // 1024, "KB")

have = {p.stem for d in (mdir, tdir) for p in d.glob("*.st*p")}
no_maker = sorted({v if isinstance(v, str) else v[0] for v in cfg.MAKER_MAP.values()} - have)
print("\nKiCad models:", len(need), "| download failures:", len(missing))
for t, code, refs in missing:
    print("  ", code, t, refs, "-> fix the name in kicad_rules")
if no_maker:
    print("maker models still missing (download by hand into", mdir, "):", no_maker)
if unmapped:
    print("no model rule (these show as boxes):")
    for fp, refs in sorted(unmapped.items()):
        print("  ", fp, refs[:6])

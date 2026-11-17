"""Assemble the self-contained 2D viewer HTML from build/data.json + layers.json (stdlib only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cfg  # noqa: E402

safe = lambda s: s.replace("</", "<\\/")
t = (cfg.ASSETS / "viewer_template.html").read_text()
for k, v in {
    "__TITLE__": cfg.TITLE, "__REV__": cfg.REV, "__VIEWER3D__": cfg.VIEWER3D.name, "__PDF_NAME__": cfg.PDF.name,
    "__DATA__": safe((cfg.BUILD / "data.json").read_text()),
    "__LAYERS__": safe((cfg.BUILD / "layers.json").read_text()),
}.items():
    t = t.replace(k, v) if k in ("__TITLE__", "__REV__") else t.replace(k, v, 1)  # once: never inside inserted code
cfg.OUT_DIR.mkdir(parents=True, exist_ok=True)
cfg.VIEWER.write_text(t)
print(cfg.VIEWER, cfg.VIEWER.stat().st_size // 1024, "KB")

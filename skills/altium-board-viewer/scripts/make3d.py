"""Assemble the standalone 3D viewer HTML (stdlib only). Needs make2d.py, conv3d.py and setup.sh vendor files."""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cfg  # noqa: E402

viewer2d = cfg.VIEWER.read_text()
style = re.search(r"<style>(.*?)</style>", (cfg.ASSETS / "viewer_template.html").read_text(), re.S).group(1)
data = re.search(r'<script type="application/json" id="data">(.*?)</script>', viewer2d, re.S).group(1)
layers = re.search(r'<script type="application/json" id="layerdata">(.*?)</script>', viewer2d, re.S).group(1)
safe = lambda s: s.replace("</", "<\\/")
t = (cfg.ASSETS / "viewer3d_template.html").read_text()
for k, v in {
    "__STYLE__": style, "__VIEWER2D__": cfg.VIEWER.name, "__TITLE__": cfg.TITLE, "__REV__": cfg.REV,
    "__DATA__": data, "__LAYERS__": layers,
    "__MODELS__": safe((cfg.OUT3D / "models.json").read_text()),
    "__PLACE__": safe((cfg.OUT3D / "placements.json").read_text()),
    "__SOURCES__": safe((cfg.OUT3D / "sources.json").read_text()),
    "__THREE__": safe((cfg.VENDOR / "three.min.js").read_text()),
    "__ORBIT__": safe((cfg.VENDOR / "OrbitControls.js").read_text()),
    "__GLTF__": safe((cfg.VENDOR / "GLTFLoader.js").read_text()),
}.items():
    t = t.replace(k, v) if k in ("__TITLE__", "__REV__") else t.replace(k, v, 1)  # once: never inside inserted code
out = cfg.VIEWER3D
out.write_text(t)
print(out, out.stat().st_size // 1024, "KB")

"""Shared settings for every step, read from a board.json file.

The config path comes from the BOARD_CONFIG environment variable, or ./board.json.
Relative paths inside it are resolved against the config file's folder.
See ../assets/board.example.json for every key.
"""
from __future__ import annotations

import json, os
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"

_path = Path(os.environ.get("BOARD_CONFIG", "board.json")).expanduser().resolve()
if not _path.exists():
    raise SystemExit(f"board config not found: {_path}  (set BOARD_CONFIG or copy assets/board.example.json)")
C: dict = json.loads(_path.read_text())
BASE = _path.parent


def p(key: str, default: str | None = None) -> Path | None:
    v = C.get(key, default)
    if v is None:
        return None
    q = Path(os.path.expandvars(str(v))).expanduser()
    return q if q.is_absolute() else (BASE / q).resolve()


NAME = C["name"]                                   # file prefix, e.g. "My_Board_REV1"
TITLE = C.get("title", NAME.replace("_", " "))     # shown in the top bar
REV = C.get("rev", "")
PRJ = p("project")
BOM = p("bom")
PNP = p("pnp")
OUT_DIR = p("out_dir", "board_viewer")
WORK = p("work_dir", os.environ.get("ABV_WORK", "~/.cache/altium-board-viewer"))
BUILD = WORK / "build"                              # data.json, layers.json, svg fragments
MODELS = WORK / "models"                            # kicad/, maker/, third_party/
OUT3D = WORK / "out3d"
VENDOR = WORK / "vendor"

VIEWER = OUT_DIR / f"{NAME}_viewer.html"
VIEWER3D = OUT_DIR / f"{NAME}_3D.html"
PDF = OUT_DIR / f"{NAME}_board.pdf"

THICK = float(C.get("board_thickness", 1.6))
BOM_COLS = {"item": 0, "name": 1, "mpn": 2, "mfr": 3, "refs": 6, **C.get("bom_columns", {})}
BOM_HEADER_ROWS = int(C.get("bom_header_rows", 2))
NNP_MARKER = C.get("nnp_marker", "NNP")
BOM_ALIAS: dict = C.get("bom_alias", {})           # designator -> text found in a BOM refs cell
PNP_COMMENT_COL = int(C.get("pnp_comment_col", 10))
MAKER_MAP: dict = C.get("maker_map", {})           # footprint -> STEP basename in models/maker or third_party
MAKER_URLS: dict = C.get("maker_urls", {})         # STEP basename -> direct download URL (no login)
MAKER_SOURCES: dict = C.get("maker_sources", {})   # STEP basename -> credit shown in the 3D detail card
ROT_OVERRIDE: dict = C.get("rot_override", {})     # designator -> extra degrees about Z
KICAD_RULES: list = C.get("kicad_rules", [])       # [prefix, footprint regex, "Lib:Name"], tried first
STACKED: list = C.get("stacked", [])               # boards mounted upside down on a socket (e.g. a Pi)
CHROME = C.get("chrome")                            # optional browser binary for PDF printing


def html_name(path: Path) -> str:
    return path.name


def chrome_bin() -> str:
    import shutil
    for b in ([CHROME] if CHROME else []) + ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                                              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if b and (shutil.which(b) or Path(b).exists()):
            return shutil.which(b) or b
    raise SystemExit("Chrome or Chromium not found: run scripts/setup.sh, or set \"chrome\" in board.json")

#!/usr/bin/env bash
# Run the pipeline for one board.   usage: run.sh <board.json> [2d|pdf|models|3d|all]   (default: 2d pdf)
#   2d      extract with altium_monkey, write <out>/<name>_viewer.html
#   pdf     overview + zoomed zone pages -> <out>/<name>_board.pdf   (needs Chrome)
#   models  download KiCad + maker STEP files (needs 2d)
#   3d      convert models, place parts, write <out>/<name>_3D.html  (needs setup.sh --3d)
# Missing requirements are installed first by setup.sh.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export BOARD_CONFIG="$(realpath "${1:?usage: run.sh <board.json> [2d|pdf|models|3d|all]}")"; shift
STEPS="${*:-2d pdf}"; [ "$STEPS" = all ] && STEPS="2d pdf models 3d"
WORK="${ABV_WORK:-$(python3 -c "import sys; sys.path.insert(0,'$HERE'); import cfg; print(cfg.WORK)")}"
export ABV_WORK="$WORK"

case " $STEPS " in *" 3d "*|*" models "*) bash "$HERE/setup.sh" --3d ;; *) bash "$HERE/setup.sh" ;; esac

for s in $STEPS; do
  echo; echo "── $s"
  case $s in
    2d)     "$WORK/venv-altium/bin/python" "$HERE/build.py" && python3 "$HERE/make2d.py" ;;
    pdf)    python3 "$HERE/make_pdf.py" ;;
    models) python3 "$HERE/fetch_models.py" ;;
    3d)     "$WORK/venv-3d/bin/python" "$HERE/conv3d.py" && python3 "$HERE/make3d.py" ;;
    *) echo "unknown step $s"; exit 2 ;;
  esac
done

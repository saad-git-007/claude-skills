#!/bin/bash
# scripts/perf/ab.sh <label> [pairs=2]   A/B of the working tree against HEAD for the files you changed: each state is
# benchmarked alternately (odd pairs prev first, even pairs cand first) with the dev server serving the working tree, so
# background drift and ordering hit both sides alike. Prints means and medians and the candidate's visual diff against
# <BASELINE> (a bench.mjs output directory; default: the first prev run). Output lands in $OUT (default /dev/shm/perf).
set -e
label=$1; pairs=${2:-2}; repo=$(git rev-parse --show-toplevel); out=${OUT:-/dev/shm/perf}; here=$repo/scripts/perf
cd $repo; files=$(git diff --name-only HEAD); [ -n "$files" ] || { echo "no changes"; exit 1; }
save=$out/cand-$label; rm -rf $save; mkdir -p $save
for f in $files; do mkdir -p $save/$(dirname $f); cp $f $save/$f; done
restore(){ cd $repo; for f in $files; do cp $save/$f $f; done; }
trap restore EXIT
for i in $(seq 1 $pairs); do
  if [ $((i%2)) = 1 ]; then sides="prev cand"; else sides="cand prev"; fi
  for side in $sides; do
    cd $repo; if [ $side = prev ]; then git checkout -q HEAD -- $files; else restore; fi; sleep 4
    node $here/bench.mjs $out/$label-$side-$i 1 | tail -1 | sed "s/^/$side $i /"
  done
done
restore; trap - EXIT
python3 - "$out" "$label" "$pairs" <<'PY'
import json,sys,statistics as st
out,label,pairs=sys.argv[1],sys.argv[2],int(sys.argv[3])
get=lambda side:[json.load(open(f'{out}/{label}-{side}-{i}/bench.json'))['frameMs'] for i in range(1,pairs+1)]
P,C=get('prev'),get('cand'); mp,mc=st.mean(P),st.mean(C); dp,dc=st.median(P),st.median(C)
print(json.dumps(dict(prevMean=round(mp,3),candMean=round(mc,3),meanGainPct=round((mp-mc)/mp*100,2),prevMedian=round(dp,3),candMedian=round(dc,3),medianGainPct=round((dp-dc)/dp*100,2))))
PY
python3 $here/compare.py ${BASELINE:-$out/$label-prev-1} $out/$label-cand-1 | python3 -c "import json,sys; d=json.load(sys.stdin); print('visual', d['worst'], 'ok' if d['ok'] else 'OVER BUDGET')" || true

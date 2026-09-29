#!/usr/bin/env python3
# Needs numpy, Pillow and scikit-image.
"""compare.py <baseline_dir> <candidate_dir>  Visual change per pose: mean absolute difference (% of full scale),
share of pixels off by more than 8/255, and SSIM. Prints JSON; exit 1 if any pose breaks the 1% budget
(mean abs diff > 1% or SSIM < 0.99)."""
import sys, json, glob, os
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
a, b = sys.argv[1], sys.argv[2]
out, bad = {}, False
for f in sorted(glob.glob(f'{a}/*.png')):
    n = os.path.basename(f)[:-4]; g = f'{b}/{n}.png'
    if not os.path.exists(g): continue
    x = np.asarray(Image.open(f).convert('RGB'), np.float32); y = np.asarray(Image.open(g).convert('RGB'), np.float32)
    d = np.abs(x - y); mad = float(d.mean() / 255 * 100); off = float((d.max(2) > 8).mean() * 100)
    s = float(ssim(x, y, channel_axis=2, data_range=255))
    out[n] = dict(meanAbsPct=round(mad, 3), pixelsOffPct=round(off, 2), ssim=round(s, 4))
    bad |= mad > 1 or s < .99
worst = dict(meanAbsPct=max(v['meanAbsPct'] for v in out.values()), ssim=min(v['ssim'] for v in out.values()), pixelsOffPct=max(v['pixelsOffPct'] for v in out.values()))
print(json.dumps(dict(worst=worst, ok=not bad, poses=out)))
sys.exit(1 if bad else 0)

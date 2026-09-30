#!/usr/bin/env python3
"""Downscale every recorded frame to 1920x1080 (Lanczos). Needed when frames were rendered at --dsf 2/3 and/or cropped
by a zoom track: the crops come out at different sizes, and scaling them down from the high-resolution source is what
keeps zoomed UI text sharp.   usage: post.py <frames_in> <frames_out> [W H]"""
import sys, glob, os
from multiprocessing import Pool
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1920, 1080)
os.makedirs(dst, exist_ok=True)
def work(f):
    im = Image.open(f).convert('RGB')
    if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
    im.save(os.path.join(dst, os.path.basename(f)), quality=97, subsampling=0)
    return im.size
if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(src, 'f*.jpg')))
    with Pool(os.cpu_count()) as p: sizes = p.map(work, files, chunksize=8)
    print(len(files), 'frames ->', set(sizes))

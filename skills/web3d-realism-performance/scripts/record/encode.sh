#!/bin/bash
# encode.sh <frames_dir> <out.mp4> [audio.m4a] [crf]
# H.264 High, yuv420p, bt709, faststart: plays everywhere, including X/Twitter. A silent AAC track is added when there
# is no audio (some uploaders and players prefer a file that has one). Check the size: chat/upload limits are often
# 25-30 MB, so make a lighter copy with `-b:v 6000k -maxrate 8M -bufsize 16M` instead of `-crf`.
set -e
IN=$1; OUT=$2; AUD=${3:-}; CRF=${4:-19}
[ -n "$AUD" ] && AIN="-i $AUD" || AIN="-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000"
ffmpeg -y -hide_banner -loglevel error -framerate 30 -i "$IN/f%05d.jpg" $AIN -shortest \
  -c:v libx264 -preset slow -crf "$CRF" -profile:v high -level 4.2 -pix_fmt yuv420p -maxrate 14M -bufsize 28M \
  -vf "scale=1920:1080:flags=lanczos,format=yuv420p" -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -r 30 -g 60 \
  -c:a aac -b:a 128k -movflags +faststart "$OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt -show_entries format=duration,size -of default=nw=1 "$OUT"

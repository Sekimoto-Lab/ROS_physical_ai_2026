#!/bin/bash
# デスクトップの一部を録画する。使い方: record.sh <秒数> [出力ファイル]
# 範囲は Gazebo のウィンドウを左上 (0,30) に 1600x1000 で置いたときの 3D 表示部分（16:9）
SEC=${1:-60}
OUT=${2:-$HOME/ros2_ws/demo.mp4}
ffmpeg -y -loglevel error -f x11grab -framerate 30 -video_size 1180x664 -i ${DISPLAY:-:1}.0+0,240 \
  -t "$SEC" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p "$OUT"
echo "保存しました: $OUT"

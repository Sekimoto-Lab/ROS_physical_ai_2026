#!/bin/bash
# Gazebo のカメラを、斜め前から板とアームが入る位置に動かす（動画撮影用）
source /opt/ros/jazzy/setup.bash
gz service -s /gui/move_to/pose --reqtype gz.msgs.GUICamera --reptype gz.msgs.Boolean --timeout 2000 \
  --req 'pose: {position: {x: 0.95, y: -1.05, z: 0.6}, orientation: {x: -0.1458, y: 0.0921, z: 0.8329, w: 0.5259}}'

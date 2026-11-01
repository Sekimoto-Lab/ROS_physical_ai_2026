#!/bin/bash
# 板とピザを最初の位置に置き直す（アームは動かさない。板に近いときは先にアームをどけておく）
source /opt/ros/jazzy/setup.bash
M=$(ros2 pkg prefix pizza_cut_demo)/share/pizza_cut_demo/models
gz topic -t /board/detach -m gz.msgs.Empty -p ''
for m in pizza board; do
  gz service -s /world/empty/remove --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean \
    --timeout 2000 --req "name: \"$m\" type: MODEL" > /dev/null
done
ros2 run ros_gz_sim create -file $M/board.sdf -name board -x 0.60 -y 0.0 -z 0.1085 > /dev/null 2>&1
sleep 1
# 板は現れた瞬間に手首へ固定されるので、すぐ解除する
gz topic -t /board/detach -m gz.msgs.Empty -p ''
ros2 run ros_gz_sim create -file $M/pizza.sdf -name pizza -x 0.60 -y 0.0 -z 0.125 > /dev/null 2>&1

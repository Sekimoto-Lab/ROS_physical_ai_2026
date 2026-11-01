#!/bin/bash
# 板とピザを最初の位置に置き直し、MoveIt の障害物も更新する。
# 先に板とピザを消し、アームを「真上」→「構え」の順に動かしてから置くので、アームと板が重ならない。
source /opt/ros/jazzy/setup.bash
M=$(cd "$(dirname "$0")/../models" && pwd)
J="[shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint]"
A=/scaled_joint_trajectory_controller/follow_joint_trajectory
T=control_msgs/action/FollowJointTrajectory

gz topic -t /board/detach -m gz.msgs.Empty -p ''
for m in pizza board; do
  gz service -s /world/empty/remove --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean \
    --timeout 2000 --req "name: \"$m\" type: MODEL" > /dev/null
done

# 今の向きのまま腕を真上に伸ばしてから、前方・手先下向きの構えへ
PAN=$(python3 - <<'PY'
import rclpy
from sensor_msgs.msg import JointState
rclpy.init(); n = rclpy.create_node('read_pan'); got = []
n.create_subscription(JointState, '/joint_states', got.append, 1)
while not got:
    rclpy.spin_once(n, timeout_sec=0.5)
print(dict(zip(got[0].name, got[0].position))['shoulder_pan_joint'])
PY
)
ros2 action send_goal $A $T "{trajectory: {joint_names: $J, points: [{positions: [${PAN:-0.0}, -1.57, 0.0, -1.57, -1.57, 0.0], time_from_start: {sec: 4}}]}}" > /dev/null
ros2 action send_goal $A $T "{trajectory: {joint_names: $J, points: [{positions: [0.0, -1.57, 1.57, -1.57, -1.57, 0.0], time_from_start: {sec: 4}}]}}" > /dev/null

ros2 run ros_gz_sim create -file $M/board.sdf -name board -x 0.60 -y 0.0 -z 0.1085 > /dev/null 2>&1
sleep 1
# 板は現れた瞬間に手首へ固定されるので、すぐ解除する
gz topic -t /board/detach -m gz.msgs.Empty -p ''
ros2 run ros_gz_sim create -file $M/pizza.sdf -name pizza -x 0.60 -y 0.0 -z 0.125 > /dev/null 2>&1
sleep 2
# MoveIt の障害物の位置も置き直した位置に合わせる
python3 "$(dirname "$0")/update_scene.py"

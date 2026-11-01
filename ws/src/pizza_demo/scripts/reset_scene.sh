#!/bin/bash
# 板とピザを最初の位置に置き直し、MoveIt の障害物も更新する。
# 先に板とピザをよけて、アームを「真上」→「構え」の順に動かしてから置くので、アームと板が重ならない。
source /opt/ros/jazzy/setup.bash
J="[shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint]"
A=/scaled_joint_trajectory_controller/follow_joint_trajectory
T=control_msgs/action/FollowJointTrajectory

# 板を手首から外し、少し待ってから動かす（板を消して出し直すと物理エンジンが壊れるので、位置だけ戻す）
gz topic -t /board/detach -m gz.msgs.Empty -p ''
sleep 1
# いったん板とピザを離れた場所へよけて、アームの通り道を空ける
set_pose() {
  gz service -s /world/empty/set_pose --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 2000 \
    --req "name: \"$1\", position: {x: $2, y: $3, z: $4}, orientation: {w: 1}" > /dev/null
}
set_pose pizza 0 2.0 0.006
set_pose board 0 2.5 0.0075

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

set_pose board 0.60 0.0 0.1080
sleep 1
set_pose pizza 0.60 0.0 0.1220
sleep 2
# MoveIt の障害物の位置も置き直した位置に合わせる
python3 "$(dirname "$0")/update_scene.py"

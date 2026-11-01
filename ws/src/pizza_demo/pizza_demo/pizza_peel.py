# ピザ見習い：板（ピール）にピザを載せて水平のまま奥へ運び、板を素早く引いてピザだけを台に残す
#
# つかむ姿勢は作者が RViz で教えた関節角（GRASP_JOINTS）を使う。
# 残りの姿勢は、つかんだときの手先の向きを保ったまま、手先の位置だけをずらして求める。
# 板は固定（attach）した瞬間の位置関係で手首にくっつくので、手先の向きが変わらなければ板は水平のまま動く。
#
# 使い方: ros2 run pizza_demo pizza_peel --pull-time 0.6
import argparse
import csv
import math
import os
import re
import subprocess
import time

from ament_index_python.packages import get_package_share_directory
import rclpy
from control_msgs.action import FollowJointTrajectory
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import RobotState
from moveit_msgs.srv import GetCartesianPath, GetPositionFK, GetPositionIK
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty
from trajectory_msgs.msg import JointTrajectoryPoint

FRAME = 'base_link'
GROUP = 'ur_manipulator'
JOINTS = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
          'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']

# 作者が RViz で教えた、持ち手をつかむ姿勢（度）
GRASP_JOINTS = [math.radians(d) for d in (-71, -82, 141, -71, -44, -263)]

APPROACH = 0.08   # つかむ前に、近づく方向の手前で待つ距離 [m]
LIFT = 0.05       # 板を持ち上げる高さ（手首が台に当たらないように）[m]
PUSH = 0.30       # 板を奥（+x）へ運ぶ距離 [m]
PULL = 0.45       # 板を手前（-x）へ引く距離 [m]
STAND_TOP = 0.10  # 台の上面の高さ [m]
PIZZA_HALF = 0.006


class PizzaPeel(Node):

    def __init__(self):
        super().__init__('pizza_peel')
        self.joint_state = None
        self.create_subscription(JointState, '/joint_states', self.on_joints, 10)
        self.fk = self.create_client(GetPositionFK, '/compute_fk')
        self.ik = self.create_client(GetPositionIK, '/compute_ik')
        self.cartesian = self.create_client(GetCartesianPath, '/compute_cartesian_path')
        self.execute = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self.follow = ActionClient(
            self, FollowJointTrajectory,
            '/scaled_joint_trajectory_controller/follow_joint_trajectory')
        self.attach_pub = self.create_publisher(Empty, '/board/attach', 1)
        self.detach_pub = self.create_publisher(Empty, '/board/detach', 1)

    def on_joints(self, msg):
        self.joint_state = msg

    def wait_ready(self):
        for c in (self.fk, self.ik, self.cartesian):
            c.wait_for_service()
        self.execute.wait_for_server()
        self.follow.wait_for_server()
        while self.joint_state is None:
            rclpy.spin_once(self, timeout_sec=0.1)

    # ---- 通信の下回り ----
    def call(self, client, req):
        fut = client.call_async(req)
        rclpy.spin_until_future_complete(self, fut)
        return fut.result()

    def run_action(self, client, goal):
        fut = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        res = fut.result().get_result_async()
        rclpy.spin_until_future_complete(self, res)
        return res.result().result

    def pause(self, sec):
        end = time.time() + sec
        while time.time() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def state(self, positions=None):
        rclpy.spin_once(self, timeout_sec=0.1)
        s = RobotState()
        if positions is None:
            s.joint_state = self.joint_state
        else:
            s.joint_state.name = JOINTS
            s.joint_state.position = list(positions)
        return s

    # ---- 姿勢の計算 ----
    def tool_pose(self, positions):
        """関節角から tool0 の姿勢を求める。"""
        req = GetPositionFK.Request()
        req.header.frame_id = FRAME
        req.fk_link_names = ['tool0']
        req.robot_state = self.state(positions)
        return self.call(self.fk, req).pose_stamped[0].pose

    def solve_ik(self, pose, seed):
        req = GetPositionIK.Request()
        req.ik_request.group_name = GROUP
        req.ik_request.robot_state = self.state(seed)
        req.ik_request.pose_stamped.header.frame_id = FRAME
        req.ik_request.pose_stamped.pose = pose
        req.ik_request.avoid_collisions = False
        req.ik_request.timeout.sec = 2
        res = self.call(self.ik, req)
        if res.error_code.val != 1:
            raise RuntimeError(f'IK に失敗しました（code {res.error_code.val}）')
        sol = dict(zip(res.solution.joint_state.name, res.solution.joint_state.position))
        return [sol[j] for j in JOINTS]

    # ---- 動かす ----
    def move_joints(self, positions, seconds):
        """関節空間でまっすぐ動かす（板を持っていないときの大きな移動用）。"""
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = JOINTS
        pt = JointTrajectoryPoint(positions=list(positions))
        pt.time_from_start.sec = int(seconds)
        pt.time_from_start.nanosec = int((seconds % 1) * 1e9)
        goal.trajectory.points = [pt]
        self.run_action(self.follow, goal)

    def line_path(self, target, speed):
        """今の姿勢から target まで、手先の向きを保ったまま直線で動く軌道を作る。"""
        req = GetCartesianPath.Request()
        req.header.frame_id = FRAME
        req.start_state = self.state()
        req.group_name = GROUP
        req.waypoints = [target]
        req.max_step = 0.005
        req.avoid_collisions = False
        req.max_velocity_scaling_factor = speed
        req.max_acceleration_scaling_factor = speed
        res = self.call(self.cartesian, req)
        if res.fraction < 0.99:
            raise RuntimeError(f'直線の経路を最後まで作れませんでした（{res.fraction:.0%}）')
        return res.solution.joint_trajectory

    def line_to(self, target, speed=0.2):
        goal = ExecuteTrajectory.Goal()
        goal.trajectory.joint_trajectory = self.line_path(target, speed)
        result = self.run_action(self.execute, goal)
        if result.error_code.val != 1:
            raise RuntimeError(f'動作が途中で止まりました（code {result.error_code.val}）')

    def line_in_time(self, target, seconds):
        """直線の軌道を、全体がちょうど seconds 秒になるよう時間を伸び縮みさせて送る（板を引く動き）。"""
        traj = self.line_path(target, 1.0)
        last = traj.points[-1].time_from_start
        total = last.sec + last.nanosec * 1e-9
        k = seconds / total
        for p in traj.points:
            t = (p.time_from_start.sec + p.time_from_start.nanosec * 1e-9) * k
            p.time_from_start.sec = int(t)
            p.time_from_start.nanosec = int((t % 1) * 1e9)
            p.velocities = [v / k for v in p.velocities]
            p.accelerations = [a / (k * k) for a in p.accelerations]
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        return self.run_action(self.follow, goal)


def shifted(pose, dx=0.0, dy=0.0, dz=0.0):
    p = type(pose)()
    p.position.x = pose.position.x + dx
    p.position.y = pose.position.y + dy
    p.position.z = pose.position.z + dz
    p.orientation = pose.orientation
    return p


def approach_dir(pose):
    """tool0 の z 軸（グリッパーが向いている方向）。"""
    q = pose.orientation
    x, y, z, w = q.x, q.y, q.z, q.w
    return (2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y))


def pizza_position():
    out = subprocess.run(['gz', 'topic', '-e', '-t', '/world/empty/pose/info', '-n', '1'],
                         capture_output=True, text=True, timeout=10).stdout
    block = out.split('name: "pizza"')[1]
    pos = re.search(r'position \{([^}]*)\}', block).group(1)
    d = dict(re.findall(r'(\w+): ([-\d.e]+)', pos))
    return [float(d.get(k, 0.0)) for k in 'xyz']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pull-time', type=float, default=0.6,
                        help=f'板を {PULL * 100:.0f} cm 引くのにかける秒数')
    parser.add_argument('--no-reset', action='store_true', help='最初に板とピザを置き直さない')
    parser.add_argument('--csv', default=os.path.expanduser('~/ros2_ws/pull_results.csv'),
                        help='結果を追記するファイル')
    args, _ = parser.parse_known_args()

    if not args.no_reset:
        script = os.path.join(get_package_share_directory('pizza_demo'), 'scripts', 'reset_scene.sh')
        subprocess.run(['bash', script], check=True)

    rclpy.init()
    node = PizzaPeel()
    node.wait_ready()
    log = node.get_logger().info

    grasp = node.tool_pose(GRASP_JOINTS)
    a = approach_dir(grasp)
    pre = shifted(grasp, -a[0] * APPROACH, -a[1] * APPROACH, -a[2] * APPROACH)
    above = shifted(pre, dz=0.15)

    log('持ち手の手前・上へ')
    node.move_joints(node.solve_ik(above, GRASP_JOINTS), 5.0)
    node.line_to(pre, speed=0.2)
    log('持ち手まで近づく')
    node.line_to(grasp, speed=0.1)
    node.pause(0.5)

    log('つかむ（板を手首に固定）')
    node.attach_pub.publish(Empty())
    node.pause(1.0)

    log('持ち上げて、水平のまま奥へ運ぶ')
    up = shifted(grasp, dz=LIFT)
    node.line_to(up, speed=0.05)
    far_up = shifted(up, dx=PUSH)
    node.line_to(far_up, speed=0.05)
    far = shifted(grasp, dx=PUSH, dz=0.003)
    node.line_to(far, speed=0.05)
    node.pause(1.0)
    before = pizza_position()

    log(f'板を素早く引く（{PULL * 100:.0f} cm を {args.pull_time:.2f} 秒）')
    result = node.line_in_time(shifted(far, dx=-PULL), args.pull_time)
    ok_motion = result.error_code == 0
    node.pause(2.0)
    after = pizza_position()

    log('板を持ったまま持ち上げる')
    node.line_to(shifted(far, dx=-PULL, dz=LIFT), speed=0.1)

    drag = before[0] - after[0]
    on_stand = abs(after[2] - (STAND_TOP + PIZZA_HALF)) < 0.004
    speed = PULL / args.pull_time
    log(f'結果: 引く時間 {args.pull_time:.2f} s（平均 {speed:.2f} m/s）、'
        f'ピザが引きずられた距離 {drag * 100:.1f} cm、'
        f'ピザの高さ {after[2]:.3f} m → {"台の上に残った" if on_stand else "台に残らなかった"}'
        f'{"" if ok_motion else "（アームの動作が途中で止まった）"}')

    new = not os.path.exists(args.csv)
    with open(args.csv, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['pull_time_s', 'mean_speed_mps', 'drag_cm', 'pizza_x', 'pizza_y', 'pizza_z',
                        'on_stand', 'motion_completed'])
        w.writerow([args.pull_time, round(speed, 3), round(drag * 100, 2),
                    *[round(v, 4) for v in after], on_stand, ok_motion])
    log(f'結果を {args.csv} に追記しました')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# Gazebo 上の台・板・ピザの今の位置を読み、MoveIt の障害物（planning scene）として登録する。
# 板やピザを動かしたあとは、もう一度実行すると位置が更新される。
import re
import subprocess

import rclpy
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, PlanningScene
from moveit_msgs.srv import ApplyPlanningScene
from shape_msgs.msg import SolidPrimitive

FRAME = 'base_link'


def gazebo_poses():
    """/world/empty/pose/info を 1 回読み、モデル名 → (位置, 姿勢) の辞書を返す。"""
    out = subprocess.run(['gz', 'topic', '-e', '-t', '/world/empty/pose/info', '-n', '1'],
                         capture_output=True, text=True, timeout=10).stdout
    poses = {}
    for block in out.split('pose {')[1:]:
        name = re.search(r'name: "([^"]+)"', block)
        if not name:
            continue
        pos = re.search(r'position \{([^}]*)\}', block)
        ori = re.search(r'orientation \{([^}]*)\}', block)

        def values(m, keys, default):
            d = dict(re.findall(r'(\w+): ([-\d.e]+)', m.group(1))) if m else {}
            return [float(d.get(k, v)) for k, v in zip(keys, default)]
        poses[name.group(1)] = (values(pos, 'xyz', [0, 0, 0]),
                                values(ori, 'xyzw', [0, 0, 0, 1]))
    return poses


def make_pose(xyz, q):
    p = Pose()
    p.position.x, p.position.y, p.position.z = map(float, xyz)
    p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w = map(float, q)
    return p


def box(size, xyz=(0, 0, 0)):
    prim = SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size))
    return prim, make_pose(xyz, (0, 0, 0, 1))


def cylinder(height, radius):
    prim = SolidPrimitive(type=SolidPrimitive.CYLINDER, dimensions=[height, radius])
    return prim, make_pose((0, 0, 0), (0, 0, 0, 1))


def collision_object(name, pose, parts):
    """parts はモデル原点から見た (形, 位置) の組。寸法は models/*.sdf と同じにする。"""
    obj = CollisionObject()
    obj.header.frame_id = FRAME
    obj.id = name
    obj.pose = make_pose(*pose)
    for prim, local in parts:
        obj.primitives.append(prim)
        obj.primitive_poses.append(local)
    obj.operation = CollisionObject.ADD
    return obj


def main():
    poses = gazebo_poses()
    shapes = {
        'stand': [box((0.90, 0.30, 0.10))],
        # 板と持ち手（持ち手は板の中心から -x へ 27.5 cm）
        'board': [box((0.40, 0.40, 0.015)), box((0.15, 0.03, 0.02), (-0.275, 0, 0.0025))],
        'pizza': [cylinder(0.012, 0.15)],
    }
    scene = PlanningScene(is_diff=True)
    for name, parts in shapes.items():
        if name in poses:
            scene.world.collision_objects.append(collision_object(name, poses[name], parts))
            print(f'{name}: x={poses[name][0][0]:.3f} y={poses[name][0][1]:.3f} z={poses[name][0][2]:.3f}')
        else:
            print(f'{name}: Gazebo に見つからないので飛ばしました')

    rclpy.init()
    node = rclpy.create_node('update_scene')
    client = node.create_client(ApplyPlanningScene, '/apply_planning_scene')
    if not client.wait_for_service(timeout_sec=10.0):
        print('move_group が見つかりません（シミュレーションを起動していますか？）')
        return
    future = client.call_async(ApplyPlanningScene.Request(scene=scene))
    rclpy.spin_until_future_complete(node, future)
    print('MoveIt に登録しました' if future.result().success else '登録に失敗しました')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

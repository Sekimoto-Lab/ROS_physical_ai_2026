# グリッパー付き UR5e（Gazebo＋MoveIt）を起動し、台・板・ピザを置く
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, ExecuteProcess,
                            IncludeLaunchDescription, TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('pizza_demo')
    models = os.path.join(pkg, 'models')
    ur_sim = os.path.join(get_package_share_directory('ur_simulation_gz'),
                          'launch', 'ur_sim_moveit.launch.py')

    # 変換プレートのメッシュは package:// で書かれているので、Gazebo が探せるようにする
    resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', '/opt/ros/jazzy/share')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(ur_sim),
        launch_arguments={
            'ur_type': 'ur5e',
            'description_file': os.path.join(pkg, 'urdf', 'ur5e_gripper.urdf.xacro'),
            # 板を素早く引くとき途中で止まらないよう、経路追従の許容誤差を外した設定
            'controllers_file': os.path.join(pkg, 'config', 'ur_controllers.yaml'),
        }.items())

    def spawn(name, x, y, z):
        return Node(package='ros_gz_sim', executable='create', output='screen',
                    arguments=['-file', os.path.join(models, name + '.sdf'),
                               '-name', name, '-x', str(x), '-y', str(y), '-z', str(z)])

    # 台（高さ 10 cm、x=0.45〜1.35）の上に板、板の上にピザ。板の持ち手はロボット側に台からはみ出す
    spawn_objects = TimerAction(period=8.0, actions=[
        spawn('stand', 0.90, 0.0, 0.05),
        spawn('board', 0.60, 0.0, 0.1085),
        spawn('pizza', 0.60, 0.0, 0.125),
    ])

    # 板は現れた瞬間に手首へ固定されるので、すぐ解除して台の上に置いた状態にする
    detach = TimerAction(period=12.0, actions=[
        ExecuteProcess(cmd=['gz', 'topic', '-t', '/board/detach',
                            '-m', 'gz.msgs.Empty', '-p', ''], output='screen'),
    ])

    # 台・板・ピザを MoveIt の障害物として登録する（RViz で計画した動きが板を突き抜けないように）
    scene = TimerAction(period=15.0, actions=[
        ExecuteProcess(cmd=['python3', os.path.join(pkg, 'scripts', 'update_scene.py')],
                       output='screen'),
    ])

    # ROS 2 から固定・解除できるようにする（std_msgs/Empty を送る）
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
                  arguments=['/board/attach@std_msgs/msg/Empty]gz.msgs.Empty',
                             '/board/detach@std_msgs/msg/Empty]gz.msgs.Empty',
                             '/board/state@std_msgs/msg/String[gz.msgs.StringMsg'])

    return LaunchDescription([resource_path, sim, spawn_objects, detach, scene, bridge])

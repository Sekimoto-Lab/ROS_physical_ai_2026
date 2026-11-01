# Physical AI 2026 応用編1 最終課題：ピザ見習い

<!-- 課題の概要・目的・工夫した点は、ここに作者が記入する -->

## 環境

Docker 上の ROS 2 Jazzy で動く。GUI はブラウザ（noVNC）で操作する。

- ベースイメージ: [`tiryoh/ros2-desktop-vnc:jazzy`](https://hub.docker.com/r/tiryoh/ros2-desktop-vnc)
- 追加パッケージ（`docker/Dockerfile`）:
  - シミュレータ: Gazebo Sim（`ros_gz`）
  - アーム: UR5e（`ur_simulation_gz`、`ur_moveit_config`、`ur_robot_driver`）
  - 軌道計画: MoveIt 2（`moveit`、`moveit_py`）
  - 制御: `gz_ros2_control`、`ros2_controllers`、`ros2controlcli`
  - グリッパー: Robotiq 2F-85（`robotiq_description`、`robotiq_controllers`）

### 起動

```bash
docker compose up -d --build
```

ブラウザで http://localhost:6080 を開いて「接続」を押す。デスクトップの端末で次を実行する。

```bash
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch pizza_cut_demo pizza_sim.launch.py
```

Gazebo と RViz（MoveIt）が開き、グリッパー付きの UR5e と、台・持ち手付きの板・ピザが置かれる。

- 板の固定・解除: `ros2 topic pub --once /board/attach std_msgs/msg/Empty` ／ `/board/detach`
  （グリッパーは見た目のみ。つかむ動作は、板を手首に固定することで表している）
- 台・板・ピザは、起動時に MoveIt の障害物として登録される。板を動かしたあとは `python3 scripts/update_scene.py` で位置を更新する
- 板とピザを置き直す（アームを退避させ、障害物も更新する）: `bash $(ros2 pkg prefix pizza_cut_demo)/share/pizza_cut_demo/scripts/reset_scene.sh`
- 撮影用のカメラ位置: `scripts/camera_view.sh`、録画: `scripts/record.sh <秒数> [出力ファイル]`

自分のパッケージは `ws/src/` に置く。コンテナ内の `~/ros2_ws` から見えるので、そこで `colcon build` する。

### 終了

```bash
docker compose down
```

## 生成AIの利用について

環境構成ファイル（`compose.yaml`、`docker/Dockerfile`）と、この README の「環境」の節は、生成AI（Claude）の支援を受けて作成した。ピザ・板・台のモデル（`ws/src/pizza_cut_demo/models/`）、グリッパー付きアームの記述（`urdf/ur5e_gripper.urdf.xacro`）、起動ファイル（`launch/pizza_sim.launch.py`）、補助スクリプト（`scripts/`）、`setup.py` のインストール設定も生成AIで作成し、作者が内容を確認した。アームの動作（板をつかんで動かすプログラム）は作者が実装した。

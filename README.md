# Physical AI 2026 応用編1 最終課題：ピザカットロボット

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
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py ur_type:=ur5e
```

自分のパッケージは `ws/src/` に置く。コンテナ内の `~/ros2_ws` から見えるので、そこで `colcon build` する。

### 終了

```bash
docker compose down
```

## 生成AIの利用について

環境構成ファイル（`compose.yaml`、`docker/Dockerfile`）と、この README の「環境」の節は、生成AI（Claude）の支援を受けて作成した。ピザのモデル（`ws/src/pizza_cut_demo/models/pizza.sdf`）も生成AIで作成し、作者が内容を確認した。それ以外の `ws/src/` 以下は作者が実装した。

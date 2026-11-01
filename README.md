# Physical AI 2026 応用編1 最終課題：ピザ見習い

ピザピール（持ち手付きの板）にピザを載せ、水平を保ったまま奥へ運び、板だけを素早く手前へ引き抜いてピザを台の上に残すロボットアーム。
ROS 2 Jazzy・Gazebo Sim・MoveIt 2 上の UR5e で動かす。板を引く速さを変えて、成否がどう変わるかも調べた。

- 動画: https://youtu.be/M2a1arvSEG8
- 説明資料: [`report/説明資料_PAI最終課題.pdf`](report/)（原稿は同じ名前の `.docx`）

## 動作の流れ

1. 持ち手をつかむ姿勢（作者が RViz で教えた関節角）の手前・上へ移動し、持ち手まで近づく
2. 板を手首に固定する（つかむ）
3. 5 cm 持ち上げ、手先の向きを保ったまま 30 cm 奥へ運び、台の上に下ろす（板は水平のまま）
4. 板を 45 cm 手前へ、指定した時間で直線的に引く
5. ピザが引きずられた距離と、台に残ったかを記録する

手先の向きを一定に保つ直線補間（MoveIt の Cartesian path）で動かすので、手首に固定された板は常に水平に保たれる。
板の上面は打ち粉をした板を想定して摩擦係数を 0.1 にしている。

## 結果（板を 45 cm 引く時間と成否）

| 引く時間 [s] | 平均速度 [m/s] | ピザが引きずられた距離 [cm] | 結果 |
|---|---|---|---|
| 1.0 | 0.45 | 31.1 | × 板に載ったまま運ばれた |
| 0.7 | 0.64 | 8.7 | ○ 台に残った |
| 0.6 | 0.75 | 19.8 | × 台の手前の端から落ちた |
| 0.5 | 0.90 | 5.3 | ○ 台に残った |
| 0.4 | 1.12 | 9.4 | ○ 台に残った |

ゆっくり引くとピザは摩擦で板と一緒に動き（引きずられる距離はおよそ ½μgT²）、0.7 秒以下では台に残った。
考察は説明資料にまとめた。

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
ros2 launch pizza_demo pizza_sim.launch.py
```

Gazebo と RViz（MoveIt）が開き、グリッパー付きの UR5e と、台・持ち手付きの板・ピザが置かれる。

### デモの実行

別の端末で（板とピザは自動で置き直される）:

```bash
source ~/ros2_ws/install/setup.bash
ros2 run pizza_demo pizza_peel --pull-time 0.5
```

`--pull-time` は板を 45 cm 引くのにかける秒数。結果は `~/ros2_ws/pull_results.csv` に追記される。

### 補助

- 板の固定・解除: `ros2 topic pub --once /board/attach std_msgs/msg/Empty` ／ `/board/detach`
  （グリッパーは見た目のみ。つかむ動作は、板を手首に固定することで表している）
- 台・板・ピザは、起動時に MoveIt の障害物として登録される。板を動かしたあとは `python3 scripts/update_scene.py` で位置を更新する
- 板とピザを置き直す（アームを退避させ、障害物も更新する）: `bash $(ros2 pkg prefix pizza_demo)/share/pizza_demo/scripts/reset_scene.sh`
- 撮影用のカメラ位置: `scripts/camera_view.sh`、録画: `scripts/record.sh <秒数> [出力ファイル]`
- 制御器の設定（`config/ur_controllers.yaml`）は、素早く引く動きで途中停止しないよう、経路追従の許容誤差を外している

### 説明資料

原稿は `report/説明資料_PAI最終課題.docx`（作者が編集したもの）で、PDF はそれを変換したもの。
最初の版は `python3 report/build_report.py` で `report/pull_results.csv` から表とグラフを作って生成した（`report_template.html` が元の文章）。

### 終了

```bash
docker compose down
```

## 生成AIの利用について

環境構成ファイル（`compose.yaml`、`docker/Dockerfile`）、ピザ・板・台のモデル（`ws/src/pizza_demo/models/`）、グリッパー付きアームの記述（`urdf/ur5e_gripper.urdf.xacro`）、起動ファイル、制御器の設定、補助スクリプト（`scripts/`）、動作プログラム `pizza_peel`（作者が RViz で教えたつかむ姿勢を起点に、残りの姿勢を計算するもの）、実験の実行、説明資料（`report/`）、この README は、生成AI（Claude）の支援を受けて作成した。
課題の設定、つかむ姿勢の教示、実験条件の指定は作者が行い、内容は作者が確認した。

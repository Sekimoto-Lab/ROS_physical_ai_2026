# 汎用 ROS 2 Jazzy 環境（講座の教材は使わず、公開イメージ・公開パッケージのみで構成）
# ブラウザ（noVNC, http://localhost:6080）でデスクトップを操作できる
FROM tiryoh/ros2-desktop-vnc:jazzy

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-ros-gz \
        ros-jazzy-turtlebot3-simulations \
        ros-jazzy-teleop-twist-keyboard \
        python3-colcon-common-extensions \
        ros-jazzy-moveit \
        ros-jazzy-moveit-py \
        ros-jazzy-ur-simulation-gz \
        ros-jazzy-ur-moveit-config \
        ros-jazzy-gz-ros2-control \
        ros-jazzy-ros2-controllers \
    && rm -rf /var/lib/apt/lists/*

# グリッパー（Robotiq 2F-85）。上の層のキャッシュを活かすため別の RUN にしている
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-robotiq-description \
        ros-jazzy-robotiq-controllers \
        ros-jazzy-ur-robot-driver \
        ros-jazzy-ros2controlcli \
    && rm -rf /var/lib/apt/lists/*

# 端末を開いたら ROS 2 とワークスペースが使えるようにする
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /home/ubuntu/.bashrc \
 && echo '[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash' >> /home/ubuntu/.bashrc \
 && echo 'export TURTLEBOT3_MODEL=burger' >> /home/ubuntu/.bashrc

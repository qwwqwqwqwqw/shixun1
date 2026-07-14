#!/bin/bash
# aliases.sh — 项目全部节点快捷别名
# 用法: source ~/yahboomcar_ros2_ws/yahboomcar_ws/src/guide_pkg/launch/aliases.sh

WS=~/yahboomcar_ros2_ws/yahboomcar_ws
BIN=$WS/install/guide_pkg/bin
SER=$WS/install/aiserver_pkg/bin
VIS=$WS/vision

# ── 核心节点（ROS2 编译包）──
alias c1="$BIN/guide_node"              # 导航核心
alias c2="$BIN/arrival_fusion"          # 融合确认
alias c3="$SER/aiserver_node"           # TCP 服务
alias c4="$BIN/joystick_ctrl"           # 摇杆/键盘
alias c5="c1 & c2 & wait"              # 一键导航+融合

# ── 视觉节点（Python 脚本）──
alias v1="python3 $VIS/face/face_recognizer.py"         # 人脸识别
alias v2="python3 $VIS/doorplate/doorplate_detector.py" # 门牌识别
alias v3="python3 $VIS/voice/voice_player.py"           # 语音模块
alias va="v1 & v2 & v3 & wait"                         # 一键视觉

# ── 硬件 ──
alias ca="ros2 launch astra_camera astra.launch.xml"    # 深度相机
alias cb="ros2 launch astra_camera astra_pro.launch.xml" # RGB相机(视觉用)

# ── 一键全系统 ──
alias all="c1 & c2 & c3 & c4 & v1 & v2 & v3 & wait"

echo "别 名: c1..c5(核心) | v1..v3(视觉) | ca/cb(相机) | all(全启动)"

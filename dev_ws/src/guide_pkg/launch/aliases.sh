#!/bin/bash
# aliases.sh — 项目节点快捷别名（source 后生效）
# 用法: source ~/yahboomcar_ros2_ws/yahboomcar_ws/src/guide_pkg/launch/aliases.sh

BIN=~/yahboomcar_ros2_ws/yahboomcar_ws/install/guide_pkg/bin
SER=~/yahboomcar_ros2_ws/yahboomcar_ws/install/aiserver_pkg/bin

alias c1="$BIN/guide_node"           # 导航核心节点
alias c2="$BIN/arrival_fusion"       # 融合确认节点
alias c3="$SER/aiserver_node"        # TCP 服务节点
alias c4="$BIN/joystick_ctrl"        # 摇杆/键盘控制
alias c5="$BIN/guide_node & $BIN/arrival_fusion & wait"  # 一键启动导航+融合
alias ca="ros2 launch astra_camera astra.launch.xml"     # 相机

echo "项目别名已加载: c1 c2 c3 c4 c5 ca"

#!/bin/bash
# start.sh — 一键启动导航核心节点（小车导航容器内使用）
# 前置条件：
#   1. 已 source yahboomcar_ws/install/setup.bash
#   2. Nav2 已启动（n1 + n3 快捷指令）
# 用法：bash start.sh [mode]
#   mode: all (默认) | nav (仅导航) | fusion (仅融合) | joystick (仅摇杆)

WS_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
BIN="$WS_DIR/install/guide_pkg/bin"

case "${1:-all}" in
    all)
        echo "[启动] 导航核心 + 融合确认"
        $BIN/guide_node &
        $BIN/arrival_fusion &
        wait
        ;;
    nav)
        $BIN/guide_node
        ;;
    fusion)
        $BIN/arrival_fusion
        ;;
    joystick)
        $BIN/joystick_ctrl
        ;;
    *)
        echo "用法: bash start.sh [all|nav|fusion|joystick]"
        ;;
esac

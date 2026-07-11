#!/bin/bash
# demo.sh — 演示脚本（固定路线）— E组员负责
# 模拟演示流程：手动导航 → 人脸导航 → 门牌确认

set -e

LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "  icar 教室导航 — 演示模式"
echo "=========================================="
echo ""

read -p "按 Enter 开始演示（或 Ctrl+C 取消）..."

echo ""
echo "[步骤 1/3] 手动模式：导航到 101 教室"
echo "  → 发布 /command_room: 101"
ros2 topic pub --once /command_room std_msgs/String '{data: "101"}' 2>/dev/null || \
  python3 "${LOCAL_DIR}/app/client_test.py" manual 101 &
sleep 5

echo ""
echo "[步骤 2/3] 人脸模式：识别人脸并导航"
echo "  → 模拟发布 /face_room: 102"
ros2 topic pub --once /face_room std_msgs/String '{data: "102"}' 2>/dev/null || \
  python3 "${LOCAL_DIR}/app/client_test.py" face 102 &
sleep 5

echo ""
echo "[步骤 3/3] 到达确认：门牌识别"
echo "  → 监听 /arrival_confirmed"
echo "  （请在小车端观察门牌识别结果）"
sleep 3

echo ""
echo "[演示结束]"

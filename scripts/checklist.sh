#!/bin/bash
# checklist.sh — 演示前检查清单 — E组员负责
# 在正式演示前逐项检查

set -e

LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "  icar 演示前检查清单"
echo "=========================================="

check() {
  echo -n "  [$1] $2 ... "
  shift 2
  if "$@" >/dev/null 2>&1; then
    echo "✓"
  else
    echo "✗ [失败]"
    return 1
  fi
}

echo ""
echo "1. ROS2 环境"
check "1.1" "ROS2 已安装" ros2 --help
check "1.2" "Nav2 已安装" ros2 pkg list

echo ""
echo "2. 地图文件"
check "2.1" "map.pgm 存在" test -f "$LOCAL_DIR/maps/map.pgm"
check "2.2" "map.yaml 存在" test -f "$LOCAL_DIR/maps/map.yaml"

echo ""
echo "3. 工作空间编译"
check "3.1" "dev_ws/build 存在" test -d "$LOCAL_DIR/dev_ws/build"
check "3.2" "guide_pkg 已编译" test -d "$LOCAL_DIR/dev_ws/install/guide_pkg"

echo ""
echo "4. 教室坐标配置"
check "4.1" "classrooms.yaml 非空" test -s "$LOCAL_DIR/dev_ws/src/guide_pkg/config/classrooms.yaml"

echo ""
echo "5. 视觉模块"
check "5.1" "best.pt 存在" test -f "$LOCAL_DIR/vision/doorplate/best.pt"
check "5.2" "已知人脸目录非空" find "$LOCAL_DIR/vision/face/known_faces" -name "*.jpg" -o -name "*.png" | head -1

echo ""
echo "6. 网络"
check "6.1" "小车可达" ping -c1 -W2 192.168.1.120

echo ""
echo "=========================================="
echo "  检查完成！"
echo "=========================================="

#!/bin/bash
# install_deps.sh — 依赖安装脚本 — E组员负责
# 在虚拟机/小车上执行，安装项目所有依赖

set -e

echo "=========================================="
echo "  icar 依赖安装"
echo "=========================================="

echo ""
echo "[1/4] 安装 ROS2 系统依赖..."
sudo apt update
sudo apt install -y \
  ros-humble-nav2-bringup \
  ros-humble-nav2-simple-commander \
  ros-humble-slam-toolbox \
  ros-humble-tf2-ros \
  ros-humor-cv-bridge 2>/dev/null || \
  sudo apt install -y ros-humble-cv-bridge

echo ""
echo "[2/4] 安装 Python 依赖..."
pip3 install --user \
  face_recognition \
  opencv-python \
  pillow \
  pyyaml \
  websockets \
  numpy

echo ""
echo "[3/4] 安装 YOLOv5 依赖..."
pip3 install --user \
  torch \
  torchvision \
  ultralytics

echo ""
echo "[4/4] 验证安装..."
python3 -c "import rclpy; print('rclpy OK')" 2>/dev/null && echo "  ✓ rclpy" || echo "  ✗ rclpy (需要 source ROS2)"
python3 -c "import face_recognition; print('face_recognition OK')" 2>/dev/null && echo "  ✓ face_recognition" || echo "  ✗ face_recognition"
python3 -c "import cv2; print('cv2 OK')" 2>/dev/null && echo "  ✓ cv2" || echo "  ✗ cv2"

echo ""
echo "[完成] 依赖安装结束！"

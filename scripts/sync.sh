#!/bin/bash
# sync.sh — 一键同步代码到小车 — E组员负责
# 用法: bash scripts/sync.sh [小车IP] (默认 192.168.1.120)
# 需要提前配置 SSH 免密登录

set -e

CAR_IP="${1:-192.168.1.120}"
CAR_USER="yahboom"
CAR_DIR="/home/yahboom/icar_classroom_guide"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "  同步代码到小车"
echo "  目标: ${CAR_USER}@${CAR_IP}:${CAR_DIR}"
echo "=========================================="

# 排除不需要同步的目录
rsync -avz --delete \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='*.pkl' \
  --exclude='vision/doorplate/dataset/' \
  --exclude='*.log' \
  --exclude='.env' \
  --exclude='build/' \
  --exclude='install/' \
  --exclude='log/' \
  "${LOCAL_DIR}/" \
  "${CAR_USER}@${CAR_IP}:${CAR_DIR}/"

echo ""
echo "[OK] 同步完成！"
echo "请在小车上执行:"
echo "  cd ${CAR_DIR}/dev_ws && colcon build"
echo "  source install/setup.bash"

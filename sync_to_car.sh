#!/bin/bash
# sync_to_car.sh — 一键同步代码到小车（首次运行需输入密码，之后免密）
# 用法: bash sync_to_car.sh [小车IP] (默认 10.112.253.188)

set -e

CAR_IP="${1:-10.112.253.188}"
CAR_USER="jetson"
CAR_WS="/home/jetson/code/yahboomcar_ws"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  同步代码到小车"
echo "  目标: ${CAR_USER}@${CAR_IP}:${CAR_WS}/src/"
echo "=========================================="

# 第一步：部署 SSH 公钥（首次需要输入密码）
echo ""
echo "[1/3] 检查 SSH 免密登录..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=3 ${CAR_USER}@${CAR_IP} "true" 2>/dev/null; then
    echo "  需要部署 SSH 公钥（输入小车密码）..."
    ssh-copy-id -o StrictHostKeyChecking=accept-new ${CAR_USER}@${CAR_IP}
    echo "  [OK] SSH 公钥部署完成，后续免密"
else
    echo "  [OK] SSH 免密登录已配置"
fi

# 第二步：创建目标目录
echo ""
echo "[2/3] 确认工作空间目录..."
ssh ${CAR_USER}@${CAR_IP} "sudo mkdir -p ${CAR_WS}/src && sudo chown -R ${CAR_USER}:${CAR_USER} ${CAR_WS}" 2>/dev/null || \
ssh ${CAR_USER}@${CAR_IP} "mkdir -p ${CAR_WS}/src" 2>/dev/null || \
{ echo "  无法创建目录，请手动在小车上执行：sudo mkdir -p ${CAR_WS}/src"; exit 1; }
echo "  [OK] ${CAR_WS}/src/ 已确认"

# 第三步：rsync 同步 dev_ws/src/ → 小车 yahboomcar_ws/src/
echo ""
echo "[3/3] 同步 ROS2 包到工作空间 src/..."
rsync -avz \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='build/' \
  --exclude='install/' \
  --exclude='log/' \
  "${LOCAL_DIR}/dev_ws/src/" \
  "${CAR_USER}@${CAR_IP}:${CAR_WS}/src/"

echo ""
echo "=========================================="
echo "  [完成] 同步成功！"
echo "=========================================="
echo ""
echo "在小车上执行:"
echo "  cd ${CAR_WS}"
echo "  colcon build --symlink-install"
echo "  source install/setup.bash"

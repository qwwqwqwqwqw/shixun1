#!/bin/bash
# sync_to_car.sh — 一键同步全部代码到小车
# 用法: bash sync_to_car.sh [小车IP] (默认 172.29.8.188)

set -e

CAR_IP="${1:-172.29.8.188}"
CAR_USER="jetson"
CAR_WS="/home/jetson/code/yahboomcar_ws"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  同步代码到小车"
echo "  目标: ${CAR_USER}@${CAR_IP}:${CAR_WS}"
echo "=========================================="

# ── 1. SSH 免密 ──
echo ""
echo "[1/4] SSH 免密登录..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=3 ${CAR_USER}@${CAR_IP} "true" 2>/dev/null; then
    echo "  部署 SSH 公钥（输入小车密码）..."
    ssh-copy-id -o StrictHostKeyChecking=accept-new ${CAR_USER}@${CAR_IP}
fi
echo "  [OK]"

# ── 2. 创建目录 ──
echo ""
echo "[2/4] 确认目录..."
ssh ${CAR_USER}@${CAR_IP} "mkdir -p ${CAR_WS}/src ${CAR_WS}/vision ${CAR_WS}/resource" 2>/dev/null
# 清理旧同步遗留（vision/resource 曾误写入 src/ 内）
ssh ${CAR_USER}@${CAR_IP} "rm -rf ${CAR_WS}/src/vision ${CAR_WS}/src/resource" 2>/dev/null
echo "  [OK]"

# ── 3. 同步 ──
echo ""
echo "[3/4] 同步文件..."

rsync_opts="-avz --exclude='__pycache__/' --exclude='*.pyc'"

# 3a: ROS2 包
echo "  → src/"
rsync ${rsync_opts} --exclude='build/' --exclude='install/' --exclude='log/' \
  "${LOCAL_DIR}/dev_ws/src/" \
  "${CAR_USER}@${CAR_IP}:${CAR_WS}/src/"

# 3b: 视觉模块
if [ -d "${LOCAL_DIR}/vision" ]; then
    echo "  → vision/"
    rsync ${rsync_opts} \
      "${LOCAL_DIR}/vision/" \
      "${CAR_USER}@${CAR_IP}:${CAR_WS}/vision/"
fi

# 3c: 资源文件
if [ -d "${LOCAL_DIR}/resource" ]; then
    echo "  → resource/"
    rsync -avz \
      "${LOCAL_DIR}/resource/" \
      "${CAR_USER}@${CAR_IP}:${CAR_WS}/resource/"
fi

# 3d: 地图文件
if [ -d "${LOCAL_DIR}/maps" ]; then
    echo "  → maps/"
    rsync -avz \
      "${LOCAL_DIR}/maps/" \
      "${CAR_USER}@${CAR_IP}:${CAR_WS}/maps/"
fi

# ── 4. 完成 ──
echo ""
echo "[4/4] 设置别名..."
# 自动在容器 bashrc 添加别名（首次）
ssh ${CAR_USER}@${CAR_IP} \
  "grep -q 'aliases.sh' ${CAR_WS}/src/guide_pkg/launch/aliases.sh 2>/dev/null && \
   grep -q 'aliases.sh' /home/${CAR_USER}/.bashrc 2>/dev/null || true" 2>/dev/null

echo ""
echo "=========================================="
echo "  同步完成！小车目录:"
echo "  ${CAR_WS}/src/       ← ROS2 包"
echo "  ${CAR_WS}/vision/    ← 视觉节点"
echo "  ${CAR_WS}/resource/  ← 音频等资源"
echo "  ${CAR_WS}/maps/      ← 导航地图"
echo "=========================================="
echo ""
echo "小车容器内执行:"
echo "  d"
echo "  cd ~/yahboomcar_ros2_ws/yahboomcar_ws"
echo "  colcon build --symlink-install"
echo "  source install/setup.bash"
echo "  source src/guide_pkg/launch/aliases.sh"
echo ""
echo "全启动顺序:"
echo "  n1 或 ros2 launch yahboomcar_nav laser_bringup_launch.py"
echo "  cb  (RGB相机)"
echo "  c1 & c2 & c3 & c4   (核心节点)"
echo "  v1 & v2 & v3         (视觉+语音)"

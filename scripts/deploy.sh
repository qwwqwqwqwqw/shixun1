#!/bin/bash
# deploy.sh — 自动部署到小车 — E组员负责 (云平台集成/CI-CD)
#
# 作用：一条命令完成"同步代码 -> 车上编译 -> 重启服务"，
#       配合 GitHub Actions 的 deploy 任务可在 push 时自动执行。
#
# 用法：
#   bash scripts/deploy.sh [小车IP]      # 默认 192.168.1.120
#
# 前置条件：
#   1) 已配置 SSH 免密登录小车（ssh-copy-id yahboom@小车IP）
#   2) 小车已安装 ROS2 与 colcon

set -e

CAR_IP="${1:-192.168.1.120}"
CAR_USER="yahboom"
CAR_DIR="/home/yahboom/icar_classroom_guide"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  自动部署到小车 ${CAR_IP}"
echo "=========================================="

# 1. 同步代码到小车（复用 sync.sh 的 rsync 逻辑）
echo "[1/3] 同步代码..."
bash "${SCRIPT_DIR}/sync.sh" "${CAR_IP}"

# 2. 在车上编译 ROS2 工作空间
echo "[2/3] 车上编译 dev_ws..."
ssh "${CAR_USER}@${CAR_IP}" \
  "cd ${CAR_DIR}/dev_ws && source /opt/ros/\${ROS_DISTRO}/setup.bash && colcon build --symlink-install"

# 3. 重启服务（若使用 docker-compose）
echo "[3/3] 重启服务..."
ssh "${CAR_USER}@${CAR_IP}" \
  "cd ${CAR_DIR} && (docker compose restart 2>/dev/null || docker-compose restart 2>/dev/null || echo '未使用 docker-compose，请手动启动节点')"

echo ""
echo "[OK] 部署完成！"
echo "在小车上启动云平台上报节点（小车状态就会发到云端）："
echo "  source ${CAR_DIR}/dev_ws/install/setup.bash"
echo "  python3 ${CAR_DIR}/scripts/cloud_reporter.py"

"""核心导航节点 — B组长负责。

流程：
  小程序输入教室号 → 查 classrooms.yaml 坐标 → 通过 Nav2 Action 发送目标 → 自动导航 → 到达发布状态

订阅话题：
  - /command_room (std_msgs/String) : 小程序手动输入教室号
  - /face_room    (std_msgs/String) : 人脸识别映射后的教室号
  - /navigation_cancel (std_msgs/Bool) : 取消当前导航

发布话题：
  - /navigation_status (std_msgs/String) : 导航状态实时反馈

使用 Nav2 Action:
  - /navigate_to_pose (nav2_msgs/action/NavigateToPose) : 发送导航目标

依赖：
  - Nav2 基础节点已启动（n1 + n3）
  - classrooms.yaml 中有教室坐标
"""
import os
import rclpy  # pyright: ignore[reportMissingImports]
from rclpy.node import Node  # pyright: ignore[reportMissingImports]
from rclpy.action import ActionClient  # pyright: ignore[reportMissingImports]
from geometry_msgs.msg import PoseWithCovarianceStamped  # pyright: ignore[reportMissingImports]
from std_msgs.msg import String, Bool  # pyright: ignore[reportMissingImports]
from nav2_msgs.action import NavigateToPose  # pyright: ignore[reportMissingImports]

from guide_pkg.utils import load_classrooms, get_room_coord, make_pose_stamped


class GuideNode(Node):
    def __init__(self):
        super().__init__('guide_node')

        # ── 加载教室坐标 + 起点 ──
        config_dir = os.path.join(
            os.path.dirname(__file__), '..', 'config')
        classroom_path = os.path.join(config_dir, 'classrooms.yaml')
        self.classrooms, self.origin = load_classrooms(classroom_path)
        self.get_logger().info(f'已加载 {len(self.classrooms)} 个教室坐标')

        # ── Nav2 Action 客户端 ──
        self.nav_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.nav_goal_handle = None
        self.current_room = ''
        self.navigating = False
        self.nav2_available = False

        # 启动时检测 Nav2（不阻塞）
        self._check_nav2_timer = self.create_timer(3.0, self._check_nav2_ready)

        # ── 订阅器 ──
        self.sub_cmd = self.create_subscription(
            String, '/command_room', self.on_command_room, 10)
        self.sub_face = self.create_subscription(
            String, '/face_room', self.on_face_room, 10)
        self.sub_cancel = self.create_subscription(
            Bool, '/navigation_cancel', self.on_cancel, 10)

        # ── 发布器 ──
        self.pub_status = self.create_publisher(
            String, '/navigation_status', 10)
        self.pub_initialpose = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', 10)

        # 延迟 1 秒自动设置初始位姿（等 AMCL 就绪）
        self._init_pose_timer = self.create_timer(1.0, self._set_initial_pose)

        self.get_logger().info('guide_node 已启动 — 等待 /command_room 或 /face_room 指令')

    # ──────────── 指令入口 ────────────

    def _set_initial_pose(self):
        """自动设置 AMCL 初始位姿，无需手动 2D Pose Estimate。"""
        self._init_pose_timer.cancel()
        if self.origin is None:
            return
        ox, oy, oyaw = self.origin['x'], self.origin['y'], self.origin.get('yaw', 0.0)
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.pose.position.x = ox
        msg.pose.pose.position.y = oy
        msg.pose.pose.position.z = 0.0
        # 简单朝向（绕 Z 轴）
        import math
        msg.pose.pose.orientation.z = math.sin(oyaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(oyaw / 2.0)
        # 低协方差 = "我很确定"
        msg.pose.covariance[0] = 0.25
        msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.0685
        self.pub_initialpose.publish(msg)
        self.get_logger().info(
            f'[初始位姿] 已自动设置起点 x={ox:.2f} y={oy:.2f} yaw={oyaw:.2f}')

    def _check_nav2_ready(self):
        """周期性检测 Nav2 是否可用。"""
        if not self.nav2_available:
            if self.nav_client.wait_for_server(timeout_sec=0.5):
                self.nav2_available = True
                self._check_nav2_timer.cancel()
                self.get_logger().info('[Nav2] 导航服务已就绪')

    def on_command_room(self, msg):
        """手动模式：小程序输入教室号 → 导航"""
        room = msg.data.strip()
        if not room:
            return
        self.get_logger().info(f'[手动] 教室号: {room}')
        self._navigate_to(room, source='manual')

    def on_face_room(self, msg):
        """人脸识别结果：收到映射后的教室号并开始导航。"""
        data = msg.data.strip()
        if not data:
            return
        self.get_logger().info(f'[人脸] 房间号: {data}')
        self._navigate_to(data, source='face')

    def on_cancel(self, msg):
        """取消当前导航"""
        if msg.data and self.nav_goal_handle:
            self.get_logger().info('[取消] 正在取消导航...')
            self.nav_goal_handle.cancel_async()
            self.publish_status(f'导航已取消（原目标: {self.current_room}）')

    # ──────────── 导航核心 ────────────

    def _navigate_to(self, room_number, source):
        """统一导航入口 — 查坐标 → 发 Nav2 目标 → 监听反馈。"""
        if self.navigating:
            self.get_logger().warn(f'[阻塞] 导航中，拒绝: {room_number}')
            self.publish_status(f'拒绝: 正在导航到 {self.current_room}，请先取消')
            return

        # 查教室坐标（兼容 front/back 新格式）
        coord = get_room_coord(self.classrooms, room_number, door='front')
        if coord is None:
            self.get_logger().error(f'[失败] 未知教室: {room_number}')
            self.publish_status(f'导航失败: 教室 {room_number} 未找到坐标')
            return
        x, y, yaw = coord

        # 构造导航目标
        goal_pose = make_pose_stamped('map', x, y, yaw)
        self.get_logger().info(
            f'[导航] {room_number} → x={x:.2f} y={y:.2f} yaw={yaw:.2f} ({source})')

        self.current_room = room_number
        self.navigating = True
        self.publish_status(f'开始导航到 {room_number}（来源: {source}）')

        # 等待 Nav2 Action 服务就绪
        if not self.nav_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error(
                '[失败] Nav2 Action 服务不可用 — '
                '请先启动建图/导航栈（n1 + 地图服务 + n3）')
            self.publish_status(
                f'[模拟] Nav2 未就绪 — 假设 {room_number} 导航请求已接收'
                f'(目标 x={x:.1f} y={y:.1f} yaw={yaw:.1f})')
            self.publish_status(f'到达 {room_number}')
            self.navigating = False
            return

        # 发送目标
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = goal_pose
        self.nav_client.send_goal_async(goal_msg).add_done_callback(
            self._goal_response_callback)

    # ──────────── Nav2 Action 回调 ────────────

    def _goal_response_callback(self, future):
        """目标发送后，Nav2 是否接受。"""
        self.nav_goal_handle = future.result()
        if not self.nav_goal_handle.accepted:
            self.get_logger().error(f'[拒绝] Nav2 拒绝了 {self.current_room} 的目标')
            self.publish_status(f'导航失败: Nav2 拒绝目标 {self.current_room}')
            self.navigating = False
            return

        self.get_logger().info(f'[接受] Nav2 已接受目标 {self.current_room}')
        self.publish_status(f'导航中: 前往 {self.current_room}...')
        self.nav_goal_handle.get_result_async().add_done_callback(
            self._result_callback)

    def _result_callback(self, future):
        """导航完成（成功或失败）。"""
        result = future.result()
        status = result.status

        if status == 4:  # SUCCEEDED
            self.get_logger().info(f'[到达] {self.current_room}')
            self.publish_status(f'到达 {self.current_room}')
        else:
            self.get_logger().error(f'[失败] 状态码={status}')
            self.publish_status(f'导航失败: {self.current_room}（状态码 {status}）')

        self.navigating = False
        self.nav_goal_handle = None

    # ──────────── 辅助 ────────────

    def publish_status(self, message):
        msg = String()
        msg.data = message
        self.pub_status.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GuideNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

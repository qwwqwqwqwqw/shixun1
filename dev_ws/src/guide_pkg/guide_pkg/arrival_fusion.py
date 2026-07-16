"""多传感器融合节点 — B组长负责。

功能：导航到达后，等待摄像头视觉门牌确认，匹配成功才发布到达确认。

订阅话题：
  - /navigation_status  (std_msgs/String) : 导航状态（guide_node 发布）
  - /doorplate_result   (std_msgs/String) : 门牌识别结果（doorplate_detector 发布）

发布话题：
  - /arrival_confirmed  (std_msgs/Bool)   : 最终到达确认
  - /fusion_status      (std_msgs/String) : 融合状态详情（供前端展示）

融合逻辑：
  1. 收到导航"到达 101" → 记录期望教室号，进入等待门牌确认状态
  2. 收到门牌识别结果 → 与期望教室号比对
  3. 匹配成功 → 发布 arrival_confirmed=True
  4. 匹配失败/超时 → 发布 arrival_confirmed=False, 提示重新检测
"""
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


# 门牌识别等待超时（秒）
DOORPLATE_TIMEOUT = 50.0


class ArrivalFusion(Node):
    def __init__(self):
        super().__init__('arrival_fusion')

        # ── 订阅器 ──
        self.sub_nav = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.sub_door = self.create_subscription(
            String, '/doorplate_result', self.on_doorplate, 10)

        # ── 发布器 ──
        self.pub_arrival = self.create_publisher(
            Bool, '/arrival_confirmed', 10)
        self.pub_fusion = self.create_publisher(
            String, '/fusion_status', 10)

        # ── 状态 ──
        self.expected_room = ''
        self.detected_room = ''
        self.waiting_for_doorplate = False
        self.arrival_time = 0.0

        self.get_logger().info('arrival_fusion 已启动')

    # ──────────── 导航状态回调 ────────────

    def on_nav_status(self, msg):
        status_text = msg.data
        self.get_logger().info(f'[导航状态] {status_text}')

        # 检测"到达 XXX"
        if '到达 ' in status_text:
            parts = status_text.split('到达 ')
            if len(parts) > 1:
                room = parts[-1].strip().split()[0]  # 提取教室号
                self.expected_room = room
                self.detected_room = ''
                self.waiting_for_doorplate = True
                self.arrival_time = time.time()
                self.get_logger().info(f'[融合] 期望教室: {room}, 等待门牌确认...')
                self._publish_fusion(f'导航到达 {room}，等待视觉确认...')

        # 导航失败/取消 → 重置状态
        elif '失败' in status_text or '取消' in status_text:
            if self.waiting_for_doorplate:
                self.waiting_for_doorplate = False
                self.expected_room = ''
                self._publish_fusion('导航中断，融合重置')

    # ──────────── 门牌识别回调 ────────────

    def on_doorplate(self, msg):
        self.detected_room = msg.data.strip()
        self.get_logger().info(f'[门牌] 识别: {self.detected_room}')

        if not self.waiting_for_doorplate:
            return

        # 与期望教室号比对
        if self.detected_room == self.expected_room:
            self.get_logger().info(f'[确认] ✓ 门牌匹配: {self.expected_room}')
            self.pub_arrival.publish(Bool(data=True))
            self._publish_fusion(f'已确认到达 {self.expected_room}（视觉校验通过）')
            self.waiting_for_doorplate = False
        else:
            self.get_logger().warn(
                f'[不匹配] 期望={self.expected_room} 实际={self.detected_room}')
            self._publish_fusion(
                f'门牌不匹配: 期望 {self.expected_room}, 识别 {self.detected_room}')

    # ──────────── 超时检测 ────────────

    def _check_timeout(self):
        """定时器回调：检测门牌确认是否超时。"""
        if self.waiting_for_doorplate:
            elapsed = time.time() - self.arrival_time
            if elapsed > DOORPLATE_TIMEOUT:
                self.get_logger().warn(f'[超时] 门牌确认超时 ({DOORPLATE_TIMEOUT}s)')
                self.pub_arrival.publish(Bool(data=False))
                self._publish_fusion(f'到达 {self.expected_room} 未收到门牌确认（超时）')
                self.waiting_for_doorplate = False

    # ──────────── 辅助 ────────────

    def _publish_fusion(self, message):
        msg = String()
        msg.data = message
        self.pub_fusion.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ArrivalFusion()

    # 定时器：每秒检查超时
    node.create_timer(1.0, node._check_timeout)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

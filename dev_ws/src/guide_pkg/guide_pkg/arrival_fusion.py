"""多传感器融合节点 — 订阅视觉/导航结果，输出最终到达确认。

订阅话题：
  - /doorplate_result  (std_msgs/String) : 门牌识别结果（C组员发布）
  - /navigation_status (std_msgs/String) : 导航状态（guide_node 发布）

发布话题：
  - /arrival_confirmed (std_msgs/Bool)   : 最终到达确认（融合导航到达 + 门牌匹配）
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class ArrivalFusion(Node):
    def __init__(self):
        super().__init__('arrival_fusion')
        self.sub_door = self.create_subscription(
            String, '/doorplate_result', self.on_doorplate, 10)
        self.sub_nav = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.pub_arrival = self.create_publisher(
            Bool, '/arrival_confirmed', 10)
        self.nav_done = False
        self.expected_room = ''
        self.detected_room = ''
        self.get_logger().info('arrival_fusion 已启动')

    def on_doorplate(self, msg):
        """门牌识别回调"""
        self.detected_room = msg.data.strip()
        self.get_logger().info(f'门牌识别结果: {self.detected_room}')
        self._check_arrival()

    def on_nav_status(self, msg):
        """导航状态回调"""
        if '到达' in msg.data or 'arrived' in msg.data.lower():
            self.nav_done = True
            self.get_logger().info('导航到达目标位置')
            self._check_arrival()
        elif '导航' in msg.data and '到' in msg.data:
            # 解析目标教室号
            pass

    def _check_arrival(self):
        """融合判定：导航到达 + 门牌匹配 = 最终确认"""
        if self.nav_done and self.detected_room:
            if self.expected_room and self.detected_room == self.expected_room:
                self.pub_arrival.publish(Bool(data=True))
                self.get_logger().info('✓ 到达确认：门牌匹配成功')
            else:
                self.pub_arrival.publish(Bool(data=False))
                self.get_logger().warn(f'✗ 门牌不匹配: 期望 {self.expected_room}, 识别 {self.detected_room}')


def main(args=None):
    rclpy.init(args=args)
    node = ArrivalFusion()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

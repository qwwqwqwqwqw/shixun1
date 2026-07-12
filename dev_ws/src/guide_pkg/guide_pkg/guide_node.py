"""核心导航节点 — B组长负责。

订阅话题：
  - /command_room (std_msgs/String) : 小程序手动输入教室号 → 原有模式
  - /face_room    (std_msgs/String) : 人脸识别映射房间号 / 人脸模式控制 → 新模式
  - /cmd_vel      (geometry_msgs/Twist) : 小程序摇杆控制（由 aiserver_node 直发底盘，此处仅记录）

发布话题：
  - /navigation_status (std_msgs/String) : 导航状态实时反馈

核心逻辑：收到教室号 → 从 classrooms.yaml 查找坐标 → 调用 Nav2 SimpleCommander 导航。
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class GuideNode(Node):
    def __init__(self):
        super().__init__('guide_node')
        # 订阅两种触发话题
        self.sub_cmd = self.create_subscription(
            String, '/command_room', self.on_command_room, 10)
        self.sub_face = self.create_subscription(
            String, '/face_room', self.on_face_room, 10)
        # 发布导航状态
        self.pub_status = self.create_publisher(
            String, '/navigation_status', 10)
        self.get_logger().info('guide_node 已启动 — 等待 /command_room 或 /face_room 指令')

    def on_command_room(self, msg):
        """手动模式：小程序输入教室号"""
        room = msg.data.strip()
        if not room:
            return
        self.get_logger().info(f'[手动] 收到教室号: {room}')
        self._navigate_to(room, source='manual')

    def on_face_room(self, msg):
        """自动模式：人脸识别结果（房间号）或人脸模式控制指令"""
        data = msg.data.strip()
        if not data:
            return

        # "start" / "stop" 为人脸模式控制指令，不触发导航
        if data.lower() in ('start', 'stop'):
            self.get_logger().info(f'[人脸] 模式控制: {data}')
            self.publish_status(f'人脸识别模式: {data}')
            return

        # 其他内容视为房间号，触发导航
        self.get_logger().info(f'[人脸] 房间号: {data}')
        self._navigate_to(data, source='face')

    def _navigate_to(self, room_number, source):
        """统一导航入口 — B组长实现 Nav2 调用。"""
        self.publish_status(f'开始导航到 {room_number}（来源: {source}）')
        # TODO: B组长实现
        # 1. 从 classrooms.yaml 加载坐标 (utils.load_classrooms)
        # 2. 使用 nav2_simple_commander 发送目标
        # 3. 等待导航完成，发布状态
        pass

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

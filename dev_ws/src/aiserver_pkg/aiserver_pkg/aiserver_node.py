"""TCP/WebSocket 服务节点 — D组员负责实现。

功能：
  1. 启动 TCP/WebSocket 服务，接收小程序/Web 前端指令
  2. 前端发来的教室号 → 发布到 /command_room 话题
  3. 订阅 /navigation_status → 实时回传前端
  4. 提供人脸注册接口（扩展）
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class AiServerNode(Node):
    def __init__(self):
        super().__init__('aiserver_node')
        # 发布：将前端指令转发为 ROS2 话题
        self.pub_command_room = self.create_publisher(
            String, '/command_room', 10)
        self.pub_face_room = self.create_publisher(
            String, '/face_room', 10)
        # 订阅：导航状态回传前端
        self.sub_status = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.get_logger().info('aiserver_node 已启动 — 等待前端连接')
        # TODO: D组员实现 TCP/WebSocket 服务端

    def on_nav_status(self, msg):
        """导航状态回调 → 通过 WebSocket 回传前端"""
        self.get_logger().info(f'导航状态: {msg.data}')
        # TODO: ws.send(msg.data)

    def handle_command(self, room_number):
        """处理前端教室号指令 → 发布到 /command_room"""
        msg = String()
        msg.data = room_number
        self.pub_command_room.publish(msg)
        self.get_logger().info(f'已转发教室号: {room_number}')

    def handle_face_result(self, room_number):
        """处理人脸识别结果 → 发布到 /face_room"""
        msg = String()
        msg.data = room_number
        self.pub_face_room.publish(msg)
        self.get_logger().info(f'已转发人脸房间号: {room_number}')


def main(args=None):
    rclpy.init(args=args)
    node = AiServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

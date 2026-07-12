#!/usr/bin/env python3
"""命令行测试客户端 — 调试用，通过 ROS2 话题手动发送导航指令。

用法：
  python3 client_test.py manual 501   # 手动模式导航到 501 教室
  python3 client_test.py face 502     # 人脸模式导航到 502 房间
  python3 client_test.py monitor      # 仅监听导航状态
"""
import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


class TestClient(Node):
    def __init__(self):
        super().__init__('test_client')
        self.pub_cmd = self.create_publisher(String, '/command_room', 10)
        self.pub_face = self.create_publisher(String, '/face_room', 10)
        self.sub_status = self.create_subscription(
            String, '/navigation_status', self.on_status, 10)
        self.sub_arrival = self.create_subscription(
            Bool, '/arrival_confirmed', self.on_arrival, 10)
        self.get_logger().info('测试客户端已启动')

    def on_status(self, msg):
        print(f'[导航状态] {msg.data}')

    def on_arrival(self, msg):
        print(f'[到达确认] {msg.data}')

    def send_manual(self, room):
        msg = String(data=room)
        self.pub_cmd.publish(msg)
        print(f'[发送] 手动教室号: {room}')

    def send_face(self, room):
        msg = String(data=room)
        self.pub_face.publish(msg)
        print(f'[发送] 人脸房间号: {room}')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    rclpy.init()
    node = TestClient()

    if sys.argv[1] == 'manual' and len(sys.argv) >= 3:
        node.send_manual(sys.argv[2])
    elif sys.argv[1] == 'face' and len(sys.argv) >= 3:
        node.send_face(sys.argv[2])
    elif sys.argv[1] == 'monitor':
        print('仅监听模式...')
    else:
        print(__doc__)
        node.destroy_node()
        rclpy.shutdown()
        return

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

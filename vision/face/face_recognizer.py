"""人脸识别节点 — C组员负责实现（酒店入住模拟功能）。

功能：
  1. 检测摄像头画面中的人脸
  2. 与 known_faces/ 中已知人脸比对（face_recognition 库）
  3. 通过 face_room_map.yaml 映射到房间号
  4. 发布到 /face_room 话题触发导航

发布话题：
  - /face_room (std_msgs/String) : 识别到的人名 → 房间号

依赖：
  - face_recognition
  - cv2 (OpenCV)
  - face_room_map.yaml（C组员维护）
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class FaceRecognizer(Node):
    def __init__(self):
        super().__init__('face_recognizer')
        self.pub_face_room = self.create_publisher(
            String, '/face_room', 10)
        self.get_logger().info('face_recognizer 已启动 — 等待人脸图像')
        # TODO: C组员实现
        # 1. 加载 known_faces/ 目录下的人脸编码
        # 2. 加载 face_room_map.yaml 映射表
        # 3. 订阅摄像头图像，检测并识别人脸
        # 4. 匹配成功后发布房间号到 /face_room

    def on_face_detected(self, person_name):
        """识别到已知人脸 → 查映射表 → 发布房间号"""
        # TODO: 从 face_room_map.yaml 查找 person_name 对应的房间号
        # room_number = self.face_map.get(person_name)
        # if room_number:
        #     msg = String(data=room_number)
        #     self.pub_face_room.publish(msg)
        pass


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

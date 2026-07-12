"""人脸识别节点 — 使用 face_recognition 库（dlib 预训练模型，无需额外训练）。

流程：
  摄像头 → 人脸检测 → 比对 known_faces/ → 查 face_room_map.yaml → /face_room

订阅话题：
  - /camera/color/image_raw (sensor_msgs/Image) : RGB 摄像头图像

发布话题：
  - /face_room (std_msgs/String) : 识别到的房间号
"""
import os
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import yaml

try:
    import face_recognition as _face_recog
    HAS_FACE_RECOG = True
except ImportError:
    _face_recog = None  # type: ignore
    HAS_FACE_RECOG = False


class FaceRecognizer(Node):
    def __init__(self):
        super().__init__('face_recognizer')

        assert HAS_FACE_RECOG, 'face_recognition 未安装，请执行: pip3 install face_recognition'

        # ── 加载已知人脸 ──
        self.known_encodings = []
        self.known_names = []
        self._load_known_faces()

        # ── 加载人名→房间号映射 ──
        self.face_room_map = {}
        self._load_face_room_map()

        # ── 发布 /face_room ──
        self.pub_face_room = self.create_publisher(
            String, '/face_room', 10)

        # ── 订阅摄像头 ──
        self.bridge = CvBridge()
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.on_image, 10)

        # ── 节流控制 ──
        self.process_interval = 1.0   # 每秒处理一帧
        self.last_process_time = 0.0
        self.last_person = ''         # 避免重复发布

        self.get_logger().info(
            f'face_recognizer 已启动 — {len(self.known_names)} 个已知人脸, '
            f'{len(self.face_room_map)} 条映射')

    # ──────────── 加载 ────────────

    def _load_known_faces(self):
        """读取 known_faces/ 下所有图片，编码人脸。"""
        base = os.path.join(os.path.dirname(__file__), 'known_faces')
        if not os.path.isdir(base):
            self.get_logger().warn(f'已知人脸目录不存在: {base}')
            return
        for fname in os.listdir(base):
            if fname.startswith('.') or fname == 'README.md':
                continue
            path = os.path.join(base, fname)
            img = _face_recog.load_image_file(path)
            encodings = _face_recog.face_encodings(img)
            if encodings:
                name = os.path.splitext(fname)[0]
                self.known_encodings.append(encodings[0])
                self.known_names.append(name)
                self.get_logger().info(f'  已加载: {name}')
            else:
                self.get_logger().warn(f'  未检测到人脸: {fname}')

    def _load_face_room_map(self):
        """加载 face_room_map.yaml"""
        config_dir = os.path.join(
            os.path.dirname(__file__), '../../src/guide_pkg/config')
        path = os.path.join(config_dir, 'face_room_map.yaml')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self.face_room_map = data.get('face_room_map', {}) if data else {}
        except FileNotFoundError:
            self.get_logger().warn(f'映射表不存在: {path}')

    # ──────────── 图像处理 ────────────

    def on_image(self, msg):
        now = time.time()
        if now - self.last_process_time < self.process_interval:
            return
        self.last_process_time = now

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception:
            return

        # 缩小以加速
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # 检测人脸位置
        locations = _face_recog.face_locations(rgb)
        if not locations:
            return

        # 编码检测到的人脸
        encodings = _face_recog.face_encodings(rgb, locations)

        for encoding in encodings:
            if not self.known_encodings:
                self.get_logger().warn('检测到人脸，但无已知人脸可对比')
                continue

            distances = _face_recog.face_distance(
                self.known_encodings, encoding)
            best_idx = int(np.argmin(distances))
            min_dist = distances[best_idx]

            # 阈值 0.5：越低越像
            if min_dist < 0.5:
                name = self.known_names[best_idx]
                if name != self.last_person:
                    self.last_person = name
                    room = self.face_room_map.get(name, '')
                    if room:
                        self.get_logger().info(
                            f'[识别] {name} → 教室 {room} (距离 {min_dist:.2f})')
                        msg_out = String(data=room)
                        self.pub_face_room.publish(msg_out)
                    else:
                        self.get_logger().warn(
                            f'[识别] {name}，但映射表中无对应教室')
                break  # 一次只认一个人


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

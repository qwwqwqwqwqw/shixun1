"""人脸识别节点 — face_recognition（dlib 预训练模型）。

摄像头：OpenCV 直读 /dev/video0（不依赖 ROS2 相机驱动）。
"""
import os
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cv2
import numpy as np
import yaml

try:
    import face_recognition as _fr
    HAS_FACE = True
except ImportError:
    _fr = None  # type: ignore
    HAS_FACE = False


class FaceRecognizer(Node):
    def __init__(self):
        super().__init__('face_recognizer')
        assert HAS_FACE, 'face_recognition 未安装: pip3 install face_recognition'

        self.known_encodings = []
        self.known_names = []
        self._load_known_faces()

        self.face_room_map = {}
        self._load_face_room_map()

        self.pub_face_room = self.create_publisher(String, '/face_room', 10)

        # OpenCV 直读摄像头（Astra depth=/dev/video0, RGB 可能在其他索引）
        self.cap = None
        for idx in [2, 4, 6, 0]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    self.cap = cap
                    self.get_logger().info(f'摄像头 /dev/video{idx} 已就绪')
                    break
                cap.release()
        assert self.cap is not None, '摄像头不可用 — 请检查 /dev/video*'

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.process_interval = 1.0
        self.last_process = 0.0
        self.last_person = ''

        # 定时器驱动帧处理
        self.timer = self.create_timer(0.3, self._process_frame)

        self.get_logger().info(
            f'face_recognizer 已启动 — {len(self.known_names)} 人脸')

    def _load_known_faces(self):
        base = os.path.join(os.path.dirname(__file__), 'known_faces')
        if not os.path.isdir(base):
            return
        for fname in os.listdir(base):
            if fname.startswith('.') or fname == 'README.md':
                continue
            path = os.path.join(base, fname)
            img = _fr.load_image_file(path)  # type: ignore
            encs = _fr.face_encodings(img)   # type: ignore
            if encs:
                self.known_encodings.append(encs[0])
                self.known_names.append(os.path.splitext(fname)[0])

    def _load_face_room_map(self):
        config_dir = os.path.join(
            os.path.dirname(__file__), '../../src/guide_pkg/config')
        path = os.path.join(config_dir, 'face_room_map.yaml')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self.face_room_map = data.get('face_room_map', {}) if data else {}
        except FileNotFoundError:
            pass

    def _process_frame(self):
        assert self.cap is not None
        now = time.time()
        if now - self.last_process < self.process_interval:
            return
        self.last_process = now

        ret, frame = self.cap.read()
        if not ret:
            return

        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locs = _fr.face_locations(rgb)  # type: ignore
        if not locs:
            return
        encs = _fr.face_encodings(rgb, locs)  # type: ignore

        for enc in encs:
            if not self.known_encodings:
                return
            dists = _fr.face_distance(self.known_encodings, enc)  # type: ignore
            idx = int(np.argmin(dists))
            if dists[idx] < 0.5:
                name = self.known_names[idx]
                if name != self.last_person:
                    self.last_person = name
                    room = self.face_room_map.get(name, '')
                    if room:
                        self.get_logger().info(f'[识别] {name} → {room}')
                        self.pub_face_room.publish(String(data=room))
                    else:
                        self.get_logger().warn(
                            f'[识别] {name}，无映射')
                break

    def destroy_node(self):
        if self.cap is not None:
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(FaceRecognizer())
    rclpy.shutdown()


if __name__ == '__main__':
    main()

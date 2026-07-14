"""按需运行的人脸识别 ROS2 节点。

订阅 /face_mode_control 的 start/stop，识别成功后向 /face_room 发布教室号，
并通过 /face_recognition_status 发布 JSON 状态。
"""
import json
import os
import time
import rclpy  # pyright: ignore[reportMissingImports]
from rclpy.node import Node  # pyright: ignore[reportMissingImports]
from std_msgs.msg import String  # pyright: ignore[reportMissingImports]
import cv2  # pyright: ignore[reportMissingImports]
import numpy as np
import yaml

try:
    import face_recognition as _fr  # pyright: ignore[reportMissingImports]
    HAS_FACE = True
except ImportError:
    _fr = None  # type: ignore
    HAS_FACE = False


class FaceRecognizer(Node):
    def __init__(self):
        super().__init__('face_recognizer')
        assert HAS_FACE, 'face_recognition 未安装: pip3 install face_recognition'

        self.declare_parameter('enabled_on_start', False)
        self.declare_parameter('camera_index', -1)
        self.declare_parameter('face_map_path', '')
        self.declare_parameter('known_faces_dir', '')
        self.declare_parameter('distance_threshold', 0.5)
        self.declare_parameter('required_matches', 2)
        self.declare_parameter('recognition_timeout', 15.0)
        self.declare_parameter('process_interval', 0.5)

        self.distance_threshold = float(
            self.get_parameter('distance_threshold').value or 0.5)
        self.required_matches = max(
            1, int(self.get_parameter('required_matches').value or 2))
        self.recognition_timeout = max(
            1.0, float(self.get_parameter('recognition_timeout').value or 15.0))
        self.process_interval = max(
            0.1, float(self.get_parameter('process_interval').value or 0.5))

        self.pub_face_room = self.create_publisher(String, '/face_room', 10)
        self.pub_status = self.create_publisher(
            String, '/face_recognition_status', 10)
        self.sub_control = self.create_subscription(
            String, '/face_mode_control', self.on_control, 10)

        self.known_encodings = []
        self.known_names = []
        self._load_known_faces()

        self.face_room_map = {}
        self._load_face_room_map()

        self.cap = None
        self.enabled = False
        self.session_started = 0.0
        self.last_process = 0.0
        self.candidate_name = ''
        self.candidate_matches = 0
        self.last_status_key = ''
        self.last_status_time = 0.0

        self.timer = self.create_timer(0.1, self._process_frame)

        self.get_logger().info(
            f'face_recognizer 已启动 — {len(self.known_names)} 张注册人脸，'
            f'{len(self.face_room_map)} 条房间映射')
        self._publish_status(
            'ready',
            f'已加载 {len(self.known_names)} 张注册人脸',
            force=True,
        )
        if bool(self.get_parameter('enabled_on_start').value):
            self._start_session()

    def _load_known_faces(self):
        configured = str(self.get_parameter('known_faces_dir').value).strip()
        base = configured or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'known_faces')
        if not os.path.isdir(base):
            self.get_logger().error(f'人脸库目录不存在: {base}')
            return

        for fname in sorted(os.listdir(base)):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            path = os.path.join(base, fname)
            try:
                img = _fr.load_image_file(path)  # type: ignore
                encs = _fr.face_encodings(img)   # type: ignore
                if encs:
                    self.known_encodings.append(encs[0])
                    self.known_names.append(os.path.splitext(fname)[0])
                else:
                    self.get_logger().warn(f'注册照片未检测到人脸: {fname}')
            except Exception as exc:
                self.get_logger().error(f'注册照片加载失败 {fname}: {exc}')

    def _load_face_room_map(self):
        configured = str(self.get_parameter('face_map_path').value).strip()
        project_root = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', '..'))
        candidates = [
            configured,
            os.environ.get('FACE_ROOM_MAP', ''),
            '/workspace/config/face_room_map.yaml',
            os.path.join(
                project_root,
                'dev_ws', 'src', 'guide_pkg', 'config',
                'face_room_map.yaml',
            ),
        ]
        path = next((item for item in candidates if item and os.path.isfile(item)), '')
        if not path:
            self.get_logger().error(
                '找不到 face_room_map.yaml，请设置 face_map_path 或 FACE_ROOM_MAP')
            return
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or {}
            mapping = data.get('face_room_map', {})
            self.face_room_map = {
                str(name): str(room) for name, room in mapping.items()
            }
            self.get_logger().info(f'已加载人脸映射: {path}')
        except (OSError, yaml.YAMLError) as exc:
            self.get_logger().error(f'人脸映射加载失败: {exc}')

    def on_control(self, msg):
        action = msg.data.strip().lower()
        if action == 'start':
            self._start_session()
        elif action == 'stop':
            self._stop_session('stopped', '人脸识别已停止')
        else:
            self._publish_status(
                'error', f'未知人脸模式指令: {action}', force=True)

    def _start_session(self):
        if not self.known_encodings:
            self._publish_status(
                'error', '未加载注册人脸，请先添加照片', force=True)
            return
        if not self.face_room_map:
            self._publish_status(
                'error', '人脸与教室映射为空', force=True)
            return
        if not self._open_camera():
            self._publish_status(
                'error', '摄像头不可用，请检查 /dev/video*', force=True)
            return

        self.enabled = True
        self.session_started = time.monotonic()
        self.last_process = 0.0
        self.candidate_name = ''
        self.candidate_matches = 0
        self._publish_status(
            'searching', '请正对摄像头，正在识别人脸', force=True)
        self.get_logger().info('[人脸模式] 开始识别')

    def _stop_session(self, status=None, message=None):
        self.enabled = False
        self.candidate_name = ''
        self.candidate_matches = 0
        self._release_camera()
        if status and message:
            self._publish_status(status, message, force=True)

    def _open_camera(self):
        if self.cap is not None and self.cap.isOpened():
            return True

        configured = int(self.get_parameter('camera_index').value or -1)
        indices = [configured] if configured >= 0 else [2, 4, 6, 0]
        for index in indices:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                continue
            ok, _ = cap.read()
            if not ok:
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap = cap
            self.get_logger().info(f'摄像头 /dev/video{index} 已就绪')
            return True
        return False

    def _release_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def _process_frame(self):
        if not self.enabled or self.cap is None:
            return

        now = time.monotonic()
        if now - self.session_started >= self.recognition_timeout:
            self._stop_session('timeout', '识别超时，请重试')
            return
        if now - self.last_process < self.process_interval:
            return
        self.last_process = now

        ret, frame = self.cap.read()
        if not ret:
            self._stop_session('error', '摄像头读取失败')
            return

        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locs = _fr.face_locations(rgb)  # type: ignore
        if not locs:
            self.candidate_name = ''
            self.candidate_matches = 0
            self._publish_status('searching', '未检测到人脸')
            return
        encs = _fr.face_encodings(rgb, locs)  # type: ignore

        best_name = ''
        best_distance = float('inf')
        for enc in encs:
            dists = _fr.face_distance(self.known_encodings, enc)  # type: ignore
            idx = int(np.argmin(dists))
            distance = float(dists[idx])
            if distance < best_distance:
                best_distance = distance
                best_name = self.known_names[idx]

        if not best_name or best_distance >= self.distance_threshold:
            self.candidate_name = ''
            self.candidate_matches = 0
            self._publish_status(
                'unknown', '检测到未注册人脸',
                distance=round(best_distance, 3),
            )
            return

        if best_name == self.candidate_name:
            self.candidate_matches += 1
        else:
            self.candidate_name = best_name
            self.candidate_matches = 1

        room = self.face_room_map.get(best_name, '')
        if not room:
            self._publish_status(
                'error', f'{best_name} 未配置目标教室',
                name=best_name, force=True)
            self.candidate_name = ''
            self.candidate_matches = 0
            return

        if self.candidate_matches < self.required_matches:
            self._publish_status(
                'confirming',
                f'正在确认 {best_name}（{self.candidate_matches}/{self.required_matches}）',
                name=best_name,
                room=room,
                distance=round(best_distance, 3),
            )
            return

        self.get_logger().info(
            f'[识别成功] {best_name} → {room}，距离={best_distance:.3f}')
        self._publish_status(
            'recognized',
            f'识别成功：{best_name}，目标教室 {room}',
            name=best_name,
            room=room,
            distance=round(best_distance, 3),
            force=True,
        )
        self.pub_face_room.publish(String(data=room))
        self._stop_session()

    def _publish_status(self, status, message, force=False, **extra):
        now = time.monotonic()
        key = f'{status}:{message}'
        if not force and key == self.last_status_key and now - self.last_status_time < 2.0:
            return
        payload = {'status': status, 'message': message, **extra}
        self.pub_status.publish(String(
            data=json.dumps(payload, ensure_ascii=False)))
        self.last_status_key = key
        self.last_status_time = now

    def destroy_node(self):
        self._stop_session()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

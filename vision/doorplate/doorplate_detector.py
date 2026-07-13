"""门牌号识别节点 — EasyOCR 预训练模型 / YOLO 自训练模型（方案可切换）。

摄像头：OpenCV 直读（不依赖 ROS2 相机驱动）。

方案切换：改 DETECTOR 变量
  - 'easyocr': 占位方案，开箱即用
  - 'yolo':    正式方案，放 doorplate_best.pt 到同级目录
"""
import time
import re
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cv2

DETECTOR = 'easyocr'
YOLO_MODEL = 'doorplate_best.pt'
YOLO_CONF = 0.5


# ── EasyOCR ──
class EasyOcrDetector:
    def __init__(self):
        try:
            import easyocr as _ec
        except ImportError:
            raise RuntimeError('easyocr 未安装: pip3 install easyocr')
        self.reader = _ec.Reader(['en'], gpu=False)  # type: ignore

    def detect(self, gray):
        results = self.reader.readtext(gray)
        candidates = []
        for (_b, text, conf) in results:
            text = text.strip()
            if re.match(r'^[A-Za-z]?\d{2,4}$', text) and conf > 0.3:
                candidates.append((text, conf))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0]
        return None


# ── YOLO ──
class YoloDetector:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO(YOLO_MODEL)

    def detect(self, frame):
        results = self.model(frame, conf=YOLO_CONF, verbose=False)
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            best = max(results[0].boxes, key=lambda b: b.conf.item())
            label = int(best.cls.item()) if hasattr(best, 'cls') else 0
            return (str(label), best.conf.item())
        return None


# ── ROS2 节点 ──
class DoorplateDetector(Node):
    def __init__(self):
        super().__init__('doorplate_detector')
        self.get_logger().info(f'[方案] {DETECTOR}')

        self.detector = (EasyOcrDetector() if DETECTOR == 'easyocr'
                         else YoloDetector())

        self.pub_result = self.create_publisher(String, '/doorplate_result', 10)

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

        self.process_interval = 1.0
        self.last_process = 0.0
        self.last_result = ''

        self.timer = self.create_timer(0.3, self._process_frame)
        self.get_logger().info('doorplate_detector 已启动')

    def _process_frame(self):
        now = time.time()
        if now - self.last_process < self.process_interval:
            return
        self.last_process = now

        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = self.detector.detect(gray if DETECTOR == 'easyocr' else frame)
        if result is None:
            return
        text, conf = result
        if text != self.last_result:
            self.last_result = text
            self.get_logger().info(f'[门牌] {text} (置信度 {conf:.2f})')
            self.pub_result.publish(String(data=text))

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(DoorplateDetector())
    rclpy.shutdown()


if __name__ == '__main__':
    main()

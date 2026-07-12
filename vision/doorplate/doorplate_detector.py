"""门牌号识别节点 — 占位方案：EasyOCR 预训练模型；正式方案：自训练 YOLO + OCR。

方案切换：修改 DETECTOR 变量即可
  - 'easyocr': 当前占位方案，使用 EasyOCR 预训练模型，开箱即用
  - 'yolo':   正式方案，使用自训练 YOLO 检测门牌区域 + 可选的 OCR 识别

订阅话题：
  - /camera/color/image_raw (sensor_msgs/Image) : RGB 摄像头图像

发布话题：
  - /doorplate_result (std_msgs/String) : 识别的门牌号文本，如 "101"
"""
import time
import re
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

# ── 方案选择 ──
DETECTOR = 'easyocr'  # 'easyocr' | 'yolo'

# YOLO 配置（正式方案时使用）
YOLO_MODEL = 'doorplate_best.pt'  # 自训练权重文件
YOLO_CONFIDENCE = 0.5             # 检测置信度阈值


# ──────────── 占位方案：EasyOCR ────────────
class EasyOcrDetector:
    """基于 EasyOCR 预训练模型的门牌识别（占位方案）。"""

    def __init__(self):
        try:
            import easyocr as _ec
        except ImportError:
            raise RuntimeError('easyocr 未安装，请执行: pip3 install easyocr')
        self.reader = _ec.Reader(['en'], gpu=False)  # type: ignore

    def detect(self, gray):
        """返回 (门牌文本, 置信度) 或 None"""
        results = self.reader.readtext(gray)
        candidates = []
        for (_bbox, text, conf) in results:
            text = text.strip()
            if re.match(r'^[A-Za-z]?\d{2,4}$', text) and conf > 0.3:
                candidates.append((text, conf))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0]
        return None


# ──────────── 正式方案：YOLO + OCR ────────────
class YoloDetector:
    """基于自训练 YOLO 模型的门牌检测（正式方案）。

    TODO: 训练好模型后将 DETECTOR 改为 'yolo'，模型文件放同级目录下。
    """

    def __init__(self):
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError('ultralytics 未安装，请执行: pip3 install ultralytics')
        self.model = YOLO(YOLO_MODEL)

    def detect(self, frame):
        """返回 (门牌文本, 置信度) 或 None。支持可选 OCR 后处理。"""
        results = self.model(frame, conf=YOLO_CONFIDENCE, verbose=False)
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            best = max(results[0].boxes, key=lambda b: b.conf.item())
            conf = best.conf.item()
            # TODO: 可选 — 对检测到的门牌区域运行 OCR 提取具体数字
            # 暂返回检测到的类别名（训练时把标签设为门牌号文本）
            label = int(best.cls.item()) if hasattr(best, 'cls') else 0
            return (str(label), conf)
        return None


# ──────────── ROS2 节点 ────────────
class DoorplateDetector(Node):
    def __init__(self):
        super().__init__('doorplate_detector')

        self.get_logger().info(f'[方案] 使用检测器: {DETECTOR}')

        if DETECTOR == 'easyocr':
            self.detector = EasyOcrDetector()
        elif DETECTOR == 'yolo':
            self.detector = YoloDetector()
        else:
            raise ValueError(f'未知检测方案: {DETECTOR}')

        self.pub_result = self.create_publisher(String, '/doorplate_result', 10)
        self.bridge = CvBridge()
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.on_image, 10)

        self.process_interval = 1.0
        self.last_process_time = 0.0
        self.last_result = ''

        self.get_logger().info('doorplate_detector 已启动')

    def on_image(self, msg):
        now = time.time()
        if now - self.last_process_time < self.process_interval:
            return
        self.last_process_time = now

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception:
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


def main(args=None):
    rclpy.init(args=args)
    node = DoorplateDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

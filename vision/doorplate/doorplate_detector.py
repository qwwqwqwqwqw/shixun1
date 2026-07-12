"""门牌号识别节点 — 使用 EasyOCR 预训练模型（无需额外训练）。

流程：
  摄像头 → EasyOCR 文字检测+识别 → 筛选房间号（3位数字） → /doorplate_result

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

try:
    import easyocr as _easyocr
    HAS_EASYOCR = True
except ImportError:
    _easyocr = None  # type: ignore
    HAS_EASYOCR = False


class DoorplateDetector(Node):
    def __init__(self):
        super().__init__('doorplate_detector')

        assert HAS_EASYOCR, 'easyocr 未安装，请执行: pip3 install easyocr'

        # ── EasyOCR 引擎（首次运行会下载模型 ~30MB）──
        self.get_logger().info('正在初始化 EasyOCR（首次需下载模型，约 30MB）...')
        self.reader = _easyocr.Reader(  # type: ignore
            ['en'],
            gpu=False
        )
        self.get_logger().info('EasyOCR 就绪')

        # ── 发布 /doorplate_result ──
        self.pub_result = self.create_publisher(
            String, '/doorplate_result', 10)

        # ── 订阅摄像头 ──
        self.bridge = CvBridge()
        self.sub_image = self.create_subscription(
            Image, '/camera/color/image_raw', self.on_image, 10)

        # ── 节流 ──
        self.process_interval = 1.0
        self.last_process_time = 0.0
        self.last_result = ''

    def on_image(self, msg):
        now = time.time()
        if now - self.last_process_time < self.process_interval:
            return
        self.last_process_time = now

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception:
            return

        # 转灰度加速 OCR
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # EasyOCR 检测+识别
        results = self.reader.readtext(gray)

        room_numbers = []
        for (_bbox, text, confidence) in results:
            text = text.strip()
            # 筛选 2-4 位数字（门牌号常见格式：101, 102, A01, 301）
            if re.match(r'^[A-Za-z]?\d{2,4}$', text):
                if confidence > 0.3:
                    room_numbers.append((text, confidence))

        if room_numbers:
            # 取置信度最高的
            room_numbers.sort(key=lambda x: x[1], reverse=True)
            best = room_numbers[0][0]

            if best != self.last_result:
                self.last_result = best
                self.get_logger().info(
                    f'[门牌] {best} (置信度 {room_numbers[0][1]:.2f})')
                msg_out = String(data=best)
                self.pub_result.publish(msg_out)


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

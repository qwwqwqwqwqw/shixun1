"""门牌号识别节点 — C组员负责实现。

使用 YOLOv5 检测门牌区域，再通过 OCR 提取门牌号码文本。

订阅话题：
  - /camera/image_raw (sensor_msgs/Image) : 摄像头图像

发布话题：
  - /doorplate_result (std_msgs/String) : 识别的门牌号文本
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class DoorplateDetector(Node):
    def __init__(self):
        super().__init__('doorplate_detector')
        # TODO: C组员实现 — 订阅摄像头图像
        self.pub_result = self.create_publisher(
            String, '/doorplate_result', 10)
        self.get_logger().info('doorplate_detector 已启动 — 等待摄像头图像')
        # TODO: C组员加载 YOLOv5 权重 (best.pt) + OCR 引擎

    def detect(self, image):
        """YOLO 检测门牌区域 → OCR 提取数字 → 发布结果"""
        # TODO: C组员实现检测和识别流水线
        pass


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

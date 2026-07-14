"""门牌号识别节点 — EasyOCR 预训练模型 / YOLO 自训练模型（方案可切换）。

摄像头：OpenCV 直读（不依赖 ROS2 相机驱动）。

检测流程（YOLO 方案）:
    摄像头帧 → YOLO 检测 → classboard? → 裁剪 ROI(+10px) → Otsu 增强 → EasyOCR 数字 → /doorplate_result

方案切换：改 DETECTOR 变量
  - 'easyocr': 占位方案，开箱即用
  - 'yolo':    正式方案，YOLO 检测门牌区域 + Otsu 增强 + EasyOCR 读数字
"""
import time
import re
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cv2
import numpy as np
import torch

DETECTOR = 'yolo'
YOLO_MODEL = 'doorplate_best.pt'
YOLO_CONF = 0.3
# classboard 和 electronic_board 做 OCR，classboard 优先
TARGET_OCR_CLASSES = {'classboard', 'electronic_board'}
DOORPLATE_CLASSES = {'classboard', 'electronic_board'}


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


# ── YOLO + Otsu 增强 + EasyOCR ──
class YoloDetector:
    """YOLO 检测门牌区域 → Otsu 增强 → EasyOCR 读数字。

    流程: YOLO → classboard? → 裁剪(+10px) → Otsu 增强 → 纯数字OCR
    """

    PAD = 10                    # ROI 外扩像素
    OCR_ALLOW = '0123456789'    # 只识别数字

    def __init__(self):
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.model = torch.hub.load('/home/jetson/yolov5', 'custom',
                                     path=YOLO_MODEL, force_reload=False,
                                     autoshape=False, verbose=False,
                                     source='local')
        self.model = self.model.to(self.device).eval()
        self.stride = max(int(self.model.stride), 32)
        self.names = self.model.names
        self.img_size = 640
        import easyocr
        self.ocr = easyocr.Reader(['en'], gpu=False)

    # ── 裁剪 ROI ──
    def _crop_roi(self, frame, bbox):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        x1 = max(0, x1 - self.PAD)
        y1 = max(0, y1 - self.PAD)
        x2 = min(w, x2 + self.PAD)
        y2 = min(h, y2 + self.PAD)
        if x1 >= x2 or y1 >= y2:
            return None
        return frame[y1:y2, x1:x2]

    # ── Otsu 增强 ──
    def _enhance_otsu(self, roi):
        """灰度 → CLAHE → Otsu → 开闭去噪 → 反转 → 放大。"""
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        # 确保文字=黑(0)、背景=白(255)
        # 如果黑色像素占多数，说明文字是白色 → 反转
        if np.sum(binary < 127) > binary.size / 2:
            binary = cv2.bitwise_not(binary)
        # 小图放大到 600px
        h, w = binary.shape[:2]
        if min(h, w) < 400:
            scale = 600.0 / min(h, w)
            binary = cv2.resize(binary, (int(w * scale), int(h * scale)),
                                interpolation=cv2.INTER_CUBIC)
        return binary

    # ── OCR 数字识别 ──
    def _recognize(self, processed_roi):
        import re
        if len(processed_roi.shape) == 2:
            processed_roi = cv2.cvtColor(processed_roi, cv2.COLOR_GRAY2BGR)
        results = self.ocr.readtext(processed_roi, min_size=3)
        if not results:
            return None
        # OCR 混淆校正：原始文本必须含数字（排除纯字母噪音）
        fix = str.maketrans({'O': '0', 'I': '1', 'L': '1', 'S': '5',
                              'Z': '2', 'B': '8', 'T': '7', 'A': '4'})
        for (_b, text, conf) in sorted(results, key=lambda r: -r[2]):
            raw = text.strip().upper()
            if not re.search(r'\d', raw):
                continue
            t = raw.translate(fix)
            t = re.sub(r'[^\d]', '', t)
            if len(t) == 3 and conf > 0.2:
                return (t, conf)
        return None

    # ── 预处理 ──
    def _preprocess(self, frame):
        """letterbox + 归一化，与训练时一致。"""
        h0, w0 = frame.shape[:2]
        r = self.img_size / max(h0, w0)
        if r != 1:
            nw, nh = int(w0 * r), int(h0 * r)
            frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        h, w = frame.shape[:2]
        dw, dh = self.img_size - w, self.img_size - h
        dw, dh = dw // 2, dh // 2
        frame = cv2.copyMakeBorder(frame, dh, dh, dw, dw,
                                    cv2.BORDER_CONSTANT, value=(114, 114, 114))
        frame = frame[:, :, ::-1].transpose(2, 0, 1)  # BGR→RGB, HWC→CHW
        frame = np.ascontiguousarray(frame, dtype=np.float32) / 255.0
        return torch.from_numpy(frame).unsqueeze(0).to(self.device), (h0, w0)

    # ── 坐标还原 ──
    def _scale_boxes(self, pred, h0, w0):
        gain = min(self.img_size / h0, self.img_size / w0)
        pad_w = (self.img_size - w0 * gain) / 2
        pad_h = (self.img_size - h0 * gain) / 2
        pred[:, [0, 2]] -= pad_w
        pred[:, [1, 3]] -= pad_h
        pred[:, :4] /= gain

    # ── NMS ──
    def _nms(self, pred):
        from torchvision.ops import nms
        keep = []
        for cls_id in pred[:, 5].unique():
            mask = (pred[:, 5] == cls_id) & (pred[:, 4] >= YOLO_CONF)
            p = pred[mask]
            if len(p) == 0:
                continue
            idx = nms(p[:, :4], p[:, 4], iou_thres=0.3)
            keep.append(p[idx])
        return torch.cat(keep, dim=0) if keep else pred[:0]

    # ── 主入口 ──
    def detect(self, frame):
        """YOLO → classboard 路由 → 裁剪 → Otsu → OCR。"""
        tensor, (h0, w0) = self._preprocess(frame)
        with torch.no_grad():
            pred = self.model(tensor)[0]
        if len(pred) == 0:
            return None
        pred = self._nms(pred)
        if len(pred) == 0:
            return None
        self._scale_boxes(pred, h0, w0)
        pred = pred.cpu()

        candidates = []
        for *xyxy, conf, cls_id in pred.tolist():
            cls_id = int(cls_id)
            cls_name = self.names.get(cls_id, '')
            if cls_name not in DOORPLATE_CLASSES:
                continue
            x1, y1, x2, y2 = map(int, xyxy)
            bbox = (x1, y1, x2, y2)

            if cls_name in TARGET_OCR_CLASSES:
                roi = self._crop_roi(frame, bbox)
                if roi is None or roi.size == 0:
                    continue
                enhanced = self._enhance_otsu(roi)
                ocr_result = self._recognize(enhanced)
                if ocr_result is None:
                    continue
                text, ocr_conf = ocr_result
                candidates.append((cls_name, text, min(conf, ocr_conf)))

        if not candidates:
            return None
        # classboard 优先 → electronic_board 退取
        candidates.sort(key=lambda x: (0 if x[0] == 'classboard' else 1, -x[2]))
        return (candidates[0][1], candidates[0][2])


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
        assert self.cap is not None
        now = time.time()
        if now - self.last_process < self.process_interval:
            return
        self.last_process = now

        ret, frame = self.cap.read()
        if not ret:
            return

        if DETECTOR == 'easyocr':
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            result = self.detector.detect(gray)
        else:
            result = self.detector.detect(frame)
        if result is None:
            return
        text, conf = result
        if text != self.last_result:
            self.last_result = text
            self.get_logger().info(f'[门牌] {text} (置信度 {conf:.2f})')
            self.pub_result.publish(String(data=text))

    def destroy_node(self):
        if self.cap is not None:
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(DoorplateDetector())
    rclpy.shutdown()


if __name__ == '__main__':
    main()

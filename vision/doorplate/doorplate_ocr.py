"""门牌号 OCR 测试工具 — 调用 YOLOv5 detect.py + Otsu 增强 + EasyOCR 数字识别。

独立脚本，不依赖 ROS2。

用法:
    cd vision/doorplate
    python doorplate_ocr.py --image 508.jpg --model best.pt

流程:
    1. subprocess 调用 detect.py → YOLOv5 检测 + 自动裁剪
    2. 读取裁剪图 → Otsu 增强 → EasyOCR 纯数字识别
    3. 输出标注图 + 门牌号
"""

import subprocess
import easyocr
import os
import glob
import cv2
import sys
import numpy as np
import shutil
from datetime import datetime
from pathlib import Path


class DoorplateRecognition:
    """YOLOv5 detect.py 检测 + Otsu + EasyOCR 识别。"""

    OCR_ALLOW = '0123456789'
    OCR_CLASSES = ['classboard', 'electronic_board']  # 都做 OCR，classboard 优先
    IMG_SIZE = 640

    def __init__(self, model_path, conf=0.3, output_dir='debug_output'):
        self.model_path = os.path.abspath(model_path)
        self.conf = conf
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 找 YOLOv5 源码目录（torch hub 缓存）
        self.yolov5_dir = self._find_yolov5_dir()
        self.detect_script = os.path.join(self.yolov5_dir, 'detect.py')
        if not os.path.isfile(self.detect_script):
            raise FileNotFoundError(f'detect.py 不存在: {self.detect_script}')
        print(f'[Init] YOLOv5 源码: {self.yolov5_dir}')

        # 加载 EasyOCR
        self.reader = easyocr.Reader(['en'], gpu=False)
        print(f'[Init] 模型: {model_path}  阈值: {conf}')
        print(f'[Init] 输出: {self.output_dir.resolve()}')

    def _find_yolov5_dir(self):
        """查找 torch hub 缓存的 YOLOv5 源码。"""
        import torch
        hub_dir = torch.hub.get_dir()
        # 查找 ultralytics_yolov5_master
        for root, dirs, _ in os.walk(hub_dir):
            for d in dirs:
                if 'ultralytics_yolov5' in d:
                    return os.path.join(root, d)
        # 备选：直接 hardcode 常见路径
        paths = [
            os.path.expanduser('~/.cache/torch/hub/ultralytics_yolov5_master'),
        ]
        for p in paths:
            if os.path.isdir(p):
                return p
        raise RuntimeError('未找到 YOLOv5 源码目录，请先运行过 torch.hub 加载模型')

    # ── Otsu 增强 ──
    def _enhance_otsu(self, roi):
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # 确保文字=黑(0)、背景=白(255)
        # 如果黑色像素占多数，说明文字是白色 → 反转
        if np.sum(binary < 127) > binary.size / 2:
            binary = cv2.bitwise_not(binary)
        k = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)
        h, w = binary.shape[:2]
        if max(h, w) < 400:
            scale = 600 / max(h, w)
            binary = cv2.resize(binary, (int(w * scale), int(h * scale)),
                                interpolation=cv2.INTER_CUBIC)
        return binary

    # ── OCR ──
    def _ocr_digits(self, roi, label=''):
        """OCR 识别。EasyOCR 需要 3 通道输入。"""
        import re
        if len(roi.shape) == 2:
            roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)

        # 获取所有检测结果
        results = self.reader.readtext(roi, detail=1, min_size=3)
        print(f'    [调试{label}] OCR检测数={len(results)}:')
        for (_b, text, conf) in sorted(results, key=lambda r: -r[2]):
            print(f'      text="{text.strip()}" conf={conf:.3f}')

        # 从结果中提取数字（OCR 混淆校正，必须原始含数字）
        candidates = []
        for (_b, text, conf) in results:
            raw = text.strip().upper()
            # 原始文本必须至少包含一个数字（排除纯字母噪音如 "Ntaz"）
            if not re.search(r'\d', raw):
                continue
            # OCR 常见混淆：O→0, I/l→1, S→5, Z→2, B→8, T→7, A→4
            t = raw.replace('O', '0').replace('I', '1').replace('L', '1')
            t = t.replace('S', '5').replace('Z', '2').replace('B', '8')
            t = t.replace('T', '7').replace('A', '4')
            t = re.sub(r'[^\d]', '', t)
            if len(t) == 3 and conf > 0.2:
                candidates.append((t, conf))
        if candidates:
            candidates.sort(key=lambda x: -x[1])
            return candidates[0][0]
        return ''

    # ── 画框 ──
    def _draw_boxes(self, img, detections):
        annotated = img.copy()
        for d in detections:
            color = (0, 255, 0)
            x1, y1, x2, y2 = d['bbox']
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{d['cls']} {d['conf']:.2f}"
            if d.get('number'):
                label += f' -> {d["number"]}'
            cv2.rectangle(annotated, (x1, y1 - 21),
                          (x1 + len(label) * 10, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 3, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return annotated

    # ── 主流程 ──
    def process(self, image_path):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        img = cv2.imread(image_path)
        if img is None:
            print(f'[错误] 无法读取图片: {image_path}')
            return

        # 步骤1：运行 YOLOv5 detect.py
        run_dir = (self.output_dir / f'run_{ts}').resolve()
        run_dir.mkdir(parents=True, exist_ok=True)

        print(f'\n[步骤1] YOLOv5 检测...')
        cmd = [
            sys.executable, self.detect_script,
            '--weights', self.model_path,
            '--img', str(self.IMG_SIZE),
            '--conf', str(self.conf),
            '--iou-thres', '0.45',
            '--max-det', '50',
            '--source', os.path.abspath(image_path),
            '--save-crop',
            '--save-txt',
            '--project', str(run_dir),
            '--name', 'exp',
            '--exist-ok',
        ]
        print(f'  命令: {" ".join(cmd)}')

        result = subprocess.run(cmd, capture_output=True, text=True,
                                 cwd=self.yolov5_dir)
        print(result.stderr.strip() if result.stderr else result.stdout.strip())

        if result.returncode != 0:
            print(f'[错误] detect.py 执行失败（返回码={result.returncode}）')
            return
        print('[步骤1] 检测完成')

        # 步骤2：读取裁剪图 → classboard/doorplate 都做 OCR，classboard 优先
        crop_dir = run_dir / 'exp' / 'crops'
        if not crop_dir.exists():
            print('[步骤2] 无裁剪图（模型未检测到任何目标）')
            return

        all_classes = [d for d in os.listdir(crop_dir)
                       if (crop_dir / d).is_dir()]
        print(f'[步骤2] 检测到的类别: {all_classes}')
        print(f'         OCR 目标: {self.OCR_CLASSES}（classboard 优先）')

        candidates = []  # [(cls_name, number)]

        for cls_name in sorted(os.listdir(crop_dir)):
            cls_path = crop_dir / cls_name
            if not cls_path.is_dir():
                continue

            images = glob.glob(str(cls_path / '*.jpg'))
            images += glob.glob(str(cls_path / '*.png'))
            if not images:
                continue

            for imp in images:
                roi = cv2.imread(imp)
                if roi is None:
                    continue

                if cls_name in self.OCR_CLASSES:
                    enhanced = self._enhance_otsu(roi)
                    otsu_path = self.output_dir / f'otsu_{cls_name}_{ts}.jpg'
                    cv2.imwrite(str(otsu_path), enhanced)
                    number = self._ocr_digits(enhanced, '_otsu') or self._ocr_digits(roi, '_raw')
                    print(f'  [{cls_name}] OCR → "{number}"')
                    if number:
                        candidates.append((cls_name, number))
                else:
                    print(f'  [{cls_name}] 跳过（不识别）')

        # 步骤3：classboard 优先 → doorplate 退取
        print(f'\n{"="*50}')
        print('[结果]')
        final = None
        for cls_name, number in candidates:
            if cls_name == 'classboard':
                final = number
                break
        if final is None and candidates:
            final = candidates[0][1]

        if final:
            print(f'  >>> 门牌号: "{final}" <<<')
        else:
            print(f'  — 未识别到数字')

        # 保存 YOLOv5 标注图（detect.py 自动绘制的，含所有检测框）
        exp_dir = run_dir / 'exp'
        for f in sorted(exp_dir.glob('*.jpg')) + sorted(exp_dir.glob('*.png')):
            if 'crops' not in str(f):
                shutil.copy(str(f), self.output_dir / f'annotated_{ts}.jpg')
                print(f'\n[标注图] {f.name} → annotated_{ts}.jpg')
                break

        print(f'\n[输出] 文件保存在: {self.output_dir.resolve()}')


def main():
    import argparse
    p = argparse.ArgumentParser(description='门牌号 OCR 测试')
    p.add_argument('--image', required=True, help='图片路径')
    p.add_argument('--model', required=True, help='模型 .pt 路径')
    p.add_argument('--conf', type=float, default=0.3, help='置信度阈值')
    p.add_argument('--out', default='debug_output', help='输出目录')
    args = p.parse_args()

    recognizer = DoorplateRecognition(args.model, args.conf, args.out)
    recognizer.process(args.image)


if __name__ == '__main__':
    main()

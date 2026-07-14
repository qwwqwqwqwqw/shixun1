"""YOLO 检测 + 裁剪 + OCR 本地测试脚本（图片模式，不依赖 ROS/摄像头）"""
import os
import sys

# 配置
IMG_PATH = 'test_doorplate.jpg'  # 测试图片（放一张带门牌的照片）
MODEL_PATH = 'best.pt'

DOORPLATE_CLASSES = {'doorplate', 'classboard'}


def main():
    base = os.path.dirname(os.path.abspath(__file__))

    # 1. 加载模型
    print('[1/4] 加载 YOLO 模型...')
    from ultralytics import YOLO
    model = YOLO(os.path.join(base, MODEL_PATH))
    print(f'  类别: {model.names}')

    # 2. 加载 OCR
    print('[2/4] 加载 EasyOCR...')
    import easyocr
    ocr = easyocr.Reader(['en'], gpu=False)

    # 3. 检测
    img_path = os.path.join(base, IMG_PATH)
    if not os.path.exists(img_path):
        print(f'\n❌ 请放一张测试图片: {img_path}')
        sys.exit(1)

    import cv2
    frame = cv2.imread(img_path)
    print(f'[3/4] 检测图片: {IMG_PATH} ({frame.shape[1]}x{frame.shape[0]})')

    results = model(frame, conf=0.4, verbose=False)
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        print('  ❌ 未检测到任何物体')
        return

    # 4. 遍历结果
    print(f'[4/4] 检测到 {len(boxes)} 个物体:')
    names = model.names

    for i, box in enumerate(boxes):
        cls_id = int(box.cls.item())
        cls_name = names.get(cls_id, 'unknown')
        conf = box.conf.item()
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        print(f'\n  [{i+1}] {cls_name} (置信度 {conf:.2f}) 位置 [{x1},{y1} {x2},{y2}]')

        if cls_name not in DOORPLATE_CLASSES:
            print(f'       ⏭ 跳过（非门牌类别）')
            continue

        # 裁剪 + OCR
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            print(f'       ⚠ 裁剪区域为空')
            continue

        # 保存裁剪图
        crop_path = os.path.join(base, f'crop_{i+1}.jpg')
        cv2.imwrite(crop_path, crop)
        print(f'       ✂ 已保存: {crop_path}')

        ocr_results = ocr.readtext(crop)
        if not ocr_results:
            print(f'       ❌ OCR 未识别到文字')
            continue

        for (_b, text, ocr_conf) in ocr_results:
            print(f'       🔍 OCR: "{text}" (置信度 {ocr_conf:.2f})')

    print('\n完成！')


if __name__ == '__main__':
    main()

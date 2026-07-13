"""人脸识别测试 — 摄像头实时模式。

使用 dlib 预训练模型，比对 known_faces/ 目录下的人脸照片。
运行 5 秒，输出识别结果。
"""
import face_recognition
import cv2
import os
import time

print("=" * 50)
print("  人脸识别测试 (摄像头模式)")
print("=" * 50)

# ── 1. 加载已知人脸 ──
FACE_DIR = os.path.join(os.path.dirname(__file__), "known_faces")
known_encodings = []
known_names = []

print(f"\n[加载] 人脸库: {FACE_DIR}")
for fname in os.listdir(FACE_DIR):
    if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
    name = os.path.splitext(fname)[0]
    path = os.path.join(FACE_DIR, fname)
    img = face_recognition.load_image_file(path)
    encodings = face_recognition.face_encodings(img)
    if encodings:
        known_encodings.append(encodings[0])
        known_names.append(name)
        print(f"   ✅ {name}")
    else:
        print(f"   ❌ {fname} — 未检测到人脸")

if not known_names:
    print("\n❌ 未加载到任何人脸，请先放入照片到 known_faces/")
    exit(1)

# ── 2. 打开摄像头 ──
print("\n[相机] 正在打开摄像头...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ 无法打开摄像头，尝试索引 2...")
    cap = cv2.VideoCapture(2)
if not cap.isOpened():
    print("❌ 摄像头不可用")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("✅ 摄像头已就绪，开始识别（5 秒）...")

# ── 3. 实时识别 5 秒 ──
DURATION = 5.0   # 识别时长（秒）
PROCESS_EVERY_N_FRAMES = 15  # 每 15 帧处理一次
start_time = time.time()
frame_count = 0
results = {}     # name → 识别次数

while time.time() - start_time < DURATION:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.05)
        continue

    frame_count += 1
    if frame_count % PROCESS_EVERY_N_FRAMES != 0:
        # 显示实时画面（带倒计时）
        remaining = DURATION - (time.time() - start_time)
        cv2.putText(frame, f"识别中... {remaining:.1f}s",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("人脸识别测试 — 按 Q 提前退出", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    # 缩小区理加速
    small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    locations = face_recognition.face_locations(rgb, model='hog')
    if locations:
        encodings = face_recognition.face_encodings(rgb, locations)
        for encoding in encodings:
            distances = face_recognition.face_distance(known_encodings, encoding)
            best_idx = int(min(range(len(distances)), key=distances.__getitem__))
            if distances[best_idx] < 0.55:
                name = known_names[best_idx]
                results[name] = results.get(name, 0) + 1

    remaining = DURATION - (time.time() - start_time)
    cv2.putText(frame, f"识别中... {remaining:.1f}s",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("人脸识别测试 — 按 Q 提前退出", frame)
    cv2.waitKey(1)

# ── 4. 输出结果 ──
cap.release()
cv2.destroyAllWindows()

print("\n" + "=" * 50)
print(f"  识别结束（共处理 {frame_count} 帧）")
print("=" * 50)

if results:
    # 取出现次数最多的人
    best_name = max(results, key=lambda k: results[k])
    count = results[best_name]
    print(f"✅ 识别结果: {best_name}（命中 {count} 次）")
else:
    print("❌ 未识别到已知人脸")

"""人脸识别测试 — 摄像头实时模式。

使用 dlib 预训练模型，比对 known_faces/ 目录下的人脸照片。
首次运行时提取特征并缓存，后续秒启动。
"""
import face_recognition  # pyright: ignore[reportMissingImports]
import cv2  # pyright: ignore[reportMissingImports]
import os
import pickle
import time

print("=" * 50)
print("  人脸识别测试 (摄像头模式)")
print("=" * 50)

# ── 1. 加载已知人脸（缓存优先） ──
FACE_DIR = os.path.join(os.path.dirname(__file__), "known_faces")
CACHE_PATH = os.path.join(FACE_DIR, "face_encodings.pkl")
known_encodings = []
known_names = []

print(f"\n[加载] 人脸库: {FACE_DIR}")

# 尝试从缓存加载
if os.path.isfile(CACHE_PATH):
    cache_mtime = os.path.getmtime(CACHE_PATH)
    photos = [os.path.join(FACE_DIR, f) for f in os.listdir(FACE_DIR)
              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if photos and all(os.path.getmtime(p) <= cache_mtime for p in photos):
        try:
            with open(CACHE_PATH, 'rb') as f:
                data = pickle.load(f)
            known_encodings = data['encodings']
            known_names = data['names']
            print(f"   从缓存加载 ({len(known_names)} 张人脸) → {CACHE_PATH}")
        except Exception as e:
            print(f"   ⚠️ 缓存无效，重新扫描: {e}")

# 缓存不可用 → 扫描照片
if not known_names:
    print("   扫描照片并提取特征...")
    for fname in sorted(os.listdir(FACE_DIR)):
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

    # 保存缓存
    if known_encodings:
        with open(CACHE_PATH, 'wb') as f:
            pickle.dump({'encodings': known_encodings, 'names': known_names}, f)
        print(f"   缓存已保存: {CACHE_PATH}")

if not known_names:
    print("\n❌ 未加载到任何人脸，请先放入照片到 known_faces/")
    exit(1)

# ── 2. 打开摄像头 ──
print("\n[相机] 正在打开摄像头...")
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"  # 静默摄像头索引报错
cap = None
for camera_index in [2, 4, 6, 0]:
    candidate = cv2.VideoCapture(camera_index)
    if candidate.isOpened():
        ok, _ = candidate.read()
        if ok:
            cap = candidate
            print(f"✅ 摄像头 /dev/video{camera_index} 已就绪")
            break
    candidate.release()
if cap is None:
    print("❌ 摄像头不可用")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("开始识别（5 秒）...")

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
            if distances[best_idx] < 0.5:
                name = known_names[best_idx]
                results[name] = results.get(name, 0) + 1

# ── 4. 输出结果 ──
cap.release()

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

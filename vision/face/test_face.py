import face_recognition
import os

print("=" * 50)
print("人脸识别测试 (图片模式)")
print("=" * 50)

# 1. 加载人脸库
known_encodings = []
known_names = []
face_dir = "known_faces/"

print(f"\n📂 加载人脸库: {face_dir}")

if not os.path.exists(face_dir):
    print(f"❌ 文件夹不存在: {face_dir}")
    exit()

files = os.listdir(face_dir)
if not files:
    print(f"❌ {face_dir} 为空，请先放入人脸照片")
    exit()

for f in files:
    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
        name = os.path.splitext(f)[0]
        img_path = os.path.join(face_dir, f)
        img = face_recognition.load_image_file(img_path)
        enc = face_recognition.face_encodings(img)
        if enc:
            known_encodings.append(enc[0])
            known_names.append(name)
            print(f"   ✅ {name} (加载成功)")
        else:
            print(f"   ❌ {f} (未检测到人脸)")

if not known_names:
    print("\n❌ 未加载到任何人脸")
    exit()

# 2. 识别测试图片
test_image = "test.jpg"
if not os.path.exists(test_image):
    print(f"\n❌ 测试图片不存在: {test_image}")
    print("请放一张 test.jpg 到当前目录")
    exit()

print(f"\n🔍 识别测试图片: {test_image}")
img = face_recognition.load_image_file(test_image)
face_locations = face_recognition.face_locations(img)
face_encodings = face_recognition.face_encodings(img, face_locations)

if not face_encodings:
    print("❌ 测试图片中未检测到人脸")
    exit()

print(f"\n检测到 {len(face_locations)} 张人脸")

for encoding in face_encodings:
    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.55)
    if True in matches:
        idx = matches.index(True)
        print(f"✅ 识别结果: {known_names[idx]}")
    else:
        print("❌ 未识别（陌生人）")

print("\n" + "=" * 50)
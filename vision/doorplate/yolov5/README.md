# 门牌号识别 — 环境部署与使用说明

C组员 | YOLOv5 检测 + Otsu 增强 + EasyOCR 数字识别

---

## 一、环境部署

### 1. Python 版本

**必须使用 Python 3.10**（3.11+ 版本依赖兼容问题多，已验证不可用）。

### 2. 创建虚拟环境

```powershell
cd D:\a\shixun1
C:\Users\89226\AppData\Local\Programs\Python\Python310\python.exe -m venv face_env
```

### 3. 激活虚拟环境

```powershell
face_env\Scripts\activate
```

> 如果 PowerShell 报执行策略错误，用 CMD 运行：输入 `cmd` 回车后执行上述命令。

### 4. 安装依赖（严格按顺序）

```powershell
# 第1步：PyTorch CPU 版
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 第2步：YOLOv5 额外依赖
pip install pandas tqdm seaborn psutil pyyaml

# 第3步：EasyOCR
pip install easyocr

# 第4步：OpenCV
pip install opencv-python
```

### 5. 人脸识别依赖（face_recognition）

**如果在系统 Python 3.10 中直接安装**（不使用虚拟环境，已验证可行）：

```powershell
# 0. 降级 setuptools（新版移除了 pkg_resources，face_recognition_models 依赖它）
pip install "setuptools<70"

# 1. 安装预编译 dlib（避免 C++ 编译失败）
pip install dlib-bin

# 2. 安装 face_recognition（跳过 dlib 编译）
pip install face_recognition --no-deps

# 3. 手动安装其余依赖
pip install face_recognition_models numpy Pillow Click

# 4. 如果 face_recognition_models 报错，用 git 方式安装
pip install git+https://github.com/ageitgey/face_recognition_models
```

### 6. 验证安装

```powershell
python -c "import torch; print('torch', torch.__version__)"
python -c "import easyocr; print('easyocr OK')"
python -c "import cv2; print('opencv', cv2.__version__)"
python -c "import face_recognition; print('face_recognition OK')"
```

---

## 二、模型文件

将训练好的 YOLOv5 `.pt` 模型放到 `vision/doorplate/` 目录：

```
vision/doorplate/
├── best.pt              ← 训练好的模型（不提交 Git）
├── doorplate_detector.py
├── doorplate_ocr.py
└── yolov5/
    └── README.md
```

> `.gitignore` 已配置忽略 `.pt` 文件，模型不会提交到 GitHub。

---

## 三、本地测试

```powershell
cd vision\doorplate
python doorplate_ocr.py --image 测试图.jpg --model best.pt
```

输出文件在 `debug_output/`：
- `annotated_*.jpg` — 原图 + 检测框
- `otsu_*.jpg` — Otsu 增强后的二值图
- 终端输出 — 识别到的门牌号

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--image` | 必填 | 测试图片路径 |
| `--model` | 必填 | YOLOv5 模型 `.pt` 路径 |
| `--conf` | 0.3 | 置信度阈值（遇漏检可降到 0.15） |
| `--out` | debug_output | 输出目录 |

---

## 四、识别的类别

模型检测到的类别共 10 类：

| ID | 类别 | 是否 OCR |
|----|------|:--:|
| 0 | doorplate | ❌ |
| 1 | classboard | ✅ 优先 |
| 2 | electronic_board | ✅ 备用 |
| 3-9 | elevator, fire_door, ... | ❌ |

**优先级**：classboard > electronic_board，都检出时取 classboard 的结果。

---

## 五、OCR 识别流程

```
YOLOv5 检测 → 裁剪 ROI(+10px) → Otsu 增强 → EasyOCR → 数字提取
```

Otsu 增强流水线：
```
灰度 → CLAHE → Otsu 二值化 → 开闭去噪 → 反转 → 等比例放大
```

OCR 后处理：
- 过滤纯字母噪音（原始文本必须含数字）
- 字母混淆校正：O→0, S→5, I→1, Z→2, B→8, T→7, A→4
- 只取 3 位纯数字

---

## 六、小车部署

模型文件通过 `scripts/sync.sh` 同步到小车。ROS2 节点启动后发布 `/doorplate_result` 话题。

```bash
# 小车上
cd ~/icar_classroom_guide/vision/doorplate
python3 doorplate_detector.py
```

---

## 七、已知问题

- 当画面中同时存在 electronic_board 和 classboard 时，模型可能只检测到其中一个（训练数据偏差导致）
- 深度优化需增加 classboard 训练样本的多样性

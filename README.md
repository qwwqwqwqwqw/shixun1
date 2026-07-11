# icar_classroom_guide — 智能小车教室导航系统

## 项目定位
基于 ROS2 + Nav2 的智能小车教室导航系统，支持两种触发模式：
1. **手动模式**：小程序输入教室号 → 小车导航到目标教室
2. **人脸模式**（酒店入住模拟）：摄像头识别人脸 → 自动映射房间号 → 导航到对应房间

到达后通过 YOLOv5 + OCR 进行门牌号视觉确认，确保到达正确教室。

## 核心技术栈
| 技术 | 用途 |
|------|------|
| ROS2 Humble (rclpy) | 机器人中间件 |
| Nav2 | 自主导航框架 |
| YOLOv5 + OCR | 门牌号检测与识别 |
| face_recognition | 人脸识别 |
| 微信小程序 | 前端控制 |
| Docker | 跨容器分布式通信 |

## 五人团队分工
| 成员 | 职责 | 负责目录 |
|------|------|----------|
| **A** | 建图与坐标标注 | `maps/`、`config/classrooms.yaml` |
| **B（组长）** | 导航核心节点 | `dev_ws/src/guide_pkg/`、接口文档 |
| **C** | 视觉识别（门牌+人脸） | `vision/`、`config/face_room_map.yaml` |
| **D** | 接口与前端 | `dev_ws/src/aiserver_pkg/`、`app/` |
| **E** | 系统集成与测试 | `scripts/`、`records/`、`.github/`、`docs/` |

## 目录结构
```
icar_classroom_guide/
├── dev_ws/src/          # ROS2 工作空间（B、D）
│   ├── guide_pkg/       # 导航核心包（B）
│   └── aiserver_pkg/    # 指令接口包（D）
├── vision/              # 视觉识别模块（C）
│   ├── doorplate/       # 门牌识别（YOLO+OCR）
│   └── face/            # 人脸识别
├── app/                 # 前端控制（D）
│   ├── miniprogram/     # 微信小程序
│   └── web/             # Web 控制台
├── maps/                # 地图文件（A）
├── records/             # 测试记录（全员）
├── scripts/             # 辅助脚本（E）
├── docs/                # 文档（E+全员）
├── .github/workflows/   # CI/CD（E）
├── README.md            # 项目总览
├── .gitignore
├── requirements.txt     # Python 依赖
└── docker-compose.yml   # 双容器编排
```

详细目录说明见 [`docs/目录说明.md`](docs/目录说明.md)

## 快速开始

### 1. 环境准备
```bash
# 安装依赖
bash scripts/install_deps.sh
```

### 2. 编译 ROS2 工作空间
```bash
cd dev_ws
colcon build --symlink-install
source install/setup.bash
```

### 3. 配置教室坐标（A组员）
编辑 `dev_ws/src/guide_pkg/config/classrooms.yaml`，填入实际建图坐标。

### 4. 配置人脸映射（C组员）
- 在 `vision/face/known_faces/` 放入注册用户照片
- 编辑 `dev_ws/src/guide_pkg/config/face_room_map.yaml` 更新映射

### 5. 启动系统
```bash
# 启动导航核心节点
ros2 launch guide_pkg guide_launch.py

# 启动指令接口节点
ros2 launch aiserver_pkg aiserver_launch.py

# 启动视觉识别（C组员）
python3 vision/launch/vision_launch.py
```

### 6. 测试
```bash
# 手动模式测试
python3 app/client_test.py manual 101

# 人脸模式测试
python3 app/client_test.py face 102

# 仅监听状态
python3 app/client_test.py monitor
```

## 两种触发模式对比
| 特性 | 手动模式 | 人脸模式 |
|------|----------|----------|
| 触发话题 | `/command_room` | `/face_room` |
| 输入来源 | 小程序/Web 输入教室号 | 摄像头人脸识别 → 映射房间号 |
| 适用场景 | 教室导航（原有功能） | 酒店入住模拟（新增功能） |
| 导航逻辑 | 相同（共用 Nav2） | 相同（共用 Nav2） |

## 同步到小车
```bash
bash scripts/sync.sh 192.168.1.120
```

## 接口定义
详见 [`docs/接口定义文档.md`](docs/接口定义文档.md)

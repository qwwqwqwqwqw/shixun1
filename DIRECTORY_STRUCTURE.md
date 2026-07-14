# icar_classroom_guide — 项目目录结构与功能说明

> 本文档详细描述 ROS2 智能教室导航小车的完整目录结构、功能说明、通信接口与团队分工。
> 版本：1.0 | 最后更新：2025-07-11

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体目录树](#2-整体目录树)
3. [目录/文件详细说明](#3-目录文件详细说明)
4. [分层架构图](#4-分层架构图)
5. [数据流与通信关系](#5-数据流与通信关系)
6. [五人分工映射表](#6-五人分工映射表)
7. [Git忽略规则](#7-git忽略规则)
8. [关键路径说明](#8-关键路径说明)

---

## 1. 项目概述

| 项目 | 说明 |
|------|------|
| **项目名称** | icar_classroom_guide — 智能教室导航小车 |
| **Git 仓库** | `git@github.com:qwwqwqwqwqw/shixun1.git` |
| **本地路径** | `~/icar_classroom_guide/`（虚拟机） |
| **小车路径** | `/home/yahboom/icar_classroom_guide/` |
| **ROS 版本** | 虚拟机 Humble（写代码）/ 小车容器 Foxy（运行） |
| **通信方式** | Topic + Service + Action + 跨容器 DDS + 跨主机 DDS |

### 核心功能模块

| 编号 | 功能 | 模式 | 涉及组员 |
|------|------|------|----------|
| 1 | 小程序输入教室号 → 小车导航到目标教室 | 手动模式（原有） | D→B→A |
| 2 | 人脸识别 → 自动映射房间号 → 导航 | 自动模式（酒店入住模拟） | C→B→A |
| 3 | 到达后门牌号 YOLO+OCR 视觉确认 | 到达校验 | C↔B |
| 4 | 导航状态实时反馈（小程序/云平台） | 状态反馈 | B→D→E |

### 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    虚拟机（开发/写代码）                        │
│  ROS2 Humble │ 写代码 + colcon build │ git push               │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ dev_ws/src/     │  │ vision/      │  │ app/           │    │
│  │ guide_pkg       │  │ doorplate    │  │ 小程序/Web     │    │
│  │ aiserver_pkg    │  │ face         │  │ client_test    │    │
│  └─────────────────┘  └──────────────┘  └────────────────┘    │
└──────────────────────┬────────────────────────────────────────┘
                       │ git push / rsync
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              小车 (Jetson Nano / Orin)                       │
│  ROS2 Foxy (Docker 容器) │ 实际运行                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Nav2 导航    │  │ YOLO+OCR     │  │ face_recog   │       │
│  │ guide_node   │  │ doorplate    │  │ face_node    │       │
│  │ fusion_node  │  │ detector     │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  跨容器 DDS (ROS_DOMAIN_ID=42, network_mode=host)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 整体目录树

```
icar_classroom_guide/
│
├── dev_ws/                              # ROS2 工作空间
│   └── src/
│       ├── guide_pkg/                   # 导航核心包（B组长）
│       │   ├── guide_pkg/
│       │   │   ├── __init__.py
│       │   │   ├── guide_node.py        # ★ 核心导航节点
│       │   │   ├── arrival_fusion.py    # ★ 多传感器融合节点
│       │   │   └── utils.py             #   辅助函数库
│       │   ├── config/
│       │   │   ├── classrooms.yaml      # ★ 教室坐标映射（A填值）
│       │   │   └── face_room_map.yaml   # ★ 人脸→房间号映射（C维护）
│       │   ├── srv/
│       │   │   └── NavigateRoom.srv     #   导航服务接口定义
│       │   ├── launch/
│       │   │   └── guide_launch.py      #   一键启动文件
│       │   ├── package.xml
│       │   ├── setup.py
│       │   └── resource/
│       │       └── guide_pkg
│       │
│       └── aiserver_pkg/                # 指令接口包（D组员）
│           ├── aiserver_pkg/
│           │   ├── __init__.py
│           │   └── aiserver_node.py     # ★ TCP Socket 服务节点
│           ├── launch/
│           │   └── aiserver_launch.py   #   启动文件
│           ├── package.xml
│           ├── setup.py
│           └── resource/
│               └── aiserver_pkg
│
├── vision/                              # 视觉识别模块（C组员）
│   ├── doorplate/                       # 门牌识别（YOLOv5 + OCR）
│   │   ├── doorplate_detector.py        # ★ 门牌识别节点
│   │   ├── best.pt                      #   YOLO 训练权重（占位）
│   │   ├── yolov5/                      #   YOLOv5 源码/软链接
│   │   └── dataset/                     #   训练数据集（不提交 Git）
│   │
│   ├── face/                            # 人脸识别（酒店入住模拟）
│   │   ├── face_recognizer.py           # ★ 人脸识别节点
│   │   ├── known_faces/                 #   已知人脸照片
│   │   │   ├── zhang_san.jpg            #   张三（占位）
│   │   │   ├── li_si.jpg                #   李四（占位）
│   │   │   └── wang_wu.jpg              #   王五（占位）
│   │   └── face_encodings.pkl           #   特征缓存（不提交 Git）
│   │
│   └── launch/
│       └── vision_launch.py             #   视觉模块启动文件
│
├── app/                                 # 前端控制（D组员）
│   ├── miniprogram/                     # 微信小程序
│   │   ├── app.js                       #   小程序入口
│   │   ├── app.json                     #   全局配置
│   │   ├── app.wxss                     #   全局样式
│   │   └── pages/
│   │       ├── index/                   # 首页
│   │       │   ├── index.js             #   教室列表/人脸触发
│   │       │   ├── index.wxml           #   页面模板
│   │       │   └── index.wxss           #   页面样式
│   │       └── status/                  # 状态页
│   │           ├── status.js            #   实时导航状态
│   │           ├── status.wxml          #   页面模板
│   │           └── status.wxss          #   页面样式
│   │
│   ├── web/                             # Web 控制台（备用）
│   │   ├── index.html
│   │   └── script.js
│   │
│   └── client_test.py                   # 命令行测试客户端
│
├── maps/                                # 地图文件（A组员）
│   ├── map.pgm                          #   当前地图（不提交 Git）
│   ├── map.yaml                         #   地图配置
│   ├── map_v1.pgm                       #   v1 备份（不提交 Git）
│   ├── map_v1.yaml                      #   v1 配置
│   └── README.md                        #   版本说明
│
├── records/                             # 测试记录（全员）
│   ├── 建图记录.md                       #   A组员填写
│   ├── 导航测试表.md                     #   B/E组员填写
│   ├── 视觉识别测试记录.md               #   C组员填写
│   ├── 人脸识别测试记录.md               #   C组员填写
│   └── 最终测试报告.md                   #   E组长汇总
│
├── scripts/                             # 辅助脚本（E组员）
│   ├── sync.sh                          #   一键同步代码到小车（rsync）
│   ├── demo.sh                          #   演示脚本（固定路线）
│   ├── checklist.sh                     #   演示前检查清单
│   └── install_deps.sh                  #   依赖安装脚本
│
├── docs/                                # 文档（E组长+全员）
│   ├── 接口定义文档.md                   #   话题/服务格式定义（B编写）
│   ├── 分布式通信配置.md                 #   跨容器/跨主机配置（B编写）
│   ├── 目录说明.md                       #   目录结构说明（本文件轻量版）
│   ├── 人脸识别使用说明.md               #   如何注册新用户（C编写）
│   ├── 系统结构图.png                    #   架构图（占位）
│   ├── 数据流图.png                      #   数据流图（占位）
│   └── 答辩PPT.pptx                     #   答辩演示文稿（占位）
│
├── .github/
│   └── workflows/
│       └── ci.yml                       # GitHub Actions CI（E配置）
│
├── DIRECTORY_STRUCTURE.md               # ★ 本文档
├── README.md                            # 项目总览与快速开始
├── process.md                           # 进度记录（不提交 Git）
├── .gitignore
├── LICENSE                              # MIT 协议
├── requirements.txt                     # Python 依赖总表
└── docker-compose.yml                   # 双容器编排
```

---

## 3. 目录/文件详细说明

### 3.1 `dev_ws/` — ROS2 工作空间（B组长统筹）

ROS2 标准工作空间，使用 `colcon build` 编译。包含两个功能包。

#### 3.1.1 `guide_pkg/` — 导航核心包

| 文件 | 功能描述 | 负责人 | 输入 | 输出 | 依赖 |
|------|----------|--------|------|------|------|
| `guide_pkg/__init__.py` | Python 包初始化标记 | B | — | — | — |
| `guide_pkg/guide_node.py` | **★ 核心导航节点**：订阅 `/command_room`（手动模式）和 `/face_room`（人脸模式），从 `classrooms.yaml` 读取坐标，调用 Nav2 SimpleCommander 导航，实时发布 `/navigation_status` | B | `/command_room` `(String)` / `/face_room` `(String)` | `/navigation_status` `(String)` | `classrooms.yaml`、Nav2、`utils.py` |
| `guide_pkg/arrival_fusion.py` | **★ 多传感器融合节点**：同时订阅导航状态和门牌识别结果，当"导航到达"且"门牌匹配"时，发布最终到达确认 | B | `/navigation_status` `(String)`、`/doorplate_result` `(String)` | `/arrival_confirmed` `(Bool)` | 无外部依赖，纯逻辑融合 |
| `guide_pkg/utils.py` | 辅助函数库：`load_classrooms()` 加载坐标、`load_face_room_map()` 加载人脸映射、`make_pose_stamped()` 构造 Nav2 目标位姿 | B | YAML 文件路径 | dict / PoseStamped | pyyaml、geometry_msgs |
| `config/classrooms.yaml` | **★ 教室号→全局坐标映射**，A组员建图后填写实际坐标值 | A | 人工填写 | 被 `guide_node.py` 读取 | SLAM 建图结果 |
| `config/face_room_map.yaml` | **★ 人脸名→房间号映射**，C组员注册新用户时更新 | C | 人工填写 | 被 `face_recognizer.py` 读取 | `known_faces/` 照片 |
| `srv/NavigateRoom.srv` | 自定义服务接口定义（可选扩展） | B | — | — | — |
| `launch/guide_launch.py` | ROS2 launch 启动文件，一次性启动 guide_node + arrival_fusion | B | — | 启动两个节点 | — |
| `package.xml` | ROS2 包依赖声明，依赖 rclpy、nav2_msgs、geometry_msgs 等 | B | — | — | — |
| `setup.py` | Python 包安装脚本，定义 console_scripts 入口点 | B | — | — | setuptools |
| `resource/guide_pkg` | ament 资源标记文件 | B | — | — | — |

#### 3.1.2 `aiserver_pkg/` — 指令接口包

| 文件 | 功能描述 | 负责人 | 输入 | 输出 | 依赖 |
|------|----------|--------|------|------|------|
| `aiserver_pkg/__init__.py` | Python 包初始化标记 | D | — | — | — |
| `aiserver_pkg/aiserver_node.py` | **★ TCP Socket 服务节点**：接收小程序导航和人脸模式指令，发布到 `/command_room`、`/face_mode_control`；订阅导航与人脸识别状态并回传前端 | D | TCP JSONL 消息 | `/command_room` `(String)`、`/face_mode_control` `(String)` | socket、std_msgs |
| `launch/aiserver_launch.py` | ROS2 launch 启动文件 | D | — | 启动 aiserve_node | — |
| `package.xml` | ROS2 包依赖声明 | D | — | — | — |
| `setup.py` | 安装脚本 | D | — | — | setuptools |
| `resource/aiserver_pkg` | ament 资源标记文件 | D | — | — | — |

---

### 3.2 `vision/` — 视觉识别模块（C组员）

#### 3.2.1 `doorplate/` — 门牌识别（YOLOv5 + OCR）

| 文件 | 功能描述 | 负责人 | 输入 | 输出 | 依赖 |
|------|----------|--------|------|------|------|
| `doorplate_detector.py` | **★ 门牌识别节点**：订阅摄像头图像 → YOLOv5 检测门牌区域 → OCR 提取号码 → 发布到 `/doorplate_result` | C | `/camera/image_raw` `(Image)` | `/doorplate_result` `(String)` | best.pt、YOLOv5、OCR |
| `best.pt` | YOLOv5 训练权重文件（占位，需替换为实际训练结果） | C | — | 被 detector 加载 | 标注数据集 |
| `yolov5/` | YOLOv5 源码或软链接 | C | — | — | — |
| `dataset/` | 训练数据集（图片+标注，不提交 Git） | C | — | 训练 best.pt | — |

#### 3.2.2 `face/` — 人脸识别（酒店入住模拟）

| 文件 | 功能描述 | 负责人 | 输入 | 输出 | 依赖 |
|------|----------|--------|------|------|------|
| `face_recognizer.py` | **★ 人脸识别节点**：接收启停指令，OpenCV 直读 RGB 摄像头 → 对比 `known_faces/` → 查映射并发布 `/face_room`，同时发布识别状态 | C | `/face_mode_control` `(String)`、`/dev/video*` | `/face_room`、`/face_recognition_status` `(String)` | face_recognition、`face_room_map.yaml` |
| `known_faces/` | 已知人脸照片目录，文件名需与 `face_room_map.yaml` 的 key 一致 | C | 人工放置 | 被 face_recognizer 编码 | 注册用户照片 |
| `face_encodings.pkl` | 预计算的人脸特征缓存（运行时生成，不提交 Git） | C | — | — | — |

#### 3.2.3 `launch/vision_launch.py`

| 文件 | 功能描述 | 负责人 | 输入 | 输出 |
|------|----------|--------|------|------|
| `launch/vision_launch.py` | 视觉模块启动脚本，同时启动 doorplate_detector 和 face_recognizer | C | — | 启动两个 Python 进程 |

---

### 3.3 `app/` — 前端控制（D组员）

| 文件 | 功能描述 | 负责人 | 输入 | 输出 | 依赖 |
|------|----------|--------|------|------|------|
| `miniprogram/app.js` | 小程序入口，初始化 TCP Socket 连接到 aiserver_node | D | — | TCP Socket 连接 | aiserver_node |
| `miniprogram/app.json` | 小程序全局配置，定义页面路由 | D | — | — | — |
| `miniprogram/app.wxss` | 小程序全局样式 | D | — | — | — |
| `miniprogram/pages/index/*` | 首页：教室列表选择 + 人脸识别触发按钮 | D | 用户点击 | TCP JSONL 指令 | aiserver_node |
| `miniprogram/pages/status/*` | 状态页：实时显示导航状态和到达确认 | D | TCP JSONL 消息 | UI 展示 | aiserver_node |
| `web/index.html` | Web 控制台页面（旧版，当前不启用） | D | 用户输入 | 需单独 WebSocket 网关 | — |
| `web/script.js` | 旧版 WebSocket 通信脚本 | D | — | 当前不连接 TCP 服务 | — |
| `client_test.py` | 命令行测试客户端，支持 manual/face/monitor 三种模式 | D | CLI 参数 | ROS2 话题 | rclpy |

---

### 3.4 `maps/` — 地图文件（A组员）

| 文件 | 功能描述 | 负责人 | 输入 | 输出 |
|------|----------|--------|------|------|
| `map.pgm` | 当前栅格地图（不提交 Git） | A | SLAM 建图 | Nav2 加载 |
| `map.yaml` | 地图配置文件（分辨率、原点、阈值） | A | 人工配置 | Nav2 加载 |
| `map_v1.pgm` / `map_v1.yaml` | v1 版本备份 | A | — | 回滚用 |
| `README.md` | 地图版本历史说明 | A | — | — |

---

### 3.5 `records/` — 测试记录（全员）

| 文件 | 功能描述 | 负责人 |
|------|----------|--------|
| `建图记录.md` | 建图过程、教室坐标标注 | A |
| `导航测试表.md` | 导航功能测试用例（手动+人脸） | B / E |
| `视觉识别测试记录.md` | YOLO+OCR 门牌识别测试 | C |
| `人脸识别测试记录.md` | 人脸识别准确率测试 | C |
| `最终测试报告.md` | 系统集成测试汇总 | E 组长 |

---

### 3.6 `scripts/` — 辅助脚本（E组员）

| 文件 | 功能描述 | 用法 |
|------|----------|------|
| `sync.sh` | 一键同步代码到小车（rsync over SSH，自动排除大文件） | `bash scripts/sync.sh [小车IP]` |
| `demo.sh` | 演示脚本：模拟手动+人脸双模式流程 | `bash scripts/demo.sh` |
| `checklist.sh` | 演示前自动检查：ROS2环境、地图、坐标、网络 | `bash scripts/checklist.sh` |
| `install_deps.sh` | 自动安装所有依赖（ROS2包 + Python库 + YOLO） | `bash scripts/install_deps.sh` |

---

### 3.7 `docs/` — 文档（E组长+全员）

| 文件 | 功能描述 | 负责人 |
|------|----------|--------|
| `接口定义文档.md` | 话题/服务格式、QoS、坐标系定义 | B 组长 |
| `分布式通信配置.md` | 跨容器/跨主机 DDS 配置指南 | B 组长 |
| `目录说明.md` | 轻量版目录说明 | E 组长 |
| `人脸识别使用说明.md` | 如何注册新用户人脸 | C 组员 |
| `系统结构图.png` | 架构图（占位） | E 组长 |
| `数据流图.png` | 数据流向图（占位） | E 组长 |
| `答辩PPT.pptx` | 答辩演示文稿（占位） | E 组长 |

---

### 3.8 `.github/workflows/` — CI/CD（E组员）

| 文件 | 功能描述 |
|------|----------|
| `ci.yml` | GitHub Actions：push/pull_request 时自动执行 flake8 语法检查、YAML 格式验证、ROS2 包完整性检查 |

---

### 3.9 根目录文件

| 文件 | 功能描述 |
|------|----------|
| `DIRECTORY_STRUCTURE.md` | ★ 本文档 |
| `README.md` | 项目总览、快速开始、两种模式对比 |
| `process.md` | 项目进度记录（不提交 Git） |
| `.gitignore` | Git 忽略规则 |
| `LICENSE` | MIT 开源协议 |
| `requirements.txt` | Python 依赖总表 |
| `docker-compose.yml` | 三容器编排（ros2-nav + vision + aiserver） |

---

## 4. 分层架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          应用层 (Application Layer)                       │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────────┐   │
│  │  微信小程序       │  │  Web 控制台      │  │  命令行测试客户端      │   │
│  │  app/miniprogram │  │  app/web         │  │  app/client_test.py   │   │
│  └────────┬────────┘  └────────┬─────────┘  └───────────┬────────────┘   │
│           │                    │                        │                │
│           └────────────────────┼────────────────────────┘                │
│                                │ TCP Socket（小程序）                   │
├────────────────────────────────┼─────────────────────────────────────────┤
│                          接口层 (Interface Layer)                        │
│                                │                                         │
│                    ┌───────────▼────────────┐                            │
│                    │ aiserver_pkg/           │  D 组员                    │
│                    │ aiserver_node.py        │                            │
│                    │ TCP Socket → ROS2       │                            │
│                    └───────────┬────────────┘                            │
│                                │                                         │
├────────────────────────────────┼─────────────────────────────────────────┤
│                          决策层 (Decision Layer)                         │
│                                │                                         │
│                 ┌──────────────┴──────────────┐                          │
│                 │ guide_pkg/                   │  B 组长                  │
│                 │                              │                          │
│  ┌──────────────▼────────────┐  ┌─────────────▼────────────┐             │
│  │ guide_node.py             │  │ arrival_fusion.py        │             │
│  │ 核心导航决策               │  │ 多传感器融合               │             │
│  │ • 接收 /command_room      │  │ • 订阅导航状态             │             │
│  │ • 接收 /face_room         │  │ • 订阅门牌识别结果          │             │
│  │ • 查教室坐标 classroooms  │  │ • 融合判定到达确认          │             │
│  │ • 调用 Nav2 导航          │  │ • 发布 /arrival_confirmed  │             │
│  └──────────────┬────────────┘  └──────────────────────────┘             │
│                 │ Nav2 Action                                            │
├─────────────────┼────────────────────────────────────────────────────────┤
│                          感知层 (Perception Layer)                       │
│                 │                                                       │
│  ┌──────────────┴──────────────────────────────────────────────┐        │
│  │ vision/                    C 组员                            │        │
│  │  ┌────────────────────┐    ┌────────────────────┐            │        │
│  │  │ doorplate/         │    │ face/              │            │        │
│  │  │ doorplate_detector │    │ face_recognizer    │            │        │
│  │  │ YOLO + OCR         │    │ face_recognition   │            │        │
│  │  │ → /doorplate_result│    │ → /face_room       │            │        │
│  │  └────────────────────┘    └────────────────────┘            │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                 │ 摄像头图像                                              │
├─────────────────┼────────────────────────────────────────────────────────┤
│                          驱动层 (Driver Layer)                           │
│                 │                                                       │
│  ┌──────────────▼──────────────────────────────────────────────────┐    │
│  │ Docker 容器 1: ros2-nav     Docker 容器 2: vision                │    │
│  │ network_mode: host          network_mode: host                  │    │
│  │ ROS_DOMAIN_ID=42            ROS_DOMAIN_ID=42                    │    │
│  │ • Nav2                      • YOLOv5                            │    │
│  │ • AMCL                      • face_recognition                  │    │
│  │ • map_server                • cv_bridge                         │    │
│  └────────────────────────────────────────────────────────────────-┘    │
│                 │ DDS Discovery (FastDDS)                                │
├─────────────────┼────────────────────────────────────────────────────────┤
│                          硬件层 (Hardware Layer)                         │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  icar 智能小车 (Jetson Nano / Orin)                               │   │
│  │                                                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐      │   │
│  │  │ 麦克纳姆轮 │  │ 激光雷达   │  │ 深度相机  │  │ 差速底盘     │      │   │
│  │  │ 底盘     │  │ LIDAR    │  │ RGB-D    │  │ 编码器+IMU  │      │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 数据流与通信关系

### 5.1 话题（Topics）

| 话题名称 | 消息类型 | 发布者 | 订阅者 | 说明 |
|----------|----------|--------|--------|------|
| `/command_room` | `std_msgs/String` | **D** aiserver_node | **B** guide_node | **手动模式**：小程序/Web 输入的教室号 |
| `/face_room` | `std_msgs/String` | **C** face_recognizer | **B** guide_node | **人脸模式**：人脸识别映射的房间号 |
| `/navigation_status` | `std_msgs/String` | **B** guide_node | **D** aiserver_node、**E** 云平台 | 导航状态实时反馈（开始/导航中/到达/失败） |
| `/doorplate_result` | `std_msgs/String` | **C** doorplate_detector | **B** arrival_fusion | YOLO+OCR 识别的门牌号码 |
| `/arrival_confirmed` | `std_msgs/Bool` | **B** arrival_fusion | **D** aiserver_node、**E** 云平台 | 融合判定后的最终到达确认 |
| `/camera/image_raw` | `sensor_msgs/Image` | 相机驱动 | **C** doorplate_detector、**C** face_recognizer | 原始摄像头图像 |

### 5.2 服务（Services）

| 服务名称 | 服务类型 | 服务端 | 客户端 | 说明 |
|----------|----------|--------|--------|------|
| `/navigate_room` | `guide_pkg/srv/NavigateRoom` | **B** guide_node | **D** aiserver_node（可选） | 请求导航，返回 success + message |

### 5.3 数据流图

```
┌──────────┐   手动输入教室号     ┌──────────────────────────────────────────┐
│ 小程序    │ ──────────────────►  │  aiserver_node (D)                       │
│ (D)      │                     │  TCP Socket 服务                          │
│          │ ◄──────────────────  │  → 发布 /command_room                    │
└──────────┘   导航状态实时更新    │  → 订阅 /navigation_status 回传          │
                                  │  → 订阅 /arrival_confirmed 回传          │
                                   └──────────┬───────────────────────────────┘
                                              │ /command_room (String)
                                              ▼
┌──────────┐  识别人脸+映射房间   ┌──────────────────────────────────────────┐
│ 摄像头    │ ──────────────────►  │  face_recognizer (C)                     │
│ (C)      │                     │  → 对比 known_faces/                      │
│          │                     │  → 查 face_room_map.yaml                  │
│          │                     │  → 发布 /face_room                        │
└──────────┘                     └──────────────────┬───────────────────────┘
                                                    │ /face_room (String)
                                                    ▼
┌──────────┐  识别门牌号码       ┌──────────────────────────────────────────┐
│ 摄像头    │ ──────────────────►  │  doorplate_detector (C)                  │
│ (C)      │                     │  → YOLO 检测门牌区域                      │
│          │                     │  → OCR 提取门牌号码                       │
│          │                     │  → 发布 /doorplate_result                 │
└──────────┘                     └──────────────────┬───────────────────────┘
                                                    │ /doorplate_result (String)
                                                    ▼
              ┌─────────────────────────────────────────────────────────────┐
              │  guide_node (B)   ←←←  /command_room / /face_room          │
              │  核心导航节点                                                │
              │  → 从 classrooms.yaml 查找坐标                               │
              │  → 调用 Nav2 SimpleCommander 导航                           │
              │  → 发布 /navigation_status 实时状态                          │
              └──────────────┬──────────────────────────────────────────────┘
                             │ /navigation_status (String)
                             ▼
              ┌─────────────────────────────────────────────────────────────┐
              │  arrival_fusion (B)                                         │
              │  多传感器融合节点                                            │
              │  ← 接收 /navigation_status: "到达"                          │
              │  ← 接收 /doorplate_result: 门牌号                           │
              │  → 融合判定: 到达 + 门牌匹配 = 确认                          │
              │  → 发布 /arrival_confirmed                                  │
              └──────────────┬──────────────────────────────────────────────┘
                             │ /arrival_confirmed (Bool)
                             ▼
              ┌─────────────────────────────────────────────────────────────┐
              │  aiserver_node (D) → 回传小程序/Web 前端                     │
              │  云平台上报 (E) → CI/CD 记录                                │
              └─────────────────────────────────────────────────────────────┘

模式对比:
  手动模式:  小程序 ──→ /command_room ──→ guide_node ──→ Nav2 ──→ 导航完成
  人脸模式:  摄像头 ──→ face_recognizer ──→ /face_room ──→ guide_node ──→ Nav2 ──→ 导航完成
  共同后续:  guide_node → arrival_fusion ← doorplate_detector → /arrival_confirmed → 小程序
```

---

## 6. 五人分工映射表

### 6.1 A组员 — 建图与坐标标注

| 文件/目录 | 角色 | 说明 |
|-----------|------|------|
| `maps/` | 负责 | SLAM 建图，输出 `.pgm` + `.yaml` |
| `dev_ws/src/guide_pkg/config/classrooms.yaml` | 参与 | 提供教室实际坐标值（B 维护文件） |
| `records/建图记录.md` | 负责 | 填写建图过程和坐标数据 |

**输入**：激光雷达 / 深度相机 → SLAM 算法
**输出**：`map.pgm` + `map.yaml` + 教室坐标数据

---

### 6.2 B组长 — ROS2 核心开发与分布式通信（我）

| 文件/目录 | 角色 | 说明 |
|-----------|------|------|
| `dev_ws/src/guide_pkg/guide_pkg/guide_node.py` | **负责** | 核心导航节点，接收两种模式入口 |
| `dev_ws/src/guide_pkg/guide_pkg/arrival_fusion.py` | **负责** | 多传感器融合节点 |
| `dev_ws/src/guide_pkg/guide_pkg/utils.py` | **负责** | 辅助函数库 |
| `dev_ws/src/guide_pkg/config/classrooms.yaml` | **维护** | 文件结构维护（A 提供坐标值） |
| `dev_ws/src/guide_pkg/srv/NavigateRoom.srv` | **负责** | 服务接口定义 |
| `dev_ws/src/guide_pkg/launch/guide_launch.py` | **负责** | 启动文件 |
| `dev_ws/src/guide_pkg/package.xml` | **负责** | 包配置 |
| `dev_ws/src/guide_pkg/setup.py` | **负责** | 安装脚本 |
| `docs/接口定义文档.md` | **负责** | 话题/服务格式定义 |
| `docs/分布式通信配置.md` | **负责** | 跨容器/跨主机配置 |
| `records/导航测试表.md` | **参与** | 与 E 共同填写 |

**输入**：`/command_room`（手动）/ `/face_room`（人脸）/ `classrooms.yaml`（坐标）
**输出**：`/navigation_status`（状态）/ `/arrival_confirmed`（确认）

---

### 6.3 C组员 — 视觉识别（门牌+人脸）

| 文件/目录 | 角色 | 说明 |
|-----------|------|------|
| `vision/doorplate/doorplate_detector.py` | **负责** | YOLO+OCR 门牌识别节点 |
| `vision/doorplate/best.pt` | **负责** | YOLO 训练权重 |
| `vision/doorplate/yolov5/` | **负责** | YOLOv5 源码 |
| `vision/doorplate/dataset/` | **负责** | 门牌标注数据集 |
| `vision/face/face_recognizer.py` | **负责** | 人脸识别节点 |
| `vision/face/known_faces/` | **负责** | 注册用户照片 |
| `vision/launch/vision_launch.py` | **负责** | 视觉启动文件 |
| `dev_ws/src/guide_pkg/config/face_room_map.yaml` | **维护** | 人脸→房间号映射表 |
| `records/视觉识别测试记录.md` | **负责** | 门牌识别测试 |
| `records/人脸识别测试记录.md` | **负责** | 人脸识别测试 |
| `docs/人脸识别使用说明.md` | **负责** | 注册新用户文档 |

**输入**：`/camera/image_raw`（摄像头图像）
**输出**：`/doorplate_result`（门牌号）/ `/face_room`（房间号）

---

### 6.4 D组员 — 接口与前端

| 文件/目录 | 角色 | 说明 |
|-----------|------|------|
| `dev_ws/src/aiserver_pkg/aiserver_pkg/aiserver_node.py` | **负责** | TCP Socket 桥接节点 |
| `dev_ws/src/aiserver_pkg/launch/aiserver_launch.py` | **负责** | 启动文件 |
| `dev_ws/src/aiserver_pkg/package.xml` | **负责** | 包配置 |
| `dev_ws/src/aiserver_pkg/setup.py` | **负责** | 安装脚本 |
| `app/miniprogram/` | **负责** | 微信小程序完整源码 |
| `app/web/` | **负责** | Web 控制台备用方案 |
| `app/client_test.py` | **负责** | 命令行测试客户端 |

**输入**：用户指令（小程序/Web 点击）
**输出**：`/command_room`（转发教室号）

---

### 6.5 E组员 — 系统集成与测试

| 文件/目录 | 角色 | 说明 |
|-----------|------|------|
| `scripts/sync.sh` | **负责** | 代码同步脚本 |
| `scripts/demo.sh` | **负责** | 演示脚本 |
| `scripts/checklist.sh` | **负责** | 检查清单 |
| `scripts/install_deps.sh` | **负责** | 依赖安装 |
| `.github/workflows/ci.yml` | **负责** | CI/CD 配置 |
| `docs/系统结构图.png` | **负责** | 架构图 |
| `docs/数据流图.png` | **负责** | 数据流图 |
| `docs/目录说明.md` | **负责** | 目录说明 |
| `docs/答辩PPT.pptx` | **负责** | 答辩演示 |
| `records/最终测试报告.md` | **负责** | 汇总 |
| `records/导航测试表.md` | **参与** | 与 B 共同填写 |
| `README.md` | **负责** | 项目总览 |
| `.gitignore` | **负责** | Git 忽略规则 |
| `requirements.txt` | **负责** | 依赖总表 |
| `docker-compose.yml` | **负责** | 容器编排 |

---

## 7. Git 忽略规则

以下内容在 `.gitignore` 中配置，不会被 Git 跟踪：

```gitignore
# Python 缓存
__pycache__/
*.pyc
*.pyo
*.egg-info/
build/
install/
log/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 地图大文件（不提交 .pgm）
*.pgm

# 人脸特征缓存
*.pkl

# 数据集（太大不提交）
vision/doorplate/dataset/
vision/face/known_faces/*.jpg
vision/face/known_faces/*.png
# 保留 README
!vision/face/known_faces/README.md
!vision/doorplate/dataset/README.md

# YOLO 权重
vision/doorplate/best.pt
# 保留 YOLOv5 目录结构
!vision/doorplate/yolov5/

# 日志
*.log
records/*.log

# 环境变量
.env
.env.*

# ROS2 构建产物
dev_ws/build/
dev_ws/install/
dev_ws/log/

# 进程记录（不提交）
process.md

# 系统文件
.DS_Store
Thumbs.db
```

---

## 8. 关键路径说明

### 8.1 手动模式完整调用链

```
[用户在小程序选择教室 "501"]
                │
                ▼
① app/miniprogram/pages/index/index.js     # 用户点击 "开始导航"
                │ TCP Socket ({"type":"navigate","room":"501"}\n)
                ▼
② dev_ws/src/aiserver_pkg/aiserver_node.py  # 收到前端消息
                │ 发布话题 /command_room (std_msgs/String, data="501")
                ▼
③ dev_ws/src/guide_pkg/guide_pkg/guide_node.py  # on_command_room() 回调
                │
                ├── 调用 _navigate_to("501", source="manual")
                │
                ├── 发布 /navigation_status: "开始导航到 501（来源: manual）"
                │
                ├── 读取 config/classrooms.yaml → 查找 "501" 坐标 (x, y, yaw)
                │       (A组员提供的坐标值)
                │
                ├── 调用 utils.load_classrooms() 加载坐标
                │
                ├── 调用 utils.make_pose_stamped() 构造 Nav2 目标位姿
                │
                └── 调用 Nav2 SimpleCommander.goToPose() 发送导航目标
                        │
                        ▼
④ Nav2 开始导航 (AMCL 定位 + 全局/局部路径规划)
                        │
                        ├── 实时发布 /navigation_status: "导航中..."
                        │       → aiserver_node 回传小程序 status 页
                        │
                        └── 到达目标后发布 /navigation_status: "到达 501"
                                │
                                ▼
⑤ dev_ws/src/guide_pkg/guide_pkg/arrival_fusion.py
                │
                ├── on_nav_status() "到达 501" → nav_done = True
                │
                └── ← 等待 /doorplate_result 结果（门牌确认）
                        │
                        ▼
      [门牌无结果 / 门牌不匹配 → 确认失败 / 等待重检]
      [门牌匹配成功        → 确认成功]
                        │
                        ▼
⑥ arrival_fusion 发布 /arrival_confirmed (Bool=True)
                │
                └── aiserver_node → 小程序 status 页显示 "已到达 501 ✓"
```

### 8.2 人脸模式完整调用链

```
[用户站在摄像头前]
                │
                ▼
① vision/face/face_recognizer.py  # 检测到人脸
                │
                ├── 编码人脸特征 → 对比 known_faces/ 目录
                │
                ├── 匹配到 zhang_san.jpg
                │
                ├── 读取 config/face_room_map.yaml → zhang_san: "501"
                │
                └── 发布话题 /face_room (std_msgs/String, data="501")
                        │
                        ▼
② → 与手动模式③同路径（共用 _navigate_to() 函数）
                        │
                        ▼
③ → 手动模式④ Nav2 导航...
                        │
                        ▼
④ 导航到达后，vision/doorplate/doorplate_detector.py
                │
                ├── YOLOv5 检测门牌区域
                ├── OCR 提取门牌号码 "501"
                └── 发布话题 /doorplate_result (std_msgs/String, data="501")
                        │
                        ▼
⑤ arrival_fusion 融合判定 → 发布 /arrival_confirmed
                │
                ▼
⑥ 更新小程序/Web 状态展示
```

### 8.3 跨容器/跨主机部署路径

```
[虚拟机开发环境]
  代码修改 → colcon build → git push
                                    │
                                    ▼
[GitHub 远程仓库]
                                    │
                                    ▼
[小车] 方法 A: git pull                              (有网络)
        方法 B: bash scripts/sync.sh 192.168.1.120   (rsync SSH)
                                    │
                                    ▼
[小车容器内] colcon build → source install/setup.bash
                                    │
                                    ▼
启动 → ros2 launch guide_pkg guide_launch.py
         (跨容器 DDS: ROS_DOMAIN_ID=42, network_mode=host)
                                    │
                                    ▼
[虚拟机] 远程 ros2 topic echo /navigation_status  ← 跨主机 DDS 可见
```

### 8.4 关键路径文件依赖图

```
触发层                          决策层                          执行层
┌──────────┐            ┌──────────────────┐             ┌──────────┐
│ 小程序    │ ──WS──►   │ aiserver_node    │ ──topic──►  │ Nav2     │
│ index.js  │           │ (D)              │             │ (Foxy)   │
└──────────┘            └────────┬─────────┘             └──────────┘
                                 │                               ▲
┌──────────┐                     │ /command_room                  │
│ 人脸识别  │ ──topic──►         │                     ┌─────────┴──────────┐
│ face.py  │ /face_room          ▼                     │ guide_node.py      │
│ (C)      │              ┌──────────────┐             │ (B)                │
└──────────┘              │ guide_node   │             │ • classrooms.yaml  │
                          │ (B)          │ ──Action──►  │ • utils.py         │
┌──────────┐              │              │             └────────────────────┘
│ 门牌识别  │              └──────┬───────┘
│ detector │ ──topic──►          │
│ (C)      │ /doorplate          ▼
└──────────┘             ┌──────────────────┐             ┌──────────────┐
                         │ arrival_fusion   │             │ 前端状态页    │
                         │ (B)              │ ──topic──►  │ status.js    │
                         │ • 融合判定        │ /confirmed  │ (D)          │
                         └──────────────────┘             └──────────────┘
```

# 已知人脸照片目录
# C组员在此放入注册用户的人脸照片（jpg/png 格式）
# 文件名必须与 face_room_map.yaml 中的 key 一致
#
# 示例:
#   zhang_san.jpg  →  face_room_map: zhang_san: "501"
#   li_si.jpg      →  face_room_map: li_si: "502"
#   wang_wu.jpg    →  face_room_map: wang_wu: "503"

# 人脸识别模块使用说明

## 1. 安装依赖（Windows 用户必看）

由于 `dlib` 在 Windows 上直接安装会编译失败，请按以下步骤安装：

```bash
# 第一步：安装预编译的 dlib
pip install dlib-bin

# 第二步：安装 face_recognition（跳过 dlib 依赖）
pip install face_recognition --no-deps
pip install face_recognition_models numpy Pillow Click
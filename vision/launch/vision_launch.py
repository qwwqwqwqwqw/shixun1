"""视觉模块一键启动 — 同时启动门牌识别和人脸识别节点。

注意：此 launch 文件以独立 Python 脚本方式运行（非 ROS2 包内 launch）。
如需集成到 ROS2 launch 系统，请将 vision/ 整理为标准 ROS2 包。
"""
import subprocess
import sys


def main():
    """启动视觉识别节点"""
    procs = []
    try:
        procs.append(subprocess.Popen([sys.executable, '../doorplate/doorplate_detector.py']))
        procs.append(subprocess.Popen([sys.executable, '../face/face_recognizer.py']))
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()


if __name__ == '__main__':
    main()

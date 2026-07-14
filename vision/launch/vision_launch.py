"""视觉模块一键启动 — 同时启动门牌识别、人脸识别和语音节点。"""
import os
import subprocess
import sys


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    doorplate = os.path.join(base, '..', 'doorplate', 'doorplate_detector.py')
    face = os.path.join(base, '..', 'face', 'face_recognizer.py')
    voice = os.path.join(base, '..', 'voice', 'voice_player.py')

    procs = []
    scripts = [(doorplate, 'doorplate'), (face, 'face'), (voice, 'voice')]
    for path, name in scripts:
        if os.path.exists(path):
            procs.append(subprocess.Popen([sys.executable, path]))
            print(f'[启动] {name}')
        else:
            print(f'[跳过] {name} — 文件不存在: {path}')

    if not procs:
        print('[错误] 无任何视觉节点可启动')
        return

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
        print('\n[停止] 所有视觉节点已终止')


if __name__ == '__main__':
    main()

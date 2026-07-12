"""语音模块独立测试 — 无需 ROS2，直接测试音频播放"""
import os
import sys
import subprocess
import time

try:
    import pygame.mixer
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

AUDIO_DIR = os.path.join(os.path.expanduser('~'),
                         'yahboomcar_ros2_ws/yahboomcar_ws/resource/audio')


def tts(text):
    """espeak 文字转语音"""
    try:
        subprocess.run(['espeak', '-v', 'zh', text], timeout=10)
    except FileNotFoundError:
        print('[WARN] espeak 未安装，跳过: sudo apt install espeak')
    except Exception as e:
        print(f'[WARN] TTS 失败: {e}')


def play_wav(filename):
    """播放 WAV 文件"""
    path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(path) and HAS_PYGAME:
        sound = pygame.mixer.Sound(path)
        sound.play()
        time.sleep(sound.get_length() + 0.5)
    else:
        print(f'[WARN] 文件不存在或 pygame 不可用: {filename}')


def play_bgm():
    """循环播放音乐 5 秒"""
    path = os.path.join(AUDIO_DIR, 'bgm.mp3')
    if os.path.exists(path) and HAS_PYGAME:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        print('[BGM] 播放中... 5秒后自动停止')
        time.sleep(5)
        pygame.mixer.music.fadeout(500)
    else:
        print(f'[WARN] bgm.mp3 不存在或 pygame 不可用')


def main():
    print('=' * 40)
    print('  语音模块独立测试')
    print('=' * 40)

    # 初始化
    if HAS_PYGAME:
        pygame.mixer.init()
        print('[OK] pygame 混音器已初始化')
    else:
        print('[WARN] pygame 未安装，仅测试 espeak TTS')

    # 1. 欢迎提示
    print('\n[1] 欢迎提示...')
    wav = os.path.join(AUDIO_DIR, 'welcome.wav')
    if os.path.exists(wav):
        play_wav('welcome.wav')
    else:
        tts('欢迎使用智能小车导航系统')

    time.sleep(1)

    # 2. 导航中提示
    print('\n[2] 导航中...')
    tts('正在导航')

    time.sleep(0.5)

    # 3. 循环 BGM
    print('\n[3] 背景音乐...')
    play_bgm()

    time.sleep(0.5)

    # 4. 到达提示
    print('\n[4] 到达提示...')
    wav = os.path.join(AUDIO_DIR, 'arrived.wav')
    if os.path.exists(wav):
        play_wav('arrived.wav')
    else:
        tts('已到达目的地，请下车')

    print('\n[完成] 测试结束')
    pygame.mixer.quit() if HAS_PYGAME else None


if __name__ == '__main__':
    main()

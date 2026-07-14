"""语音模块独立测试 — 零依赖，基于 aplay + ffplay"""
import os
import subprocess
import time

AUDIO_DIR = os.path.join(os.path.expanduser('~'),
                         'yahboomcar_ros2_ws/yahboomcar_ws/resource/audio')

# 检测可用工具
WAV_PLAYER = 'aplay'
MP3_PLAYER = None
for cmd in ['ffplay', 'mpg123', 'ffmpeg']:
    if subprocess.run(['which', cmd], capture_output=True).returncode == 0:
        MP3_PLAYER = cmd
        break

print(f'播放器: WAV={WAV_PLAYER}, MP3={MP3_PLAYER or "无"}')
print(f'音频目录: {AUDIO_DIR}')
print('=' * 40)


def play_wav(name):
    path = os.path.join(AUDIO_DIR, name)
    if os.path.exists(path):
        print(f'[播放] {name}')
        subprocess.run([WAV_PLAYER, '-q', path], capture_output=True)
    else:
        print(f'[跳过] {name} 不存在')


def play_bgm(seconds=5):
    if not MP3_PLAYER:
        print('[跳过] 无 MP3 播放器，小车可 apt install ffmpeg')
        return
    path = os.path.join(AUDIO_DIR, 'bgm.mp3')
    if not os.path.exists(path):
        print('[跳过] bgm.mp3 不存在')
        return
    print(f'[BGM] 播放 {seconds} 秒...')
    p = None
    try:
        if MP3_PLAYER == 'ffplay':
            p = subprocess.Popen(
                ['ffplay', '-nodisp', '-loop', '0', '-autoexit',
                 path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif MP3_PLAYER == 'mpg123':
            p = subprocess.Popen(
                ['mpg123', '--loop', '-1', path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif MP3_PLAYER == 'ffmpeg':
            p = subprocess.Popen(
                ['ffmpeg', '-stream_loop', '-1', '-i', path,
                 '-f', 'alsa', 'default', '-q:a', '0'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(seconds)
    finally:
        if p:
            p.terminate()


# ── 测试序列 ──
print('\n[1] 欢迎')
play_wav('welcome.wav')
time.sleep(0.5)

print('\n[2] 导航中')
play_wav('navigating.wav')
time.sleep(0.5)

print('\n[3] BGM 背景音乐')
play_bgm(5)

print('\n[4] 到达')
play_wav('arrived.wav')

print('\n[完成]')

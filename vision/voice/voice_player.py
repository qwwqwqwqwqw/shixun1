"""语音模块节点 — 零外部依赖，基于系统 aplay/ffplay。

触发时机：
  1. 小程序连接 → welcome.wav
  2. 导航开始   → navigating.wav + bgm.mp3 循环
  3. 到达确认   → arrived.wav

音频文件（resource/audio/）:
  - welcome.wav / navigating.wav / arrived.wav : 语音提示
  - bgm.mp3 : 背景音乐
"""
import os
import subprocess
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class VoicePlayer(Node):
    def __init__(self):
        super().__init__('voice_player')

        self.audio_dir = os.path.join(os.path.expanduser('~'),
                                      'yahboomcar_ros2_ws/yahboomcar_ws/resource/audio')

        # ── 检测可用播放器 ──
        self.wav_player = 'aplay'   # WAV 播放器（ALSA 自带）
        self.mp3_player = self._find_mp3_player()

        # ── 状态 ──
        self.bgm_proc = None

        # ── 订阅 ──
        self.sub_client = self.create_subscription(
            String, '/client_event', self.on_client, 10)
        self.sub_status = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.sub_arrival = self.create_subscription(
            Bool, '/arrival_confirmed', self.on_arrival, 10)

        self.get_logger().info(
            f'voice_player 已启动 — WAV={self.wav_player}, MP3={self.mp3_player or "无"}')

    def _find_mp3_player(self):
        """查找可用的 MP3 播放器"""
        for cmd in ['ffplay', 'mpg123', 'ffmpeg', 'cvlc']:
            if subprocess.run(['which', cmd],
                              capture_output=True).returncode == 0:
                return cmd
        return None

    # ──────────── 事件回调 ────────────

    def on_client(self, msg):
        if msg.data == 'connected':
            self._play_wav('welcome.wav')

    def on_nav_status(self, msg):
        text = msg.data
        if '导航中' in text or '开始导航' in text:
            self._play_wav('navigating.wav')
            self._start_bgm()

    def on_arrival(self, msg):
        if msg.data:
            self._stop_bgm()
            self._play_wav('arrived.wav')

    # ──────────── 音频播放 ────────────

    def _play_wav(self, filename):
        path = os.path.join(self.audio_dir, filename)
        if not os.path.exists(path):
            self.get_logger().warn(f'文件不存在: {filename}')
            return
        self.get_logger().info(f'[语音] {filename}')
        threading.Thread(
            target=lambda: subprocess.run(
                [self.wav_player, '-q', path],
                capture_output=True),
            daemon=True
        ).start()

    def _start_bgm(self):
        if not self.mp3_player:
            return
        path = os.path.join(self.audio_dir, 'bgm.mp3')
        if not os.path.exists(path):
            return
        self._stop_bgm()
        # ffplay 循环播放
        if self.mp3_player == 'ffplay':
            self.bgm_proc = subprocess.Popen(
                ['ffplay', '-nodisp', '-loop', '0',
                 '-autoexit', path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif self.mp3_player == 'mpg123':
            self.bgm_proc = subprocess.Popen(
                ['mpg123', '--loop', '-1', path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif self.mp3_player == 'ffmpeg':
            self.bgm_proc = subprocess.Popen(
                ['ffmpeg', '-stream_loop', '-1', '-i', path,
                 '-f', 'alsa', 'default', '-q:a', '0'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return
        self.get_logger().info('[BGM] 开始播放')

    def _stop_bgm(self):
        if self.bgm_proc:
            self.bgm_proc.terminate()
            self.bgm_proc = None
            self.get_logger().info('[BGM] 停止')

    def destroy_node(self):
        self._stop_bgm()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VoicePlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

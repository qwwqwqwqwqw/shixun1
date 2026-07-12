"""语音模块节点 — 小程序连接/导航中/到达确认 三个节点播放语音。

触发时机：
  1. 小程序 TCP 连接成功 → 播放欢迎提示
  2. 导航开始 → 循环播放背景音乐
  3. 到达确认 → 停止音乐，播放到达提示

依赖音频文件（resource/audio/）:
  - welcome.wav : 欢迎提示
  - arrived.wav : 到达提示
  - bgm.mp3     : 背景音乐

若缺失则自动用 espeak TTS 合成语音。
"""
import os
import subprocess
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool

try:
    import pygame.mixer
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class VoicePlayer(Node):
    def __init__(self):
        super().__init__('voice_player')

        self.declare_parameter('audio_dir', '')
        audio_dir = self.get_parameter('audio_dir').value or \
            os.path.join(os.path.expanduser('~'),
                         'yahboomcar_ros2_ws/yahboomcar_ws/resource/audio')
        self.audio_dir = os.path.abspath(audio_dir)

        # ── 初始化 pygame 混音器 ──
        self.has_audio = False
        if HAS_PYGAME:
            try:
                pygame.mixer.init()
                self.has_audio = True
            except Exception as e:
                self.get_logger().warn(f'pygame 混音器初始化失败: {e}')

        # ── 状态 ──
        self.navigating = False
        self.arrived = False
        self.bgm_playing = False

        # ── 订阅 ──
        self.sub_client = self.create_subscription(
            String, '/client_event', self.on_client, 10)
        self.sub_status = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.sub_arrival = self.create_subscription(
            Bool, '/arrival_confirmed', self.on_arrival, 10)

        self.get_logger().info('voice_player 已启动')

    # ──────────── 事件回调 ────────────

    def on_client(self, msg):
        """客户端连接/断开事件"""
        if msg.data == 'connected':
            self._speak('welcome.wav', '欢迎使用智能小车导航系统')

    def on_nav_status(self, msg):
        text = msg.data
        if '导航中' in text or '开始导航' in text:
            if not self.navigating:
                self.navigating = True
                self._start_bgm()
        elif '拒绝' in text or '失败' in text or '取消' in text:
            self._stop_bgm()
            self.navigating = False

    def on_arrival(self, msg):
        if msg.data:
            self._stop_bgm()
            self.navigating = False
            self._speak('arrived.wav', '已到达目的地，请下车')

    # ──────────── 音频播放 ────────────

    def _speak(self, filename, fallback_text):
        """播放语音文件；不存在则用 espeak TTS 合成"""
        path = os.path.join(self.audio_dir, filename)
        if os.path.exists(path) and self.has_audio:
            self._play_file(path)
            self.get_logger().info(f'[语音] {filename}')
        else:
            self._tts(fallback_text)

    def _start_bgm(self):
        """开始循环背景音乐"""
        if not self.bgm_playing and self.has_audio:
            bgm_path = os.path.join(self.audio_dir, 'bgm.mp3')
            if os.path.exists(bgm_path):
                try:
                    pygame.mixer.music.load(bgm_path)
                    pygame.mixer.music.play(-1)  # 循环播放
                    pygame.mixer.music.set_volume(0.3)
                    self.bgm_playing = True
                    self.get_logger().info('[BGM] 开始播放')
                except Exception as e:
                    self.get_logger().warn(f'BGM 加载失败: {e}')

    def _stop_bgm(self):
        if self.bgm_playing and self.has_audio:
            pygame.mixer.music.fadeout(500)
            self.bgm_playing = False
            self.get_logger().info('[BGM] 停止')

    def _play_file(self, path):
        """异步播放单个音频文件"""
        def _play():
            try:
                sound = pygame.mixer.Sound(path)
                sound.play()
            except Exception as e:
                self.get_logger().warn(f'播放失败 {path}: {e}')
        threading.Thread(target=_play, daemon=True).start()

    def _tts(self, text):
        """espeak 语音合成"""
        def _speak():
            try:
                subprocess.run(
                    ['espeak', '-v', 'zh', text],
                    timeout=5, capture_output=True)
            except FileNotFoundError:
                self.get_logger().warn('espeak 未安装，跳过语音')
            except Exception as e:
                self.get_logger().warn(f'TTS 失败: {e}')
        threading.Thread(target=_speak, daemon=True).start()

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

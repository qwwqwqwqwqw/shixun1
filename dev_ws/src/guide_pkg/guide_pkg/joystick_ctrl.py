"""摇杆/键盘控制节点 — 支持小程序远程控制 + 本地键盘调试。

发布话题：
  - /cmd_vel (geometry_msgs/Twist) : 底盘速度指令

小程序远程控制路径：
  小程序 → TCP:9090(aiserver_node) → /app_joystick(Twist) → joystick_ctrl → /cmd_vel → 底盘

本地键盘控制（调试）：
  u i o j k l m , . 全向移动  q/e 平移  w/x 加减速  空格急停

小车信息：
  - 底盘：麦克纳姆轮，AT32 驱动
  - 底盘驱动：ros2 run icar_bringup Mcnamu_driver_X3（快捷指令 n1）
"""
import sys
import termios
import tty
import select
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


# ── 键位映射（本地调试） ──
KEY_MAP = {
    'i': ( 1,  0,  0),   # 前进
    ',': (-1,  0,  0),   # 后退
    'j': ( 0,  0,  1),   # 左转
    'l': ( 0,  0, -1),   # 右转
    'u': ( 1,  0,  1),   # 左前
    'o': ( 1,  0, -1),   # 右前
    'm': (-1,  0,  1),   # 左后
    '.': (-1,  0, -1),   # 右后
    'q': ( 0,  1,  0),   # 左平移
    'e': ( 0, -1,  0),   # 右平移
    'k': ( 0,  0,  0),   # 停止
    ' ': ( 0,  0,  0),   # 急停
}


class JoystickCtrl(Node):
    def __init__(self):
        super().__init__('joystick_ctrl')
        # ── 发布底盘速度 ──
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)

        # ── 订阅小程序摇杆指令 ──
        self.sub_app = self.create_subscription(
            Twist, '/app_joystick', self.on_app_joystick, 10)

        # ── 速度参数 ──
        self.linear_speed = 0.3
        self.angular_speed = 0.8
        self.speed_scale = 1.0

        self.get_logger().info('joystick_ctrl 已启动 — 小程序远程 + 键盘调试')

    # ──────────── 小程序远程摇杆 ────────────

    def on_app_joystick(self, twist):
        """接收小程序摇杆指令（Twist），转发到 /cmd_vel"""
        self.pub_cmd.publish(twist)
        if twist.linear.x == 0 and twist.linear.y == 0 and twist.angular.z == 0:
            self.get_logger().info('[小程序] ■ 停止')
        else:
            self.get_logger().info(
                f'[小程序] → vx={twist.linear.x:.2f} '
                f'vy={twist.linear.y:.2f} wz={twist.angular.z:.2f}')

    # ──────────── 本地键盘控制 ────────────

    def _print_help(self):
        print("""
╔══════════════════════════════════════╗
║  iCar 键盘控制（调试用）             ║
║  u i o  左前/前/右前  q/e  左/右平移  ║
║  j k l  左转/停/右转  w/x  加减速     ║
║  m , .  左后/后/右后  空格  急停      ║
║  倍率: %.1fx  v=%.2f  w=%.2f         ║
╚══════════════════════════════════════╝
""" % (self.speed_scale,
       self.linear_speed * self.speed_scale,
       self.angular_speed * self.speed_scale))

    def process_key(self, key):
        if key == 'w':
            self.speed_scale = min(self.speed_scale + 0.2, 3.0)
            self._print_help()
            return
        if key == 'x':
            self.speed_scale = max(self.speed_scale - 0.2, 0.2)
            self._print_help()
            return
        if key not in KEY_MAP:
            return
        dx, dy, dz = KEY_MAP[key]
        twist = Twist()
        twist.linear.x = dx * self.linear_speed * self.speed_scale
        twist.linear.y = dy * self.linear_speed * self.speed_scale
        twist.angular.z = dz * self.angular_speed * self.speed_scale
        self.pub_cmd.publish(twist)
        self.get_logger().info(
            f'[键盘] vx={twist.linear.x:.2f} '
            f'vy={twist.linear.y:.2f} wz={twist.angular.z:.2f}')

    def stop(self):
        self.pub_cmd.publish(Twist())


def get_key(timeout=0.1):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.read(1) if rlist else ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main(args=None):
    rclpy.init(args=args)
    node = JoystickCtrl()
    node._print_help()
    try:
        while rclpy.ok():
            key = get_key(0.1)
            if key:
                if key == '\x03':
                    break
                node.process_key(key)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

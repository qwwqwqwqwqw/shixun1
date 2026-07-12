"""摇杆/键盘控制节点 — 用于测试 ROS2 节点发布与底盘运动是否正常。

发布话题：
  - /cmd_vel (geometry_msgs/Twist) : 麦克纳姆轮底盘速度指令

控制方式：终端键盘输入（类似 yahboom_keyboard）
  u  i  o       左前  前  右前
  j  k  l   →   左转  停  右转
  m  ,  .       左后  后  右后

  q : 左平移     e : 右平移
  w : 加速       x : 减速
  空格 : 急停

小车信息（iCar 智能小车）：
  - 底盘：4 麦克纳姆轮，AT32 开发板驱动
  - 底盘驱动节点：ros2 run icar_bringup Mcnamu_driver_X3（快捷指令 n1）
  - ROS 版本：小车容器内 Foxy
  - 速度档位参考：30 / 50 / 70 / 100（全速）

用法：
  ros2 run guide_pkg joystick_ctrl
  或
  python3 joystick_ctrl.py
"""
import sys
import termios
import tty
import select
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


# 键位 → (线速度x, 线速度y, 角速度z) 映射
# 麦轮底盘支持全向移动：x=前后, y=左右平移, z=旋转
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
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        # 速度参数（米/秒 和 弧度/秒）
        self.linear_speed = 0.3    # 线速度基础值
        self.angular_speed = 0.8   # 角速度基础值
        self.speed_scale = 1.0     # 速度倍率（w 加速 / x 减速）
        self.max_scale = 3.0
        self.min_scale = 0.2
        self.current_twist = Twist()
        self.get_logger().info('joystick_ctrl 已启动 — 等待键盘输入')
        self._print_help()

    def _print_help(self):
        help_text = """
╔══════════════════════════════════════╗
║     iCar 摇杆/键盘控制 — 测试模式     ║
╠══════════════════════════════════════╣
║  u  i  o      左前  前  右前         ║
║  j  k  l  →   左转  停  右转         ║
║  m  ,  .      左后  后  右后         ║
║                                      ║
║  q : 左平移    e : 右平移            ║
║  w : 加速      x : 减速              ║
║  空格 : 急停   Ctrl+C : 退出         ║
╠══════════════════════════════════════╣
║  当前速度倍率: %.1fx                 ║
║  线速度: %.2f m/s  角速度: %.2f rad/s║
╚══════════════════════════════════════╝
""" % (self.speed_scale, self.linear_speed * self.speed_scale,
       self.angular_speed * self.speed_scale)
        print(help_text)

    def process_key(self, key):
        """处理键盘输入，发布对应速度指令"""
        if key == 'w':
            self.speed_scale = min(self.speed_scale + 0.2, self.max_scale)
            self.get_logger().info(f'加速 → 倍率 {self.speed_scale:.1f}x')
            self._print_help()
            return
        if key == 'x':
            self.speed_scale = max(self.speed_scale - 0.2, self.min_scale)
            self.get_logger().info(f'减速 → 倍率 {self.speed_scale:.1f}x')
            self._print_help()
            return
        if key not in KEY_MAP:
            return

        dx, dy, dz = KEY_MAP[key]
        twist = Twist()
        twist.linear.x = dx * self.linear_speed * self.speed_scale
        twist.linear.y = dy * self.linear_speed * self.speed_scale
        twist.angular.z = dz * self.angular_speed * self.speed_scale
        self.current_twist = twist
        self.pub_cmd.publish(twist)

        if key in ('k', ' '):
            self.get_logger().info('■ 停止')
        else:
            self.get_logger().info(
                f'→ vx={twist.linear.x:.2f} vy={twist.linear.y:.2f} '
                f'wz={twist.angular.z:.2f}')

    def stop(self):
        """停止时发布零速度"""
        self.pub_cmd.publish(Twist())
        self.get_logger().info('已发布停止指令')


def get_key(timeout=0.1):
    """非阻塞读取单字符按键"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return key


def main(args=None):
    rclpy.init(args=args)
    node = JoystickCtrl()

    try:
        while rclpy.ok():
            key = get_key(0.1)
            if key:
                if key == '\x03':  # Ctrl+C
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

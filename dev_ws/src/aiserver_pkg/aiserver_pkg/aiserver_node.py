"""TCP Socket 服务节点 — B组长与D组员协作。

通信协议：TCP（非WebSocket），小程序通过 wx.createTCPSocket() 连接。

功能：
  1. TCP Server（端口 9090），接收小程序 JSONL 指令
  2. 指令类型：
     - 导航:  {"type":"navigate", "room":"501"}
     - 摇杆:  {"type":"joystick", "vx":0.3, "vy":0, "wz":0}
     - 取消:  {"type":"cancel"}
     - 人脸:  {"type":"face_mode", "action":"start"}
     - 心跳:  {"type":"ping"}
  3. 订阅 ROS2 状态话题，实时回传小程序
"""
import json
import math
import socket
import threading
import rclpy  # pyright: ignore[reportMissingImports]
from rclpy.node import Node  # pyright: ignore[reportMissingImports]
from std_msgs.msg import String, Bool  # pyright: ignore[reportMissingImports]
from geometry_msgs.msg import Twist  # pyright: ignore[reportMissingImports]


class AiServerNode(Node):
    def __init__(self):
        super().__init__('aiserver_node')
        self.declare_parameter('tcp_host', '0.0.0.0')
        self.declare_parameter('tcp_port', 9090)
        self.tcp_host = self.get_parameter('tcp_host').value
        self.tcp_port = self.get_parameter('tcp_port').value

        # ── 发布器 ──
        self.pub_command_room = self.create_publisher(
            String, '/command_room', 10)
        self.pub_face_control = self.create_publisher(
            String, '/face_mode_control', 10)
        self.pub_app_joystick = self.create_publisher(
            Twist, '/app_joystick', 10)
        self.pub_cancel = self.create_publisher(
            Bool, '/navigation_cancel', 10)
        self.pub_client_event = self.create_publisher(
            String, '/client_event', 10)

        # ── 订阅器 ──
        self.sub_status = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.sub_arrival = self.create_subscription(
            Bool, '/arrival_confirmed', self.on_arrival, 10)
        self.sub_face_status = self.create_subscription(
            String, '/face_recognition_status', self.on_face_status, 10)

        # ── TCP 客户端管理 ──
        self._tcp_clients = []  # type: list[socket.socket]
        self._tcp_lock = threading.Lock()

        # ── 启动 TCP 服务 ──
        self._start_tcp_server()
        self.get_logger().info(
            f'TCP 服务已启动 — {self.tcp_host}:{self.tcp_port}')

    # ──────────── ROS2 状态回调 ────────────

    def on_nav_status(self, msg):
        self.get_logger().info(f'[导航状态] {msg.data}')
        self._broadcast({'type': 'nav_status', 'message': msg.data})

    def on_arrival(self, msg):
        self.get_logger().info(f'[到达确认] {msg.data}')
        self._broadcast({'type': 'arrival', 'message': msg.data})

    def on_face_status(self, msg):
        """把视觉节点的 JSON 状态转发给小程序。"""
        try:
            payload = json.loads(msg.data)
            if not isinstance(payload, dict):
                raise ValueError('状态不是 JSON 对象')
        except (json.JSONDecodeError, ValueError):
            payload = {'status': 'info', 'message': msg.data}
        payload['type'] = 'face_status'
        self._broadcast(payload)

    # ──────────── TCP 广播 ────────────

    def _broadcast(self, data):
        payload = (json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8')
        with self._tcp_lock:
            dead = []
            for sock in self._tcp_clients:
                try:
                    sock.sendall(payload)
                except (BrokenPipeError, OSError):
                    dead.append(sock)
            for s in dead:
                self._tcp_clients.remove(s)

    # ──────────── TCP 服务器 ────────────

    def _start_tcp_server(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.tcp_host, self.tcp_port))
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while rclpy.ok():
            try:
                conn, addr = self.server_sock.accept()
                self.get_logger().info(f'[连接] 小程序 {addr[0]}:{addr[1]}')
                self.pub_client_event.publish(String(data='connected'))
                with self._tcp_lock:
                    self._tcp_clients.append(conn)
                threading.Thread(
                    target=self._client_handler,
                    args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _client_handler(self, conn, addr):
        buf = b''
        try:
            while rclpy.ok():
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    self._process_command(line.decode('utf-8'))
        except (ConnectionResetError, OSError):
            pass
        finally:
            self.get_logger().info(f'[断开] {addr[0]}:{addr[1]}')
            self.pub_client_event.publish(String(data='disconnected'))
            # TCP 断开时立即发布零速度，避免小车保持最后一条运动指令。
            self.pub_app_joystick.publish(Twist())
            self.pub_face_control.publish(String(data='stop'))
            with self._tcp_lock:
                if conn in self._tcp_clients:
                    self._tcp_clients.remove(conn)
            try:
                conn.close()
            except OSError:
                pass

    # ──────────── 指令处理 ────────────

    def _process_command(self, raw):
        try:
            cmd = json.loads(raw)
        except json.JSONDecodeError:
            self.get_logger().warn(f'[协议错误] {raw[:50]}')
            return

        msg_type = cmd.get('type', '')

        if msg_type == 'navigate':
            room = cmd.get('room', '')
            if room:
                msg = String(data=str(room))
                self.pub_command_room.publish(msg)
                self.get_logger().info(f'[导航] 教室 {room}')
                self._broadcast({
                    'type': 'ack', 'command': 'navigate',
                    'room': room, 'status': 'accepted'
                })

        elif msg_type == 'joystick':
            twist = Twist()
            twist.linear.x = self._bounded_float(cmd.get('vx', 0), -0.5, 0.5)
            twist.linear.y = self._bounded_float(cmd.get('vy', 0), -0.5, 0.5)
            twist.angular.z = self._bounded_float(cmd.get('wz', 0), -1.5, 1.5)
            self.pub_app_joystick.publish(twist)

        elif msg_type == 'cancel':
            self.pub_cancel.publish(Bool(data=True))
            self.get_logger().info('[导航] 取消')
            self._broadcast({'type': 'ack', 'command': 'cancel', 'status': 'accepted'})

        elif msg_type == 'face_mode':
            action = str(cmd.get('action', 'start')).strip().lower()
            if action not in ('start', 'stop'):
                self._broadcast({
                    'type': 'error',
                    'message': f'不支持的人脸模式指令: {action}',
                })
                return
            if (action == 'start' and
                    self.pub_face_control.get_subscription_count() == 0):
                self._broadcast({
                    'type': 'error',
                    'message': '人脸识别节点未启动或尚未接入 ROS2',
                })
                return
            self.get_logger().info(f'[人脸] {action}')
            self.pub_face_control.publish(String(data=action))
            self._broadcast({
                'type': 'ack',
                'command': 'face_mode',
                'action': action,
                'status': 'accepted',
            })

        elif msg_type == 'ping':
            self._broadcast({'type': 'pong', 'message': 'ok'})

        else:
            self.get_logger().warn(f'[未知指令] {msg_type}')

    @staticmethod
    def _bounded_float(value, lower, upper):
        """将外部速度值转换为有限浮点数并限制在安全范围内。"""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(number):
            return 0.0
        return max(lower, min(upper, number))

    # ──────────── 资源释放 ────────────

    def destroy_node(self):
        self.pub_app_joystick.publish(Twist())
        self.pub_face_control.publish(String(data='stop'))
        with self._tcp_lock:
            for s in self._tcp_clients:
                try:
                    s.close()
                except OSError:
                    pass
            self._tcp_clients.clear()
        try:
            self.server_sock.close()
        except OSError:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = AiServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

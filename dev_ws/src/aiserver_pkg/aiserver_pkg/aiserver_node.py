"""微信小程序/Web 与 ROS2 之间的 WebSocket 桥接节点。"""
import asyncio
import json
import queue
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
import websockets
from websockets.exceptions import ConnectionClosed


class AiServerNode(Node):
    def __init__(self):
        super().__init__('aiserver_node')
        self.declare_parameter('ws_host', '0.0.0.0')
        self.declare_parameter('ws_port', 9090)
        self.ws_host = self.get_parameter('ws_host').value
        self.ws_port = self.get_parameter('ws_port').value

        # 发布：将前端指令转发为 ROS2 话题
        self.pub_command_room = self.create_publisher(
            String, '/command_room', 10)
        self.pub_face_room = self.create_publisher(
            String, '/face_room', 10)
        self.pub_cancel = self.create_publisher(
            Bool, '/navigation_cancel', 10)

        # 订阅：导航状态回传前端
        self.sub_status = self.create_subscription(
            String, '/navigation_status', self.on_nav_status, 10)
        self.sub_arrival = self.create_subscription(
            Bool, '/arrival_confirmed', self.on_arrival_confirmed, 10)
        self.sub_pose = self.create_subscription(
            String, '/robot_pose', self.on_robot_pose, 10)

        self._clients = set()
        self._command_queue = queue.Queue()
        self._last_status = '等待导航指令'
        self._current_room = ''
        self._loop = None
        self._shutdown_event = None
        self._ws_thread = threading.Thread(
            target=self._run_websocket_server,
            name='aiserver-websocket',
            daemon=True,
        )
        self._ws_thread.start()
        self._queue_timer = self.create_timer(0.05, self._drain_command_queue)
        self.get_logger().info('aiserver_node 已启动 — 等待前端连接')

    def on_nav_status(self, msg):
        """导航状态回调 → 通过 WebSocket 回传前端"""
        self._last_status = msg.data
        self.get_logger().info(f'导航状态: {msg.data}')
        self._broadcast({
            'type': 'nav_status',
            'message': msg.data,
            'room': self._current_room,
        })

    def on_arrival_confirmed(self, msg):
        """将多传感器到达确认结果回传前端。"""
        self._broadcast({
            'type': 'arrival_confirmed',
            'confirmed': bool(msg.data),
            'room': self._current_room,
        })

    def on_robot_pose(self, msg):
        """转发可选的位置信息；消息可以是 JSON，也可以是普通文本。"""
        try:
            pose = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError):
            pose = {'text': msg.data}
        self._broadcast({'type': 'robot_pose', 'data': pose})

    def handle_command(self, room_number):
        """处理前端教室号指令 → 发布到 /command_room"""
        self._current_room = room_number
        msg = String()
        msg.data = room_number
        self.pub_command_room.publish(msg)
        self.get_logger().info(f'已转发教室号: {room_number}')

    def handle_face_result(self, room_number):
        """处理人脸识别结果 → 发布到 /face_room"""
        msg = String()
        msg.data = room_number
        self.pub_face_room.publish(msg)
        self.get_logger().info(f'已转发人脸房间号: {room_number}')

    def _drain_command_queue(self):
        """在 ROS2 执行线程中处理来自 WebSocket 线程的指令。"""
        while True:
            try:
                command, data = self._command_queue.get_nowait()
            except queue.Empty:
                return

            if command == 'command_room':
                self.handle_command(data)
            elif command == 'face_room':
                self.handle_face_result(data)
            elif command == 'cancel':
                self.pub_cancel.publish(Bool(data=True))
                self._last_status = '正在取消导航'
                self.get_logger().info('已转发导航取消指令')

    @staticmethod
    def _valid_room(room):
        """教室号只允许简短可打印文本，防止空值和异常载荷。"""
        return (
            isinstance(room, str)
            and 0 < len(room.strip()) <= 32
            and all(char.isprintable() for char in room)
        )

    async def _handle_ws_message(self, websocket, raw_message):
        try:
            message = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            await self._send(websocket, {
                'type': 'error',
                'message': '消息必须是合法 JSON',
            })
            return

        message_type = message.get('type')
        if message_type in ('command_room', 'face_room'):
            room = str(message.get('data', '')).strip()
            if not self._valid_room(room):
                await self._send(websocket, {
                    'type': 'error',
                    'message': '教室号不能为空且不能超过 32 个字符',
                })
                return
            self._command_queue.put((message_type, room))
            await self._send(websocket, {
                'type': 'command_ack',
                'command': message_type,
                'room': room,
            })
        elif message_type == 'cancel':
            self._command_queue.put(('cancel', None))
            await self._send(websocket, {
                'type': 'command_ack',
                'command': 'cancel',
            })
        elif message_type == 'status':
            await self._send(websocket, {
                'type': 'nav_status',
                'message': self._last_status,
                'room': self._current_room,
            })
        elif message_type == 'ping':
            await self._send(websocket, {'type': 'pong'})
        else:
            await self._send(websocket, {
                'type': 'error',
                'message': f'不支持的指令类型: {message_type}',
            })

    async def _ws_handler(self, websocket, *args):
        self._clients.add(websocket)
        remote = getattr(websocket, 'remote_address', 'unknown')
        self.get_logger().info(f'前端已连接: {remote}')
        try:
            await self._send(websocket, {
                'type': 'connection',
                'connected': True,
                'message': '已连接小车服务',
            })
            await self._send(websocket, {
                'type': 'nav_status',
                'message': self._last_status,
                'room': self._current_room,
            })
            async for raw_message in websocket:
                await self._handle_ws_message(websocket, raw_message)
        except ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            self.get_logger().info(f'前端已断开: {remote}')

    @staticmethod
    async def _send(websocket, payload):
        await websocket.send(json.dumps(payload, ensure_ascii=False))

    async def _broadcast_async(self, payload):
        if not self._clients:
            return
        encoded = json.dumps(payload, ensure_ascii=False)
        disconnected = []
        for client in tuple(self._clients):
            try:
                await client.send(encoded)
            except ConnectionClosed:
                disconnected.append(client)
        for client in disconnected:
            self._clients.discard(client)

    def _broadcast(self, payload):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_async(payload),
                self._loop,
            )

    def _run_websocket_server(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._shutdown_event = asyncio.Event()
        try:
            self._loop.run_until_complete(self._serve_websocket())
        except Exception as exc:
            self.get_logger().error(f'WebSocket 服务异常: {exc}')
        finally:
            self._loop.close()

    async def _serve_websocket(self):
        async with websockets.serve(
            self._ws_handler,
            self.ws_host,
            self.ws_port,
            ping_interval=20,
            ping_timeout=20,
        ):
            self.get_logger().info(
                f'WebSocket 服务监听 ws://{self.ws_host}:{self.ws_port}')
            await self._shutdown_event.wait()

    def stop_websocket(self):
        """停止 WebSocket 线程，供节点退出时调用。"""
        if self._loop and self._loop.is_running() and self._shutdown_event:
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        if self._ws_thread.is_alive():
            self._ws_thread.join(timeout=3)


def main(args=None):
    rclpy.init(args=args)
    node = AiServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_websocket()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

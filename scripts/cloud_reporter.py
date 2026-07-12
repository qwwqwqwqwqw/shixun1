#!/usr/bin/env python3
"""云平台上报节点 (MQTT) — E组员负责 (云平台集成)

这个程序的唯一作用：把小车本地的 ROS2 状态话题，通过 MQTT 转发到云端，
从而实现"远程监控"（在手机/电脑/云平台上实时看到小车在干什么）。

订阅的本地话题：
  - /navigation_status  (std_msgs/String)   导航状态，例如 "开始导航到 101"
  - /arrival_confirmed  (std_msgs/Bool)      最终到达确认（true / false）

发布到云端的 MQTT 主题：
  - icar/<车号>/status   导航状态（JSON）
  - icar/<车号>/arrival  到达确认（JSON）

可用环境变量（在 Linux 小车里用 export 设置，或写进 .env）：
  MQTT_BROKER    默认 broker.emqx.io  （一个免费的公共测试 Broker，免账号）
  MQTT_PORT      默认 1883
  MQTT_USERNAME  可选（如果云端 Broker 需要账号）
  MQTT_PASSWORD  可选
  CAR_ID         默认 icar01  （多台小车时用它区分，例如 icar02）

纯 MQTT 自测（不需要 ROS2，在你自己的 Windows 电脑上就能跑）：
  pip install paho-mqtt
  ICAR_SELFTEST=1 python3 scripts/cloud_reporter.py
"""
import os
import json
import time
import datetime


def _car_id():
    return os.environ.get("CAR_ID", "icar01")


def build_status_payload(text):
    return {
        "car_id": _car_id(),
        "type": "navigation_status",
        "status": text,
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
    }


def build_arrival_payload(confirmed: bool):
    return {
        "car_id": _car_id(),
        "type": "arrival_confirmed",
        "confirmed": bool(confirmed),
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
    }


class MqttBridge:
    """对 paho-mqtt 的轻封装，方便单独测试。"""

    def __init__(self, broker=None, port=None, username=None, password=None):
        import paho.mqtt.client as mqtt
        self.broker = broker or os.environ.get("MQTT_BROKER", "broker.emqx.io")
        self.port = int(port or os.environ.get("MQTT_PORT", "1883"))
        self.username = username or os.environ.get("MQTT_USERNAME") or None
        self.password = password or os.environ.get("MQTT_PASSWORD") or None
        # 兼容 paho-mqtt 1.x 与 2.x 两种 API
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            self.client = mqtt.Client()
        if self.username:
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = lambda c, u, f, rc, p=None: print(f"[MQTT] 连接结果 rc={rc}")

    def connect(self):
        print(f"[MQTT] 正在连接 {self.broker}:{self.port}")
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def publish(self, topic, payload: dict):
        msg = json.dumps(payload, ensure_ascii=False)
        info = self.client.publish(topic, msg, qos=1)
        print(f"[MQTT] 发布 {topic}: {msg} (mid={info.mid})")

    def status_topic(self):
        return f"icar/{_car_id()}/status"

    def arrival_topic(self):
        return f"icar/{_car_id()}/arrival"

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


def selftest():
    """不需要 ROS2，直接演示把一条状态发到云端。"""
    print("=== MQTT 自测模式（不依赖 ROS2）===")
    bridge = MqttBridge()
    try:
        bridge.connect()
        time.sleep(1.0)
        bridge.publish(bridge.status_topic(), build_status_payload("开始导航到 101（来源: manual）"))
        time.sleep(0.5)
        bridge.publish(bridge.arrival_topic(), build_arrival_payload(True))
        time.sleep(1.0)
        print("自测完成。请用 EMQX 在线客户端订阅主题 icar/icar01/status 查看消息。")
    finally:
        bridge.disconnect()


def main():
    """ROS2 节点主体：订阅本地话题 -> 转发到云端 MQTT。"""
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Bool

    class CloudReporterNode(Node):
        def __init__(self):
            super().__init__('cloud_reporter')
            self.bridge = MqttBridge()
            self.bridge.connect()
            self.sub_status = self.create_subscription(
                String, '/navigation_status', self.on_status, 10)
            self.sub_arrival = self.create_subscription(
                Bool, '/arrival_confirmed', self.on_arrival, 10)
            self.get_logger().info('cloud_reporter 已启动，MQTT 上报已开启')

        def on_status(self, msg):
            self.bridge.publish(self.bridge.status_topic(), build_status_payload(msg.data))

        def on_arrival(self, msg):
            self.bridge.publish(self.bridge.arrival_topic(), build_arrival_payload(msg.data))

        def destroy(self):
            self.bridge.disconnect()
            super().destroy_node()

    rclpy.init()
    node = CloudReporterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy()
    rclpy.shutdown()


if __name__ == '__main__':
    if os.environ.get('ICAR_SELFTEST') == '1':
        selftest()
    else:
        main()

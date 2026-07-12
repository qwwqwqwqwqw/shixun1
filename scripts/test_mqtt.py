#!/usr/bin/env python3
"""MQTT 接收测试 — 仅用于本地验证"云端能否收到消息"。
不需要 ROS2。运行： python3 scripts/test_mqtt.py
它会订阅 icar/icar01/# 并打印收到的消息（监听 15 秒）。
配合 cloud_reporter.py 的 ICAR_SELFTEST=1 自测一起用：
  终端 A: python3 scripts/test_mqtt.py
  终端 B: ICAR_SELFTEST=1 python3 scripts/cloud_reporter.py
终端 A 能看到终端 B 发出的消息，就说明上报链路通了。
"""
import os
import time

import paho.mqtt.client as mqtt

BROKER = os.environ.get("MQTT_BROKER", "broker.emqx.io")
PORT = int(os.environ.get("MQTT_PORT", "1883"))
TOPIC = f"icar/{os.environ.get('CAR_ID', 'icar01')}/#"


def on_connect(c, u, f, rc, p=None):
    print(f"[SUB] 连接 rc={rc}，订阅 {TOPIC}")
    c.subscribe(TOPIC)


def on_message(c, u, msg):
    print(f"[SUB] 收到 {msg.topic}: {msg.payload.decode('utf-8', 'ignore')}")


try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()
print("监听 15 秒，请在此期间用 cloud_reporter 自测发布消息……")
time.sleep(15)
client.loop_stop()
client.disconnect()
print("结束。")

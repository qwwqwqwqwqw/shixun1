# iCar 智能教室导航小程序

## 开发者工具运行

1. 用微信开发者工具导入本目录 `app/miniprogram`。
2. 在 `app.js` 中把 `serverUrl` 改为小车实际地址，例如
   `ws://192.168.8.10:9090`。
3. 电脑、小车和调试手机连接同一局域网。
4. 开发阶段在“详情 → 本地设置”中勾选“不校验合法域名”。

`project.config.json` 使用测试 AppID。需要真机发布时，替换成自己的
小程序 AppID，并使用备案域名提供 `wss://` 服务。

## 小车端启动

在 ROS2 容器内执行：

```bash
cd /home/yahboom/icar_classroom_guide/dev_ws
colcon build --packages-select aiserver_pkg --symlink-install
source install/setup.bash
ros2 launch aiserver_pkg aiserver_launch.py ws_port:=9090
```

启动成功后应出现：

```text
WebSocket 服务监听 ws://0.0.0.0:9090
```

如果缺少依赖：

```bash
python3 -m pip install "websockets>=10.0"
```

## 联调检查

监听小程序发出的教室号：

```bash
ros2 topic echo /command_room
```

模拟导航状态与位置：

```bash
ros2 topic pub --once /navigation_status std_msgs/msg/String \
  "{data: '导航中...'}"
ros2 topic pub --once /robot_pose std_msgs/msg/String \
  "{data: '{\"x\":1.2,\"y\":3.4,\"yaw\":0.0}'}"
ros2 topic pub --once /arrival_confirmed std_msgs/msg/Bool \
  "{data: true}"
```

监听取消指令：

```bash
ros2 topic echo /navigation_cancel
```

注意：`guide_node` 还需要订阅 `/navigation_cancel` 并调用 Nav2 取消接口，
小程序的“取消导航”按钮才能真正停止小车。

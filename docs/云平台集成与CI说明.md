# 云平台集成与 CI/CD 说明（E 组员交付物）

> 本文档给你（E 组员）用。目标：通过 GitHub Actions 实现代码自动构建，
> 通过 MQTT 把小车状态上报云端，实现持续集成与远程监控。

---

## 一、你做了哪三件事

| 交付物 | 文件 | 一句话作用 |
|--------|------|------------|
| 1. GitHub Actions CI | `.github/workflows/ci.yml` | 你一推送代码，GitHub 云端自动帮你"检查语法 + 编译 ROS2 代码" |
| 2. MQTT 状态上报 | `scripts/cloud_reporter.py` | 把小车状态（`/navigation_status`、`/arrival_confirmed`）发到云端，手机/电脑可远程看 |
| 3. 自动部署脚本 | `scripts/deploy.sh` | 一条命令把最新代码同步到小车并重新编译、重启 |

辅助文件：
- `scripts/test_mqtt.py`：本地验证"消息确实发到云端"的小工具
- `requirements.txt` 已加入 `paho-mqtt`（MQTT 用的 Python 库）

---

## 二、名词先解释

- **GitHub Actions**：GitHub 自带的一个"机器人"。你 push 代码，它就在云端自动跑你写好的脚本。
- **CI（持续集成）**：上面那个机器人自动"构建/检查"你的代码，避免把坏代码合进去。
- **MQTT**：一种很轻量的"发消息"协议。一个程序往某个"主题"发消息，另一个程序订阅这个主题就能收到。非常适合物联网/小车上报状态。
- **Broker（代理）**：收发 MQTT 消息的中转服务器。本项目用免费的 `broker.emqx.io`，不用你自己搭服务器。
- **ROS2 话题**：小车内部各模块之间传递消息的通道。我们要上报的就是其中两个：`/navigation_status`（导航状态）和 `/arrival_confirmed`（到达确认）。

---

## 三、验证成果（最重要）

### ✅ 验证 1：CI 自动构建（最容易，只要会 git push）

1. 把代码推送到 GitHub：
   ```bash
   git add .
   git commit -m "feat: 添加云平台集成与CI/CD"
   git push
   ```
2. 打开 GitHub 仓库页面 → 点顶部 **Actions** 标签。
3. 应该能看到一个叫 **CI** 的工作流在运行，最后变成绿色 ✅。
4. 点进去能看到三个任务都打勾：
   - `语法与格式检查 (Lint)` ✅
   - `ROS2 自动构建 (Build)` ✅（用 ROS2 官方镜像编译了 guide_pkg、aiserver_pkg）
   - `自动部署到小车 (Deploy)`：如果没配置小车密钥会显示"跳过"，这**是正常的**。

> 看到 Lint 和 Build 都是绿色，就说明"GitHub Actions 实现代码自动构建"完成了。

### ✅ 验证 2：MQTT 状态上报（在你自己电脑就能测，不需要小车）

这一步不需要 ROS2，也不需要小车，只要能上网。

1. 安装 MQTT 库（在你自己的电脑，Windows 也行）：
   ```bash
   pip install paho-mqtt
   ```
2. 打开**两个**命令行窗口（终端 A、终端 B），都进入项目目录。
3. 终端 A 先运行"接收测试"（它会监听 15 秒）：
   ```bash
   python scripts/test_mqtt.py
   ```
4. 终端 B 再运行"上报自测"（会发两条测试消息）：
   ```bash
   # Linux/Mac:
   ICAR_SELFTEST=1 python scripts/cloud_reporter.py
   # Windows PowerShell:
   $env:ICAR_SELFTEST="1"; python scripts/cloud_reporter.py
   ```
5. 如果终端 A 里出现了类似下面的内容，就说明**上报链路通了**：
   ```
   [SUB] 收到 icar/icar01/status: {"car_id": "icar01", "type": "navigation_status", "status": "开始导航到 101（来源: manual）", ...}
   [SUB] 收到 icar/icar01/arrival: {"car_id": "icar01", "type": "arrival_confirmed", "confirmed": true, ...}
   ```

**另一种更直观的验证**：打开网页 https://www.emqx.io/online-mqtt-client ，
点击"Connect"，然后订阅主题 `icar/icar01/#`，再运行上面的上报自测，
网页上就能实时看到小车状态消息——这就是"远程监控"的效果。

> 看到消息从脚本发到云端（被另一个客户端收到），就说明"通过 MQTT 将小车状态上报云端"完成了。

### ✅ 验证 3：自动部署脚本（需要能 SSH 连上小车）

1. 先配置好 SSH 免密登录（只需做一次）：
   ```bash
   ssh-copy-id yahboom@192.168.1.120
   ```
2. 运行部署脚本：
   ```bash
   bash scripts/deploy.sh 192.168.1.120
   ```
3. 看到 `[OK] 部署完成！` 就说明代码已同步到小车并重新编译。

> 注意：`.sh` 脚本要在 **Linux 环境**里运行（你的 Ubuntu 虚拟机，或 WSL，或小车本身）。
> 直接在 Windows 的 CMD/PowerShell 里跑不了 `.sh`。

---

## 四、在小车真正运行时怎么用

当小车的 ROS2 系统启动后，额外再开一个终端运行上报节点，小车状态就会自动流向云端：

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
source ~/icar_classroom_guide/dev_ws/install/setup.bash
python3 ~/icar_classroom_guide/scripts/cloud_reporter.py
```

如果想让它在后台一直跑，可加 `nohup ... &` 或写进 `docker-compose.yml` 的 `command` 里。

---

## 五、可选：让 CI 自动部署到小车

如果你希望"push 代码后 GitHub 自动帮你部署到小车"，需要在 GitHub 仓库设置里
（Settings → Secrets and variables → Actions → New repository secret）添加两个密钥：
- `CAR_SSH_KEY`：你电脑上 `~/.ssh/id_ed25519` 的**私钥内容**
- `CAR_HOST`：小车 IP，例如 `192.168.1.120`

配置好后，push 到 `master` 分支时，`deploy` 任务就会自动执行 `scripts/deploy.sh`。
**没配置也没关系，CI 其余部分照常工作。**

---

## 六、常见问题

- **CI 里 flake8 报黄字/警告**：正常现象，已被设为"仅提示，不阻断"，不影响绿色通过。
- **build 任务失败**：通常是某个 Python 文件语法错误。看 Actions 日志里 `Python 语法编译检查` 的输出，改掉报错的文件即可。
- **MQTT 测不通**：确认电脑能上网；免费公共 Broker `broker.emqx.io` 偶尔不稳，可换 `test.mosquitto.org`。
- **deploy 跳过**：没配置 Secrets 就会跳过，属正常。

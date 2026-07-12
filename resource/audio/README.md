# audio/ — 语音模块音频文件

## 文件列表

| 文件 | 用途 | 生成方式 |
|------|------|----------|
| `welcome.wav` | 小程序连接提示 | `espeak -w welcome.wav "欢迎使用智能小车导航系统"` |
| `arrived.wav` | 到达确认提示 | `espeak -w arrived.wav "已到达目的地"` |
| `bgm.mp3` | 导航中背景音乐 | 放入任意 MP3 文件 |

## 快速生成语音文件（小车上执行）

```bash
cd ~/code/yahboomcar_ws/src/resource/audio
sudo apt install -y espeak
espeak -w welcome.wav -v zh "欢迎使用智能小车导航系统"
espeak -w arrived.wav -v zh "已到达目的地，请下车"
```

// app.js — 小程序入口
App({
  globalData: {
    serverUrl: 'ws://192.168.1.100:9090',  // aiserver_node 的 WebSocket 地址
    currentRoom: '',
    navStatus: '',
    ws: null,
  },
  onLaunch() {
    this.connectWebSocket();
  },
  connectWebSocket() {
    const ws = wx.connectSocket({ url: this.globalData.serverUrl });
    ws.onMessage((res) => {
      const data = JSON.parse(res.data);
      if (data.type === 'nav_status') {
        this.globalData.navStatus = data.message;
      }
    });
    this.globalData.ws = ws;
  },
  sendCommand(room) {
    if (this.globalData.ws) {
      this.globalData.ws.send({ data: JSON.stringify({ type: 'command_room', data: room }) });
    }
  },
});

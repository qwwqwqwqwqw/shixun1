// 首页逻辑 — 选择或输入教室号并发送导航指令
const app = getApp();

Page({
  data: {
    rooms: ['101', '102', '103', '104', '105'],
    selectedRoom: '',
    customRoom: '',
    connected: false,
  },

  onLoad() {
    this.unsubscribe = app.subscribe((state) => {
      this.setData({ connected: state.connected });
    });
  },

  onUnload() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
  },

  selectRoom(e) {
    const room = e.currentTarget.dataset.room;
    this.setData({ selectedRoom: room, customRoom: '' });
    app.globalData.currentRoom = room;
  },

  inputRoom(e) {
    const room = e.detail.value.replace(/\s/g, '').slice(0, 32);
    this.setData({ customRoom: room, selectedRoom: '' });
    app.globalData.currentRoom = room;
  },

  reconnect() {
    app.reconnect();
    wx.showToast({ title: '正在连接小车', icon: 'none' });
  },

  startNavigate() {
    const room = (this.data.customRoom || this.data.selectedRoom).trim();
    if (!room) {
      wx.showToast({ title: '请选择或输入教室号', icon: 'none' });
      return;
    }
    app.sendCommand(room);
    wx.navigateTo({ url: '/pages/status/status' });
  },

  startFaceRecognition() {
    wx.showToast({
      title: '人脸识别为第二版功能',
      icon: 'none',
    });
  },
});

// 首页逻辑 — 选择或输入教室号并发送导航指令
const app = getApp();

Page({
  data: {
    customRoom: '',
    connected: false,
    manualActive: '',
  },

  onLoad() {
    this.unsubscribe = app.subscribe((state) => {
      this.setData({ connected: state.connected });
      if (!state.connected && this.data.manualActive) {
        this.stopManualControl();
      }
    });
  },

  onHide() {
    this.stopManualControl();
  },

  onUnload() {
    this.stopManualControl();
    if (this.unsubscribe) {
      this.unsubscribe();
    }
  },

  inputRoom(e) {
    const room = e.detail.value.replace(/\s/g, '').slice(0, 32);
    this.setData({ customRoom: room });
    app.globalData.currentRoom = room;
  },

  reconnect() {
    app.reconnect();
    wx.showToast({ title: '正在连接小车', icon: 'none' });
  },

  startNavigate() {
    const room = this.data.customRoom.trim();
    if (!room) {
      wx.showToast({ title: '请输入教室号', icon: 'none' });
      return;
    }
    if (!this.data.connected) {
      wx.showToast({ title: '请先连接小车', icon: 'none' });
      return;
    }
    app.sendCommand(room);
    wx.navigateTo({ url: '/pages/status/status' });
  },

  startFaceRecognition() {
    if (!this.data.connected) {
      wx.showToast({ title: '请先连接小车', icon: 'none' });
      return;
    }
    this.stopManualControl();
    app.sendFaceMode('start');
    wx.navigateTo({ url: '/pages/status/status?source=face' });
  },

  startManualControl(e) {
    if (!this.data.connected) {
      wx.showToast({ title: '请先连接小车', icon: 'none' });
      return;
    }

    const action = e.currentTarget.dataset.action;
    const commands = {
      forward: { vx: 0.2, vy: 0, wz: 0 },
      backward: { vx: -0.2, vy: 0, wz: 0 },
      shiftLeft: { vx: 0, vy: 0.2, wz: 0 },
      shiftRight: { vx: 0, vy: -0.2, wz: 0 },
      turnLeft: { vx: 0, vy: 0, wz: 0.6 },
      turnRight: { vx: 0, vy: 0, wz: -0.6 },
    };
    const command = commands[action];
    if (!command) {
      return;
    }

    this.stopManualControl();
    this.setData({ manualActive: action });
    this.manualCommand = command;
    if (app.globalData.faceMode) {
      app.sendFaceMode('stop');
    }
    app.sendMessage({ type: 'cancel' });
    this.sendManualCommand();
    this.manualTimer = setInterval(() => {
      if (!app.globalData.connected) {
        this.stopManualControl();
        return;
      }
      this.sendManualCommand();
    }, 100);
  },

  sendManualCommand() {
    if (this.manualCommand) {
      app.sendJoystick(
        this.manualCommand.vx,
        this.manualCommand.vy,
        this.manualCommand.wz,
      );
    }
  },

  stopManualControl() {
    if (this.manualTimer) {
      clearInterval(this.manualTimer);
      this.manualTimer = null;
    }
    if (this.manualCommand && app.globalData.connected) {
      app.sendJoystick(0, 0, 0);
    }
    this.manualCommand = null;
    if (this.data.manualActive) {
      this.setData({ manualActive: '' });
    }
  },

  emergencyStop() {
    this.stopManualControl();
    if (app.globalData.connected) {
      app.sendJoystick(0, 0, 0);
    }
  },
});

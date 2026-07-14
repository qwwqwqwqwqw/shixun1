// 状态页逻辑 — 由 TCP Socket 消息事件实时驱动
const app = getApp();

Page({
  data: {
    targetRoom: '',
    status: '等待指令...',
    statusClass: 'running',
    connected: false,
    positionText: '暂无位置数据',
    arrivalConfirmed: false,
    faceMode: false,
    faceStatus: '',
    recognizedName: '',
  },

  onLoad() {
    this.unsubscribe = app.subscribe((state) => {
      const status = state.navStatus || '等待指令...';
      this.setData({
        targetRoom: state.currentRoom,
        status,
        statusClass: this.getStatusClass(status),
        connected: state.connected,
        positionText: this.formatPose(state.robotPose),
        arrivalConfirmed: state.arrivalConfirmed,
        faceMode: state.faceMode,
        faceStatus: state.faceStatus,
        recognizedName: state.recognizedName,
      });
    });
  },

  onUnload() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
  },

  getStatusClass(status) {
    if (/失败|超时|取消|failed|timeout/i.test(status)) {
      return 'failed';
    }
    if (/到达|arrived/i.test(status)) {
      return 'arrived';
    }
    return 'running';
  },

  formatPose(pose) {
    if (!pose) {
      return '暂无位置数据';
    }
    if (pose.text) {
      return pose.text;
    }
    if (pose.x !== undefined && pose.y !== undefined) {
      const x = Number(pose.x).toFixed(2);
      const y = Number(pose.y).toFixed(2);
      return `x: ${x} m，y: ${y} m`;
    }
    return '位置数据格式未知';
  },

  cancelNavigation() {
    const recognizing = this.data.faceMode;
    wx.showModal({
      title: recognizing ? '停止识别' : '取消导航',
      content: recognizing
        ? '确定要停止本次人脸识别吗？'
        : '确定要停止当前导航任务吗？',
      confirmColor: '#e64340',
      success: (result) => {
        if (result.confirm) {
          app.sendFaceMode('stop');
          if (!recognizing) {
            app.cancelNavigation();
          }
        }
      },
    });
  },

  reconnect() {
    app.reconnect();
    wx.showToast({ title: '正在重新连接', icon: 'none' });
  },
});

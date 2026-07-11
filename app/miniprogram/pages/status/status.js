// 状态页逻辑
const app = getApp();

Page({
  data: {
    targetRoom: '',
    status: '等待指令...',
    arrivalConfirmed: false,
  },

  onShow() {
    this.setData({ targetRoom: app.globalData.currentRoom });
    // TODO: 通过 WebSocket 实时更新状态
    this.timer = setInterval(() => {
      this.setData({ status: app.globalData.navStatus || '导航中...' });
    }, 1000);
  },

  onUnload() {
    clearInterval(this.timer);
  },
});

// 首页逻辑 — 教室列表 + 人脸识别触发
const app = getApp();

Page({
  data: {
    rooms: ['101', '102', '103', '104', '105'],
    selectedRoom: '',
  },

  selectRoom(e) {
    const room = e.currentTarget.dataset.room;
    this.setData({ selectedRoom: room });
    app.globalData.currentRoom = room;
  },

  startNavigate() {
    if (!this.data.selectedRoom) {
      wx.showToast({ title: '请先选择教室', icon: 'none' });
      return;
    }
    app.sendCommand(this.data.selectedRoom);
    wx.navigateTo({ url: '/pages/status/status' });
  },

  startFaceRecognition() {
    // 触发人脸识别模式 — 调用摄像头拍照并上传
    wx.chooseImage({
      count: 1,
      sourceType: ['camera'],
      success: (res) => {
        const tempPath = res.tempFilePaths[0];
        wx.uploadFile({
          url: app.globalData.serverUrl.replace('ws', 'http') + '/face',
          filePath: tempPath,
          name: 'image',
          success: (uploadRes) => {
            wx.navigateTo({ url: '/pages/status/status' });
          },
          fail: () => {
            wx.showToast({ title: '上传失败', icon: 'none' });
          }
        });
      }
    });
  },
});

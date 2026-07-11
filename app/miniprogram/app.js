// app.js — WebSocket 连接和全局导航状态
App({
  globalData: {
    // 部署前改成小车实际 IP；开发者工具中需关闭“校验合法域名”。
    serverUrl: 'ws://192.168.1.100:9090',
    currentRoom: '',
    navStatus: '等待导航指令',
    robotPose: null,
    arrivalConfirmed: false,
    connected: false,
    ws: null,
  },

  _listeners: [],
  _pendingMessages: [],
  _reconnectTimer: null,
  _manualClose: false,

  onLaunch() {
    this.connectWebSocket();
  },

  onHide() {
    // 小程序进入后台时保持连接，便于继续接收导航状态。
  },

  connectWebSocket() {
    if (this.globalData.ws) {
      return;
    }

    this._manualClose = false;
    const ws = wx.connectSocket({ url: this.globalData.serverUrl });
    this.globalData.ws = ws;

    ws.onOpen(() => {
      this.globalData.connected = true;
      this._notify();
      this._flushPendingMessages();
      this.sendMessage({ type: 'status' });
    });

    ws.onMessage((res) => {
      let data;
      try {
        data = JSON.parse(res.data);
      } catch (error) {
        console.warn('收到无法解析的服务端消息', res.data);
        return;
      }

      this._handleServerMessage(data);
    });

    ws.onError((error) => {
      console.warn('WebSocket 连接错误', error);
    });

    ws.onClose(() => {
      this.globalData.ws = null;
      this.globalData.connected = false;
      this._notify();
      if (!this._manualClose) {
        this._scheduleReconnect();
      }
    });
  },

  _handleServerMessage(data) {
    if (data.type === 'nav_status') {
      this.globalData.navStatus = data.message || '状态未知';
      if (data.room) {
        this.globalData.currentRoom = data.room;
      }
    } else if (data.type === 'arrival_confirmed') {
      this.globalData.arrivalConfirmed = Boolean(data.confirmed);
    } else if (data.type === 'robot_pose') {
      this.globalData.robotPose = data.data || null;
    } else if (data.type === 'error') {
      wx.showToast({ title: data.message || '服务端错误', icon: 'none' });
    }
    this._notify(data);
  },

  _scheduleReconnect() {
    if (this._reconnectTimer) {
      return;
    }
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connectWebSocket();
    }, 3000);
  },

  reconnect() {
    if (this.globalData.connected) {
      return;
    }
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this.connectWebSocket();
  },

  sendMessage(payload) {
    if (!this.globalData.connected || !this.globalData.ws) {
      this._pendingMessages.push(payload);
      this.reconnect();
      return false;
    }
    this.globalData.ws.send({
      data: JSON.stringify(payload),
      fail: () => {
        this._pendingMessages.unshift(payload);
      },
    });
    return true;
  },

  _flushPendingMessages() {
    const messages = this._pendingMessages.splice(0);
    messages.forEach((message) => this.sendMessage(message));
  },

  sendCommand(room) {
    const normalizedRoom = String(room || '').trim();
    if (!normalizedRoom) {
      return false;
    }
    this.globalData.currentRoom = normalizedRoom;
    this.globalData.navStatus = this.globalData.connected
      ? '指令已发送，等待小车响应'
      : '正在连接小车，指令将在连接后发送';
    this.globalData.arrivalConfirmed = false;
    this.sendMessage({ type: 'command_room', data: normalizedRoom });
    this._notify();
    return true;
  },

  cancelNavigation() {
    this.globalData.navStatus = '正在取消导航';
    this.sendMessage({ type: 'cancel' });
    this._notify();
  },

  subscribe(listener) {
    if (typeof listener !== 'function') {
      return () => {};
    }
    this._listeners.push(listener);
    listener(this.getState());
    return () => {
      this._listeners = this._listeners.filter((item) => item !== listener);
    };
  },

  getState() {
    return {
      connected: this.globalData.connected,
      currentRoom: this.globalData.currentRoom,
      navStatus: this.globalData.navStatus,
      robotPose: this.globalData.robotPose,
      arrivalConfirmed: this.globalData.arrivalConfirmed,
    };
  },

  _notify(message) {
    const state = this.getState();
    this._listeners.slice().forEach((listener) => listener(state, message));
  },
});

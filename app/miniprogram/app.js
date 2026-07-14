// app.js — TCP Socket 连接和全局导航状态
App({
  globalData: {
    // 部署前改成小车实际 IPv4 地址，不能包含 ws:// 或 http://。
    serverHost: '10.143.0.188',
    serverPort: 9090,
    currentRoom: '',
    navStatus: '等待导航指令',
    robotPose: null,
    arrivalConfirmed: false,
    faceMode: false,
    faceStatus: '',
    recognizedName: '',
    connected: false,
    tcp: null,
  },

  _listeners: [],
  _pendingMessages: [],
  _reconnectTimer: null,
  _connecting: false,
  _receiveBuffer: '',
  _textDecoder: null,

  onLaunch() {
    if (typeof TextDecoder !== 'undefined') {
      this._textDecoder = new TextDecoder('utf-8');
    }
    this.connectTcp();
  },

  onHide() {
    // 小程序进入后台时保持连接，便于继续接收导航状态。
  },

  connectTcp() {
    if (this.globalData.tcp || this._connecting) {
      return;
    }
    if (typeof wx.createTCPSocket !== 'function') {
      wx.showToast({ title: '当前基础库不支持 TCP Socket', icon: 'none' });
      return;
    }

    this._connecting = true;
    const tcp = wx.createTCPSocket({ type: 'ipv4' });
    this.globalData.tcp = tcp;

    tcp.onConnect(() => {
      this._connecting = false;
      this.globalData.connected = true;
      this._receiveBuffer = '';
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer);
        this._reconnectTimer = null;
      }
      this._notify();
      this._flushPendingMessages();
      this.sendMessage({ type: 'ping' });
    });

    tcp.onMessage((res) => {
      this._receiveBuffer += this._decodeTcpData(res.message);
      this._consumeTcpMessages();
    });

    tcp.onError((error) => {
      console.warn('TCP Socket 连接错误', error);
      this._handleTcpDisconnected(tcp);
      try {
        tcp.close();
      } catch (closeError) {
        console.warn('关闭 TCP Socket 失败', closeError);
      }
    });

    tcp.onClose(() => {
      this._handleTcpDisconnected(tcp);
    });

    tcp.connect({
      address: this.globalData.serverHost,
      port: this.globalData.serverPort,
      timeout: 5,
    });
  },

  _decodeTcpData(arrayBuffer) {
    if (this._textDecoder) {
      return this._textDecoder.decode(arrayBuffer, { stream: true });
    }
    const bytes = new Uint8Array(arrayBuffer);
    let binary = '';
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    try {
      return decodeURIComponent(escape(binary));
    } catch (error) {
      return binary;
    }
  },

  _consumeTcpMessages() {
    const lines = this._receiveBuffer.split('\n');
    this._receiveBuffer = lines.pop();
    lines.forEach((line) => {
      const text = line.trim();
      if (!text) {
        return;
      }
      try {
        this._handleServerMessage(JSON.parse(text));
      } catch (error) {
        console.warn('收到无法解析的 TCP 消息', text);
      }
    });
  },

  _handleTcpDisconnected(tcp) {
    if (this.globalData.tcp !== tcp) {
      return;
    }
    this.globalData.tcp = null;
    this.globalData.connected = false;
    this.globalData.faceMode = false;
    this._connecting = false;
    this._notify();
    this._scheduleReconnect();
  },

  _handleServerMessage(data) {
    if (data.type === 'nav_status') {
      this.globalData.navStatus = data.message || '状态未知';
      if (data.room) {
        this.globalData.currentRoom = data.room;
      }
    } else if (data.type === 'arrival') {
      this.globalData.arrivalConfirmed = Boolean(data.message);
    } else if (data.type === 'robot_pose') {
      this.globalData.robotPose = data.data || null;
    } else if (data.type === 'face_status') {
      this.globalData.faceStatus = data.message || '人脸识别状态未知';
      if (data.name) {
        this.globalData.recognizedName = data.name;
      }
      if (data.room) {
        this.globalData.currentRoom = data.room;
      }
      this.globalData.faceMode = ![
        'ready', 'recognized', 'stopped', 'timeout', 'error',
      ].includes(data.status);
    } else if (data.type === 'error') {
      if (/人脸/.test(data.message || '')) {
        this.globalData.faceMode = false;
        this.globalData.faceStatus = data.message;
      }
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
      this.connectTcp();
    }, 20000);
  },

  reconnect() {
    if (this.globalData.connected) {
      return;
    }
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this.connectTcp();
  },

  sendMessage(payload, queueIfOffline = true) {
    if (!this.globalData.connected || !this.globalData.tcp) {
      if (queueIfOffline) {
        this._pendingMessages.push(payload);
      }
      this.reconnect();
      return false;
    }
    try {
      // TCP 没有消息边界，服务端约定每条 JSON 以换行符结束。
      this.globalData.tcp.write(`${JSON.stringify(payload)}\n`);
      return true;
    } catch (error) {
      if (queueIfOffline) {
        this._pendingMessages.unshift(payload);
      }
      console.warn('TCP 指令发送失败', error);
      return false;
    }
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
    if (this.globalData.faceMode) {
      this.sendMessage({ type: 'face_mode', action: 'stop' });
    }
    this.globalData.faceMode = false;
    this.globalData.faceStatus = '';
    this.globalData.recognizedName = '';
    this.globalData.currentRoom = normalizedRoom;
    this.globalData.navStatus = this.globalData.connected
      ? '指令已发送，等待小车响应'
      : '正在连接小车，指令将在连接后发送';
    this.globalData.arrivalConfirmed = false;
    this.sendMessage({ type: 'navigate', room: normalizedRoom });
    this._notify();
    return true;
  },

  cancelNavigation() {
    this.globalData.navStatus = '正在取消导航';
    this.sendMessage({ type: 'cancel' });
    this._notify();
  },

  sendJoystick(vx = 0, vy = 0, wz = 0) {
    return this.sendMessage({
      type: 'joystick',
      vx,
      vy,
      wz,
    }, false);
  },

  sendFaceMode(action) {
    if (action === 'start') {
      this.globalData.faceMode = true;
      this.globalData.faceStatus = '正在启动人脸识别';
      this.globalData.recognizedName = '';
      this.globalData.currentRoom = '';
      this.globalData.arrivalConfirmed = false;
      this.globalData.navStatus = '等待人脸识别结果';
    } else {
      this.globalData.faceMode = false;
      this.globalData.faceStatus = '人脸识别已停止';
    }
    const sent = this.sendMessage({ type: 'face_mode', action });
    this._notify();
    return sent;
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
      faceMode: this.globalData.faceMode,
      faceStatus: this.globalData.faceStatus,
      recognizedName: this.globalData.recognizedName,
    };
  },

  _notify(message) {
    const state = this.getState();
    this._listeners.slice().forEach((listener) => listener(state, message));
  },
});

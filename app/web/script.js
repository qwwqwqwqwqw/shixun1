// Web 控制台 — 通过 WebSocket 连接 aiserver_node
const WS_URL = 'ws://localhost:9090';
let ws = null;

function connect() {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => { document.getElementById('statusDisplay').textContent = '已连接服务器'; };
  ws.onmessage = (event) => { document.getElementById('statusDisplay').textContent = event.data; };
  ws.onclose = () => { document.getElementById('statusDisplay').textContent = '连接断开，3秒后重连...'; setTimeout(connect, 3000); };
}

function sendRoom() {
  const room = document.getElementById('roomInput').value.trim();
  if (room && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'command_room', data: room }));
  }
}

function startFace() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'start_face' }));
  }
}

window.onload = connect;

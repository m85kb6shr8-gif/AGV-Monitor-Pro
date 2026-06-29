/**
 * Popup Script
 * Displays AGV status in the extension popup
 */

document.addEventListener('DOMContentLoaded', init);

const agvListEl = document.getElementById('agv-list');
const connectionStatusEl = document.getElementById('connection-status');
const alarmSwitchEl = document.getElementById('alarm-switch');
const settingsBtnEl = document.getElementById('settings-btn');
const logsBtnEl = document.getElementById('logs-btn');
const helpBtnEl = document.getElementById('help-btn');
const settingsModalEl = document.getElementById('settings-modal');
const alarmModalEl = document.getElementById('alarm-modal');
const closeModalEl = document.querySelector('.close');
const saveSettingsBtnEl = document.getElementById('save-settings');
const acknowledgeBtn = document.getElementById('acknowledge-btn');

let updateInterval;
let currentAlarm = null;

function init() {
    updateStatus();
    updateInterval = setInterval(updateStatus, 1000);
    
    alarmSwitchEl.addEventListener('change', (e) => {
        chrome.runtime.sendMessage({
            type: 'set_alarm',
            enabled: e.target.checked
        });
    });
    
    settingsBtnEl.addEventListener('click', showSettings);
    logsBtnEl.addEventListener('click', showLogs);
    helpBtnEl.addEventListener('click', showHelp);
    closeModalEl.addEventListener('click', closeSettingsModal);
    saveSettingsBtnEl.addEventListener('click', saveSettings);
    acknowledgeBtn.addEventListener('click', acknowledgeAlarm);
    
    window.addEventListener('beforeunload', () => {
        clearInterval(updateInterval);
    });
}

function updateStatus() {
    chrome.runtime.sendMessage({ type: 'get_status' }, (response) => {
        if (!response) return;
        
        const connected = response.connected;
        connectionStatusEl.textContent = connected ? '🟢 已连接' : '⚫ 未连接';
        connectionStatusEl.className = connected ? 'status-connected' : 'status-disconnected';
        
        alarmSwitchEl.checked = response.alarmEnabled;
        
        renderAGVList(response.agvs);
    });
}

function renderAGVList(agvs) {
    if (!agvs || Object.keys(agvs).length === 0) {
        agvListEl.innerHTML = '<p class="loading">等待数据...</p>';
        return;
    }
    
    agvListEl.innerHTML = '';
    
    Object.keys(agvs)
        .map(Number)
        .sort((a, b) => a - b)
        .forEach(agvId => {
            const agv = agvs[agvId];
            const agvEl = createAGVElement(agvId, agv);
            agvListEl.appendChild(agvEl);
        });
}

function createAGVElement(agvId, agv) {
    const div = document.createElement('div');
    div.className = 'agv-item';
    
    if (agv.is_alarming) {
        div.classList.add('alarming');
        if (agv.alarm_type === 'MANUAL') div.classList.add('manual');
        else if (agv.alarm_type === 'ERROR') div.classList.add('error');
        else if (agv.alarm_type === 'FAULT') div.classList.add('fault');
    }
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'agv-info';
    
    const nameDiv = document.createElement('div');
    nameDiv.className = 'agv-name';
    nameDiv.textContent = `AGV${agvId}`;
    
    const statusDiv = document.createElement('div');
    statusDiv.className = 'agv-status';
    
    const mode = agv.auto ? 'AUTO' : 'MANUAL';
    const status = agv.is_alarming 
        ? `${agv.alarm_type}${agv.fault_codes && agv.fault_codes.length > 0 ? ': ' + agv.fault_codes.join(', ') : ''}`
        : agv.agv_state;
    
    statusDiv.textContent = `${mode} • ${status}`;
    
    infoDiv.appendChild(nameDiv);
    infoDiv.appendChild(statusDiv);
    
    const toggleDiv = document.createElement('div');
    toggleDiv.className = 'agv-monitor-toggle';
    const toggleInput = document.createElement('input');
    toggleInput.type = 'checkbox';
    toggleInput.checked = agv.monitor_enabled;
    toggleInput.title = '启用/禁用该AGV监控';
    toggleInput.addEventListener('change', (e) => {
        chrome.runtime.sendMessage({
            type: 'toggle_agv_monitor',
            agv_id: agvId,
            enabled: e.target.checked
        });
    });
    toggleDiv.appendChild(toggleInput);
    
    div.appendChild(infoDiv);
    div.appendChild(toggleDiv);
    
    return div;
}

function showSettings() {
    chrome.storage.local.get(['wsUrl', 'broker', 'port'], (result) => {
        document.getElementById('ws-input').value = result.wsUrl || 'ws://localhost:9000';
        document.getElementById('broker-input').value = result.broker || 'localhost';
        document.getElementById('port-input').value = result.port || '1883';
    });
    settingsModalEl.classList.remove('hidden');
}

function closeSettingsModal() {
    settingsModalEl.classList.add('hidden');
}

function saveSettings() {
    const wsUrl = document.getElementById('ws-input').value;
    const broker = document.getElementById('broker-input').value;
    const port = document.getElementById('port-input').value;
    
    chrome.storage.local.set({ wsUrl, broker, port });
    chrome.runtime.sendMessage({
        type: 'save_settings',
        wsUrl: wsUrl
    });
    
    closeSettingsModal();
}

function showAlarmPopup(alarmData) {
    currentAlarm = alarmData;
    
    document.getElementById('alarm-title').textContent = `⚠️ AGV${alarmData.agv_id} 告警`;
    document.getElementById('alarm-message').textContent = alarmData.message;
    document.getElementById('alarm-type').textContent = `类型: ${alarmData.alarm_type}`;
    document.getElementById('alarm-time').textContent = `时间: ${new Date().toLocaleTimeString()}`;
    
    alarmModalEl.classList.remove('hidden');
}

function acknowledgeAlarm() {
    alarmModalEl.classList.add('hidden');
    currentAlarm = null;
}

function showLogs() {
    alert('日志功能敬请期待 👀');
}

function showHelp() {
    alert(
        'AGV Monitor Pro V0.2 - Chrome 插件\n\n' +
        '功能：\n' +
        '• 实时监控AGV状态\n' +
        '• 自动报警提示（MANUAL/ERROR/FAULT）\n' +
        '• 系统声音+弹窗通知\n' +
        '• 必须确认才能关闭\n' +
        '• 单个或全局告警控制\n\n' +
        '使用：\n' +
        '1. 确保Python后端服务运行\n' +
        '2. 点击插件图标查看状态\n' +
        '3. 设置中配置MQTT和WebSocket\n\n' +
        '更多信息：https://github.com/m85kb6shr8-gif/AGV-Monitor-Pro'
    );
}

// 监听来自 background 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'status_update' || message.type === 'connected' || message.type === 'disconnected') {
        updateStatus();
    } else if (message.type === 'alarm') {
        showAlarmPopup(message);
    }
});

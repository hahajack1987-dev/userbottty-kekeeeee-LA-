const API_BASE = '';

async function fetchJSON(url, options = {}) {
    const res = await fetch(url, options);
    return res.json();
}

async function saveConfig() {
    const chatIds = document.getElementById('chatIds').value;
    const messages = document.getElementById('messages').value;
    const delaySec = parseFloat(document.getElementById('delaySec').value);
    const loop = document.getElementById('loop').checked;

    const payload = { chatIds, messages, delaySec, loop };
    const data = await fetchJSON(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    console.log('Config saved:', data);
    alert('Konfigürasyon kaydedildi!');
    updateStatus();
}

async function startSpam() {
    const data = await fetchJSON(`${API_BASE}/start`);
    if (data.error) alert(data.error);
    else alert('Spam başlatıldı');
    updateStatus();
}

async function stopSpam() {
    await fetchJSON(`${API_BASE}/stop`);
    alert('Spam durduruldu');
    updateStatus();
}

async function updateStatus() {
    const statusDiv = document.getElementById('status');
    try {
        const data = await fetchJSON(`${API_BASE}/status`);
        statusDiv.innerHTML = `
            🟢 Çalışıyor: ${data.running ? 'Evet' : 'Hayır'}<br>
            📡 Chat sayısı: ${data.chatIds.length}<br>
            💬 Mesaj sayısı: ${data.messages.length}<br>
            ⏱ Gecikme: ${data.delaySec} sn<br>
            🔁 Döngü: ${data.loop ? 'Açık' : 'Kapalı'}<br>
            📍 Sıra: Chat ${data.currentChatIndex+1}/${data.chatIds.length}, Mesaj ${data.currentMsgIndex+1}/${data.messages.length}
        `;
    } catch(e) {
        statusDiv.innerHTML = '❌ Sunucuya bağlanılamadı';
    }
}

async function loadLogs() {
    const logDiv = document.getElementById('logArea');
    try {
        const data = await fetchJSON(`${API_BASE}/logs`);
        if (!data.logs) return;
        logDiv.innerHTML = data.logs.map(log => {
            let cls = '';
            if (log.type === 'error') cls = 'error';
            else if (log.type === 'sent') cls = 'sent';
            else cls = 'info';
            let text = `[${new Date(log.timestamp).toLocaleTimeString()}] ${log.type.toUpperCase()}`;
            if (log.chat_id) text += ` | Chat: ${log.chat_id}`;
            if (log.message) text += ` | Msg: ${log.message.substring(0, 80)}`;
            if (log.error) text += ` | HATA: ${log.error}`;
            return `<div class="${cls}">${text}</div>`;
        }).join('');
        logDiv.scrollTop = 0;
    } catch(e) {
        logDiv.innerHTML = '<div class="error">Loglar alınamıyor.</div>';
    }
}

document.getElementById('saveBtn').addEventListener('click', saveConfig);
document.getElementById('startBtn').addEventListener('click', startSpam);
document.getElementById('stopBtn').addEventListener('click', stopSpam);

setInterval(() => {
    updateStatus();
    loadLogs();
}, 2000);

updateStatus();
loadLogs();

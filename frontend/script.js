// /frontend/script.js
const chatWindow = document.getElementById('chat-window');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');

// URL dari API backend FastAPI kita
const API_URL = 'http://127.0.0.1:8000/chat';

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function sendMessage() {
    const message = messageInput.value.trim();
    if (message === '') return;

    // Tampilkan pesan user di UI
    addMessageToUI(message, 'user');
    
    // Kirim pesan ke backend
    fetch(API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        // Tampilkan jawaban bot dan nama agent-nya di UI
        addMessageToUI(data.response, 'bot', data.source_agent);
    })
    .catch(error => {
        console.error('Error:', error);
        addMessageToUI('Maaf, terjadi kesalahan koneksi ke server.', 'bot');
    });

    messageInput.value = '';
}

function addMessageToUI(message, sender, sourceAgent = null) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', `${sender}-message`);

    // Jika ada source agent (hanya untuk bot), tambahkan elemen nama agent
    if (sourceAgent) {
        const agentNameElement = document.createElement('p');
        agentNameElement.classList.add('agent-name');
        agentNameElement.textContent = sourceAgent;
        messageElement.appendChild(agentNameElement);
    }

    const p = document.createElement('p');
    p.textContent = message;
    messageElement.appendChild(p);

    chatWindow.appendChild(messageElement);
    // Auto-scroll ke pesan terbaru
    chatWindow.scrollTop = chatWindow.scrollHeight;
}
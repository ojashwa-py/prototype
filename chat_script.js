document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    // Generate or retrieve session ID
    let userId = localStorage.getItem('chat_user_id');
    if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chat_user_id', userId);
    }

    // Bot Response Logic (Connected to Backend)
    const handleBotResponse = (userMsg) => {
        // Use relative URL for deployment compatibility
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: userMsg,
                user_id: userId
            }),
        })
            .then(response => response.json())
            .then(data => {
                setTimeout(() => {
                    if (typeof data.response === 'object') {
                        // It's the new structured format {text: "...", options: [...]}
                        appendMessage('bot', data.response.text);
                        if (data.response.options && data.response.options.length > 0) {
                            appendOptions(data.response.options);
                        }
                    } else {
                        // Fallback for plain string
                        appendMessage('bot', data.response);
                    }
                    scrollToBottom();
                }, 500);
            })
            .catch(error => {
                console.error('Error:', error);
                appendMessage('bot', "Sorry, I'm having trouble connecting to the server.");
            });
    };

    // Append Message to UI
    window.appendMessage = (sender, text) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const formattedText = text.replace(/\n/g, '<br>');

        msgDiv.innerHTML = `
            <div class="bubble">${formattedText}</div>
            <span class="timestamp">${time}</span>
        `;

        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    };

    // Append Options (Buttons)
    window.appendOptions = (options) => {
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'options-container';

        options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerText = opt;
            btn.onclick = () => window.sendQuickReply(opt);
            optionsDiv.appendChild(btn);
        });

        chatMessages.appendChild(optionsDiv);
        scrollToBottom();
    };

    // Scroll to bottom helper
    const scrollToBottom = () => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    // Send Message Handler
    const sendMessage = () => {
        const text = userInput.value.trim();
        if (text === "") return;

        appendMessage('user', text);
        userInput.value = "";

        // Trigger bot response
        handleBotResponse(text);
    };

    // Quick Reply Handler (Global)
    window.sendQuickReply = (text) => {
        appendMessage('user', text);
        handleBotResponse(text);
    };

    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Initial scroll
    scrollToBottom();
});

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
        // Show typing indicator or just wait (optional)

        // Use absolute URL to allow file:// access if server is running
        fetch('http://127.0.0.1:5000/chat', {
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
                    appendMessage('bot', data.response);
                    scrollToBottom();
                }, 500); // Small delay for natural feel
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

        // Convert newlines to <br> for bot messages
        const formattedText = text.replace(/\n/g, '<br>');

        msgDiv.innerHTML = `
            <div class="bubble">${formattedText}</div>
            <span class="timestamp">${time}</span>
        `;

        chatMessages.appendChild(msgDiv);
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

    // Quick Reply Handler (Global window object for onclick in HTML)
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

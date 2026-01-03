document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatWidget = document.getElementById('chat-widget');

    // Force Open for Static View
    chatWidget.classList.add('open');

    // Generate or retrieve session ID
    let userId = localStorage.getItem('chat_user_id');
    if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chat_user_id', userId);
    }

    // --- LOCAL BOT ENGINE (Offline Fallback) ---
    const LocalBot = {
        state: "IDLE",
        cart: [],
        userInfo: {},
        fallbackCount: 0,

        // Constants (Mirrored from Python)
        WELCOME_MESSAGE: {
            text: "Welcome to PosterMan! 🎨\nI'm PosterBot, your personal art curator.\nLooking for some museum-grade art for your walls today? (Offline Mode)",
            options: ["🛒 Place an order", "📦 Track Order", "✨ Custom Print", "🦸 Anime Collection"]
        },
        POLICIES_MESSAGE: {
            text: "📜 **PosterMan Policies**\n\n• **Shipping**: Free Shipping over ₹999. Dispatched within 24-48 hours.\n• **Returns**: We offer Free Replacements for damage during transit (video proof required).\n• **Refunds**: Issued only after verification.\n• **Note**: Custom orders cannot be cancelled once confirmed.",
            options: ["🔙 Main Menu"]
        },

        // Helper: Mock Order Status
        getOrderStatus: (id) => {
            if (id === "1234") return { text: `Order #1234: Shipped 🚀\nExpected Delivery: Tomorrow`, options: ["🔙 Main Menu"] };
            return { text: `Order #${id}: Processing ⚙️`, options: ["🔙 Main Menu"] };
        },

        // Core Logic
        handleMessage: function (msg) {
            const lowerMsg = msg.toLowerCase().trim();

            // 1. Global Resets
            if (["hi", "hello", "hey", "menu", "start", "restart", "main menu", "🔙 main menu"].includes(lowerMsg)) {
                this.state = "IDLE";
                this.fallbackCount = 0;
                return this.WELCOME_MESSAGE;
            }

            // 2. IDLE State Rules
            if (this.state === "IDLE") {
                // Rule #1: Tracking
                if (lowerMsg.match(/track|status|where is my order/)) {
                    this.state = "CHECK_STATUS";
                    return { text: "Sure! Please enter your **Order ID** (e.g., 1234) to check status.", options: ["🔙 Main Menu"] };
                }

                // Rule #2: Products
                if (lowerMsg.match(/anime|marvel|cars|gift|collection/)) {
                    let cat = "all";
                    if (lowerMsg.includes("anime")) cat = "anime";
                    else if (lowerMsg.includes("marvel")) cat = "marvel";
                    else if (lowerMsg.includes("cars")) cat = "cars";

                    return {
                        text: `Welcome to the Otaku Zone! Check out our ${cat} collection.\n🔥 **Admin Tip**: Buy 2 Get 10% Off!\n\n<a href="/products.html?cat=${cat}" target="_blank" style="color:white;text-decoration:underline;">View Collection</a>`,
                        options: ["🛒 Place an order", "✨ Custom Print"]
                    };
                }

                // Rule #3: Custom
                if (lowerMsg.match(/custom|personal|my own photo|print|image uploaded/)) {
                    if (lowerMsg.includes("image uploaded")) {
                        this.state = "CUSTOM_ASK_QTY";
                        return { text: "Wow, great shot! 📸 I've received your image. How many copies do you need?", options: ["1", "2", "3", "5"] };
                    }
                    return {
                        text: "Finding your masterpiece? We use **240gsm premium paper** for custom prints! 🖼️\n\nUpload your art by clicking the 📎 icon below.",
                        options: ["🔙 Main Menu"]
                    };
                }

                // Rule #4: Policies
                if (lowerMsg.match(/return|broken|refund|shipping|policy/)) return this.POLICIES_MESSAGE;

                // Cart
                if (lowerMsg.match(/checkout|buy|cart/)) return { text: "Ready to own your art? 🛒\n\n<a href='#' style='color:gold;font-weight:bold;'>Proceed to Checkout</a>", options: ["🔙 Main Menu"] };

                // Place Order flow initiator
                if (lowerMsg.includes("place an order")) {
                    this.state = "ASK_ORDER_CATEGORY";
                    return { text: "What would you like to order?", options: ["Website Product", "Custom Product"] };
                }
            }

            // 3. State Machine flows
            if (this.state === "CHECK_STATUS") {
                this.state = "IDLE";
                return this.getOrderStatus(msg.replace("#", ""));
            }

            if (this.state === "ASK_ORDER_CATEGORY") {
                if (lowerMsg.includes("website")) {
                    this.state = "WEBSITE_SELECT_PRODUCT";
                    return { text: "Select a product from our catalog:", options: ["Poster A", "Poster B", "Poster C", "🔙 Main Menu"] };
                } else if (lowerMsg.includes("custom")) {
                    this.state = "CUSTOM_UPLOAD_DETAILS";
                    return { text: "For custom products, please describe or upload an image.", options: ["I have uploaded details", "🔙 Main Menu"] };
                }
            }

            if (this.state === "WEBSITE_SELECT_PRODUCT") {
                if (lowerMsg.includes("main menu")) { this.state = "IDLE"; return this.WELCOME_MESSAGE; }
                this.state = "WEBSITE_ASK_QTY";
                return { text: `Selected '${msg}'. Quantity?`, options: ["1", "2", "3"] };
            }

            if (this.state === "CUSTOM_UPLOAD_DETAILS") {
                this.state = "CUSTOM_ASK_QTY";
                return { text: "Got it. Quantity?", options: ["1", "2", "3"] };
            }

            if (this.state === "WEBSITE_ASK_QTY" || this.state === "CUSTOM_ASK_QTY") {
                this.state = "ASK_ADD_MORE";
                return { text: "Added to cart 🛒. Add another product?", options: ["Yes", "No, Checkout"] };
            }

            if (this.state === "ASK_ADD_MORE") {
                if (lowerMsg.includes("yes")) {
                    this.state = "ASK_ORDER_CATEGORY";
                    return { text: "Category?", options: ["Website Product", "Custom Product"] };
                } else {
                    this.state = "ASK_NAME";
                    return { text: "Please enter your Full Name:", options: [] };
                }
            }

            if (this.state === "ASK_NAME") {
                this.userInfo.name = msg;
                this.state = "ASK_ADDRESS";
                return { text: "Please enter your Full Address:", options: [] };
            }

            if (this.state === "ASK_ADDRESS") {
                this.userInfo.address = msg;
                this.state = "ASK_PHONE";
                return { text: "Please enter your 10-digit Mobile Number:", options: [] };
            }

            if (this.state === "ASK_PHONE") {
                this.state = "IDLE";
                return {
                    text: `Order Placed Successfully! (Offline Mode) ✅\nOrder #LOCAL-${Math.floor(Math.random() * 1000)}\nName: ${this.userInfo.name}\n\nWe will contact you shortly to confirm details.`,
                    options: ["Check Order Status", "Place another order"]
                };
            }

            // Fallback
            this.fallbackCount++;
            if (this.fallbackCount >= 3) {
                this.fallbackCount = 0;
                return { text: "I'm having trouble finding that. Would you like to chat with a human expert on WhatsApp?\n\n<a href='https://wa.me/919876543210' target='_blank'>Click to Chat</a>", options: ["Main Menu"] };
            }

            return { text: "I didn't quite catch that. Could you rephrase? 🤔", options: this.WELCOME_MESSAGE.options };
        }
    };

    // Bot Response Logic (Hybrid: Server -> Local Fallback)
    const handleBotResponse = (userMsg) => {
        // Try Backend First
        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userMsg, user_id: userId }),
        })
            .then(response => {
                if (!response.ok) throw new Error("Server Offline");
                return response.json();
            })
            .then(data => {
                setTimeout(() => {
                    const res = data.response;
                    appendMessage('bot', typeof res === 'object' ? res.text : res);
                    if (res.options) appendOptions(res.options);
                }, 500);
            })
            .catch(error => {
                console.log('Server unreachable, using LocalBot engine:', error);
                // Use Local Bot Engine
                setTimeout(() => {
                    const localRes = LocalBot.handleMessage(userMsg);
                    appendMessage('bot', localRes.text);
                    if (localRes.options) appendOptions(localRes.options);
                }, 500);
            });
    };

    // Append Message to UI
    window.appendMessage = (sender, text) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Simple URL to link converter
        let formattedText = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color: white; text-decoration: underline;">$1</a>');
        formattedText = formattedText.replace(/\n/g, '<br>');

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

    // Append Product Card
    window.appendProductCard = (product) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message bot';

        msgDiv.innerHTML = `
            <div class="product-card">
                <img src="${product.image}" alt="${product.title}">
                <div class="product-info">
                    <h4>${product.title}</h4>
                    <p>${product.price}</p>
                </div>
            </div>
            <span class="timestamp">Just now</span>
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

    // Image Upload Logic
    const attachBtn = document.getElementById('attach-btn');
    const imageInput = document.getElementById('image-upload');

    if (attachBtn && imageInput) {
        attachBtn.addEventListener('click', () => imageInput.click());

        imageInput.addEventListener('change', () => {
            const file = imageInput.files[0];
            if (!file) return;

            // Show preview immediately? Or upload then show?
            // Let's upload first
            const formData = new FormData();
            formData.append('file', file);

            // Start Upload UI
            const originalIcon = attachBtn.innerHTML;
            attachBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            attachBtn.disabled = true;
            userInput.placeholder = "Uploading image...";

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.url) {
                        // Send URL as message to bot
                        const msgDiv = document.createElement('div');
                        msgDiv.className = 'message user';
                        msgDiv.innerHTML = `<div class="bubble"><img src="${data.url}" style="max-width: 200px; border-radius: 10px;"></div><span class="timestamp">Just now</span>`;
                        chatMessages.appendChild(msgDiv);
                        scrollToBottom();

                        // Send to backend
                        handleBotResponse(`[Image Uploaded] ${data.url}`);
                    } else {
                        appendMessage('bot', '❌ Upload failed.');
                    }
                })
                .catch(err => {
                    console.error(err);
                    appendMessage('bot', '❌ Upload error.');
                })
                .finally(() => {
                    // Reset UI
                    attachBtn.innerHTML = originalIcon;
                    attachBtn.disabled = false;
                    userInput.placeholder = "Type a message...";
                    imageInput.value = '';
                });
        });
    }

    // Initial scroll
    scrollToBottom();
});

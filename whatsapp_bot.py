import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import re
import json
import os
import threading
import time
import random
from datetime import datetime

# Define Base Directory for robust path finding
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class IDecorBot:
    def __init__(self, sheet_name="PosterMan Orders", creds_file="credentials.json"):
        self.sheet_name = sheet_name
        self.creds_file = os.path.join(BASE_DIR, creds_file)
        self.user_sessions = {}
        self.sheet = None
        self.products = []
        self.load_products()
        self.connect_gsheet()
        
        # Identity & Tone
        self.BOT_NAME = "PosterBot"
        self.WHATSAPP_LINK = "https://wa.me/919876543210" # Placeholder number
        
        self.WELCOME_MESSAGE = {
            "text": (
                "Welcome to PosterMan! 🎨\n"
                "I'm PosterBot, your personal art curator.\n"
                "Looking for some museum-grade art for your walls today?"
            ),
            "options": ["🛒 Place an order", "📦 Track Order", "✨ Custom Print", "🦸 Anime Collection"]
        }
        
        # Responses
        self.FAQ_MESSAGE = {
            "text": "Please note: PosterMan does not offer replacement. Courier damage is not refundable.",
            "options": ["🔙 Main Menu"]
        }

        self.POLICIES_MESSAGE = {
            "text": (
                "📜 **PosterMan Policies**\n\n"
                "• **Shipping**: Free Shipping over ₹999. Dispatched within 24-48 hours.\n"
                "• **Returns**: We offer Free Replacements for damage during transit (video proof required).\n"
                "• **Refunds**: Issued only after verification.\n"
                "• **Note**: Custom orders cannot be cancelled once confirmed."
            ),
            "options": ["🔙 Main Menu"]
        }

        self.PAYMENT_QR_MESSAGE = (
            "Please scan the QR code below to complete payment 💳\n"
            "Our team will verify the payment within 7 hours.\n"
            "You will receive a confirmation message after verification."
        )

    def load_products(self):
        try:
            p_path = os.path.join(BASE_DIR, "products.json")
            if os.path.exists(p_path):
                with open(p_path, "r") as f:
                    self.products = json.load(f)
            else:
                self.products = []
        except Exception as e:
            print(f"Error loading products: {e}")
            self.products = []

    def connect_gsheet(self):
        """Connects to Google Sheets using the service account (File or Env Var)."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = None
            
            # 1. Try Environment Variable (Best for Render/Heroku)
            def clean_key(key):
                key = key.strip().strip('"').strip("'")
                key = key.replace('\\n', '\n')
                key = key.replace('\\\\n', '\n')
                return key

            json_creds = os.environ.get("GOOGLE_CREDENTIALS")
            if json_creds and json_creds.strip():
                try:
                    creds_dict = json.loads(json_creds)
                    if 'private_key' in creds_dict:
                        raw_key = creds_dict['private_key']
                        creds_dict['private_key'] = clean_key(raw_key) 
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                except Exception as e:
                    print(f"[ERROR] Failed to load credentials from Env. Error: {e}")
            
            # 2. Try Local File (Fallback)
            if not creds:
                if os.path.exists(self.creds_file):
                    try:
                        with open(self.creds_file, 'r') as f:
                            file_creds = json.load(f)
                        if 'private_key' in file_creds:
                             file_creds['private_key'] = clean_key(file_creds['private_key'])
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(file_creds, scope)
                    except Exception as e:
                         print(f"[ERROR] Fallback file loading failed: {e}")
                else:
                    return

            client = gspread.authorize(creds)
            try:
                self.sheet = client.open(self.sheet_name).sheet1
                print("[SYSTEM]: Connected to Google Sheet successfully.")
            except gspread.exceptions.SpreadsheetNotFound:
                print(f"[ERROR]: Sheet '{self.sheet_name}' not found.")
            
        except Exception as e:
            print(f"[ERROR]: Could not connect to Google Sheets: {e}")

    def generate_order_id(self):
        return f"ID{random.randint(1000, 9999)}"

    def get_order_status(self, order_id):
        if not self.sheet:
            self.connect_gsheet()
            if not self.sheet: return {"text": "System Error: Database not connected.", "options": ["🔙 Main Menu"]}

        try:
            records = self.sheet.get_all_records()
            for row in records:
                if str(row.get('Order ID', '')) == str(order_id):
                    verified = str(row.get('Payment Verified', '') or row.get('- Payment Verified', '')).strip().lower()
                    if verified == 'yes':
                        return {"text": f"Order #{order_id}: Confirmed ✅", "options": ["🔙 Main Menu"]}
                    else:
                        return {"text": f"Order #{order_id}: Payment Pending ⏳", "options": ["🔙 Main Menu"]}
            return {"text": "Order ID not found.", "options": ["🔙 Main Menu", "Use Check Status Again"]}
        except Exception as e:
            print(f"Error fetching status: {e}")
            pass
        return {"text": "Order ID not found.", "options": ["🔙 Main Menu"]}

    def save_order_batch(self, session_data):
        if not self.sheet:
            self.connect_gsheet()
            if not self.sheet: return False

        try:
            order_id = self.generate_order_id()
            cart = session_data.get('cart', [])
            user_info = session_data.get('user_info', {})
            
            rows_to_add = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for item in cart:
                row = [
                    order_id,
                    user_info.get('name', 'Unknown'),
                    item.get('product_name', 'Unknown'),
                    item.get('type', 'Unknown'),
                    item.get('size', 'NA'),
                    item.get('qty', 1),
                    timestamp,
                    user_info.get('address', 'Unknown'),
                    str(user_info.get('phone', '')),
                    '', 
                    'No',
                    'No'
                ]
                rows_to_add.append(row)
            
            # Using append_rows if available in gspread version, else loop append_row
            try:
                self.sheet.append_rows(rows_to_add)
            except AttributeError:
                for r in rows_to_add:
                    self.sheet.append_row(r)
            
            return order_id
        except Exception as e:
            print(f"Error saving order: {e}")
            return None

    def check_for_notifications(self):
        if not self.sheet: return []
        notifications = []
        try:
            rows = self.sheet.get_all_values()
            if len(rows) < 2: return []
            headers = rows[0]
            
            def find_col(possible_names):
                for name in possible_names:
                    if name in headers: return headers.index(name)
                raise ValueError
            
            try:
                idx_verified = find_col(['Payment Verified', '- Payment Verified'])
                idx_conf_sent = find_col(['Confirmation Sent', '- Confirmation Sent'])
                idx_order_id = find_col(['Order ID', '- Order ID'])
                idx_phone = find_col(['Contact no.', '- Contact no.'])
            except:
                return []

            for i in range(1, len(rows)):
                row_data = rows[i]
                if len(row_data) <= max(idx_verified, idx_conf_sent): continue

                payment_verified = row_data[idx_verified].strip().lower()
                conf_sent = row_data[idx_conf_sent].strip().lower()
                
                if payment_verified == 'yes' and conf_sent != 'yes':
                    order_id = row_data[idx_order_id]
                    phone = row_data[idx_phone]
                    notifications.append((phone, f"Your order #{order_id} is Confirmed! ✅"))
                    self.sheet.update_cell(i + 1, idx_conf_sent + 1, 'Yes')
        except:
            pass
        return notifications

    def get_website_product_options(self):
        # Simply return names from products.json
        return [p['name'] for p in self.products] if self.products else ["Generic Website Product"]

    def handle_message(self, user_phone, message):
        message = message.strip()
        msg_lower = message.lower()

        # Initialize Session
        if user_phone not in self.user_sessions:
            self.user_sessions[user_phone] = {
                "state": "IDLE", 
                "cart": [],
                "user_info": {"phone": user_phone},
                "fallback_count": 0
            }
        
        session = self.user_sessions[user_phone]
        state = session["state"]

        # --- 1. Global Resets ---
        if msg_lower in ["hi", "hello", "hey", "menu", "start", "restart", "main menu", "🔙 main menu"]:
            session["state"] = "IDLE"
            session["fallback_count"] = 0
            return self.WELCOME_MESSAGE

        # --- 2. IDLE State & Keyword Rules ---
        if state == "IDLE":
            # Rule #1: Order Tracking
            if any(w in msg_lower for w in ["track", "order status", "where is my order", "status"]):
                session["state"] = "CHECK_STATUS"
                session["fallback_count"] = 0
                return {"text": "Sure! Please enter your **Order ID** (e.g., #PM-1234) to check status.", "options": ["🔙 Main Menu"]}

            # Rule #2: Product Recommendations
            if any(w in msg_lower for w in ["anime", "marvel", "cars", "gift", "collection"]):
                session["fallback_count"] = 0
                category = "all"
                if "anime" in msg_lower: category = "anime"
                elif "marvel" in msg_lower: category = "marvel"
                elif "cars" in msg_lower: category = "cars"
                
                offer_text = "🔥 **Admin Tip**: Buy 2 Get 10% Off!"
                return {
                    "text": f"Welcome to the Otaku Zone! Check out our {category.capitalize()} collection.\n{offer_text}\n\n[View Collection](/products.html?cat={category})",
                    "options": ["🛒 Place an order", "✨ Custom Print"]
                }

            # Rule #3: Custom Orders
            if any(w in msg_lower for w in ["custom", "personal", "my own photo", "print", "image uploaded"]):
                session["fallback_count"] = 0
                if "[image uploaded]" in msg_lower:
                    # Direct upload from idle, save as detail
                    url = message.split("] ")[1] if "] " in message else message
                    session["current_item"] = {"type": "Custom", "product_name": "Custom Upload", "details": f"Image: {url}"}
                    session["state"] = "CUSTOM_ASK_QTY"
                    return {
                        "text": "Wow, great shot! 📸 I've received your image. How many copies do you need?",
                        "options": ["1", "2", "3", "5"]
                    }

                return {
                    "text": "Finding your masterpiece? We use **240gsm premium paper** for custom prints! 🖼️\n\nUpload your art by clicking the 📎 icon below.",
                    "options": ["🔙 Main Menu"]
                }

            # Rule #4: Policies
            if any(w in msg_lower for w in ["return", "broken", "refund", "shipping", "shipping time", "policy"]):
                session["fallback_count"] = 0
                return self.POLICIES_MESSAGE

            # Cart / Checkout
            if any(w in msg_lower for w in ["checkout", "buy", "cart"]):
                session["fallback_count"] = 0
                return {
                    "text": "Ready to own your art? 🛒\n\n[Proceed to Checkout](/checkout.html)", 
                    "options": ["🔙 Main Menu"]
                }

            # Chat on WhatsApp Action
            if "chat upon whatsapp" in msg_lower or "chat on whatsapp" in msg_lower:
                 return {
                     "text": f"Click here to chat with our expert: [Open WhatsApp]({self.WHATSAPP_LINK})",
                     "options": ["🔙 Main Menu"]
                 }
                 
            # Existing Flow: Place Order
            if "place an order" in msg_lower or "cart" in msg_lower:
                session["state"] = "ASK_ORDER_CATEGORY"
                session["fallback_count"] = 0
                return {
                    "text": "What would you like to order?",
                    "options": ["Website Product", "Custom Product"]
                }

        # --- 3. State Machine Logic (For Ongoing Flows) ---
        
        # CHECK STATUS
        if state == "CHECK_STATUS":
            order_id = message.replace("#", "").strip()
            status = self.get_order_status(order_id)
            session["state"] = "IDLE"
            return status

        # ORDER FLOW (Website/Custom)
        elif state == "ASK_ORDER_CATEGORY":
            if "website" in msg_lower:
                session["state"] = "WEBSITE_SELECT_PRODUCT"
                opts = self.get_website_product_options()
                out_opts = opts[:10]
                out_opts.append("🔙 Main Menu")
                return {"text": "Select a product from our catalog:", "options": out_opts}
            elif "custom" in msg_lower:
                session["state"] = "CUSTOM_UPLOAD_DETAILS"
                return {"text": "For custom products, please describe/upload details here.", "options": ["I have uploaded details", "🔙 Main Menu"]}
            else:
                 return {"text": "Please choose:", "options": ["Website Product", "Custom Product"]}

        elif state == "WEBSITE_SELECT_PRODUCT":
            # Simple product selection
            if "main menu" in msg_lower:
                session["state"] = "IDLE"
                return self.WELCOME_MESSAGE
            session["current_item"] = {"type": "Website", "product_name": message, "size": "NA"}
            session["state"] = "WEBSITE_ASK_QTY"
            return {"text": f"Selected '{message}'. Quantity?", "options": ["1", "2", "3"]}
            
        elif state == "WEBSITE_ASK_QTY":
            session["current_item"]["qty"] = message
            session["cart"].append(session["current_item"])
            session["state"] = "ASK_ADD_MORE"
            return {"text": "Added to cart. Add more?", "options": ["Yes", "No, Checkout"]}
            
        elif state == "CUSTOM_UPLOAD_DETAILS":
            desc = message
            if "[image uploaded]" in msg_lower:
                url = message.split("] ")[1] if "] " in message else message
                desc = f"Image: {url}"
            
            session["current_item"] = {"type": "Custom", "product_name": "Custom", "details": desc}
            session["state"] = "CUSTOM_ASK_QTY"
            return {"text": "Got it. Quantity?", "options": ["1", "2", "3"]}
            
        elif state == "CUSTOM_ASK_QTY":
            session["current_item"]["qty"] = message
            session["cart"].append(session["current_item"])
            session["state"] = "ASK_ADD_MORE"
            return {"text": "Added to cart. Add more?", "options": ["Yes", "No, Checkout"]}

        elif state == "ASK_ADD_MORE":
            if "yes" in msg_lower:
                session["state"] = "ASK_ORDER_CATEGORY"
                return {"text": "Category?", "options": ["Website Product", "Custom Product"]}
            else:
                # Checkout Sequence
                session["state"] = "ASK_NAME"
                return {"text": "Please enter your Full Name:", "options": []}

        # Info Collection
        elif state == "ASK_NAME":
            session["user_info"]["name"] = message
            session["state"] = "ASK_ADDRESS"
            return {"text": "Please enter your Full Address:", "options": []}

        elif state == "ASK_ADDRESS":
            session["user_info"]["address"] = message
            session["state"] = "ASK_PHONE"
            return {"text": "Please enter your 10-digit Mobile Number:", "options": []}

        elif state == "ASK_PHONE":
            phone_input = message.replace(" ", "").replace("+91", "")
            if len(phone_input) == 10 and phone_input.isdigit():
                session["user_info"]["phone"] = phone_input
                return self.finalize_order(user_phone)
            else:
                return {"text": "⚠️ Invalid number. Please enter exactly 10 digits:", "options": []}

        # --- 4. Fallback Mechanism ---
        # If we reached here, the input didn't match the current state's expected input 
        # (For open-ended inputs like Name/Details, we handled them in state blocks. 
        # But if state was IDLE and no keywords matched, we fall through)
        
        if state == "IDLE":
            session["fallback_count"] += 1
            if session["fallback_count"] >= 3:
                session["fallback_count"] = 0
                return {
                    "text": "I'm having trouble finding that. Would you like to chat with a human expert on WhatsApp?",
                    "options": ["Chat on WhatsApp", "🔙 Main Menu"]
                }
            
        return {
            "text": "I didn't quite catch that. Could you rephrase? 🤔",
            "options": self.WELCOME_MESSAGE["options"]
        }

    def finalize_order(self, user_key):
        session = self.user_sessions[user_key]
        order_id = self.save_order_batch(session)
        
        if order_id:
            msg_text = (
                f"Order Placed Successfully! ✅\n"
                f"Order ID: #{order_id}\n\n"
                f"Items: {len(session['cart'])}\n"
                f"Name: {session['user_info']['name']}\n"
                f"Phone: {session['user_info']['phone']}\n\n"
                f"{self.PAYMENT_QR_MESSAGE}"
            )
            session["cart"] = []
            session["state"] = "IDLE"
            return {"text": msg_text, "options": ["Check Order Status", "Place another order"]}
        else:
            return {"text": "⚠️ System Error: Could not save order. Please try again later.", "options": ["Main Menu"]}

def monitor_notifications(bot):
    print("\n[SYSTEM]: Background monitoring initialized.")
    while True:
        results = bot.check_for_notifications()
        time.sleep(5)

# Initialize Flask
# We use static_url_path='' so that files effectively live at root /
# static_folder='.' sets the serving directory to the current folder
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

bot = IDecorBot()

t = threading.Thread(target=monitor_notifications, args=(bot,), daemon=True)
t.start()

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    user_id = data.get('user_id', 'web_guest')
    response_data = bot.handle_message(user_id, message)
    return jsonify({"response": response_data})

import os
import uuid

# ... other imports ...

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        upload_folder = os.path.join(app.static_folder, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        
        file_url = f"/uploads/{filename}"
        return jsonify({'url': file_url})

if __name__ == "__main__":
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"===================================================")
        print(f"Server Running! 🚀")
        print(f"Access on this PC:   http://localhost:5000")
        print(f"Access on Mobile:    http://{local_ip}:5000")
        print(f"===================================================")
    except:
        print("Server Running on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

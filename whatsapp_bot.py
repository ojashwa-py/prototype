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
    def __init__(self, sheet_name="iDecor Orders", creds_file="credentials.json"):
        self.sheet_name = sheet_name
        self.creds_file = os.path.join(BASE_DIR, creds_file)
        self.user_sessions = {}
        self.sheet = None
        self.products = []
        self.load_products()
        self.connect_gsheet()
        
        # Policy and text constants
        self.WELCOME_MESSAGE = {
            "text": (
                "Welcome to iDecor 🖼️\n"
                "Custom posters, polaroids & stickers.\n"
                "How can I help you today?"
            ),
            "options": ["🛒 Place an order", "📦 Check order status", "ℹ️ FAQ", "📜 Policies"]
        }
        
        self.FAQ_MESSAGE = {
            "text": "Please note: iDecor does not offer replacement. Courier damage is not refundable.",
            "options": ["🔙 Main Menu"]
        }

        self.POLICIES_MESSAGE = {
            "text": (
                "📜 iDecor Store Policies\n\n"
                "• All products are customized. Once an order is confirmed, it cannot be modified or cancelled.\n"
                "• Refunds are not guaranteed and are issued only after verification.\n"
                "• Courier damage after dispatch is not refundable.\n"
                "• iDecor does not offer replacement under any circumstances."
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
                "user_info": {"phone": user_phone}
            }
        
        session = self.user_sessions[user_phone]
        state = session["state"]

        # 1. Global Commands
        if msg_lower in ["hi", "hello", "hey", "menu", "start", "restart", "main menu", "🔙 main menu"]:
            session["state"] = "IDLE"
            session["cart"] = []
            return self.WELCOME_MESSAGE

        # 2. State Machine
        if state == "IDLE":
            if "place an order" in msg_lower or "cart" in msg_lower:
                session["state"] = "ASK_ORDER_CATEGORY"
                return {
                    "text": "What would you like to order?",
                    "options": ["Website Product", "Custom Product"]
                }
            
            elif "check order status" in msg_lower:
                session["state"] = "CHECK_STATUS"
                return {"text": "Please enter your Order ID:", "options": ["🔙 Main Menu"]}
            
            elif "faq" in msg_lower:
                return self.FAQ_MESSAGE
            
            elif "policies" in msg_lower:
                return self.POLICIES_MESSAGE
            
            else:
                return {
                    "text": "I didn't understand that. Please select an option:",
                    "options": self.WELCOME_MESSAGE["options"]
                }

        # --- ORDER FLOW ---
        elif state == "ASK_ORDER_CATEGORY":
            if "website" in msg_lower:
                session["state"] = "WEBSITE_SELECT_PRODUCT"
                opts = self.get_website_product_options()
                out_opts = opts[:10]
                out_opts.append("🔙 Main Menu")
                return {
                    "text": "Select a product from our catalog:",
                    "options": out_opts
                }
            elif "custom" in msg_lower:
                session["state"] = "CUSTOM_UPLOAD_DETAILS"
                return {
                    "text": "For custom products, please upload/describe clear photos and details here.",
                    "options": ["I have uploaded/sent details", "🔙 Main Menu"]
                }
            else:
                 return {"text": "Please choose:", "options": ["Website Product", "Custom Product"]}

        # Website Flow
        elif state == "WEBSITE_SELECT_PRODUCT":
            if "main menu" in msg_lower:
                session["state"] = "IDLE"
                return self.WELCOME_MESSAGE

            product_name = message
            session["current_item"] = {"type": "Website Product", "product_name": product_name, "size": "NA"}
            session["state"] = "WEBSITE_ASK_QTY"
            return {
                "text": f"Selected '{product_name}'. Quantity?", 
                "options": ["1", "2", "3", "4", "5"]
            }

        elif state == "WEBSITE_ASK_QTY":
            qty = message
            if "current_item" in session:
                session["current_item"]["qty"] = qty
                session["cart"].append(session["current_item"])
                del session["current_item"]
            
            session["state"] = "ASK_ADD_MORE"
            return {
                "text": "Item added to cart 🛒. Add another product?",
                "options": ["Yes, add more", "No, Checkout"]
            }

        # Custom Flow
        elif state == "CUSTOM_UPLOAD_DETAILS":
            if "main menu" in msg_lower:
                 session["state"] = "IDLE"
                 return self.WELCOME_MESSAGE

            desc = message
            session["current_item"] = {"type": "Custom Product", "product_name": "Custom Order", "size": "Custom", "details": desc}
            session["state"] = "CUSTOM_ASK_QTY"
            return {
                "text": "Got it. Quantity?",
                "options": ["1", "2", "3", "5", "10"]
            }
        
        elif state == "CUSTOM_ASK_QTY":
            qty = message
            if "current_item" in session:
                session["current_item"]["qty"] = qty
                session["cart"].append(session["current_item"])
                del session["current_item"]
            
            session["state"] = "ASK_ADD_MORE"
            return {
                "text": "Item added to cart 🛒. Add another product?",
                "options": ["Yes, add more", "No, Checkout"]
            }

        # Loop or Checkout
        elif state == "ASK_ADD_MORE":
            if "yes" in msg_lower:
                session["state"] = "ASK_ORDER_CATEGORY"
                return {
                    "text": "What kind of product?",
                    "options": ["Website Product", "Custom Product"]
                }
            else:
                # Checkout Sequence
                user_info = session.get("user_info", {})
                
                if not user_info.get("name"):
                    session["state"] = "ASK_NAME"
                    return {"text": "Please enter your Full Name:", "options": []}
                
                if not user_info.get("address"):
                    session["state"] = "ASK_ADDRESS"
                    return {"text": "Please enter your Full Address:", "options": []}
                
                saved_phone = user_info.get("phone", "")
                if not saved_phone or len(saved_phone) != 10 or not saved_phone.isdigit():
                    session["state"] = "ASK_PHONE"
                    return {"text": "Please enter your 10-digit Mobile Number:", "options": []}
                
                return self.finalize_order(user_phone)

        # Info Collection
        elif state == "ASK_NAME":
            session["user_info"]["name"] = message
            if not session["user_info"].get("address"):
                session["state"] = "ASK_ADDRESS"
                return {"text": "Please enter your Full Address:", "options": []}
            session["state"] = "ASK_PHONE"
            return {"text": "Please enter your 10-digit Mobile Number:", "options": []}

        elif state == "ASK_ADDRESS":
            session["user_info"]["address"] = message
            p = session["user_info"].get("phone", "")
            if p and len(p) == 10 and p.isdigit():
                 return self.finalize_order(user_phone)
            session["state"] = "ASK_PHONE"
            return {"text": "Please enter your 10-digit Mobile Number:", "options": []}

        elif state == "ASK_PHONE":
            phone_input = message.replace(" ", "").replace("+91", "")
            if len(phone_input) == 10 and phone_input.isdigit():
                session["user_info"]["phone"] = phone_input
                return self.finalize_order(user_phone)
            else:
                return {
                    "text": "⚠️ Invalid number. Please enter exactly 10 digits:",
                    "options": []
                }

        # STATUS CHECK
        elif state == "CHECK_STATUS":
            order_id = message.replace("#", "").strip()
            status = self.get_order_status(order_id)
            session["state"] = "IDLE"
            return status

        return {
            "text": "I didn't understand. Type 'hi' to restart.",
            "options": ["Hi"]
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

if __name__ == "__main__":
    print("Starting Flask connection for iDecor Chat...")
    app.run(port=5000, debug=True)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import json
import os
import threading
import time
import random
from datetime import datetime

class IDecorBot:
    def __init__(self, sheet_name="iDecor Orders", creds_file="credentials.json"):
        self.sheet_name = sheet_name
        self.creds_file = creds_file
        self.user_sessions = {}
        self.sheet = None
        self.connect_gsheet()
        
        # Policy and text constants
        self.WELCOME_MESSAGE = (
            "Welcome to iDecor 🖼️\n"
            "Custom posters, polaroids & stickers.\n"
            "How can I help you today?\n\n"
            "• 🛒 Place an order\n"
            "• 📦 Check order status\n"
            "• ℹ️ FAQ\n"
            "• 📜 Policies\n"
            "• 🌐 Website link"
        )
        
        self.FAQ_MESSAGE = (
            "Please note: iDecor does not offer replacement. Courier damage is not refundable."
        )

        self.POLICIES_MESSAGE = (
            "📜 iDecor Store Policies\n\n"
            "• All products are customized. Once an order is confirmed, it cannot be modified or cancelled after printing or packaging starts.\n"
            "• Product images are for reference only. Minor color or size variations may occur and are not considered defects.\n"
            "• Refunds are not guaranteed and are issued only after internal verification and approval.\n"
            "• Courier damage after dispatch is not refundable. Packing proof is recorded before dispatch.\n"
            "• Any issue must be reported within 24–48 hours of delivery with a clear unedited unboxing video.\n"
            "• Delays, damage, or loss caused by courier partners are not the responsibility of iDecor.\n"
            "• Refusal to accept delivery, incorrect address, or customer dissatisfaction is non-refundable.\n"
            "• Customized or made-to-order products cannot be cancelled once confirmed.\n"
            "• iDecor does not offer replacement under any circumstances.\n\n"
            "By placing an order, you agree to all store policies."
        )

        self.PAYMENT_QR_MESSAGE = (
            "Please scan the QR code below to complete payment 💳\n"
            "Our team will verify the payment within 7 hours.\n"
            "You will receive a confirmation message after verification."
        )

        self.PAYMENT_PENDING_MESSAGE = (
            "Your payment is under verification ⏳\n"
            "Our team will confirm it within 7 hours."
        )

        self.ORDER_CANCELLED_MSG = (
            "Orders can only be cancelled before printing or packaging begins. Once processing starts, cancellation is not possible."
        )

    def connect_gsheet(self):
        """Connects to Google Sheets using the service account (File or Env Var)."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = None
            
            # 1. Try Environment Variable (Best for Render/Heroku)
            
            # Helper to clean private key
            def clean_key(key):
                # Remove extra quotes if user pasted them
                key = key.strip().strip('"').strip("'")
                # Fix escaped newlines - mostly it's \\n from JSON string or copy-paste
                key = key.replace('\\n', '\n')
                # Sometimes triple escapes happen
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
                    # Print snippet to help debug (masked)
                    print(f"[DEBUG] Env Content Snippet: {json_creds[:20]}...")
            
            # 2. Try Local File (Fallback)
            if not creds:
                print("[SYSTEM] Attempting fallback to local 'credentials.json'...")
                if os.path.exists(self.creds_file):
                    # Manual load to apply the \n fix even for files, just in case
                    try:
                        with open(self.creds_file, 'r') as f:
                            file_creds = json.load(f)
                        
                        if 'private_key' in file_creds:
                             file_creds['private_key'] = clean_key(file_creds['private_key'])
                        
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(file_creds, scope)
                    except Exception as e:
                         print(f"[ERROR] Fallback file loading failed: {e}")
                else:
                    print(f"[ERROR]: '{self.creds_file}' not found and 'GOOGLE_CREDENTIALS' env var is empty/invalid.")
                    return

            client = gspread.authorize(creds)
            
            # Open the sheet
            try:
                self.sheet = client.open(self.sheet_name).sheet1
                print("[SYSTEM]: Connected to Google Sheet successfully.")
            except gspread.exceptions.SpreadsheetNotFound:
                print(f"[ERROR]: Sheet '{self.sheet_name}' not found. Please create it and share with the service account.")
            
        except Exception as e:
            print(f"[ERROR]: Could not connect to Google Sheets: {e}")

    def generate_order_id(self):
        return f"ID{random.randint(1000, 9999)}"

    def get_order_status(self, order_id):
        if not self.sheet:
            self.connect_gsheet()
            if not self.sheet: return "System Error: Database not connected."

        try:
            # Fetch all records
            records = self.sheet.get_all_records()
            
            # Find the order
            for row in records:
                # Convert to string for safe comparison
                if str(row.get('Order ID', '')) == str(order_id):
                    verified = str(row.get('Payment Verified', '')).strip().lower()
                    if verified == 'yes':
                        return "Confirmed"
                    else:
                        return "Payment Pending"
            
            return "Order ID not found."
        except Exception as e:
            print(f"Error fetching status: {e}")
            pass
        return "Order ID not found."

    def generate_order_id(self):
        return f"ID{random.randint(1000, 9999)}"



    def save_order(self, order_data):
        if not self.sheet:
            self.connect_gsheet()
            if not self.sheet: return False

        try:
            # Prepare row data [Order ID, Name, Product, Type, Size, Qty, Date, Address, Phone, AltPhone, Paid, Confirmed]
            # Must match the header order in the Sheet for get_all_records to work nicely, 
            # OR we just append a list in order.
            
            row = [
                order_data['order_id'],
                order_data['name'],
                order_data['product_name'],
                order_data['type'],
                order_data['size'],
                order_data['qty'],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                order_data.get('address', ''),
                str(order_data['phone']),
                '', # another contact no
                'No', # Payment Verified
                'No'  # Confirmation Sent
            ]
            
            self.sheet.append_row(row)
            return True
        except Exception as e:
            print(f"Error saving order to sheet: {e}")
            return False

    def check_for_notifications(self):
        """Checks for confirmed payments that haven't been notified yet."""
        if not self.sheet:
            return []
        
        notifications = []
        try:
            # Get all values (list of lists) to find indices
            # Warning: get_all_records() is easier for dict access but harder for writing back to specific cell
            # So we use get_all_values() which includes headers
            rows = self.sheet.get_all_values()
            
            if len(rows) < 2: return [] # Empty or just header
            
            headers = rows[0]
            try:
                idx_verified = headers.index('Payment Verified')
                idx_conf_sent = headers.index('Confirmation Sent')
                idx_order_id = headers.index('Order ID')
                idx_phone = headers.index('Contact no.')
            except ValueError:
                return [] # Headers missing

            # Iterate rows (1-based index for GSheets/gspread update)
            # Row 1 is header, so data starts at row 2 in the sheet (index 1 in py list)
            for i in range(1, len(rows)):
                row_data = rows[i]
                
                # Safety check for column length
                if len(row_data) <= max(idx_verified, idx_conf_sent): continue

                payment_verified = row_data[idx_verified].strip().lower()
                conf_sent = row_data[idx_conf_sent].strip().lower()
                
                if payment_verified == 'yes' and conf_sent != 'yes':
                    # Prepare Notification
                    order_id = row_data[idx_order_id]
                    phone = row_data[idx_phone]
                    notifications.append((phone, f"Your order #{order_id} is Confirmed! ✅"))
                    
                    # Update 'Confirmation Sent' cell
                    # i + 1 is the row number (since range starts at 1, but sheet rows start at 1 and we have header)
                    # Actually: i is index in `rows`. rows[0] is Row 1. rows[1] is Row 2.
                    # So absolute row number is i + 1.
                    self.sheet.update_cell(i + 1, idx_conf_sent + 1, 'Yes')
                    
        except Exception as e:
            # print(f"Error checking notifications: {e}")
            pass
            
        return notifications

    def try_parse_auto_order(self, message):
        """Attempts to parse the [New Order Request ...] format."""
        try:
            # Basic checks
            if "[New Order Request" not in message:
                return None
            
            # Simple line-based extraction (robust enough for template)
            lines = [l.strip() for l in message.split('\n') if l.strip()]
            
            # Helper to extract value after bullet or key
            def extract(line):
                return re.sub(r'^[•\-\*]\s*', '', line).strip()

            # We need to find the block relative to "New Order Request"
            start_idx = -1
            for i, line in enumerate(lines):
                if "[New Order Request" in line:
                    start_idx = i
                    break
            
            if start_idx == -1 or start_idx + 3 >= len(lines):
                return None
            
            # Assume strict structure as per prompt example
            # • Name
            # • Address
            # • Phone
            name = extract(lines[start_idx + 1])
            address = extract(lines[start_idx + 2])
            phone = extract(lines[start_idx + 3])
            
            # Order Details
            # Look for lines that might be product details? 
            # The prompt says: "Order Details with product name, quantity, price, specs"
            # Since standardizing this is hard without more strict formatting, 
            # we will take the rest of the text as "Product Details" or try to parse
            
            product_name = "Website Order"
            qty = 1
            # Try to find specific product info if possible, otherwise use generic
            # For now, we'll store the raw message or basic info
            
            # Check for total amount
            amount = "Unknown"
            for line in lines[start_idx:]:
                if "Total Amount" in line or "Total:" in line:
                    amount = line.split(":")[-1].strip()
            
            # Generate ID and save
            order_id = self.generate_order_id()
            
            order_data = {
                'order_id': order_id,
                'name': name,
                'product_name': 'Website Auto-Order', # Placeholder or extract from text
                'type': 'Website',
                'size': 'NA',
                'qty': qty,
                'phone': phone,
                'address': address
            }
            
            # Attempt to extract better product details from "Order Details X"
            # This is heuristics since prompt format is loose
            
            if self.save_order(order_data):
                return (
                    f"Your order request has been received ✅\n"
                    f"Order ID: #{order_id}\n"
                    f"Status: Payment Pending\n\n"
                    f"Our team will review and contact you shortly for payment confirmation."
                )
        except Exception as e:
            print(f"Auto-parse failed: {e}")
        return None

    def handle_message(self, user_phone, message):
        message = message.strip()
        
        # 1. Check for Automatic Order Format FIRST
        auto_response = self.try_parse_auto_order(message)
        if auto_response:
            # Reset session since this is a fresh order
            self.user_sessions[user_phone] = {"state": "IDLE", "data": {}}
            return auto_response

        if user_phone not in self.user_sessions:
            self.user_sessions[user_phone] = {"state": "IDLE", "data": {}}
        
        session = self.user_sessions[user_phone]
        state = session["state"]
        
        msg_lower = message.lower()

        # Global Resets / Commands
        if msg_lower in ["hi", "hello", "hey"]:
            session["state"] = "IDLE"
            session["data"] = {}
            return self.WELCOME_MESSAGE

        # IDLE State
        if state == "IDLE":
            if "place an order" in msg_lower:
                session["state"] = "ASK_ORDER_CATEGORY"
                return (
                    "Please choose order type:\n"
                    "• Website product\n"
                    "• Custom product"
                )
            
            elif "check order status" in msg_lower:
                session["state"] = "CHECK_STATUS"
                return "Please enter your Order ID:"
            
            elif "faq" in msg_lower:
                return self.FAQ_MESSAGE
            
            elif "policies" in msg_lower or any(x in msg_lower for x in ["refund", "cancellation", "store rules", "replacement", "delivery", "policy"]):
                return self.POLICIES_MESSAGE
            
            elif "website link" in msg_lower:
                 return "🌐 Visit us at: https://idecor.com" # Replace with actual link if known

            elif "cancel" in msg_lower and "order" in msg_lower:
                return self.ORDER_CANCELLED_MSG

            elif "confirmed" in msg_lower and ("payment" in msg_lower or "order" in msg_lower):
                return self.PAYMENT_PENDING_MESSAGE
            
            else:
                return "I didn't understand that. Type 'hi' to see the options."

        # MANUAL ORDER FLOW
        elif state == "ASK_ORDER_CATEGORY":
            if "website" in msg_lower:
                session["state"] = "WEBSITE_ASK_PRODUCT"
                return "Please share the product name as shown on the website."
            elif "custom" in msg_lower:
                session["state"] = "CUSTOM_ASK_NAME"
                return "Please share your name:"
            else:
                return "Please choose order type:\n• Website product\n• Custom product"

        # --- Website Product Branch ---
        elif state == "WEBSITE_ASK_PRODUCT":
            session["data"]["product_name"] = message
            session["data"]["type"] = "Website Product"
            session["data"]["size"] = "NA"
            session["state"] = "WEBSITE_ASK_QTY"
            return "Please tell the quantity."
        
        elif state == "WEBSITE_ASK_QTY":
            # Taking name from session or default if not asked in this flow
            # Prompt didn't specify asking name in Website flow, so we default or use phone
            if "name" not in session["data"]:
                 session["data"]["name"] = "Guest" 
            
            session["data"]["qty"] = message # Store as string or int
            session["data"]["phone"] = user_phone
            
            # Generate & Save
            order_id = self.generate_order_id()
            session["data"]["order_id"] = order_id
            
            if self.save_order(session["data"]):
                session["state"] = "IDLE"
                return (
                    f"Your order has been booked ✅\n"
                    f"Order ID: #{order_id}\n"
                    f"Product: {session['data']['product_name']}\n"
                    f"Type: website\n" 
                    f"Size: NA\n"
                    f"Quantity: {session['data']['qty']}\n"
                    f"Status: Payment Pending\n\n"
                    f"{self.PAYMENT_QR_MESSAGE}"
                )
            else:
                return "Error saving order."

        # --- Custom Product Branch ---
        elif state == "CUSTOM_ASK_NAME":
            session["data"]["name"] = message
            session["state"] = "CUSTOM_ASK_PRODUCT"
            return "Please type the product name:" # Prompt says "Ask for product name"
        
        elif state == "CUSTOM_ASK_PRODUCT":
            session["data"]["product_name"] = message
            session["state"] = "CUSTOM_ASK_TYPE"
            return (
                "Please select product type:\n"
                "• Custom poster\n"
                "• Custom polaroid\n"
                "• Custom sticker"
            )
        
        elif state == "CUSTOM_ASK_TYPE":
            if "poster" in msg_lower:
                session["data"]["type"] = "Custom poster"
                session["state"] = "CUSTOM_ASK_SIZE_POSTER"
                return "Which size? A4 / A3 / 12x18 / 13x19"
            elif "sticker" in msg_lower:
                session["data"]["type"] = "Custom sticker"
                session["state"] = "CUSTOM_ASK_SIZE_STICKER"
                return "Please enter sticker size:"
            elif "polaroid" in msg_lower:
                session["data"]["type"] = "Custom polaroid"
                session["data"]["size"] = "NA"
                session["state"] = "CUSTOM_ASK_QTY"
                return "Please enter quantity:"
            else:
                return "Please select: Custom poster, Custom polaroid, or Custom sticker."

        elif state == "CUSTOM_ASK_SIZE_POSTER":
            valid_sizes = ["a4", "a3", "12x18", "13x19"]
            if message.lower() not in valid_sizes:
                return "Please choose a valid size: A4 / A3 / 12x18 / 13x19"
            session["data"]["size"] = message.upper()
            session["state"] = "CUSTOM_ASK_QTY"
            return "Please enter quantity:"
        
        elif state == "CUSTOM_ASK_SIZE_STICKER":
            session["data"]["size"] = message
            session["state"] = "CUSTOM_ASK_QTY"
            return "Please enter quantity:"
        
        elif state == "CUSTOM_ASK_QTY":
            session["data"]["qty"] = message
            session["data"]["phone"] = user_phone
            
            # Generate & Save
            order_id = self.generate_order_id()
            session["data"]["order_id"] = order_id
            
            if self.save_order(session["data"]):
                session["state"] = "IDLE"
                # Receipt
                return (
                    f"Your order has been booked ✅\n"
                    f"Order ID: #{order_id}\n"
                    f"Product: {session['data']['product_name']}\n"
                    f"Type: {session['data']['type'].lower()}\n"
                    f"Size: {session['data']['size']}\n"
                    f"Quantity: {session['data']['qty']}\n"
                    f"Status: Payment Pending\n\n"
                    f"{self.PAYMENT_QR_MESSAGE}"
                )
            else:
                return "Error saving order."

        # STATUS CHECK
        elif state == "CHECK_STATUS":
            order_id_input = message.replace("#", "").strip()
            # If user tries cancel here by mistake
            if "cancel" in msg_lower:
                session["state"] = "IDLE"
                return self.ORDER_CANCELLED_MSG

            status = self.get_order_status(order_id_input)
            session["state"] = "IDLE"
            return status

        return "I didn't understand that. Type 'hi' to start over."

def monitor_notifications(bot):
    """Background thread to check for notifications."""
    print("\n[SYSTEM]: Background monitoring initialized.")
    while True:
        results = bot.check_for_notifications()
        
        # --- VERBOSE DEBUGGING FOR USER ---
        # Show what the bot sees in the file every few loops
        try:
                # We check silently just to help user debug
                if bot.sheet:
                   pass
                   # With Google Sheets, frequent API calls might hit rate limits, so we avoid polling too aggressively in debug print
                   # print("[SYSTEM]: Checking Google Sheet for updates...", end="\r")
        except:
            pass
        # ----------------------------------

        for res in results:
            if isinstance(res, str) and "ERROR" in res:
                # Only print error once per occurrence
                print(f"\n[SYSTEM]: {res}\nUser: ", end="")
            elif isinstance(res, tuple):
                phone, msg = res
                print(f"\n\n[WHATSAPP NOTIFICATION to {phone}]: {msg}\nUser: ", end="")
        
        time.sleep(3) # Check every 3 seconds

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

bot = IDecorBot()

# Start background thread for notifications (logs to server console)
# We check if it is the main thread/reloader to avoid duplicate threads in some envs, 
# but for simple deployment this is okay.
t = threading.Thread(target=monitor_notifications, args=(bot,), daemon=True)
t.start()

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    user_id = data.get('user_id', 'web_guest') # Use provided user_id or default
    
    response = bot.handle_message(user_id, message)
    return jsonify({"response": response})

if __name__ == "__main__":
    print("Starting Flask connection for iDecor Chat...")
    app.run(port=5000, debug=True)

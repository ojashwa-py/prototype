from whatsapp_bot import IDecorBot
import sys
import os

print("--- Testing New Credentials ---")

# 1. Check if file exists
if not os.path.exists("credentials.json"):
    print("[ERROR] 'credentials.json' file not found in folder.")
    sys.exit(1)

print("[INFO] 'credentials.json' found.")

try:
    bot = IDecorBot()
    # Force connect
    bot.connect_gsheet()
    
    if bot.sheet:
        print(f"[SUCCESS] Connected to Google Sheet: '{bot.sheet.title}'")
        print("[INFO] The new credentials are working correctly locally.")
        print("[IMPORTANT] Now copy the content of 'credentials.json' and paste it into Render 'GOOGLE_CREDENTIALS'.")
    else:
        print("[FAILURE] Could not connect. Check the error message above.")
        print("[TIP] Did you share the sheet with the NEW client_email?")

except Exception as e:
    print(f"[EXCEPTION]: {e}")

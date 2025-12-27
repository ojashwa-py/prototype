from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from whatsapp_bot import IDecorBot
import os

# Initialize Flask with current directory for templates and static files
app = Flask(__name__, template_folder=os.getcwd(), static_folder=os.getcwd())
CORS(app) # Allow cross-origin requests

# Initialize the bot
bot = IDecorBot()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_msg = data.get('message', '')
        # Use a fixed ID for the web interface session
        user_phone = "WEB_USER_SESSION" 
        
        # Get response from the existing bot logic
        response = bot.handle_message(user_phone, user_msg)
        
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": "Error processing message."}), 500

if __name__ == '__main__':
    print("Starting iDecor Chat Server...")
    app.run(debug=True, port=5000)

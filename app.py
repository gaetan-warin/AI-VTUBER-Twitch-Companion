import os
import eventlet
from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv, find_dotenv
import ollama
import re
import bleach

# Monkey patching for eventlet compatibility
eventlet.monkey_patch(thread=True, os=True, select=True, socket=True)

# Load default .env file
load_dotenv(encoding='latin1')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Ollama CFG
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
PRE_PROMPT = os.getenv("PRE_PROMPT")
PERSONA_NAME = os.getenv("PERSONA_NAME")
PERSONA_ROLE = os.getenv("PERSONA_ROLE")

# Socket.IO CFG
SOCKETIO_IP = os.getenv("SOCKETIO_IP")
SOCKETIO_IP_PORT = os.getenv("SOCKETIO_IP_PORT")

# CURRENT SERVER CFG
API_URL = os.getenv("API_URL")
API_URL_PORT = os.getenv("API_URL_PORT")

AVATAR_MODEL = os.getenv("API_URL_PORT")

# Configure SocketIO with CORS and async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


# Serve the home page
@app.route('/')
def home():
    return render_template('avatar.html')

# Trigger speak endpoint
@app.route('/trigger_speak', methods=['POST'])
def trigger_speak():
    data = request.get_json()
    text = data.get('text', '').strip()

    if text:
        socketio.emit('speak_text', {'text': text})
        return jsonify({'status': 'success', 'message': 'Text sent to speak'}, 200)
    return jsonify({'status': 'error', 'message': 'No text provided'}, 400)

@app.route('/trigger_ai_request', methods=['POST'])
def trigger_ai_request():
    print("in trigger_ai_request")
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
        user_input = data.get('message', '').strip()
        response, status_code = process_ai_request(user_input)
        if status_code == 200:
            socketio.emit('speak_text', {'text': response['message']})
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_model', methods=['GET'])
def getModel():
    avatar_model_path = "models/shizuku/shizuku.model.json"
    if (avatar_model_path ==  "shizuku"):
        avatar_model_path = "models/shizuku/shizuku.model.json"
    return avatar_model_path

@app.route('/get_ollama_models', methods=['GET'])
def get_ollama_models():
    try:
        response = ollama.list()
        models = response.models
        model_names = [model.model for model in models]
        return jsonify({'status': 'success', 'models': model_names}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def process_ai_request(user_input):
    if not user_input:
        return {'status': 'error', 'message': 'No message provided'}, 400

    if not OLLAMA_MODEL:
        return {'status': 'error', 'message': 'Missing OLLAMA configuration'}, 500

    # Sanitize the user input
    sanitized_input = bleach.clean(user_input)

    # Create a structured prompt
    structured_prompt = f"""
    Persona:
    Name: {PERSONA_NAME}
    Role: {PERSONA_ROLE}

    Instructions:
    {PRE_PROMPT}

    User: {sanitized_input}
    """

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": structured_prompt.strip()}])
        final_response = response['message']['content'].strip()
        cleaned_response = clean_response(final_response)
        return {'status': 'success', 'message': cleaned_response}, 200
    except Exception as e:
        return {'status': 'error', 'message': f'Request error: {str(e)}'}, 500

def clean_response(response):
    response = re.sub(r'<think>\s*.*?\s*</think>', '', response, flags=re.DOTALL)
    response = re.sub(r'[^\x00-\x7F]+', '', response)
    response = re.sub(r'\\_\\_\\_', '', response)
    response = re.sub(r'\s+', ' ', response).strip()
    return response

# Serve model files and resources (textures, expressions, motions, sounds)
@app.route('/models/<path:filename>')
def serve_model_files(filename):
    models_dir = os.path.join(app.root_path, 'models')
    if os.path.isfile(os.path.join(models_dir, filename)):
        return send_from_directory(models_dir, filename)
    else:
        abort(404)

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('speak')
def handle_speak(data):
    text = data.get('text', '').strip()
    if text:
        socketio.emit('speak_text', {'text': text})

@socketio.on('request_model_path')
def handle_request_model_path():
    avatar_model_path = "models/shizuku/shizuku.model.json"
    socketio.emit('model_path', {'path': avatar_model_path})

@socketio.on('ask_ai')
def handle_ask_ai(data):
    user_input = data.get('text', '').strip()
    response, status_code = process_ai_request(user_input)
    if status_code == 200:
        socketio.emit('ai_response', {'text': response['message']})

@socketio.on('display_question')
def handle_display_question(data):
    socketio.emit('display_question', data)

@socketio.on('trigger_ai_request')
def handle_trigger_ai_request(data):
    try:
        user_input = data.get('message', '').strip()
        response, status_code = process_ai_request(user_input)
        if status_code == 200:
            socketio.emit('speak_text', {'text': response['message']})
    except Exception as e:
        print(f"Error processing AI request: {e}")

@socketio.on('save_config')
def handle_save_config(data):
    try:
        with open('.env', 'w', encoding='latin1') as f:
            for key, value in data.items():
                if ' ' in value:
                    value = f'"{value}"'
                f.write(f"{key}={value}\n")
        print("Configuration saved to .env")
    except Exception as e:
        print(f"Error saving configuration: {e}")

@socketio.on('update_live_global_env')
def handle_update_live_global_env(data):
    try:
        persona_name = data.get('personaName', '').strip()
        persona_role = data.get('personaRole', '').strip()
        pre_prompt = data.get('prePrompt', '').strip()  
        ollama_model = data.get('ollamaModel', '').strip()
        avatar_model = data.get('avatarModel', '').strip()
        
        # TODO give information to twichLister.py
        channel_name = data.get('channelName', '').strip()
        token = data.get('token', '').strip()
        clientId = data.get('clientId', '').strip()
        botName = data.get('botName', '').strip()
        extraDelayListener = data.get('extraDelayListener', '').strip()
        nbSpamMessage = data.get('nbSpamMessage', '').strip()

        # Update the environment variables
        global PERSONA_NAME, PERSONA_ROLE, PRE_PROMPT, OLLAMA_MODEL, AVATAR_MODEL
        PERSONA_NAME = persona_name
        PERSONA_ROLE = persona_role
        PRE_PROMPT = pre_prompt
        PRE_PROMPT = pre_prompt
        OLLAMA_MODEL = ollama_model
        AVATAR_MODEL = avatar_model

        socketio.emit('update_live_global_env_response', {'status': 'success', 'message': 'Persona updated successfully'})
    except Exception as e:
        socketio.emit('update_live_global_env_response', {'status': 'error', 'message': str(e)})

@socketio.on('load_config')
def handle_load_config():
    try:
        # Reload the .env file to get the most recent values
        load_dotenv(override=True, encoding='latin1')
        config = {
            'PERSONA_NAME': os.getenv('PERSONA_NAME', ''),
            'PERSONA_ROLE': os.getenv('PERSONA_ROLE', ''),
            'PRE_PROMPT': os.getenv('PRE_PROMPT', ''),
            'AVATAR_MODEL': os.getenv('AVATAR_MODEL', ''),
            'CHANNEL_NAME': os.getenv('CHANNEL_NAME', ''),
            'TOKEN': os.getenv('TOKEN', ''),
            'CLIENT_ID': os.getenv('CLIENT_ID', ''),
            'BOT_NAME': os.getenv('BOT_NAME', ''),
            'EXTRA_DELAY_LISTENER': os.getenv('EXTRA_DELAY_LISTENER', ''),
            'NB_SPAM_MESSAGE': os.getenv('NB_SPAM_MESSAGE', ''),
            'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL', '')
        }
        socketio.emit('load_config', config)
    except Exception as e:
        socketio.emit('load_config_error', {'status': 'error', 'message': str(e)})

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

# Main entry point
if __name__ == '__main__':
    try:
        print(f"\n🔥 Starting server at {API_URL}:{API_URL_PORT}...")
        socketio.run(app, host=SOCKETIO_IP, port=SOCKETIO_IP_PORT)
    except Exception as e:
        print(f"Error starting server: {e}")

import os
import eventlet
from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv
import requests
import re
import json

# Monkey patching for eventlet compatibility
eventlet.monkey_patch(thread=True, os=True, select=True, socket=True)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Ollam CFG
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
PRE_PROMPT = os.getenv("PRE_PROMPT")

# Socket.IO CFG
SOCKETIO_IP = os.getenv("SOCKETIO_IP")
SOCKETIO_IP_PORT = os.getenv("SOCKETIO_IP_PORT")

# CURRENT SERVER CFG
API_URL = os.getenv("API_URL")
API_URL_PORT = os.getenv("API_URL_PORT")

DEFAULT_AVATAR_MODEL = os.getenv("API_URL_PORT")

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

@app.route('/process_message', methods=['POST'])
def process_message():
    try:
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
            
        user_input = data.get('message', '').strip()
        print(f"Received message: {user_input}")
        
        if not user_input:
            return jsonify({'status': 'error', 'message': 'No message provided'}), 400
        
        if not OLLAMA_URL or not OLLAMA_MODEL:
            print("Missing OLLAMA configuration")
            return jsonify({'status': 'error', 'message': 'Missing OLLAMA configuration'}), 500
        
        # Prepare prompt with PRE_PROMPT
        formatted_input = f"{PRE_PROMPT} Your prompt is: {user_input}." if PRE_PROMPT else user_input
        print(f"Sending to Ollama: {formatted_input}")
        print({"model": OLLAMA_MODEL, "prompt": formatted_input})
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": formatted_input},
            timeout=30  # Add timeout
        )
        
        print(f"Ollama response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Ollama error response: {response.text}")
            return jsonify({'status': 'error', 'message': f'LLM API error: {response.status_code}'}), 500

        # Process response
        full_response = []
        for line in response.text.splitlines():
            try:
                response_data = json.loads(line)
                if response_data.get('done', False):
                    full_response.append(response_data.get('response', ''))
                    break
                else:
                    full_response.append(response_data.get('response', ''))
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON line: {e}")
                print(f"Problematic line: {line}")
            except Exception as e:
                print(f"Unexpected error parsing line: {e}")
        
        final_response = ''.join(full_response).strip()
        cleaned_response = clean_response(final_response)
        print(f"Final response: {cleaned_response}")
        
        # Emit the response via Socket.IO
        socketio.emit('speak_text', {'text': cleaned_response})
        
        return jsonify({'status': 'success', 'message': cleaned_response}), 200
        
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Request error: {str(e)}'}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/get_model', methods=['GET'])
def getModel():
    avatar_model_path = "models/shizuku/shizuku.model.json"
    if (avatar_model_path ==  "shizuku"):
        avatar_model_path = "models/shizuku/shizuku.model.json"
    return avatar_model_path

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

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)



# Main entry point
if __name__ == '__main__': 
    try: 
        print(f"\n🔥 Starting server at  {API_URL}:{API_URL_PORT}...") 
        socketio.run(app, host=SOCKETIO_IP, port=SOCKETIO_IP_PORT) 
    except Exception as e: 
        print(f"Error starting server: {e}")

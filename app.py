"""Flask application for AI-powered Live2D avatar with Twitch integration.

This module provides a web server that manages a Live2D avatar, processes AI responses
through Ollama, and handles Twitch chat interactions with WebSocket communication.
"""

import os
import re
import socket
import eventlet
import bleach
from flask import Flask, render_template, send_from_directory, request, jsonify, abort
from flask_socketio import SocketIO
from dotenv import load_dotenv, find_dotenv
import ollama

# Monkey patching for eventlet compatibility
eventlet.monkey_patch(thread=True, os=True, select=True, socket=True)

# Load default .env file
dotenv_path = find_dotenv()
if not dotenv_path:
    dotenv_path = find_dotenv('.env.example')
load_dotenv(dotenv_path, encoding='latin1')

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
SOCKETIO_CORS_ALLOWED = os.getenv("SOCKETIO_CORS_ALLOWED")

# CURRENT SERVER CFG
API_URL = os.getenv("API_URL")
API_URL_PORT = os.getenv("API_URL_PORT")

AVATAR_MODEL = os.getenv("AVATAR_MODEL")

# Configure SocketIO with CORS and async mode
socketio = SocketIO(app, cors_allowed_origins=SOCKETIO_CORS_ALLOWED, async_mode='eventlet')

class Config:
    """Configuration class to manage environment variables."""
    def __init__(self):
        self.persona_name = os.getenv("PERSONA_NAME")
        self.persona_role = os.getenv("PERSONA_ROLE")
        self.pre_prompt = os.getenv("PRE_PROMPT")
        self.ollama_model = os.getenv("OLLAMA_MODEL")
        self.avatar_model = os.getenv("AVATAR_MODEL")
        self.background_image = os.getenv("BACKGROUND_IMAGE")

    def update(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key.lower()):
                setattr(self, key.lower(), value)
        if 'background_image' in kwargs:
            self.background_image = kwargs['background_image']

config = Config()

@app.route('/')
def home():
    """Render the main avatar interface page."""
    return render_template('avatar.html')

@app.route('/trigger_speak', methods=['POST'])
def trigger_speak():
    """Emit text to the frontend for speech synthesis via WebSocket."""
    data = request.get_json()
    text = data.get('text', '').strip()

    if text:
        socketio.emit('speak_text', {'text': text})
        return jsonify({'status': 'success', 'message': 'Text sent to speak'}, 200)
    return jsonify({'status': 'error', 'message': 'No text provided'}, 400)

@app.route('/trigger_ai_request', methods=['POST'])
def trigger_ai_request():
    """Handle AI request processing and response emission."""
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
    except (ValueError, KeyError) as e:
        return jsonify({'status': 'error', 'message': f'Invalid request format: {str(e)}'}), 400
    except ollama.ResponseError as e:
        return jsonify({'status': 'error', 'message': f'AI processing error: {str(e)}'}), 500
    except (ConnectionError, TimeoutError) as e:
        return jsonify({'status': 'error', 'message': f'Service connection error: {str(e)}'}), 503

@app.route('/get_model', methods=['GET'])
def get_model():
    """Get the path to the Live2D model file."""
    avatar_model_path = "models/shizuku/shizuku.model.json"
    if avatar_model_path == "shizuku":
        avatar_model_path = "models/shizuku/shizuku.model.json"
    return avatar_model_path

@app.route('/get_ollama_models', methods=['GET'])
def get_ollama_models():
    """Retrieve list of available Ollama models."""
    try:
        response = ollama.list()
        models = response.models
        model_names = [model.model for model in models]
        return jsonify({'status': 'success', 'models': model_names}), 200
    except (ollama.ResponseError, ConnectionError) as e:
        return jsonify({'status': 'error', 'message': f'Ollama service error: {str(e)}'}), 500
    except AttributeError as e:
        return jsonify({'status': 'error', 'message': f'Invalid response format: {str(e)}'}), 500

@app.route('/trigger_event', methods=['POST'])
def trigger_event():
    """Handle POST requests for triggering celebration events."""
    data = request.get_json()
    event_type = data.get('event_type', '').strip()
    username = data.get('username', '').strip()

    if event_type and username:
        emit_celebration_event(event_type, username)
        response = {
            'status': 'success',
            'message': f'{event_type} event triggered for {username}'
        }
        return jsonify(response), 200
    return jsonify({'status': 'error', 'message': 'Invalid event data'}), 400

@app.route('/get_background_images', methods=['GET'])
def get_background_images():
    """Retrieve list of available background images."""
    images_dir = os.path.join(app.root_path, 'static', 'images', 'background')
    try:
        images = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
        return jsonify({'status': 'success', 'images': images}), 200
    except (OSError, IOError) as e:
        return jsonify({'status': 'error', 'message': f'Error accessing images: {str(e)}'}), 500

@app.route('/get_avatar_models', methods=['GET'])
def get_avatar_models():
    """Retrieve list of available avatar models."""
    models_dir = os.path.join(app.root_path, 'models')
    try:
        models = [f for f in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, f))]
        return jsonify({'status': 'success', 'models': models}), 200
    except (OSError, IOError) as e:
        return jsonify({'status': 'error', 'message': f'Error accessing models: {str(e)}'}), 500

@socketio.on('trigger_event')
def handle_trigger_event(data):
    """Handle WebSocket events for triggering celebrations."""
    event_type = data.get('event_type', '').strip()
    username = data.get('username', '').strip()
    if event_type and username:
        emit_celebration_event(event_type, username)
        response = {
            'status': 'success',
            'message': f'{event_type} event triggered for {username}'
        }
        socketio.emit('event_response', response)
    else:
        socketio.emit('event_response', {
            'status': 'error',
            'message': 'Invalid event data'
        })

def emit_celebration_event(event_type, username):
    """Emit celebration events to the frontend based on event type.

    Args:
        event_type (str): Type of event ('follow' or 'sub')
        username (str): Username of the follower/subscriber
    """
    message = ""
    if event_type == 'follow':
        message = f"New FOLLOW: {username}"
    elif event_type == 'sub':
        message = f"NEW SUB: {username}"
    if message:
        socketio.emit('fireworks', {'message': message})

def process_ai_request(user_input):
    """Process user input through Ollama AI and return formatted response.

    Args:
        user_input (str): The user's message to process

    Returns:
        tuple: (response_dict, status_code)
    """
    if not user_input:
        return {'status': 'error', 'message': 'No message provided'}, 400

    if not config.ollama_model:
        return {'status': 'error', 'message': 'Missing OLLAMA configuration'}, 500

    # Sanitize the user input
    sanitized_input = bleach.clean(user_input)

    # Create a structured prompt
    structured_prompt = f"""
    Persona:
    Name: {config.persona_name}
    Role: {config.persona_role}

    Instructions:
    {config.pre_prompt}

    User: {sanitized_input}
    """

    try:
        messages = [{
            "role": "user",
            "content": structured_prompt.strip()
        }]
        response = ollama.chat(
            model=config.ollama_model,
            messages=messages
        )
        final_response = response['message']['content'].strip()
        cleaned_response = clean_response(final_response)
        return {'status': 'success', 'message': cleaned_response}, 200
    except (ollama.ResponseError, ConnectionError) as e:
        return {'status': 'error', 'message': f'AI service error: {str(e)}'}, 500
    except (KeyError, ValueError) as e:
        return {'status': 'error', 'message': f'Response format error: {str(e)}'}, 500

def clean_response(response):
    """Clean and format the AI response text.

    Args:
        response (str): Raw response text from AI

    Returns:
        str: Cleaned response with removed tags and normalized whitespace
    """
    response = re.sub(r'<think>\s*.*?\s*</think>', '', response, flags=re.DOTALL)
    response = re.sub(r'[^\x00-\x7F]+', '', response)
    response = re.sub(r'\\_\\_\\_', '', response)
    response = re.sub(r'\s+', ' ', response).strip()
    return response

@socketio.on('load_config')
def handle_load_config():
    """Load and emit current configuration values from environment variables.

    Reloads the .env file and sends all configuration values to the client.
    """
    try:
        # Reload the .env file to get the most recent values
        load_dotenv(override=True, encoding='latin1')
        env_config = {
            'PERSONA_NAME': os.getenv('PERSONA_NAME', ''),
            'PERSONA_ROLE': os.getenv('PERSONA_ROLE', ''),
            'PRE_PROMPT': os.getenv('PRE_PROMPT', ''),
            'AVATAR_MODEL': os.getenv('AVATAR_MODEL', ''),
            'CHANNEL_NAME': os.getenv('CHANNEL_NAME', ''),
            'TOKEN': os.getenv('TOKEN', ''),
            'CLIENT_ID': os.getenv('CLIENT_ID', ''),
            'EXTRA_DELAY_LISTENER': os.getenv('EXTRA_DELAY_LISTENER', ''),
            'NB_SPAM_MESSAGE': os.getenv('NB_SPAM_MESSAGE', ''),
            'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL', ''),
            'BOT_NAME_FOLLOW_SUB': os.getenv('BOT_NAME_FOLLOW_SUB', ''),
            'KEY_WORD_FOLLOW': os.getenv('KEY_WORD_FOLLOW', ''),
            'KEY_WORD_SUB': os.getenv('KEY_WORD_SUB', ''),
            'DELIMITER_NAME': os.getenv('DELIMITER_NAME', ''),
            'DELIMITER_NAME_END': os.getenv('DELIMITER_NAME_END', ''),
            'BACKGROUND_IMAGE': os.getenv('BACKGROUND_IMAGE', '')
        }
        print("Loaded config:", env_config)  # Debugging line
        socketio.emit('load_config', env_config)
    except (IOError, OSError) as e:
        error_msg = f'File operation error: {str(e)}'
        print(error_msg)  # Debugging line
        socketio.emit('load_config_error', {'status': 'error', 'message': error_msg})
    except (KeyError, ValueError) as e:
        error_msg = f'Configuration error: {str(e)}'
        print(error_msg)  # Debugging line
        socketio.emit('load_config_error', {'status': 'error', 'message': error_msg})

# Serve model files and resources (textures, expressions, motions, sounds)
@app.route('/models/<path:filename>')
def serve_model_files(filename):
    """Serve Live2D model files and resources from the models directory.

    Args:
        filename (str): Path to the requested model file
    """
    models_dir = os.path.join(app.root_path, 'models')
    if os.path.isfile(os.path.join(models_dir, filename)):
        return send_from_directory(models_dir, filename)
    return abort(404)

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket client connections."""
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnections."""
    print("Client disconnected")

@socketio.on('speak')
def handle_speak(data):
    """Handle text-to-speech requests via WebSocket."""
    text = data.get('text', '').strip()
    if text:
        socketio.emit('speak_text', {'text': text})

@socketio.on('request_model_path')
def handle_request_model_path():
    """Handle requests for Live2D model path and emit to client."""
    avatar_model_path = "models/shizuku/shizuku.model.json"
    socketio.emit('model_path', {'path': avatar_model_path})

@socketio.on('ask_ai')
def handle_ask_ai(data):
    """Process AI requests from WebSocket and emit response."""
    user_input = data.get('text', '').strip()
    response, status_code = process_ai_request(user_input)
    if status_code == 200:
        socketio.emit('ai_response', {'text': response['message']})

@socketio.on('display_question')
def handle_display_question(data):
    """Forward question display events to connected clients."""
    socketio.emit('display_question', data)

@socketio.on('trigger_ai_request')
def handle_trigger_ai_request(data):
    """Process AI requests and emit speech response."""
    try:
        user_input = data.get('message', '').strip()
        response, status_code = process_ai_request(user_input)
        if status_code == 200:
            socketio.emit('speak_text', {'text': response['message']})
    except (ollama.ResponseError, ConnectionError) as e:
        print(f"AI service error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data format error: {e}")

@socketio.on('save_config')
def handle_save_config(data):
    """Save configuration data to .env file and update twitch listener."""
    try:
        # Load existing .env values
        env_file_path = find_dotenv()
        load_dotenv(env_file_path, override=False, encoding='latin1')

        # Read existing .env file
        existing_env = {}
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='latin1') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        existing_env[key] = value.strip('"')

        # Update with new data
        for key, value in data.items():
            existing_env[key] = value

        # Write back to .env file
        with open(env_file_path, 'w', encoding='latin1') as f:
            for key, value in existing_env.items():
                if value is not None:
                    if ' ' in value:
                        value = f'"{value}"'
                    f.write(f"{key}={value}\n")
        print("Configuration saved to .env")

        # Forward relevant config updates to twitch listener
        twitch_config = {
            'EXTRA_DELAY_LISTENER': data.get('EXTRA_DELAY_LISTENER', ''),
            'NB_SPAM_MESSAGE': data.get('NB_SPAM_MESSAGE', ''),
            'BOT_NAME_FOLLOW_SUB': data.get('BOT_NAME_FOLLOW_SUB', ''),
            'KEY_WORD_FOLLOW': data.get('KEY_WORD_FOLLOW', ''),
            'KEY_WORD_SUB': data.get('KEY_WORD_SUB', ''),
            'DELIMITER_NAME': data.get('DELIMITER_NAME', ''),
            'DELIMITER_NAME_END': data.get('DELIMITER_NAME_END', '')
        }
        socketio.emit('update_twitch_config', twitch_config)

        # Emit the updated configuration back to the client
        socketio.emit('save_config_response', {'status': 'success', 'config': existing_env})

    except (IOError, OSError) as e:
        error_msg = f"File operation error: {str(e)}"
        print(error_msg)
        socketio.emit('save_config_response', {'status': 'error', 'message': error_msg})
    except (KeyError, ValueError) as e:
        error_msg = f"Data format error: {str(e)}"
        print(error_msg)
        socketio.emit('save_config_response', {'status': 'error', 'message': error_msg})

@socketio.on('update_live_global_env')
def handle_update_live_global_env(data):
    """Update global environment variables with new configuration values.

    Handles real-time updates to persona, model, and bot settings without server restart.
    """
    try:
        config.update(
            persona_name = data.get('personaName', '').strip(),
            persona_role = data.get('personaRole', '').strip(),
            pre_prompt = data.get('prePrompt', '').strip(),
            ollama_model = data.get('ollamaModel', '').strip(),
            avatar_model = data.get('avatarModel', '').strip(),
            background_image = data.get('backgroundImage', '').strip()
        )
        socketio.emit('update_live_global_env_response',
                     {'status': 'success', 'message': 'Persona updated successfully'})
    except (KeyError, ValueError) as e:
        socketio.emit('update_live_global_env_response',
                     {'status': 'error', 'message': f'Data format error: {str(e)}'})
    except AttributeError as e:
        socketio.emit('update_live_global_env_response',
                     {'status': 'error', 'message': f'Variable access error: {str(e)}'})

@socketio.on('load_config')
def handle_load_config():
    """Load and emit current configuration values from environment variables.

    Reloads the .env file and sends all configuration values to the client.
    """
    try:
        # Reload the .env file to get the most recent values
        load_dotenv(override=True, encoding='latin1')
        env_config = {
            'PERSONA_NAME': os.getenv('PERSONA_NAME', ''),
            'PERSONA_ROLE': os.getenv('PERSONA_ROLE', ''),
            'PRE_PROMPT': os.getenv('PRE_PROMPT', ''),
            'AVATAR_MODEL': os.getenv('AVATAR_MODEL', ''),
            'CHANNEL_NAME': os.getenv('CHANNEL_NAME', ''),
            'TOKEN': os.getenv('TOKEN', ''),
            'CLIENT_ID': os.getenv('CLIENT_ID', ''),
            'EXTRA_DELAY_LISTENER': os.getenv('EXTRA_DELAY_LISTENER', ''),
            'NB_SPAM_MESSAGE': os.getenv('NB_SPAM_MESSAGE', ''),
            'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL', ''),
            'BOT_NAME_FOLLOW_SUB': os.getenv('BOT_NAME_FOLLOW_SUB', ''),
            'KEY_WORD_FOLLOW': os.getenv('KEY_WORD_FOLLOW', ''),
            'KEY_WORD_SUB': os.getenv('KEY_WORD_SUB', ''),
            'DELIMITER_NAME': os.getenv('DELIMITER_NAME', ''),
            'DELIMITER_NAME_END': os.getenv('DELIMITER_NAME_END', ''),
            'BACKGROUND_IMAGE': os.getenv('BACKGROUND_IMAGE', '')
        }
        socketio.emit('load_config', env_config)
    except (IOError, OSError) as e:
        socketio.emit('load_config_error',
                     {'status': 'error', 'message': f'File operation error: {str(e)}'})
    except (KeyError, ValueError) as e:
        socketio.emit('load_config_error',
                     {'status': 'error', 'message': f'Configuration error: {str(e)}'})

@socketio.on('update_twitch_listener')
def handle_update_twitch_listener(data):
    """Update Twitch listener configuration values in real-time.

    Handles real-time updates to twitch listener settings without restart.
    """
    try:
        # Forward the configuration update to the twitch listener
        socketio.emit('update_twitch_config', {
            'EXTRA_DELAY_LISTENER': data.get('extraDelayListener', ''),
            'NB_SPAM_MESSAGE': data.get('nbSpamMessage', ''),
            'BOT_NAME_FOLLOW_SUB': data.get('botNameFollowSub', ''),
            'KEY_WORD_FOLLOW': data.get('keyWordFollow', ''),
            'KEY_WORD_SUB': data.get('keyWordSub', ''),
            'DELIMITER_NAME': data.get('delimiterName', ''),
            'DELIMITER_NAME_END': data.get('delimiterNameEnd', '')
        })
        socketio.emit('update_twitch_listener_response',
                     {'status': 'success', 'message': 'Twitch listener updated successfully'})
    except (KeyError, ValueError) as e:
        socketio.emit('update_twitch_listener_response',
                     {'status': 'error', 'message': f'Data format error: {str(e)}'})
    except (ConnectionError, TimeoutError) as e:
        socketio.emit('update_twitch_listener_response',
                     {'status': 'error', 'message': f'Socket connection error: {str(e)}'})

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files (CSS, JS, images, sounds) from the static directory.

    Args:
        filename (str): Path to the requested static file within the static directory
    """
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

# Main entry point
if __name__ == '__main__':
    try:
        print(f"\n🔥 Starting server at {API_URL}:{API_URL_PORT}...")
        socketio.run(app, host=SOCKETIO_IP, port=SOCKETIO_IP_PORT)
    except (OSError, socket.error) as e:
        print(f"Network error starting server: {e}")
    except ValueError as e:
        print(f"Configuration error starting server: {e}")
    except RuntimeError as e:
        print(f"Server runtime error: {e}")

"""Flask application for AI-powered Live2D avatar with Twitch integration.

This module provides a web server that manages a Live2D avatar, processes AI responses
through Ollama, and handles Twitch chat interactions with WebSocket communication.
"""

import os
import re
import socket
import eventlet
import bleach
import subprocess
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
        self.channel_name = os.getenv("CHANNEL_NAME")
        self.twitch_token = os.getenv("TWITCH_TOKEN")
        self.client_id = os.getenv("CLIENT_ID")
        self.extra_delay_listener = os.getenv("EXTRA_DELAY_LISTENER")
        self.nb_spam_message = os.getenv("NB_SPAM_MESSAGE")
        self.bot_name_follow_sub = os.getenv("BOT_NAME_FOLLOW_SUB")
        self.key_word_follow = os.getenv("KEY_WORD_FOLLOW")
        self.key_word_sub = os.getenv("KEY_WORD_SUB")
        self.delimiter_name = os.getenv("DELIMITER_NAME")
        self.delimiter_name_end = os.getenv("DELIMITER_NAME_END")

    def update(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key.lower()):
                setattr(self, key.lower(), value)
        # if 'background_image' in kwargs:
        #     self.background_image = kwargs['background_image']

config = Config()

listener_process = None

@app.route('/')
def home():
    """Render the main avatar interface page."""
    return render_template('avatar.html')

# Modify existing functions to return only the data, not the full response
def get_avatar_models():
    models_dir = os.path.join(app.root_path, 'models')
    try:
        return {'models': [f for f in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, f))]}
    except (OSError, IOError) as e:
        return {'models': [], 'error': str(e)}

def get_background_images():
    images_dir = os.path.join(app.root_path, 'static', 'images', 'background')
    try:
        return {'images': [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]}
    except (OSError, IOError) as e:
        return {'images': [], 'error': str(e)}

def get_ollama_models():
    try:
        response = ollama.list()
        return {'models': [model['model'] for model in response['models']]}
    except Exception as e:
        return {'models': [], 'error': str(e)}

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
        
        config.update(**data)
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

@socketio.on('get_listener_status')
def handle_get_listener_status():
    status = 'running' if listener_process is not None and listener_process.poll() is None else 'stopped'
    socketio.emit('listener_status', {'status': status})

@socketio.on('start_listener')
def handle_start_listener():
    global listener_process
    if listener_process is None:
        # Start the listener process
        listener_dir = os.path.join(app.root_path, 'listener')
        venv_python = os.path.join(app.root_path, 'venv', 'Scripts', 'python.exe')
        if not os.path.isdir(listener_dir):
            socketio.emit('listener_update', {'status': 'error', 'action': 'start', 'message': 'Listener directory does not exist'})
            return
        listener_process = subprocess.Popen([venv_python, 'twitch_listener.py'], cwd=listener_dir)
        socketio.emit('listener_update', {'status': 'success', 'action': 'start'})
    else:
        socketio.emit('listener_update', {'status': 'error', 'action': 'start', 'message': 'Listener already running'})

@socketio.on('stop_listener')
def handle_stop_listener():
    global listener_process
    if listener_process is not None:
        listener_process.terminate()
        listener_process = None
        socketio.emit('listener_update', {'status': 'success', 'action': 'stop'})
    else:
        socketio.emit('listener_update', {'status': 'error', 'action': 'stop', 'message': 'Listener not running'})

@socketio.on('get_init_cfg')
def handle_get_init_cfg():
    """Handle WebSocket request for initial configuration data."""
    print(config.avatar_model)
    try:
        configObj = {
            'PERSONA_NAME': config.persona_name,
            'PERSONA_ROLE': config.persona_role,
            'PRE_PROMPT': config.pre_prompt,
            'AVATAR_MODEL': config.avatar_model,
            'CHANNEL_NAME': config.channel_name,
            'TWITCH_TOKEN': config.twitch_token,
            'CLIENT_ID': config.client_id,
            'EXTRA_DELAY_LISTENER': config.extra_delay_listener,
            'NB_SPAM_MESSAGE': config.nb_spam_message,
            'OLLAMA_MODEL': config.ollama_model,
            'BOT_NAME_FOLLOW_SUB': config.bot_name_follow_sub,
            'KEY_WORD_FOLLOW': config.key_word_follow,
            'KEY_WORD_SUB': config.key_word_sub,
            'DELIMITER_NAME': config.delimiter_name,
            'DELIMITER_NAME_END': config.delimiter_name_end,
            'BACKGROUND_IMAGE': config.background_image
        }

        avatar_models = get_avatar_models()
        background_images = get_background_images()
        ollama_models = get_ollama_models()

        socketio.emit('init_cfg', {
            'status': 'success',
            'data': {
                'config': configObj,
                'avatarList': avatar_models.get('models', []),
                'backgroundList': background_images.get('images', []),
                'ollamaModelList': ollama_models.get('models', [])
            }
        })
    except Exception as e:
        socketio.emit('init_cfg', {'status': 'error', 'message': str(e)})

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files (CSS, JS, images, sounds) from the static directory.

    Args:
        filename (str): Path to the requested static file within the static directory
    """
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

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
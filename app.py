"""Flask application for AI-powered Live2D avatar with Twitch integration.

This module provides a web server that manages a Live2D avatar, processes AI responses
through Ollama, and handles Twitch chat interactions with WebSocket communication.
"""

import os
import re
import eventlet
import bleach
import subprocess
from flask import Flask, render_template, send_from_directory, abort
from flask_socketio import SocketIO
from dotenv import load_dotenv, find_dotenv
import ollama
import logging
from langdetect import detect

# Monkey patching for eventlet compatibility
eventlet.monkey_patch(thread=True, os=True, select=True)

# Load default .env file
dotenv_path = find_dotenv()
if not dotenv_path:
    dotenv_path = find_dotenv('.env.example')
load_dotenv(dotenv_path, encoding='latin1')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration class
class Config:
    def __init__(self):
        self.fields = [
            'PERSONA_NAME', 'PERSONA_ROLE', 'PRE_PROMPT', 'AVATAR_MODEL', 'BACKGROUND_IMAGE',
            'CHANNEL_NAME', 'TWITCH_TOKEN', 'CLIENT_ID', 'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE',
            'OLLAMA_MODEL', 'BOT_NAME_FOLLOW_SUB', 'KEY_WORD_FOLLOW', 'KEY_WORD_SUB',
            'DELIMITER_NAME', 'DELIMITER_NAME_END', 'SOCKETIO_IP', 'SOCKETIO_IP_PORT',
            'SOCKETIO_CORS_ALLOWED', 'API_URL', 'API_URL_PORT', 'FIXED_LANGUAGE', 'VOICE_GENDER',
            'WAKE_WORD', 'WAKE_WORD_ENABLED', 'CELEBRATE_FOLLOW', 'CELEBRATE_SUB'
        ]
        self.load()

    def load(self):
        for field in self.fields:
            setattr(self, field.lower(), os.getenv(field))

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key.upper() in self.fields:
                setattr(self, key.lower(), value)
        self.save()

    def save(self):
        env_file_path = find_dotenv()
        with open(env_file_path, 'w', encoding='latin1') as f:
            for field in self.fields:
                value = getattr(self, field.lower())
                if value is not None:
                    f.write(f"{field}={value}\n")

    def to_dict(self):
        return {field: getattr(self, field.lower()) for field in self.fields}

config = Config()

# SocketIO setup
socketio = SocketIO(app, cors_allowed_origins=config.socketio_cors_allowed, async_mode='eventlet')

listener_process = None

# Route handlers
@app.route('/')
def home():
    return render_template('avatar.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

@app.route('/models/<path:filename>')
def serve_model_files(filename):
    models_dir = os.path.join(app.root_path, 'models')
    if os.path.isfile(os.path.join(models_dir, filename)):
        return send_from_directory(models_dir, filename)
    return abort(404)

# Helper functions
def get_directory_contents(directory):
    try:
        return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
    except OSError as e:
        logger.error(f"Error accessing directory {directory}: {e}")
        return []

def get_file_contents(directory):
    try:
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    except OSError as e:
        logger.error(f"Error accessing directory {directory}: {e}")
        return []

def get_avatar_models():
    return {'models': get_directory_contents(os.path.join(app.root_path, 'models'))}

def get_background_images():
    return {'images': get_file_contents(os.path.join(app.root_path, 'static', 'images', 'background'))}

def get_ollama_models():
    try:
        response = ollama.list()
        return {'models': [model['model'] for model in response['models']]}
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return {'models': []}

def process_ai_request(data):
    text = data.get('text', '').strip()
    source = data.get('source', 'twitch')
    fixed_language = data.get('fixedLanguage')

    if not text:
        return {'status': 'error', 'message': 'No text provided'}, 400

    sanitized_input = bleach.clean(text)
    
    # Detect input language or use fixed language for microphone input
    if source == 'microphone' and fixed_language:
        detected_language = fixed_language
    else:
        try:
            detected_language = detect(sanitized_input)
        except:
            detected_language = 'en'
    
    print(f"Using language: {detected_language}")

    # Build language-specific prompt
    language_instruction = f"Please respond in {detected_language} language. "

    structured_prompt = f"""
    Persona:
    Name: {config.persona_name}
    Role: {config.persona_role}

    Instructions:
    {language_instruction}{config.pre_prompt}

    User: {sanitized_input}
    """

    try:
        response = ollama.chat(
            model=config.ollama_model, 
            messages=[{"role": "user", "content": structured_prompt.strip()}]
        )
        
        cleaned_response = re.sub(
            r'<think>.*?</think>|\s+', 
            ' ', 
            response['message']['content'], 
            flags=re.DOTALL
        ).strip()

        # Detect language of the response
        try:
            response_language = detect(cleaned_response)
        except:
            response_language = detected_language
        print(f"response_language: {response_language}")
        return {
            'status': 'success',
            'message': cleaned_response,
            'language': response_language
        }, 200

    except Exception as e:
        logger.error(f"AI processing error: {e}")
        return {'status': 'error', 'message': f'AI service error: {str(e)}'}, 500

def emit_celebration_event(event_type, username):
    """Emit celebration events to the frontend based on event type."""
    message = ""
    # Convert string 'true'/'false' to boolean or handle direct boolean values
    celebrate_follow = str(config.celebrate_follow).lower() == 'true'
    celebrate_sub = str(config.celebrate_sub).lower() == 'true'
    
    if event_type == 'follow' and celebrate_follow:
        message = f"New FOLLOW: {username}"
    elif event_type == 'sub' and celebrate_sub:
        message = f"NEW SUB: {username}"
        
    if message:
        socketio.emit('fireworks', {'message': message})

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected")

@socketio.on('speak')
def handle_speak(data):
    text = data.get('text', '').strip()
    if text:
        try:
            # Detect language of the text to speak
            detected_language = detect(text)
        except:
            detected_language = 'en'

        print(f"detected_language: {detected_language}")

        socketio.emit('speak_text', {
            'text': text,
            'fixedLanguage': detected_language  # Use detected language instead of passed language
        })

@socketio.on('ask_ai')
def handle_ask_ai(data):
    response, status_code = process_ai_request(data)
    if status_code == 200:
        socketio.emit('ai_response', {
            'text': response['message'],
            'fixedLanguage': response['language']
        })

@socketio.on('save_config')
def handle_save_config(data):
    try:
        config.update(**data)
        socketio.emit('update_twitch_config', {k: v for k, v in data.items() if k in [
            'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE', 'BOT_NAME_FOLLOW_SUB',
            'KEY_WORD_FOLLOW', 'KEY_WORD_SUB', 'DELIMITER_NAME', 'DELIMITER_NAME_END'
        ]})
        socketio.emit('save_config_response', {'status': 'success', 'config': config.to_dict()})
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        socketio.emit('save_config_response', {'status': 'error', 'message': str(e)})

@socketio.on('get_init_cfg')
def handle_get_init_cfg():
    try:
        socketio.emit('init_cfg', {
            'status': 'success',
            'data': {
                'config': config.to_dict(),
                'avatarList': get_avatar_models().get('models', []),
                'backgroundList': get_background_images().get('images', []),
                'ollamaModelList': get_ollama_models().get('models', [])
            }
        })
    except Exception as e:
        logger.error(f"Error getting initial configuration: {e}")
        socketio.emit('init_cfg', {'status': 'error', 'message': str(e)})

@socketio.on('get_listener_status')
def handle_get_listener_status():
    status = 'running' if listener_process and listener_process.poll() is None else 'stopped'
    socketio.emit('listener_status', {'status': status})

@socketio.on('start_listener')
def handle_start_listener():
    global listener_process
    if not listener_process:
        try:
            listener_dir = os.path.join(app.root_path, 'listener')
            venv_python = os.path.join(app.root_path, 'venv', 'Scripts', 'python.exe')
            listener_process = subprocess.Popen([venv_python, 'twitch_listener.py'], cwd=listener_dir)
            socketio.emit('listener_update', {'status': 'success', 'action': 'start'})
        except Exception as e:
            logger.error(f"Error starting listener: {e}")
            socketio.emit('listener_update', {'status': 'error', 'action': 'start', 'message': str(e)})
    else:
        socketio.emit('listener_update', {'status': 'error', 'action': 'start', 'message': 'Listener already running'})

@socketio.on('stop_listener')
def handle_stop_listener():
    global listener_process
    if listener_process:
        listener_process.terminate()
        listener_process = None
        socketio.emit('listener_update', {'status': 'success', 'action': 'stop'})
    else:
        socketio.emit('listener_update', {'status': 'error', 'action': 'stop', 'message': 'Listener not running'})

@socketio.on('trigger_event')
def handle_trigger_event(data):
    """Handle WebSocket events for triggering celebrations."""
    event_type = data.get('event_type', '').strip()
    username = data.get('username', '').strip()
    if event_type and username:
        emit_celebration_event(event_type, username)
        socketio.emit('event_response', {
            'status': 'success',
            'message': f'{event_type} event triggered for {username}'
        })
    else:
        socketio.emit('event_response', {
            'status': 'error',
            'message': 'Invalid event data'
        })

@socketio.on('trigger_ai_request')
def handle_trigger_ai_request(data):
    """Process AI requests from Twitch and emit speech response."""
    try:
        response, status_code = process_ai_request({
            'text': data.get('message', '').strip(),
            'source': 'twitch'
        })
        if status_code == 200:
            socketio.emit('speak_text', {
                'text': response['message'],
                'fixedLanguage': response['language']
            })
    except Exception as e:
        logger.error(f"AI request error: {e}")
        socketio.emit('ai_response_error', {'message': str(e)})

@socketio.on('display_question')
def handle_display_question(data):
    """Forward question display events to connected clients."""
    socketio.emit('display_question', data)

# Main entry point
if __name__ == '__main__':
    try:
        logger.info(f"Starting server at {config.api_url}:{config.api_url_port}")
        socketio.run(app, host=config.socketio_ip, port=int(config.socketio_ip_port))
    except Exception as e:
        logger.error(f"Error starting server: {e}")
import eventlet
eventlet.monkey_patch(thread=True, os=True, select=True, socket=True)

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
import os
import logging

# Force verbose logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configure CORS properly for production
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,          # Enable Socket.IO logs
    engineio_logger=True  # Enable Engine.IO logs
)

# Unified model serving route using blueprint-like structure
MODEL_BASE = 'model/shizuku'

@app.route('/')
def home():
    return render_template('avatar.html')

@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.route(f'/{MODEL_BASE}/<path:filename>')
def serve_model_files(filename):
    logger.debug(f"Serving model file: {filename}")
    try:
        return send_from_directory(MODEL_BASE, filename)
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        abort(404)

@app.route(f'/{MODEL_BASE}/shizuku1024/<path:filename>')
def serve_textures(filename):
    return send_from_directory(f'{MODEL_BASE}/shizuku1024', filename)

@app.route(f'/{MODEL_BASE}/expressions/<path:filename>')
def serve_expressions(filename):
    return send_from_directory(f'{MODEL_BASE}/expressions', filename)

@app.route(f'/{MODEL_BASE}/motions/<path:filename>')
def serve_motions(filename):
    return send_from_directory(f'{MODEL_BASE}/motions', filename)

@app.route(f'/{MODEL_BASE}/sounds/<path:filename>')
def serve_sounds(filename):
    return send_from_directory(f'{MODEL_BASE}/sounds', filename)

# SOCKET IO BAS
@socketio.on('connect')
def handle_connect():
    logger.debug("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.debug("Client disconnected")

@socketio.on('speak')
def handle_speak(data):
    text = data.get('text', '').strip()
    if text:
        socketio.emit('speak_text', {'text': text})

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

if __name__ == '__main__':
    try:
        logger.debug("\n🔥 Starting server...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
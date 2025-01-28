import os
import eventlet
from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO

# Monkey patching for eventlet compatibility
eventlet.monkey_patch(thread=True, os=True, select=True, socket=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configure SocketIO with CORS and async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Model base path
MODEL_BASE = 'model/shizuku'

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

# Serve model files and resources (textures, expressions, motions, sounds)
@app.route(f'/{MODEL_BASE}/<path:filename>')
def serve_model_files(filename):
    return send_from_directory(MODEL_BASE, filename)

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

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

# Main entry point
if __name__ == '__main__':
    try:
        print("\n🔥 Starting server...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting server: {e}")

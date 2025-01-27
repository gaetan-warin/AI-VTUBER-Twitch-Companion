from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import eventlet

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def home():
    return render_template('avatar.html')

@app.route('/speak', methods=['POST'])
def speak():
    data = request.get_json()
    if 'text' not in data:
        return jsonify({"error": "Missing 'text' field"}), 400
    socketio.emit('speak_text', {'text': data['text']})
    return jsonify({"message": "Text sent to avatar"}), 200

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    socketio.run(app, debug=True)

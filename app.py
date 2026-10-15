from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room
import datetime
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# מילון ניהול שחקנים בעולם ה-3D
connected_players = {}

@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "error": "חובה להזין שם משתמש"}), 400
    
    return jsonify({"success": True, "username": username})

@socketio.on('join_game')
def on_join(data):
    username = data.get('username')
    connected_players[request.sid] = {
        "username": username,
        "x": 0,
        "y": 1,
        "z": 0,
        "color": "#38bdf8"
    }
    socketio.emit('update_players', connected_players)

@socketio.on('player_move')
def on_move(data):
    if request.sid in connected_players:
        connected_players[request.sid]["x"] = data.get("x", 0)
        connected_players[request.sid]["y"] = data.get("y", 1)
        connected_players[request.sid]["z"] = data.get("z", 0)
        socketio.emit('update_players', connected_players)

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in connected_players:
        del connected_players[request.sid]
        socketio.emit('update_players', connected_players)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

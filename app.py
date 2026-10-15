from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room
import datetime
import os
import random
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_players = {}
bots = {}

def init_bots():
    for i in range(1, 4):
        bot_id = f"bot_{i}"
        bots[bot_id] = {
            "username": f"בוט מחבל #{i}",
            "team": "terrorist",
            "x": random.randint(-15, 15),
            "y": 0,
            "z": random.randint(-25, -5),
            "rot": 0,
            "health": 100,
            "weapon": "AK47"
        }

init_bots()

def bot_ai_loop():
    while True:
        time.sleep(0.05)
        for bot_id, b in bots.items():
            b["rot"] += random.choice([-0.05, 0.05, 0])
        socketio.emit('update_game_state', {"players": connected_players, "bots": bots})

threading.Thread(target=bot_ai_loop, daemon=True).start()

@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    team = data.get('team', 'idf')
    weapon = data.get('weapon', 'M16')

    if not username:
        return jsonify({"success": False, "error": "חובה להזין שם לוחם"}), 400
    
    return jsonify({"success": True, "username": username, "team": team, "weapon": weapon})

@socketio.on('join_game')
def on_join(data):
    username = data.get('username')
    team = data.get('team', 'idf')
    weapon = data.get('weapon', 'M16')

    connected_players[request.sid] = {
        "username": username,
        "team": team,
        "weapon": weapon,
        "x": random.randint(-5, 5),
        "y": 0,
        "z": 5,
        "rot": 0,
        "health": 100,
        "score": 0
    }
    socketio.emit('update_game_state', {"players": connected_players, "bots": bots})

@socketio.on('player_move')
def on_move(data):
    if request.sid in connected_players:
        connected_players[request.sid]["x"] = data.get("x", 0)
        connected_players[request.sid]["y"] = data.get("y", 0)
        connected_players[request.sid]["z"] = data.get("z", 0)
        connected_players[request.sid]["rot"] = data.get("rot", 0)
        socketio.emit('update_game_state', {"players": connected_players, "bots": bots})

@socketio.on('player_shoot')
def on_shoot(data):
    target_id = data.get('target_id')
    if target_id in bots:
        bots[target_id]["health"] -= 34
        if bots[target_id]["health"] <= 0:
            bots[target_id]["x"] = random.randint(-20, 20)
            bots[target_id]["z"] = random.randint(-25, -5)
            bots[target_id]["health"] = 100
            if request.sid in connected_players:
                connected_players[request.sid]["score"] += 1
        socketio.emit('update_game_state', {"players": connected_players, "bots": bots})

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in connected_players:
        del connected_players[request.sid]
        socketio.emit('update_game_state', {"players": connected_players, "bots": bots})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

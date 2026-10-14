from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room
import datetime
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

active_sessions = {
    "pc_avi": {
        "owner": "אבי",
        "status": "מחובר (Online)",
        "last_seen": "עכשיו",
        "files": {"welcome.txt": "היי, זה הקובץ של אבי.", "notes.txt": "רשימת משימות."},
        "last_activity": "התחבר למערכת"
    },
    "pc_shilo": {
        "owner": "שילו",
        "status": "מנותק (Offline)",
        "last_seen": "טרם התחבר",
        "files": {"hello.txt": "שלום משרת הבדיקה של שילו."},
        "last_activity": "נוצר מראש"
    }
}

admins_db = {
    "admin": "123"
}

@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username:
        return jsonify({"success": False, "error": "חובה להזין שם משתמש"}), 400

    if username in admins_db and admins_db[username] == password:
        return jsonify({"success": True, "role": "admin"})
    
    if username not in active_sessions:
        active_sessions[username] = {
            "owner": username,
            "status": "מחובר (Online)",
            "last_seen": datetime.datetime.now().strftime('%H:%M:%S'),
            "files": {"notes.txt": f"מסמך עבור {username}"},
            "last_activity": "התחבר למערכת"
        }
    else:
        active_sessions[username]["status"] = "מחובר (Online)"
        active_sessions[username]["last_seen"] = datetime.datetime.now().strftime('%H:%M:%S')

    socketio.emit('fleet_updated', active_sessions)
    return jsonify({"success": True, "role": "user", "pc_id": username})

@app.route('/api/admin/add_pc', methods=['POST'])
def add_pc():
    data = request.get_json()
    pc_id = data.get('pc_id', '').strip()
    if not pc_id:
        return jsonify({"success": False, "error": "שם מחשב ריק"})
    
    if pc_id in active_sessions:
        return jsonify({"success": False, "error": "המחשב כבר קיים"})

    active_sessions[pc_id] = {
        "owner": "לא משויך",
        "status": "מנותק (Offline)",
        "last_seen": "טרם התחבר",
        "files": {"config.txt": "הגדרות ראשוניות."},
        "last_activity": "נוצר מרחוק"
    }
    socketio.emit('fleet_updated', active_sessions)
    return jsonify({"success": True, "message": f"המחשב {pc_id} נוסף בהצלחה!"})

@app.route('/api/computer/<pc_id>', methods=['GET'])
def get_computer_data(pc_id):
    if pc_id in active_sessions:
        return jsonify(active_sessions[pc_id])
    return jsonify({"error": "המחשב אינו קיים"}), 404

@app.route('/api/computer/save', methods=['POST'])
def save_computer_file():
    data = request.get_json()
    pc_id = data.get('pc_id')
    filename = data.get('filename')
    content = data.get('content')

    if pc_id in active_sessions:
        active_sessions[pc_id]["files"][filename] = content
        active_sessions[pc_id]["last_activity"] = f"שמר את הקובץ: {filename}"
        active_sessions[pc_id]["last_seen"] = datetime.datetime.now().strftime('%H:%M:%S')
        
        # שליחת עדכון ספציפי אך ורק לחדר של אותו לקוח/מחשב
        socketio.emit('file_updated', {"pc_id": pc_id, "files": active_sessions[pc_id]["files"]}, room=pc_id)
        socketio.emit('fleet_updated', active_sessions)
        return jsonify({"success": True, "message": "הקובץ נשמר בהצלחה!"})
    
    return jsonify({"success": False, "error": "שגיאה בשמירה"}), 400

@app.route('/api/computer/command', methods=['POST'])
def run_command():
    data = request.get_json()
    pc_id = data.get('pc_id')
    command = data.get('command', '').strip()

    if pc_id not in active_sessions:
        return jsonify({"output": "שגיאה: מחשב לא נמצא"})

    pc = active_sessions[pc_id]
    output = ""
    cmd_lower = command.lower()

    if cmd_lower == 'help':
        output = "פקודות זמינות: help, date, ls, cat <filename>, clear"
    elif cmd_lower == 'date':
        output = str(datetime.datetime.now())
    elif cmd_lower == 'ls':
        output = "קבצים בדיסק:\n" + "\n".join([f" 📄 {f}" for f in pc["files"].keys()])
    elif cmd_lower.startswith('cat '):
        filename = command.split(' ', 1)[1].strip()
        if filename in pc["files"]:
            output = pc["files"][filename]
        else:
            output = f"שגיאה: הקובץ '{filename}' לא נמצא."
    else:
        output = f"הפקודה '{command}' בוצעה בהצלחה."

    pc["last_activity"] = f"הריץ פקודה: {command}"
    socketio.emit('fleet_updated', active_sessions)
    return jsonify({"output": output})

@app.route('/api/admin/all_computers', methods=['GET'])
def get_all_computers():
    return jsonify(active_sessions)

@socketio.on('join_pc_room')
def on_join(data):
    pc_id = data.get('pc_id')
    if pc_id:
        join_room(pc_id)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

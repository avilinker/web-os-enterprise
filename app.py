from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room
import datetime
import os
import random
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

active_sessions = {
    "pc_avi": {
        "owner": "אבי",
        "status": "מחובר (Online)",
        "last_seen": "עכשיו",
        "cpu": 24,
        "ram": 58,
        "files": {"welcome.txt": "היי, זה הקובץ של אבי.", "notes.txt": "רשימת משימות מערכת."},
        "processes": [
            {"pid": 101, "name": "python.exe", "cpu": 12, "memory": "45MB"},
            {"pid": 104, "name": "nginx_service", "cpu": 5, "memory": "22MB"}
        ],
        "command_history": ["help", "ls", "top"],
        "last_activity": "התחבר למערכת"
    },
    "pc_shilo": {
        "owner": "שילו",
        "status": "מנותק (Offline)",
        "last_seen": "טרם התחבר",
        "cpu": 0,
        "ram": 15,
        "files": {"hello.txt": "שלום משרת הבדיקה של שילו."},
        "processes": [
            {"pid": 201, "name": "systemd", "cpu": 1, "memory": "10MB"}
        ],
        "command_history": ["help"],
        "last_activity": "נוצר מראש"
    }
}

admins_db = {
    "admin": "123"
}

# מנוע רקע אוטומטי שמעדכן מדדים ומדמה תהליכים חיים בלייב לכל המחשבים
def background_fleet_simulator():
    while True:
        time.sleep(5)
        for pc_id, info in active_sessions.items():
            if info["status"].includes("Online") or info["status"].__contains__("מחובר"):
                info["cpu"] = random.randint(12, 88)
                info["ram"] = random.randint(25, 82)
        socketio.emit('fleet_updated', active_sessions)

threading.Thread(target=background_fleet_simulator, daemon=True).start()

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
            "cpu": random.randint(15, 45),
            "ram": random.randint(30, 70),
            "files": {"notes.txt": f"מסמך אישי עבור {username}"},
            "processes": [
                {"pid": random.randint(300, 900), "name": "user_shell.py", "cpu": random.randint(5, 20), "memory": "30MB"}
            ],
            "command_history": ["help"],
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
        "cpu": 0,
        "ram": 10,
        "files": {"config.txt": "הגדרות ראשוניות."},
        "processes": [],
        "command_history": [],
        "last_activity": "נוצר מרחוק"
    }
    socketio.emit('fleet_updated', active_sessions)
    return jsonify({"success": True, "message": f"המחשב {pc_id} נוסף בהצלחה!"})

@app.route('/api/computer/<pc_id>', methods=['GET'])
def get_computer_data(pc_id):
    if pc_id in active_sessions:
        return jsonify(active_sessions[pc_id])
    return jsonify({"error": "המחשב אינו קיים"}), 404

@app.route('/api/computer/kill_process', methods=['POST'])
def kill_process():
    data = request.get_json()
    pc_id = data.get('pc_id')
    pid = int(data.get('pid'))

    if pc_id in active_sessions:
        pc = active_sessions[pc_id]
        pc["processes"] = [p for p in pc["processes"] if p["pid"] != pid]
        pc["last_activity"] = f"חיסל תהליך PID: {pid}"
        socketio.emit('fleet_updated', active_sessions)
        socketio.emit('process_killed', {"pc_id": pc_id, "processes": pc["processes"]}, room=pc_id)
        return jsonify({"success": True, "message": f"התהליך {pid} חוסל בהצלחה"})
    return jsonify({"success": False, "error": "שגיאה"})

@app.route('/api/computer/command', methods=['POST'])
def run_command():
    data = request.get_json()
    pc_id = data.get('pc_id')
    command = data.get('command', '').strip()

    if pc_id not in active_sessions:
        return jsonify({"output": "שגיאה: מחשב לא נמצא"})

    pc = active_sessions[pc_id]
    pc["command_history"].append(command)
    output = ""
    cmd_lower = command.lower()

    if cmd_lower == 'help':
        output = "פקודות זמינות:\n - help: הצגת עזרה\n - date: תאריך ושעה\n - ls: הצגת קבצים\n - top: סיכום משאבים\n - ps: הצגת תהליכים רצים\n - clear: ניקוי מסך"
    elif cmd_lower == 'date':
        output = str(datetime.datetime.now())
    elif cmd_lower == 'ls':
        output = "קבצים בדיסק:\n" + "\n".join([f" 📄 {f}" for f in pc["files"].keys()])
    elif cmd_lower == 'top':
        output = f"CPU: {pc['cpu']}% | RAM: {pc['ram']}% | Active Processes: {len(pc['processes'])}"
    elif cmd_lower == 'ps':
        output = "PID\tNAME\t\tCPU\tMEM\n" + "\n".join([f"{p['pid']}\t{p['name']}\t{p['cpu']}%\t{p['memory']}" for p in pc["processes"]])
    elif cmd_lower.startswith('cat '):
        filename = command.split(' ', 1)[1].strip()
        if filename in pc["files"]:
            output = pc["files"][filename]
        else:
            output = f"שגיאה: הקובץ '{filename}' לא נמצא."
    else:
        output = f"הפקודה '{command}' בוצעה בהצלחה בסביבה המבודדת."

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

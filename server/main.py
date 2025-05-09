import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import uuid
import time
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

players = {}
pigeon_fund = 0
last_message_time = {}  # player_id -> timestamp

banned_words = [
    "nigger", "niga", "kike", "chink", "gook", "wetback", "spic",
    "faggot", "retard", "tranny", "coon", "towelhead", "camel jockey"
]
banned_regex = re.compile(r"|".join(rf"\b{re.escape(word)}\b" for word in banned_words), re.IGNORECASE)

@app.route('/ping', methods=['POST'])
def ping():
    data = request.get_json()
    player_id = data.get('player_id')

    if not player_id or player_id not in players:
        new_id = str(uuid.uuid4())
        players[new_id] = {"last_seen": time.time(), "spent_coins": 0}
    else:
        players[player_id]["last_seen"] = time.time()

    now = time.time()
    online_count = sum(1 for p in players.values() if now - p["last_seen"] <= 40)
    return jsonify(online_count), 200

@app.route('/updateSpentCoins', methods=['POST'])
def update_spent_coins():
    global pigeon_fund
    data = request.get_json()
    player_id = data.get('player_id')
    amount = data.get('amount')

    if not player_id or player_id not in players:
        return jsonify({"error": "Player not found"}), 400

    if amount is None or not isinstance(amount, int) or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    players[player_id]["spent_coins"] += amount
    pigeon_fund += amount

    return jsonify({
        "message": f"Spent {amount} coins",
        "spent_coins": players[player_id]["spent_coins"],
        "total_fund": pigeon_fund
    }), 200

@app.route('/getTotalFund', methods=['GET'])
def get_total_fund():
    return jsonify({"pigeon_fund": pigeon_fund}), 200

@socketio.on('send_message')
def handle_message(data):
    nickname = data.get('nickname', 'Anonymous')
    text = data.get('text', '')
    player_id = data.get('player_id', 'anon')

    now = time.time()

    # Антифлуд
    if player_id in last_message_time and now - last_message_time[player_id] < 5:
        emit('receive_message', {"nickname": "System", "text": "Slow down! Wait 5 seconds."}, room=request.sid)
        return

    # Фильтр токсик-контента
    if banned_regex.search(text):
        emit('receive_message', {"nickname": "System", "text": "Message blocked for inappropriate content."}, room=request.sid)
        return

    last_message_time[player_id] = now
    emit('receive_message', {"nickname": nickname, "text": text}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
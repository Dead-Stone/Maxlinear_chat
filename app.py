from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def handle_join_room_event(data):
    join_room(data['ticket'])

@socketio.on('send_message')
def handle_send_message_event(data):
    try:
        # Requesting response from backend
        response = requests.post('http://localhost:8000/send_message', json={'content': data['message']})
        print("response",response.json())
        if response.status_code == 200:
            bot_response = response.json()['response']
            print("bot_response",bot_response)
            timestamp = datetime.now().strftime("%d-%b, %H:%M")
            data['Date'] = timestamp
            
            # Emit user message first
            socketio.emit('receive_message', data, room=data['ticket'])
            print("data_receive_message_end",data)
            # Emit bot message separately
            bot_data = {
                'message': bot_response,
                'username': 'Astranetix',
                'ticket': data['ticket'],
                'Date': datetime.now().strftime("%d-%b, %H:%M")
            }
            print("bot_data",bot_data)
            socketio.emit('receive_message', bot_data, room=data['ticket'])
            print("bot_data123",bot_data)
        else:
            raise Exception('Non-200 response from backend')
    except Exception as e:
        print(f"Error: {e}")
        socketio.emit('error', {'message': 'Failed to send message'}, room=data['ticket'])


@app.route('/status')
def get_status():
    return jsonify({'status': 'Connected'})

@app.route('/data/<path:filename>')
def serve_pdf(filename):
    return send_from_directory('data', filename)

if __name__ == '__main__':
    socketio.run(app, debug=True)
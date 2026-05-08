from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from core.monitor import DrowsinessMonitor

app = Flask(__name__)
# Initialize SocketIO with gevent async mode for production
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

monitor = DrowsinessMonitor()

@app.route('/')
def index():
    """Render the main dashboard"""
    return render_template('index.html')

@socketio.on('connect')
def test_connect():
    print('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@socketio.on('process_frame')
def handle_frame(base64_image):
    """Receive frame from client, process it, and emit back annotated frame and stats"""
    annotated_frame, stats = monitor.process_client_frame(base64_image)
    if annotated_frame:
        emit('processed_result', {
            'image': annotated_frame,
            'stats': stats
        })

@app.route('/api/control', methods=['POST'])
def control():
    """API endpoint to start/stop the system and update settings"""
    data = request.json
    action = data.get('action')
    
    if action == 'start':
        monitor.start()
        return jsonify({"message": "System started"})
    elif action == 'stop':
        monitor.stop()
        return jsonify({"message": "System stopped"})
    elif action == 'reset':
        monitor.reset()
        return jsonify({"message": "Alarms and system reset"})
    elif action == 'update_settings':
        ear = data.get('ear_thresh')
        mar = data.get('mar_thresh')
        if ear and mar:
            monitor.update_settings(ear, mar)
            return jsonify({"message": "Settings updated"})
            
    return jsonify({"error": "Invalid action"}), 400

if __name__ == '__main__':
    # Use SocketIO run instead of app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)

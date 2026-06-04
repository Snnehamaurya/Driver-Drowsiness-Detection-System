from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from core.monitor import DrowsinessMonitor

app = Flask(__name__)
# Initialize SocketIO with gevent async mode for production
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

monitor = DrowsinessMonitor()

import os

# Email SMTP settings (Set these via environment variables, or edit placeholders here)
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'snnehamaurya123@gmail.com')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', 'xoynizwublylnhez') # Gmail App Password (16 chars)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))

def send_email_alert(recipient_email, subject, body):
    """Sends email alert via SMTP_SSL using configured sender credentials."""
    import smtplib
    from email.mime.text import MIMEText
    
    if SENDER_EMAIL == 'your_email@gmail.com' or SENDER_PASSWORD == 'your_app_password':
        print("[EMAIL WARNING] Email credentials not configured in app.py. Skipping email send.")
        return False
        
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL SUCCESS] Email alert successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {recipient_email}: {e}")
        return False

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

@app.route('/api/emergency', methods=['POST'])
def emergency_alert():
    """Endpoint triggered when the driver's eyes remain closed for more than 1 minute.
    Logs coordinates, maps link, and saved contact details, saving them to emergency logs.
    """
    import os
    import csv
    from datetime import datetime

    data = request.json or {}
    name = data.get('name', 'Unknown Family Contact')
    contact = data.get('contact', 'Unknown Contact Details')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    maps_link = data.get('maps_link')

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Output to the server logs
    print(f"\n========================================================")
    print(f"[EMERGENCY ALERT TRIGGERED - {timestamp}]")
    print(f"Driver has had eyes closed continuously for > 1 minute!")
    print(f"Dispatched location to: {name} ({contact})")
    if maps_link:
        print(f"Live Location URL: {maps_link} (Lat: {latitude}, Lon: {longitude})")
    else:
        print(f"Live Location URL: NOT AVAILABLE (Geolocation permission denied/timeout)")
    print(f"========================================================\n")

    # Save to a local CSV file for persistent logs
    log_dir = 'logs'
    log_file = os.path.join(log_dir, 'emergency_alerts.csv')
    
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_exists = os.path.isfile(log_file)
        with open(log_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Contact Name', 'Contact Info', 'Latitude', 'Longitude', 'Maps Link'])
            writer.writerow([timestamp, name, contact, latitude or 'N/A', longitude or 'N/A', maps_link or 'N/A'])
    except Exception as e:
        print(f"Error saving emergency log: {e}")

    # Send real email alert if recipient is an email address
    if '@' in contact:
        subject = f"Sentinel AI - EMERGENCY ALERT: Driver Unresponsive"
        body = (
            f"EMERGENCY WARNING\n\n"
            f"The Sentinel AI driver monitoring system has detected that the driver has been unresponsive "
            f"with eyes closed for more than 1 minute.\n\n"
            f"Driver live location URL: {maps_link or 'UNAVAILABLE (geolocation permission denied)'}\n"
            f"GPS Coordinates: Latitude {latitude or 'N/A'}, Longitude {longitude or 'N/A'}\n"
            f"Timestamp: {timestamp}\n\n"
            f"Please check on them immediately."
        )
        send_email_alert(contact, subject, body)
    else:
        print(f"[EMAIL INFO] Contact '{contact}' is not a valid email address. Skipping email alert transmission.")

    # =========================================================================
    # TWILIO SMS / SMTP EMAIL INTEGRATION GUIDE FOR PRODUCTION DEPLOYMENT
    # =========================================================================
    # A developer can easily trigger a real SMS alert using Twilio:
    # 
    # from twilio.rest import Client
    # client = Client("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN")
    # message = client.messages.create(
    #     body=f"EMERGENCY: The driver has been unresponsive with eyes closed for > 1 min. Live location: {maps_link}",
    #     from_="+1XXXXXXXXXX", # Twilio Phone Number
    #     to=contact
    # )
    # 
    # Or send an Email via standard Python SMTP:
    # 
    # import smtplib
    # from email.mime.text import MIMEText
    # msg = MIMEText(f"EMERGENCY ALERT: Eyes closed > 1 min.\nLive Location: {maps_link}")
    # msg['Subject'] = "Sentinel AI - Driver Emergency Alert"
    # msg['From'] = "alerts@sentinelai.com"
    # msg['To'] = contact
    # with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    #     server.login("your_email@gmail.com", "your_app_password")
    #     server.send_message(msg)
    # =========================================================================

    return jsonify({
        "status": "success",
        "message": "Emergency alert logged on server and location logged",
        "dispatched_to": {
            "name": name,
            "contact": contact
        }
    })

if __name__ == '__main__':
    # Use SocketIO run instead of app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)

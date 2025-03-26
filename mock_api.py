from flask import Flask, jsonify, request
import time

app = Flask(__name__)

@app.route('/oauth2/token', methods=['POST'])
def fake_auth():
    return jsonify({
        "access_token": "fake_access_token_123",
        "expires_in": 3600
    })

@app.route('/patients/<patient_id>/vitals', methods=['POST'])
def fake_vitals(patient_id):
    print(f"Alınan Nabız Verisi: {request.json['heartRate']} BPM")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(port=5000)
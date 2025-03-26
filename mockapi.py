# Mock API için (test amaçlı)
from flask import Flask, jsonify, request
import random

app = Flask(__name__)

@app.route('/patients/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    return jsonify({
        "patientId": patient_id,
        "fullName": "Ahmet Yılmaz",
        "age": 45,
        "gender": "Erkek",
        "bloodType": "A Rh+",
        "admissionDate": "2023-01-15"
    })

@app.route('/patients/<patient_id>/lab-results', methods=['GET'])
def get_lab_results(patient_id):
    return jsonify({
        "patientId": patient_id,
        "tests": [
            {
                "testName": "Hemoglobin",
                "resultValue": 14.2,
                "unit": "g/dL",
                "referenceRange": "12.0-16.0",
                "status": "Normal"
            },
            {
                "testName": "Glukoz",
                "resultValue": 92,
                "unit": "mg/dL",
                "referenceRange": "70-100",
                "status": "Normal"
            }
        ]
    })

@app.route('/patients/<patient_id>/vitals', methods=['POST'])
def post_vitals(patient_id):
    data = request.json
    print(f"Received vitals for {patient_id}: {data}")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(port=5000)
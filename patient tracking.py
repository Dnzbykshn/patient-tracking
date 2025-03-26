import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np
import cv2
from cvzone.FaceDetectionModule import FaceDetector
import time
import threading
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import os
import logging
from secure_hospital_api import SecureHospitalAPI  # Güvenli API modülü



# Ortam Değişkenlerini Yükle
load_dotenv()

# API İstemcisini Başlat
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.demo-hastane.com/v1")
CLIENT_ID = os.getenv("CLIENT_ID", "medical_device_001")
ENCRYPTED_SECRET = os.getenv("ENCRYPTED_CLIENT_SECRET")

# Ana uygulama başlangıcında API istemcisini güvenli şekilde başlat
try:
    hospital_api = SecureHospitalAPI(
        base_url=os.getenv("API_BASE_URL"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("ENCRYPTED_CLIENT_SECRET")
    )
except Exception as e:
    messagebox.showerror("Kritik Hata", f"API bağlantısı kurulamadı: {str(e)}")
    exit()  # Uygulamayı kapat

# Hasta ID'si (Gerçek uygulamada login sistemi ile alınmalı)
CURRENT_PATIENT_ID = "12345"

# Webcam Parameters
realWidth = 640
realHeight = 480
videoWidth = 160
videoHeight = 120
videoChannels = 3
videoFrameRate = 15

# Helper Methods
def buildGauss(frame, levels):
    pyramid = [frame]
    for level in range(levels):
        frame = cv2.pyrDown(frame)
        pyramid.append(frame)
    return pyramid

def reconstructFrame(pyramid, index, levels):
    filteredFrame = pyramid[index]
    for level in range(levels):
        filteredFrame = cv2.pyrUp(filteredFrame)
    filteredFrame = filteredFrame[:videoHeight, :videoWidth]
    return filteredFrame

# Color Magnification Parameters
levels = 3
alpha = 170
minFrequency = 1.0
maxFrequency = 2.0
bufferSize = 150
bufferIndex = 0

# Initialize Gaussian Pyramid
firstFrame = np.zeros((videoHeight, videoWidth, videoChannels))
firstGauss = buildGauss(firstFrame, levels+1)[levels]
videoGauss = np.zeros((bufferSize, firstGauss.shape[0], firstGauss.shape[1], videoChannels))
fourierTransformAvg = np.zeros((bufferSize))

# Bandpass Filter for Specified Frequencies
frequencies = (1.0*videoFrameRate) * np.arange(bufferSize) / (1.0*bufferSize)
mask = (frequencies >= minFrequency) & (frequencies <= maxFrequency)

# Heart Rate Calculation Variables
bpmCalculationFrequency = 10
bpmBufferIndex = 0
bpmBufferSize = 10
bpmBuffer = np.zeros((bpmBufferSize))
bpm_value = 0  # Global nabız değişkeni

# Nabız Ölçme Fonksiyonu
def measure_pulse():
    global bpm_value
    webcam = cv2.VideoCapture(0)
    if not webcam.isOpened():
        messagebox.showerror("Hata", "Kamera açılamadı!")
        return

    webcam.set(3, realWidth)
    webcam.set(4, realHeight)

    detector = FaceDetector()

    while True:
        ret, frame = webcam.read()
        if not ret:
            messagebox.showerror("Hata", "Kameradan görüntü alınamadı!")
            break

        frame, bboxs = detector.findFaces(frame, draw=False)
        
        if bboxs:
            x1, y1, w1, h1 = bboxs[0]['bbox']
            detectionFrame = frame[y1:y1 + h1, x1:x1 + w1]
            detectionFrame = cv2.resize(detectionFrame, (videoWidth, videoHeight))

            # Construct Gaussian Pyramid
            videoGauss[bufferIndex] = buildGauss(detectionFrame, levels+1)[levels]
            fourierTransform = np.fft.fft(videoGauss, axis=0)

            # Bandpass Filter
            fourierTransform[mask == False] = 0

            # Grab a Pulse
            if bufferIndex % bpmCalculationFrequency == 0:
                for buf in range(bufferSize):
                    fourierTransformAvg[buf] = np.real(fourierTransform[buf]).mean()
                hz = frequencies[np.argmax(fourierTransformAvg)]
                bpm = 60.0 * hz
                bpmBuffer[bpmBufferIndex] = bpm
                bpmBufferIndex = (bpmBufferIndex + 1) % bpmBufferSize

            # Amplify
            filtered = np.real(np.fft.ifft(fourierTransform, axis=0))
            filtered = filtered * alpha

            # Reconstruct Resulting Frame
            filteredFrame = reconstructFrame(filtered, bufferIndex, levels)
            outputFrame = detectionFrame + filteredFrame
            outputFrame = cv2.convertScaleAbs(outputFrame)

            bufferIndex = (bufferIndex + 1) % bufferSize
            bpm_value = bpmBuffer.mean()

            pulse_label.config(text=f"Nabız: {bpm_value:.2f} BPM")
            check_health_conditions(bpm_value)
            
            # API'ye veri gönder
            try:
                vitals = {
                    "timestamp": datetime.now().isoformat(),
                    "heartRate": round(bpm_value, 2),
                    "deviceType": "RGB_CAMERA",
                    "status": "NORMAL" if 60 <= bpm_value <= 100 else "WARNING"
                }
                hospital_api.post_vital_signs(CURRENT_PATIENT_ID, vitals)
            except Exception as e:
                logging.error(f"Veri gönderilemedi: {str(e)}")

        else:
            pulse_label.config(text="Yüz algılanmadı! Lütfen kameraya doğru bakın ve aydınlatmayı artırın.")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    webcam.release()
    cv2.destroyAllWindows()

# Sağlık Kontrolleri
def check_health_conditions(bpm):
    try:
        # API'den hasta sağlık verilerini çek
        health_data = hospital_api.get_health_status(CURRENT_PATIENT_ID)
        
        respiration = health_data.get('respiration', 15)
        spine_pressure = health_data.get('spine_pressure', 50)
        humidity = health_data.get('humidity', 40)
        blood_pressure = health_data.get('blood_pressure', 120)

        if respiration < 10:
            messagebox.showwarning("Uyarı", "Solunum seviyesi düşük! Ozon terapisi kapatılıyor.")
        if bpm < 40:
            messagebox.showerror("ALARM", "Nabız çok düşük! Acil müdahale gerekiyor.")
        elif bpm < 60:
            messagebox.showwarning("Uyarı", "Nabız düşük! Doktora haber veriliyor.")
        elif bpm > 110:
            messagebox.showwarning("Uyarı", "Nabız yüksek! Doktora haber veriliyor.")
        if spine_pressure > 60:
            messagebox.showinfo("Bilgi", "Omurga baskısı algılandı! Yatak dik pozisyona getiriliyor.")
        if humidity > 50 and spine_pressure > 50 and 60 <= bpm <= 100:
            messagebox.showinfo("Bilgi", "Sırt basıncı ve nem fazla! Ozon terapisi uygulanıyor.")
        if blood_pressure < 90:
            messagebox.showinfo("Bilgi", "Tansiyon düşük! Yatağın ayak bölümü yükseltiliyor.")
            
    except Exception as e:
        logging.error(f"Sağlık verileri alınamadı: {str(e)}")

# Nabız Ölçme İşlemini Başlat
def start_pulse_measurement():
    threading.Thread(target=measure_pulse, daemon=True).start()

# Hasta Bilgisi
def show_patient_info():
    try:
        patient_data = hospital_api.get_patient_info(CURRENT_PATIENT_ID)
        if patient_data:
            info_text = (
                f"Hasta Adı: {patient_data.get('fullName', 'Bilgi Yok')}\n"
                f"Yaş: {patient_data.get('age', 'Bilgi Yok')}\n"
                f"Cinsiyet: {patient_data.get('gender', 'Bilgi Yok')}\n"
                f"Hasta No: {patient_data.get('patientId', 'Bilgi Yok')}\n"
                f"Kan Grubu: {patient_data.get('bloodType', 'Bilgi Yok')}"
            )
            messagebox.showinfo("Hasta Bilgisi", info_text)
        else:
            messagebox.showerror("Hata", "Hasta bilgileri alınamadı")
    except Exception as e:
        messagebox.showerror("API Hatası", str(e))

# Tahlil Sonuçları
def show_lab_results():
    try:
        lab_data = hospital_api.get_lab_results(CURRENT_PATIENT_ID)
        if lab_data:
            results_text = "Son Tahlil Sonuçları:\n\n"
            for test in lab_data.get('tests', []):
                results_text += (
                    f"{test.get('testName', 'Test')}: "
                    f"{test.get('resultValue', 'N/A')} "
                    f"{test.get('unit', '')} - "
                    f"{test.get('status', 'Sonuç Yok')}\n"
                )
            messagebox.showinfo("Tahlil Sonuçları", results_text)
        else:
            messagebox.showerror("Hata", "Tahlil sonuçları alınamadı")
    except Exception as e:
        messagebox.showerror("API Hatası", str(e))

# Yatak Verileri
def show_bed_data():
    try:
        bed_data = hospital_api.get_bed_data(CURRENT_PATIENT_ID)
        if bed_data:
            info_text = (
                f"Pozisyon: {bed_data.get('position', 'Bilgi Yok')}\n"
                f"Basınç: {bed_data.get('pressure', 'Bilgi Yok')} kPa\n"
                f"Nem: {bed_data.get('humidity', 'Bilgi Yok')}%"
            )
            messagebox.showinfo("Yatak Verileri", info_text)
        else:
            messagebox.showerror("Hata", "Yatak verileri alınamadı")
    except Exception as e:
        messagebox.showerror("API Hatası", str(e))

# Beslenme
def show_nutrition():
    try:
        nutrition_data = hospital_api.get_nutrition_data(CURRENT_PATIENT_ID)
        if nutrition_data:
            info_text = (
                f"Son Öğün: {nutrition_data.get('lastMeal', 'Bilgi Yok')}\n"
                f"Kalori: {nutrition_data.get('calories', 'Bilgi Yok')} kcal\n"
                f"Sıvı Alımı: {nutrition_data.get('fluidIntake', 'Bilgi Yok')} L"
            )
            messagebox.showinfo("Beslenme", info_text)
        else:
            messagebox.showerror("Hata", "Beslenme bilgileri alınamadı")
    except Exception as e:
        messagebox.showerror("API Hatası", str(e))

# Acil Durum
def emergency_alert():
    try:
        response = hospital_api.send_emergency_alert(
            patient_id=CURRENT_PATIENT_ID,
            alert_type="MANUAL",
            message="Hemşire panelinden acil çağrı gönderildi"
        )
        if response:
            messagebox.showwarning("Acil Durum", "Acil durum bildirildi! Doktor bilgilendiriliyor...")
    except Exception as e:
        messagebox.showerror("API Hatası", f"Acil çağrı gönderilemedi: {str(e)}")

# Otomatik Token Yenileme
def auto_refresh_tokens():
    while True:
        time.sleep(300)  # 5 dakikada bir
        try:
            hospital_api.refresh_tokens()
        except Exception as e:
            logging.error(f"Token yenileme hatası: {str(e)}")

# Token yenileme thread'ini başlat
threading.Thread(target=auto_refresh_tokens, daemon=True).start()

# Ana Uygulama
app = tk.Tk()
app.title("Hasta Takip Paneli")
app.geometry("600x400")
app.configure(bg="#f0f0f0")

# Başlık
title_label = tk.Label(app, text="Hasta Takip Paneli", font=("Segoe UI", 24, "bold"), bg="#f0f0f0", fg="black")
title_label.pack(pady=20)

# Butonlar
button_frame = tk.Frame(app, bg="#f0f0f0")
button_frame.pack()

buttons = [
    ("Hasta Bilgisi", show_patient_info),
    ("Tahlil Sonuçları", show_lab_results),
    ("Sağlık Verileri", start_pulse_measurement),
    ("Yatak Verileri", show_bed_data),
    ("Beslenme", show_nutrition),
    ("Acil Durum", emergency_alert),
]

for text, command in buttons:
    button = ttk.Button(button_frame, text=text, command=command, width=20, style="TButton")
    button.pack(pady=10, padx=10, fill=tk.X)

# Nabız Sonucu Gösterme
pulse_label = tk.Label(app, text="Nabız: -- BPM", font=("Segoe UI", 18), bg="#f0f0f0", fg="black")
pulse_label.pack(pady=20)

# Stil Ayarları
style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 12), padding=10, background="#0078d7", foreground="white")
style.map("TButton", background=[("active", "#005bb5")])

# Uygulamayı Başlat
app.mainloop()
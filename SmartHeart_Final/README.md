# SmartHeart - AI Cardiac Risk Prediction System

A professional hospital-grade heart disease prediction web application built with Flask, ML (Scikit-learn), OCR (Tesseract), and Bootstrap.

---

## 🏥 Features

- **Role-based access**: Doctor and Patient portals
- **Manual Assessment**: Input vitals directly for instant AI prediction
- **Scan Report Upload**: OCR extracts values from medical images
- **ML Prediction**: GradientBoosting classifier (trained on synthetic data)
- **Hospital PDF Report**: Downloadable professional PDF using ReportLab
- **Doctor Dashboard**: View all patients, filter by risk level, add clinical remarks
- **Responsive UI**: Clean medical theme (blue/white) with Bootstrap

---

## 🚀 Quick Start

### 1. Install Python dependencies

```bash
cd SmartHeart
pip install -r requirements.txt
```

For OCR support, also install Tesseract:
- **Ubuntu/Debian**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

### 2. Run the application

```bash
python app.py
```

### 3. Open in browser

```
http://localhost:5000
```

---

## 👤 Default Accounts

| Role   | Email                     | Password    |
|--------|---------------------------|-------------|
| Doctor | doctor@smartheart.com     | Doctor@123  |

Register your own patient account from the login page.

---

## 📁 Project Structure

```
SmartHeart/
├── app.py                          # Flask entry point
├── requirements.txt
├── smartheart.db                   # SQLite (auto-created)
├── models/
│   ├── database.py                 # DB operations
│   ├── ml_model.py                 # ML training + prediction
│   └── heart_model.pkl             # Saved model (auto-generated)
├── controllers/
│   ├── auth_controller.py          # Login/Register/Logout
│   ├── patient_controller.py       # Patient features
│   └── doctor_controller.py        # Doctor features
├── utils/
│   ├── ocr_processor.py            # Tesseract OCR
│   └── pdf_generator.py            # ReportLab PDF
├── templates/
│   ├── base.html
│   ├── select_role.html            # Landing page
│   ├── login.html                  # Auth page
│   ├── _sidebar.html               # Shared sidebar
│   ├── patient_dashboard.html
│   ├── assess.html                 # Manual input form
│   ├── scan_upload.html            # Scan upload
│   ├── result.html                 # Prediction result
│   ├── patient_reports.html
│   ├── patient_profile.html
│   ├── doctor_dashboard.html
│   ├── doctor_patients.html
│   └── doctor_report_detail.html
└── static/
    ├── uploads/                    # Uploaded scan images
    └── reports/                    # Generated PDFs
```

---

## 🧠 Machine Learning

- **Algorithm**: GradientBoostingClassifier (200 estimators)
- **Features**: Age, Gender, BP, Cholesterol, Heart Rate, Blood Sugar, Chest Pain Type
- **Output**: Risk probability (0–100%) → Severity (Low / Moderate / High / Critical)
- **Training**: Synthetic data based on known cardiac risk factor correlations

---

## ⚠️ Disclaimer

This system is intended for clinical support only. Always consult a qualified healthcare professional for medical decisions.

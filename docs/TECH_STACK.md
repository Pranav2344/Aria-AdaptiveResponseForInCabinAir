# ARIA Project - Technology Stack Documentation

## 1. Project Overview
ARIA (Adaptive Response for In-Cabin Air) is an AI-assisted cabin air quality decision platform.
It combines rule-based safety logic with a machine learning confidence model and provides both web and desktop dashboards.

## 2. Core Languages
- Python 3.11
- HTML5
- CSS3
- JavaScript (ES6, vanilla)
- Windows Batch scripting (.bat)

## 3. Backend and API Layer
- Framework: Flask 3.x
- API style: REST-like JSON endpoints
- Key endpoints:
  - GET /api/health
  - GET /api/current
  - POST /api/recommend
  - GET /api/history
  - GET /api/config
- HTTP utilities: urllib (for service probing)

## 4. AI/ML Stack
- ML Library: scikit-learn
- Model: RandomForestClassifier
- Pipeline components:
  - StandardScaler
  - RandomForestClassifier (n_estimators=320, max_depth=12, min_samples_leaf=2)
- Validation and metrics:
  - train_test_split
  - accuracy_score
  - classification_report
- Model serialization: joblib

## 5. Data Processing and Decisioning
- Data handling: pandas, numpy
- Input features include PM2.5, AQI, CO2, temperature, humidity
- Engine design:
  - Rule-based priority engine (safety-authoritative)
  - ML confidence scoring and agreement checks
- Threat modeling:
  - CO2 threat score
  - Pollution threat score
  - Conflict detection across simultaneous risks

## 6. Frontend Stack
- Server-rendered templates (Jinja2 via Flask templates)
- Static assets:
  - styles.css
  - app.js
  - styles_new_features.css
  - app_features.js
- UI capabilities:
  - Live polling dashboard
  - Manual input mode
  - Decision history table
  - Dark mode
  - Health recommendations
  - Threat gauges
  - CSV export
  - Settings modal

## 7. Desktop Interface
- Toolkit: Tkinter (ttk)
- Features:
  - Real-time metric cards
  - Decision output panel
  - Pause/Resume stream control
  - Manual refresh action

## 8. Data and Storage Formats
- Configuration: JSON (config.json)
- Historical/live datasets: CSV (data folder)
- Decision logs: CSV (logs/decisions.csv)
- Model artifact: Joblib (models/aria_model.joblib)
- Training metrics: JSON (models/training_metrics.json)

## 9. Runtime and Operations
- Primary launch:
  - python app.py
- Optional desktop mode:
  - python app.py --desktop
- Windows launcher:
  - start_aria.bat
- Default web runtime:
  - Host: 127.0.0.1
  - Port: 8000 (with auto-fallback to next free port)

## 10. Dependency Summary (requirements.txt)
- Flask>=3.0.0
- pandas>=2.2.0
- numpy>=1.26.0
- scikit-learn>=1.4.0
- joblib>=1.3.0
- requests>=2.32.0

## 11. Architecture Snapshot
- Hybrid intelligence model:
  - Deterministic safety rules decide final mode
  - ML model estimates confidence for transparency
- Web and desktop clients share the same core decision agent
- Log-based history tracking enables monitoring and post-analysis

## 12. Generated Document Info
This document was generated from the current repository implementation and configuration as of April 17, 2026.

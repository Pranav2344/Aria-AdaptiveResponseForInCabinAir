# ARIA Backend Implementation and Tech Stack

## 1. Executive Summary
ARIA backend is a Python-based, safety-first decision platform for in-cabin air quality control.
The implementation combines deterministic rule-based logic with machine learning confidence scoring.
This hybrid model provides explainable decisions while maintaining operational safety under extreme conditions.

## 2. Backend Technology Stack
- Language: Python 3.11
- Web framework: Flask 3.x
- Data processing: pandas, numpy
- Machine learning: scikit-learn
- Model persistence: joblib
- Data transport format: JSON over HTTP
- Data storage format: CSV and JSON
- Desktop support: Tkinter (optional runtime mode)

## 3. Dependency Matrix
- Flask>=3.0.0: API server and template rendering
- pandas>=2.2.0: data preparation and feature engineering
- numpy>=1.26.0: numerical operations and synthetic data generation
- scikit-learn>=1.4.0: model training, prediction, metrics
- joblib>=1.3.0: model artifact serialization
- requests>=2.32.0: HTTP utility dependency

## 4. Backend Architecture
- Entry point layer:
  - app.py selects web mode or desktop mode using CLI flags.
- Service layer:
  - web_app.py initializes Flask app, routes, decision logging, and server lifecycle.
- Decision intelligence layer:
  - agent.py hosts AriaDecisionAgent and returns structured decision results.
- Data and feature layer:
  - data_processing.py handles cleaning, feature engineering, threat scoring, and rule priorities.
- Live input simulation layer:
  - live_data.py generates realistic streaming sensor values.
- Model training layer:
  - train_model.py trains and persists the ML pipeline with metrics.

## 5. API Implementation
- GET /api/health
  - Purpose: service health validation and instance detection.
  - Response: status and service identifier.

- GET /api/current
  - Purpose: fetch next live simulated reading and decision.
  - Flow: simulator -> decision agent -> CSV log -> JSON response.

- POST /api/recommend
  - Purpose: submit manual sensor payload for recommendation.
  - Validation: required fields are normalized and cast to float.
  - Fallback: uses simulator when payload is not provided.

- GET /api/history
  - Purpose: fetch recent decisions from logs/decisions.csv.
  - Guardrails: limit constrained between 1 and 500.

- GET /api/config
  - Purpose: expose safe limits and polling configuration to frontend.

## 6. Decision Engine Implementation
- Primary decision authority:
  - Rule-based priority engine in data_processing.py.
- Secondary intelligence:
  - ML model predicts mode and contributes confidence score.
- Consistency control:
  - If ML disagrees with rule decision, confidence is capped.
- Conflict handling:
  - Threat scores compare CO2 risk vs pollution risk.
  - Weighted priority favors CO2 for cognitive safety.

## 7. Rule Priority Model
- Priority 1: critical CO2
- Priority 2: extreme outside pollution
- Priority 3: simultaneous conflict resolution
- Priority 4: elevated CO2
- Priority 5: thermal comfort out-of-range
- Priority 6: high PM2.5 or AQI
- Priority 7: mild CO2 elevation
- Priority 8: stable conditions

## 8. Feature Engineering and Data Flow
- Raw input features:
  - pm25, aqi, co2, temperature, humidity
- Derived features:
  - pollution_pressure
  - comfort_gap
  - ventilation_need
  - conflict_score
  - co2_vs_pollution
- Pipeline flow:
  - input normalization -> feature enrichment -> rule evaluation -> ML confidence -> structured decision output

## 9. Model Training and Artifact Management
- Training script: train_model.py
- Pipeline: StandardScaler + RandomForestClassifier
- Training split: stratified train_test_split
- Metrics persisted:
  - accuracy
  - class distribution
  - feature importance
  - classification report
- Artifacts generated:
  - models/aria_model.joblib
  - models/training_metrics.json

## 10. Reliability and Runtime Controls
- Startup checks:
  - Reuses existing ARIA server instance if already running.
  - Detects and selects available port when preferred port is occupied.
- Logging strategy:
  - Writes all decision outcomes to CSV for auditability.
- Compatibility checks:
  - Validates sklearn version, logic version, and feature columns before loading model.
  - Retrains model automatically on incompatibility.

## 11. Storage and Configuration
- Configuration file: config.json
  - stores paths, limits, server settings, and training parameters.
- Runtime data:
  - data/air_quality_live.csv for generated stream inputs.
  - logs/decisions.csv for decision history.
- Training data:
  - data/air_quality_data.csv for model training dataset.

## 12. Security and Validation Controls
- Manual input validation:
  - Required sensor fields enforced before decisioning.
  - Invalid payload returns HTTP 400 with error details.
- Server-side normalization:
  - All numeric fields converted to float types.
- Defensive limits:
  - History endpoint bounds request size to prevent oversized responses.

## 13. Deployment and Operations
- Web launch command:
  - python app.py
- Desktop launch command:
  - python app.py --desktop
- Windows launcher:
  - start_aria.bat
- Default server settings:
  - host 127.0.0.1
  - port 8000
  - polling interval 4 seconds

## 14. Presentation Talking Points
- Hybrid architecture enables both safety determinism and ML transparency.
- Rule-based logic remains authoritative for critical scenarios.
- Explainable outputs include trigger, risk level, reasoning, and alerts.
- CSV logging and JSON metrics support audits and model lifecycle review.
- Modular file structure simplifies maintenance, testing, and scaling.

## 15. Conclusion
ARIA backend is implemented as a robust, explainable, and production-oriented decision service.
The selected tech stack balances rapid development, interpretability, and operational reliability.
The architecture is suitable for demonstration, academic projects, and future enterprise hardening.

Generated on: April 17, 2026

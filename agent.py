from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import sklearn

from data_processing import (
    FEATURE_COLUMNS,
    MODEL_COLUMNS,
    MODEL_LOGIC_VERSION,
    _compute_threat_scores,
    _priority_mode,
    load_config,
    prepare_feature_row,
    resolve_project_path,
)
from train_model import train_and_save_model


@dataclass
class DecisionResult:
    timestamp: str
    mode: str
    confidence: float
    risk_level: str
    reason: str
    alerts: list[str]
    input_reading: dict[str, float]
    priority_trigger: str       # which parameter caused the decision
    conflict_detected: bool     # True when multiple parameters exceed thresholds simultaneously
    threat_scores: dict[str, float]  # co2_threat and pollution_threat scores


class AriaDecisionAgent:
    def __init__(self, config_path: str | Path = "config.json") -> None:
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.model_path = resolve_project_path(self.config_path, self.config["paths"]["model"])
        self.metrics_path = resolve_project_path(self.config_path, self.config["paths"]["metrics"])
        self.pipeline = None
        self.feature_columns: list[str] = []
        self.classes: list[str] = []
        self._load_or_train_model()

    def _is_model_compatible(self) -> bool:
        if not self.metrics_path.exists() or not self.model_path.exists():
            return False

        try:
            with self.metrics_path.open("r", encoding="utf-8") as handle:
                metrics = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return False

        # Check sklearn version matches
        if str(metrics.get("sklearn_version", "")).strip() != sklearn.__version__:
            return False

        # Check feature columns match current MODEL_COLUMNS
        saved_features = metrics.get("feature_columns", [])
        if list(saved_features) != list(MODEL_COLUMNS):
            return False

        if str(metrics.get("logic_version", "")).strip() != MODEL_LOGIC_VERSION:
            return False

        return True

    def _load_or_train_model(self) -> None:
        if not self.model_path.exists() or not self._is_model_compatible():
            train_and_save_model(self.config_path)

        artifact = joblib.load(self.model_path)
        self.pipeline = artifact["pipeline"]
        self.feature_columns = list(artifact["feature_columns"])
        self.classes = list(artifact.get("classes", []))

    def _risk_level(self, reading: dict[str, float]) -> str:
        critical_limits = self.config.get("limits", {}).get("critical", {})

        if (
            reading["pm25"] >= float(critical_limits.get("pm25", 120))
            or reading["aqi"] >= float(critical_limits.get("aqi", 220))
            or reading["co2"] >= float(critical_limits.get("co2", 1800))
        ):
            return "critical"

        if reading["pm25"] >= 90 or reading["aqi"] >= 180 or reading["co2"] >= 1450:
            return "high"
        if reading["pm25"] >= 50 or reading["aqi"] >= 120 or reading["co2"] >= 1100:
            return "moderate"
        return "low"

    def _build_alerts(self, reading: dict[str, float]) -> list[str]:
        alerts: list[str] = []
        safe_limits = self.config.get("limits", {}).get("safe", {})

        if reading["pm25"] > float(safe_limits.get("pm25", 35)):
            alerts.append("PM2.5 is above healthy range.")
        if reading["aqi"] > float(safe_limits.get("aqi", 100)):
            alerts.append("AQI is unhealthy for sensitive groups.")
        if reading["co2"] > float(safe_limits.get("co2", 1000)):
            alerts.append("CO2 is elevated; fresh air is recommended.")
        if reading["temperature"] < float(safe_limits.get("temperature_min", 20)):
            alerts.append("Cabin temperature is low.")
        if reading["temperature"] > float(safe_limits.get("temperature_max", 27)):
            alerts.append("Cabin temperature is high.")
        if reading["humidity"] < float(safe_limits.get("humidity_min", 35)):
            alerts.append("Humidity is below comfort range.")
        if reading["humidity"] > float(safe_limits.get("humidity_max", 65)):
            alerts.append("Humidity is above comfort range.")

        return alerts

    @staticmethod
    def _build_priority_reason(mode: str, reading: dict[str, float], trigger: str) -> str:
        p = reading
        messages: dict[str, str] = {
            "co2_critical": (
                f"CRITICAL PRIORITY — CO2 at {p['co2']:.0f} ppm has reached a dangerous level. "
                "Fresh air is mandatory to prevent hypoxia and cognitive impairment, overriding all other factors. "
                "Incoming outside air passes through the cabin particulate filter before entry."
            ),
            "extreme_pollution": (
                f"CRITICAL OUTSIDE POLLUTION — PM2.5 = {p['pm25']:.1f} µg/m³ (critical ≥ 120), "
                f"AQI = {p['aqi']:.0f} (critical ≥ 220). "
                f"At these extreme concentrations the cabin filter would be saturated and overwhelmed — "
                f"drawing air through an overloaded filter risks particles bypassing it entirely. "
                f"Recirculating to protect occupants even though CO2 ({p['co2']:.0f} ppm) is elevated. "
                f"Monitor CO2 closely; if it approaches 1800 ppm open vents briefly."
            ),
            "co2_priority_over_pollution": (
                f"CONFLICT RESOLVED — CO2 ({p['co2']:.0f} ppm) AND pollution (PM2.5 {p['pm25']:.1f} µg/m³, "
                f"AQI {p['aqi']:.0f}) are both above safe limits. "
                "CO2 threat is higher priority (weight ×1.4) — fresh air selected to prevent cognitive impairment. "
                "The cabin particulate filter will clean PM2.5 from incoming air, making fresh air the safe choice here."
            ),
            "pollution_priority_over_co2": (
                f"CONFLICT RESOLVED — CO2 ({p['co2']:.0f} ppm) AND pollution (PM2.5 {p['pm25']:.1f} µg/m³, "
                f"AQI {p['aqi']:.0f}) are both above safe limits. "
                "Outside pollution threat outweighs CO2 risk at this level — recirculation selected. "
                "Straining the cabin filter under this pollution load risks reduced efficiency; "
                "recirculating keeps cabin air cleaner while CO2 remains manageable."
            ),
            "co2_elevated": (
                f"CO2 at {p['co2']:.0f} ppm is elevated. "
                "Fresh air selected to restore oxygen balance — incoming outside air passes through the "
                "cabin particulate filter before entering, so occupants are protected from outdoor PM2.5 "
                "while CO2 is cleared."
            ),
            "comfort_out_of_range": (
                f"Temperature {p['temperature']:.1f} °C or humidity {p['humidity']:.0f}% is outside comfort range. "
                "Fresh air selected to restore cabin comfort. "
                "Incoming outside air passes through the cabin filter; adjust climate control as needed."
            ),
            "pm25_aqi_elevated": (
                f"Outside PM2.5 = {p['pm25']:.1f} µg/m³ and AQI = {p['aqi']:.0f} are high. "
                "Although the cabin filter handles particulates when fresh air is used, recirculation is "
                "preferred at these levels to preserve filter life and keep the cabin air quality optimal. "
                "CO2 is within acceptable range."
            ),
            "co2_mildly_elevated": (
                f"CO2 mildly elevated at {p['co2']:.0f} ppm. "
                "Fresh air will clear the build-up; outside air passes through the cabin filter before "
                "entering so any outdoor particulates are removed."
            ),
            "stable_conditions": (
                "All parameters are within safe limits. "
                "Recirculating cabin air maintains comfort with optimal energy efficiency — "
                "no filter load from outside air while conditions remain stable."
            ),
        }
        return messages.get(
            trigger,
            f"{'Fresh air' if mode == 'fresh_air' else 'Recirculation'} selected based on multi-parameter analysis.",
        )

    def decide(self, reading: dict[str, Any]) -> dict[str, Any]:
        if self.pipeline is None:
            self._load_or_train_model()

        normalized: dict[str, float] = {}
        for field in FEATURE_COLUMNS:
            if field not in reading:
                raise ValueError(f"Missing required field: {field}")
            normalized[field] = float(reading[field])

        # ---------------------------------------------------------------
        # Rule-based priority engine is AUTHORITATIVE for safety.
        # The ML model provides a confidence signal; if it disagrees with
        # the rule-based decision, confidence is capped to flag the mismatch.
        # ---------------------------------------------------------------
        rule_mode, trigger = _priority_mode(
            normalized["pm25"], normalized["aqi"], normalized["co2"],
            normalized["temperature"], normalized["humidity"],
        )

        feature_frame = prepare_feature_row(normalized)
        ml_prediction = str(self.pipeline.predict(feature_frame[self.feature_columns])[0])
        ml_agrees = ml_prediction == rule_mode

        confidence = 0.7
        if hasattr(self.pipeline, "predict_proba"):
            classes = list(self.pipeline.classes_)
            probabilities = self.pipeline.predict_proba(feature_frame[self.feature_columns])[0]
            if rule_mode in classes:
                # Use the probability the model assigns to the rule-based (correct) class
                rule_idx = classes.index(rule_mode)
                confidence = float(probabilities[rule_idx])
            else:
                confidence = float(max(probabilities))

        # Cap confidence when ML model disagreed — signals reduced certainty
        if not ml_agrees:
            confidence = min(confidence, 0.72)

        scores = _compute_threat_scores(normalized["pm25"], normalized["aqi"], normalized["co2"])
        conflict = scores["co2_threat"] >= 0.25 and scores["pollution_threat"] >= 0.25

        result = DecisionResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=rule_mode,           # rule-based mode is the final authoritative answer
            confidence=round(confidence, 4),
            risk_level=self._risk_level(normalized),
            reason=self._build_priority_reason(rule_mode, normalized, trigger),
            alerts=self._build_alerts(normalized),
            input_reading={key: round(value, 2) for key, value in normalized.items()},
            priority_trigger=trigger,
            conflict_detected=conflict,
            threat_scores={
                "co2_threat": round(scores["co2_threat"], 3),
                "pollution_threat": round(scores["pollution_threat"], 3),
            },
        )
        return asdict(result)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["pm25", "aqi", "co2", "temperature", "humidity"]
DERIVED_COLUMNS = [
    "pollution_pressure",
    "comfort_gap",
    "ventilation_need",
    "conflict_score",      # high when BOTH co2 AND pollution exceed safe limits
    "co2_vs_pollution",   # ratio: >1 means CO2 threat dominates; <1 means pollution dominates
]
MODEL_COLUMNS = FEATURE_COLUMNS + DERIVED_COLUMNS
TARGET_COLUMN = "recommended_mode"
MODEL_LOGIC_VERSION = "2026-03-14-filter-aware-v1"

# Conflict threshold: a parameter must be at least this fraction above its safe limit
# before it counts as a "threat" in conflict scoring.
CONFLICT_THRESHOLD = 0.25

# CO2 is weighted 1.4x because elevated CO2 impairs cognition faster than PM2.5
CO2_PRIORITY_WEIGHT = 1.4

# Fresh-air intake passes through the cabin particulate filter.
# For non-extreme outdoor pollution, discount the pollution threat so
# filter-protected fresh air can beat rising CO2 more often.
CABIN_FILTER_DISCOUNT = 0.45


def load_config(config_path: str | Path = "config.json") -> dict[str, Any]:
    config_file = Path(config_path)
    with config_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_project_path(config_path: str | Path, relative_path: str) -> Path:
    config_file = Path(config_path).resolve()
    return (config_file.parent / relative_path).resolve()


def _compute_threat_scores(pm25: float, aqi: float, co2: float) -> dict[str, float]:
    """Normalised severity scores used by the priority engine.

    Pollution is discounted to reflect cabin-filter protection during
    fresh-air intake. Extreme pollution remains a separate hard-stop rule.
    """
    co2_threat = max(0.0, (co2 - 1000.0) / 1000.0)        # 0 at ≤1000 ppm,  1.0 at 2000 ppm
    pm25_threat = max(0.0, (pm25 - 35.0) / 85.0)           # 0 at ≤35 µg/m³,  1.0 at 120 µg/m³
    aqi_threat = max(0.0, (aqi - 100.0) / 150.0)           # 0 at ≤100 AQI,   1.0 at 250 AQI
    # PM2.5 direct measurement is more reliable than AQI, weight it higher
    raw_pollution_threat = max(pm25_threat, aqi_threat * 0.85)
    pollution_threat = raw_pollution_threat * CABIN_FILTER_DISCOUNT
    return {"co2_threat": co2_threat, "pollution_threat": pollution_threat}


def _priority_mode(pm25: float, aqi: float, co2: float, temperature: float, humidity: float) -> tuple[str, str]:
    """Priority-based decision engine.  Returns (mode, trigger_key).

    Priority order (highest → lowest):
      1. CO2 critical  (≥ 2000 ppm)                   → fresh_air
            2. Extreme outside pollution (PM2.5 ≥ 120 or AQI ≥ 220) → recirculation
            3. CONFLICT: both CO2 and filter-adjusted pollution above threshold simultaneously
           → weighted scoring decides (CO2 weight × 1.4)
      4. CO2 alone elevated (≥ 1200 ppm)              → fresh_air
      5. Comfort: temperature or humidity out of range → fresh_air
            6. PM2.5 / AQI high even after filter margin     → recirculation
      7. CO2 mildly elevated (≥ 950 ppm)              → fresh_air
      8. Stable conditions                              → recirculation
    """
    scores = _compute_threat_scores(pm25, aqi, co2)
    co2_threat = scores["co2_threat"]
    poll_threat = scores["pollution_threat"]

    # --- Priority 1: critical CO2 overrides everything ---
    if co2 >= 2000:
        return "fresh_air", "co2_critical"

    # --- Priority 2: critical outside pollution (aligned with config.json critical limits) ---
    # PM2.5 >= 120 µg/m³ or AQI >= 220 means outside air is critically toxic.
    # Opening vents would flood the cabin with harmful particles; recirculate even if CO2 is rising.
    if pm25 >= 120 or aqi >= 220:
        return "recirculation", "extreme_pollution"

    # --- Priority 3: conflict — both threats active simultaneously ---
    if co2_threat >= CONFLICT_THRESHOLD and poll_threat >= CONFLICT_THRESHOLD:
        if co2_threat * CO2_PRIORITY_WEIGHT >= poll_threat:
            return "fresh_air", "co2_priority_over_pollution"
        return "recirculation", "pollution_priority_over_co2"

    # --- Priority 4: CO2 elevated alone ---
    if co2 >= 1200:
        return "fresh_air", "co2_elevated"

    # --- Priority 5: comfort factors ---
    if temperature < 18 or temperature > 30 or humidity < 30 or humidity > 70:
        return "fresh_air", "comfort_out_of_range"

    # --- Priority 6: high outside pollution even after filter protection ---
    if pm25 >= 85 or aqi >= 170:
        return "recirculation", "pm25_aqi_elevated"

    # --- Priority 7: mild CO2 build-up ---
    if co2 >= 950:
        return "fresh_air", "co2_mildly_elevated"

    # --- Priority 8: stable ---
    return "recirculation", "stable_conditions"


def _rule_based_mode(row: pd.Series) -> str:
    """Pandas-compatible wrapper — returns mode string only."""
    mode, _ = _priority_mode(
        float(row["pm25"]), float(row["aqi"]), float(row["co2"]),
        float(row["temperature"]), float(row["humidity"]),
    )
    return mode


def generate_synthetic_environmental_data(row_count: int = 3000, random_state: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)

    pm25 = np.clip(rng.gamma(shape=2.6, scale=13.0, size=row_count), 5, 260)
    aqi = np.clip(pm25 * 1.8 + rng.normal(18, 20, row_count), 20, 500)
    co2 = np.clip(rng.normal(860, 260, row_count), 420, 2500)
    temperature = np.clip(rng.normal(24, 4.3, row_count), 10, 40)
    humidity = np.clip(rng.normal(50, 14.0, row_count), 10, 95)

    # Traffic scenario: high PM2.5 + AQI (outdoor pollution spike)
    traffic_mask = rng.random(row_count) < 0.18
    pm25[traffic_mask] += np.clip(rng.normal(55, 18, traffic_mask.sum()), 20, 140)
    aqi[traffic_mask] += np.clip(rng.normal(65, 20, traffic_mask.sum()), 20, 180)

    # Crowded cabin: high CO2
    crowded_mask = rng.random(row_count) < 0.14
    co2[crowded_mask] += np.clip(rng.normal(620, 160, crowded_mask.sum()), 220, 1200)

    # *** CONFLICT SCENARIO: high CO2 AND high PM2.5/AQI simultaneously ***
    # Represents: stuck in polluted traffic jam with windows closed for a long time
    conflict_mask = rng.random(row_count) < 0.12
    pm25[conflict_mask] += np.clip(rng.normal(70, 22, conflict_mask.sum()), 30, 160)
    aqi[conflict_mask] += np.clip(rng.normal(90, 25, conflict_mask.sum()), 40, 200)
    co2[conflict_mask] += np.clip(rng.normal(550, 150, conflict_mask.sum()), 200, 1000)

    # *** CO2 CRITICAL SCENARIO: very high CO2 (sleepy occupants, long tunnel) ***
    critical_co2_mask = rng.random(row_count) < 0.06
    co2[critical_co2_mask] = np.clip(rng.normal(1900, 200, critical_co2_mask.sum()), 1600, 2500)

    # *** EXTREME POLLUTION SCENARIO: heavy smog outside ***
    extreme_poll_mask = rng.random(row_count) < 0.05
    pm25[extreme_poll_mask] = np.clip(rng.normal(170, 30, extreme_poll_mask.sum()), 140, 260)
    aqi[extreme_poll_mask] = np.clip(rng.normal(260, 40, extreme_poll_mask.sum()), 230, 500)

    thermal_mask = rng.random(row_count) < 0.11
    temperature[thermal_mask] += rng.choice([-1, 1], size=thermal_mask.sum()) * np.clip(
        rng.normal(7, 2.5, thermal_mask.sum()), 2, 12
    )
    humidity[thermal_mask] += rng.choice([-1, 1], size=thermal_mask.sum()) * np.clip(
        rng.normal(18, 7, thermal_mask.sum()), 6, 32
    )

    pm25 = np.clip(pm25, 5, 260)
    aqi = np.clip(aqi, 20, 500)
    co2 = np.clip(co2, 420, 2500)
    temperature = np.clip(temperature, 10, 40)
    humidity = np.clip(humidity, 10, 95)

    frame = pd.DataFrame(
        {
            "pm25": pm25.round(2),
            "aqi": aqi.round(2),
            "co2": co2.round(2),
            "temperature": temperature.round(2),
            "humidity": humidity.round(2),
        }
    )
    frame[TARGET_COLUMN] = frame.apply(_rule_based_mode, axis=1)
    return frame


def clean_environmental_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()

    for column in FEATURE_COLUMNS:
        if column not in cleaned.columns:
            cleaned[column] = np.nan
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    for column in FEATURE_COLUMNS:
        median_value = float(cleaned[column].median()) if cleaned[column].notna().any() else 0.0
        cleaned[column] = cleaned[column].fillna(median_value)

    return cleaned[FEATURE_COLUMNS]


def enrich_features(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = clean_environmental_frame(frame)

    enriched["pollution_pressure"] = (
        0.45 * (enriched["pm25"] / 120.0)
        + 0.35 * (enriched["aqi"] / 250.0)
        + 0.20 * (enriched["co2"] / 2000.0)
    )
    enriched["comfort_gap"] = (
        (enriched["temperature"] - 24.0).abs() / 10.0
        + (enriched["humidity"] - 50.0).abs() / 25.0
    )
    enriched["ventilation_need"] = (
        0.60 * (enriched["co2"] / 1200.0) + 0.40 * enriched["comfort_gap"]
    )

    # --- NEW: conflict-aware features ---
    # Normalised threat scores (mirrors _compute_threat_scores but vectorised)
    co2_threat = ((enriched["co2"] - 1000.0) / 1000.0).clip(lower=0)
    pm25_threat = ((enriched["pm25"] - 35.0) / 85.0).clip(lower=0)
    aqi_threat = ((enriched["aqi"] - 100.0) / 150.0).clip(lower=0) * 0.85
    pollution_threat = pm25_threat.combine(aqi_threat, max) * CABIN_FILTER_DISCOUNT

    # conflict_score: near-zero when only one threat is active;
    # rises sharply when BOTH co2 AND pollution are above CONFLICT_THRESHOLD (0.25).
    conflict_co2 = (co2_threat - CONFLICT_THRESHOLD).clip(lower=0)
    conflict_poll = (pollution_threat - CONFLICT_THRESHOLD).clip(lower=0)
    enriched["conflict_score"] = (conflict_co2 * conflict_poll * 16.0).clip(upper=4.0)

    # co2_vs_pollution: >1 means CO2 threat dominates; <1 means pollution dominates.
    enriched["co2_vs_pollution"] = (
        (co2_threat * CO2_PRIORITY_WEIGHT) / (pollution_threat + 0.001)
    ).clip(upper=10.0)

    for column in DERIVED_COLUMNS:
        enriched[column] = enriched[column].clip(lower=0).round(4)

    return enriched[MODEL_COLUMNS]


def prepare_training_data(config_path: str | Path = "config.json") -> pd.DataFrame:
    config = load_config(config_path)
    training_data_path = resolve_project_path(config_path, config["paths"]["training_data"])
    training_data_path.parent.mkdir(parents=True, exist_ok=True)

    if training_data_path.exists():
        raw_frame = pd.read_csv(training_data_path)
    else:
        row_count = int(config.get("training", {}).get("rows", 3000))
        random_state = int(config.get("training", {}).get("random_state", 42))
        raw_frame = generate_synthetic_environmental_data(row_count=row_count, random_state=random_state)
        raw_frame.to_csv(training_data_path, index=False)

    cleaned = clean_environmental_frame(raw_frame)
    enriched = enrich_features(cleaned)

    # Always relabel from the current rule engine so training stays aligned
    # when thresholds or priority logic change.
    labels = cleaned.apply(_rule_based_mode, axis=1)

    enriched[TARGET_COLUMN] = labels.values

    # Always regenerate the CSV so it keeps the priority-labelled targets
    raw_to_save = cleaned.copy()
    raw_to_save[TARGET_COLUMN] = labels.values
    raw_to_save.to_csv(training_data_path, index=False)

    return enriched[MODEL_COLUMNS + [TARGET_COLUMN]]


def prepare_feature_row(reading: dict[str, float]) -> pd.DataFrame:
    frame = pd.DataFrame([reading])
    return enrich_features(frame)

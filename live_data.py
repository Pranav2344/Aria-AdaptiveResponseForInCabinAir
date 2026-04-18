from __future__ import annotations

import csv
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_processing import FEATURE_COLUMNS, load_config, resolve_project_path


class LiveDataSimulator:
    def __init__(self, config_path: str | Path = "config.json", seed: int = 42) -> None:
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.random = random.Random(seed)
        self.tick = 0

        self.live_data_path = resolve_project_path(self.config_path, self.config["paths"]["live_data"])
        self.live_data_path.parent.mkdir(parents=True, exist_ok=True)

        self.state = {
            "pm25": self.random.uniform(14, 30),
            "aqi": self.random.uniform(45, 85),
            "co2": self.random.uniform(650, 980),
            "temperature": self.random.uniform(22, 27),
            "humidity": self.random.uniform(40, 58),
        }
        self._ensure_live_data_file()

    def _ensure_live_data_file(self) -> None:
        if self.live_data_path.exists():
            return

        with self.live_data_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", *FEATURE_COLUMNS])
            writer.writeheader()

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(value, high))

    def _append_to_csv(self, reading: dict[str, Any]) -> None:
        with self.live_data_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", *FEATURE_COLUMNS])
            writer.writerow(reading)

    def next_reading(self) -> dict[str, Any]:
        self.tick += 1

        self.state["pm25"] += self.random.gauss(0, 4.2)
        self.state["aqi"] += self.random.gauss(0, 6.8)
        self.state["co2"] += self.random.gauss(0, 58)
        self.state["temperature"] += self.random.gauss(0, 0.55)
        self.state["humidity"] += self.random.gauss(0, 1.9)

        if self.random.random() < 0.12:
            self.state["pm25"] += self.random.uniform(20, 95)
            self.state["aqi"] += self.random.uniform(30, 130)

        if self.random.random() < 0.08:
            self.state["co2"] += self.random.uniform(180, 760)

        if self.random.random() < 0.06:
            self.state["temperature"] += self.random.choice([-1.0, 1.0]) * self.random.uniform(2, 8)
            self.state["humidity"] += self.random.choice([-1.0, 1.0]) * self.random.uniform(8, 25)

        self.state["pm25"] = self._clamp(self.state["pm25"], 5, 260)
        self.state["aqi"] = self._clamp(self.state["aqi"], 20, 500)
        self.state["co2"] = self._clamp(self.state["co2"], 420, 2500)
        self.state["temperature"] = self._clamp(self.state["temperature"], 10, 40)
        self.state["humidity"] = self._clamp(self.state["humidity"], 10, 95)

        reading = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pm25": round(self.state["pm25"], 2),
            "aqi": round(self.state["aqi"], 2),
            "co2": round(self.state["co2"], 2),
            "temperature": round(self.state["temperature"], 2),
            "humidity": round(self.state["humidity"], 2),
        }

        self._append_to_csv(reading)
        return reading

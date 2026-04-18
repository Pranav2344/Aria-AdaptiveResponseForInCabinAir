from __future__ import annotations

import csv
import socket
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from flask import Flask, jsonify, render_template, request

from agent import AriaDecisionAgent
from data_processing import FEATURE_COLUMNS, load_config, resolve_project_path
from live_data import LiveDataSimulator

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
CONFIG = load_config(CONFIG_PATH)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

AGENT = AriaDecisionAgent(CONFIG_PATH)
SIMULATOR = LiveDataSimulator(CONFIG_PATH)
DECISION_LOG_PATH = resolve_project_path(CONFIG_PATH, CONFIG["paths"]["decision_log"])


def _ensure_decision_log() -> None:
    DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DECISION_LOG_PATH.exists():
        return

    with DECISION_LOG_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "timestamp",
                "pm25",
                "aqi",
                "co2",
                "temperature",
                "humidity",
                "mode",
                "confidence",
                "risk_level",
                "reason",
                "alerts",
            ],
        )
        writer.writeheader()


def _append_decision(reading: dict[str, Any], decision: dict[str, Any]) -> None:
    _ensure_decision_log()
    row = {
        "timestamp": reading.get("timestamp", decision.get("timestamp")),
        "pm25": reading.get("pm25"),
        "aqi": reading.get("aqi"),
        "co2": reading.get("co2"),
        "temperature": reading.get("temperature"),
        "humidity": reading.get("humidity"),
        "mode": decision.get("mode"),
        "confidence": decision.get("confidence"),
        "risk_level": decision.get("risk_level"),
        "reason": decision.get("reason"),
        "alerts": " | ".join(decision.get("alerts", [])),
    }

    with DECISION_LOG_PATH.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        writer.writerow(row)


def _read_history(limit: int) -> list[dict[str, str]]:
    _ensure_decision_log()
    with DECISION_LOG_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-limit:]


def _normalize_reading(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in FEATURE_COLUMNS:
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")
        normalized[field] = float(payload[field])
    return normalized


@app.get("/")
def index() -> str:
    return render_template("index.html", project_name=CONFIG.get("project_name", "ARIA"))


@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "ok", "service": "aria-api"})


@app.get("/api/current")
def current_reading() -> Any:
    reading = SIMULATOR.next_reading()
    decision = AGENT.decide(reading)
    _append_decision(reading, decision)
    return jsonify({"reading": reading, "decision": decision})


@app.post("/api/recommend")
def recommend() -> Any:
    payload = request.get_json(silent=True) or {}

    if payload:
        try:
            reading = _normalize_reading(payload)
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        reading["timestamp"] = payload.get("timestamp") or decision_timestamp()
    else:
        reading = SIMULATOR.next_reading()

    decision = AGENT.decide(reading)
    _append_decision(reading, decision)
    return jsonify({"reading": reading, "decision": decision})


@app.get("/api/history")
def history() -> Any:
    limit = request.args.get("limit", default=30, type=int)
    safe_limit = max(1, min(limit, 500))
    return jsonify({"history": _read_history(safe_limit)})


@app.get("/api/config")
def get_config() -> Any:
    return jsonify(
        {
            "project_name": CONFIG.get("project_name"),
            "limits": CONFIG.get("limits", {}),
            "poll_interval_seconds": CONFIG.get("server", {}).get("poll_interval_seconds", 4),
        }
    )


def decision_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def find_available_port(host: str, start_port: int, max_attempts: int = 50) -> int:
    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue

    raise RuntimeError(f"No free port found between {start_port} and {start_port + max_attempts - 1}")


def _health_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/api/health"


def is_aria_server(host: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with urlopen(_health_url(host, port), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("service") == "aria-api" and payload.get("status") == "ok"
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def find_running_aria_port(host: str, start_port: int, max_attempts: int = 50) -> int | None:
    for offset in range(max_attempts):
        candidate = start_port + offset
        if is_aria_server(host, candidate):
            return candidate
    return None


def run_web_server(host: str | None = None, port: int | None = None, debug: bool = False) -> int:
    import threading
    import time
    import webbrowser

    server_config = CONFIG.get("server", {})
    host_value = host or str(server_config.get("host", "127.0.0.1"))
    preferred_port = int(port or server_config.get("port", 8000))

    # If ARIA is already running, reuse that instance instead of starting a duplicate.
    existing_port = find_running_aria_port(host_value, preferred_port)
    if existing_port is not None:
        existing_url = f"http://{host_value}:{existing_port}"
        print(f"ARIA is already running at {existing_url}")

        def _open_existing_browser() -> None:
            time.sleep(0.8)
            webbrowser.open(existing_url)

        threading.Thread(target=_open_existing_browser, daemon=True).start()
        return existing_port

    active_port = find_available_port(host_value, preferred_port)
    url = f"http://{host_value}:{active_port}"

    print(f"ARIA web dashboard running at {url}")
    print("Press CTRL+C to stop the server.")

    def _open_browser() -> None:
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()
    # Disable Flask reloader to avoid auto-switching ports across restarts.
    app.run(host=host_value, port=active_port, debug=debug, use_reloader=False)
    return active_port


if __name__ == "__main__":
    run_web_server()

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from agent import AriaDecisionAgent
from live_data import LiveDataSimulator


class AriaDesktopGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ARIA Desktop Dashboard")
        self.root.geometry("900x560")
        self.root.configure(bg="#f6f9f8")

        self.agent = AriaDecisionAgent("config.json")
        self.simulator = LiveDataSimulator("config.json")
        self.running = True
        self.poll_ms = 3000

        self.metric_vars = {
            "pm25": tk.StringVar(value="--"),
            "aqi": tk.StringVar(value="--"),
            "co2": tk.StringVar(value="--"),
            "temperature": tk.StringVar(value="--"),
            "humidity": tk.StringVar(value="--"),
        }
        self.mode_var = tk.StringVar(value="--")
        self.confidence_var = tk.StringVar(value="--")
        self.risk_var = tk.StringVar(value="--")
        self.reason_var = tk.StringVar(value="Waiting for first reading...")

        self._build_ui()
        self.root.after(300, self.refresh_loop)

    def _build_ui(self) -> None:
        title = tk.Label(
            self.root,
            text="ARIA - Adaptive Response for In-Cabin Air",
            font=("Segoe UI", 20, "bold"),
            bg="#f6f9f8",
            fg="#13364a",
        )
        title.pack(pady=12)

        card_frame = ttk.Frame(self.root)
        card_frame.pack(fill="x", padx=20)

        for index, metric in enumerate(["pm25", "aqi", "co2", "temperature", "humidity"]):
            card = ttk.LabelFrame(card_frame, text=metric.upper())
            card.grid(row=0, column=index, padx=6, pady=8, sticky="nsew")
            value_label = ttk.Label(card, textvariable=self.metric_vars[metric], font=("Segoe UI", 13, "bold"))
            value_label.pack(padx=10, pady=14)
            card_frame.columnconfigure(index, weight=1)

        decision_box = ttk.LabelFrame(self.root, text="Decision Output")
        decision_box.pack(fill="x", padx=20, pady=12)

        ttk.Label(decision_box, text="Mode:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(decision_box, textvariable=self.mode_var, font=("Segoe UI", 11)).grid(row=0, column=1, sticky="w")

        ttk.Label(decision_box, text="Confidence:", font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(decision_box, textvariable=self.confidence_var, font=("Segoe UI", 11)).grid(row=1, column=1, sticky="w")

        ttk.Label(decision_box, text="Risk Level:", font=("Segoe UI", 11, "bold")).grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(decision_box, textvariable=self.risk_var, font=("Segoe UI", 11)).grid(row=2, column=1, sticky="w")

        reason_box = ttk.LabelFrame(self.root, text="Reasoning")
        reason_box.pack(fill="both", expand=True, padx=20, pady=8)
        reason_label = ttk.Label(
            reason_box,
            textvariable=self.reason_var,
            wraplength=820,
            justify="left",
            font=("Segoe UI", 11),
        )
        reason_label.pack(padx=10, pady=12, anchor="w")

        controls = ttk.Frame(self.root)
        controls.pack(fill="x", padx=20, pady=8)

        self.toggle_button = ttk.Button(controls, text="Pause", command=self.toggle_stream)
        self.toggle_button.pack(side="left")

        ttk.Button(controls, text="Refresh Now", command=self.single_refresh).pack(side="left", padx=8)

    def toggle_stream(self) -> None:
        self.running = not self.running
        self.toggle_button.config(text="Pause" if self.running else "Resume")

    def single_refresh(self) -> None:
        reading = self.simulator.next_reading()
        decision = self.agent.decide(reading)
        self._apply(reading, decision)

    def refresh_loop(self) -> None:
        if self.running:
            self.single_refresh()
        self.root.after(self.poll_ms, self.refresh_loop)

    def _apply(self, reading: dict[str, float], decision: dict[str, object]) -> None:
        self.metric_vars["pm25"].set(f"{reading['pm25']} ug/m3")
        self.metric_vars["aqi"].set(str(reading["aqi"]))
        self.metric_vars["co2"].set(f"{reading['co2']} ppm")
        self.metric_vars["temperature"].set(f"{reading['temperature']} C")
        self.metric_vars["humidity"].set(f"{reading['humidity']} %")

        mode_text = str(decision.get("mode", "--")).replace("_", " ").title()
        confidence = float(decision.get("confidence", 0.0))
        self.mode_var.set(mode_text)
        self.confidence_var.set(f"{confidence:.1%}")
        self.risk_var.set(str(decision.get("risk_level", "unknown")).upper())

        alerts = decision.get("alerts", [])
        if alerts:
            alert_text = " Alerts: " + " | ".join(str(item) for item in alerts)
        else:
            alert_text = ""
        self.reason_var.set(f"{decision.get('reason', '')}{alert_text}")


def launch_desktop_gui() -> None:
    root = tk.Tk()
    AriaDesktopGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_desktop_gui()

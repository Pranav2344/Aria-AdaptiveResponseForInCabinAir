const ids = {
  serviceStatus: document.getElementById("serviceStatus"),
  refreshBtn: document.getElementById("refreshBtn"),
  freshModeBtn: document.getElementById("freshModeBtn"),
  recirculationModeBtn: document.getElementById("recirculationModeBtn"),
  bannerOptimalItem: document.getElementById("bannerOptimalItem"),
  bannerOptimalStatus: document.getElementById("bannerOptimalStatus"),
  decisionPanel: document.getElementById("decisionPanel"),
  pm25: document.getElementById("pm25Value"),
  aqi: document.getElementById("aqiValue"),
  co2: document.getElementById("co2Value"),
  temperature: document.getElementById("tempValue"),
  humidity: document.getElementById("humidityValue"),
  mode: document.getElementById("modeValue"),
  confidence: document.getElementById("confidenceValue"),
  risk: document.getElementById("riskValue"),
  reason: document.getElementById("reasonValue"),
  alertsList: document.getElementById("alertsList"),
  historyBody: document.getElementById("historyBody"),
};

let pollIntervalMs = 4000;
let pollTimer = null;
let lastLiveReading = null;
let isManualMode = false;
let lastEffectiveMode = "idle";
let selectedUserMode = null;
let lastRecommendedDecision = null;
let lastDecisionTimestamp = null;

const OPTIMAL_STATUS_MESSAGE = "System is in optimal condition.";

function syncManualUiState() {
  const liveToggle = document.getElementById("liveToggle");
  const manualToggle = document.getElementById("manualToggle");
  const cabinForm = document.getElementById("cabinForm");

  if (isManualMode) {
    manualToggle.classList.add("active");
    liveToggle.classList.remove("active");
    cabinForm.classList.remove("hidden");
  } else {
    liveToggle.classList.add("active");
    manualToggle.classList.remove("active");
    cabinForm.classList.add("hidden");
  }
}

function formatMode(mode) {
  if (!mode) return "--";
  return mode.replace("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function syncUserModeUiState() {
  const freshSelected = selectedUserMode === "fresh_air";
  const recirculationSelected = selectedUserMode === "recirculation";

  ids.freshModeBtn.classList.toggle("active", freshSelected);
  ids.recirculationModeBtn.classList.toggle("active", recirculationSelected);

  ids.freshModeBtn.setAttribute("aria-pressed", freshSelected ? "true" : "false");
  ids.recirculationModeBtn.setAttribute("aria-pressed", recirculationSelected ? "true" : "false");
}

function getConditionState(decision) {
  if (!decision) {
    return {
      state: "unselected",
      text: "Awaiting Data",
      detail: "Waiting for ARIA recommendation...",
    };
  }

  const recommendedMode = String(decision.mode || "");
  if (!selectedUserMode) {
    return {
      state: "unselected",
      text: "Select Mode",
      detail: `ARIA recommends ${formatMode(recommendedMode)}. Select a mode.`,
    };
  }

  if (selectedUserMode === recommendedMode) {
    return {
      state: "optimal",
      text: "Optimal",
      detail: `${OPTIMAL_STATUS_MESSAGE} Your selection matches ARIA recommendation.`,
    };
  }

  return {
    state: "mismatch",
    text: "Not Optimal",
    detail: `Selection mismatch. ARIA recommends ${formatMode(recommendedMode)}, but selected ${formatMode(selectedUserMode)}.`,
  };
}

function updateBannerCondition(decision) {
  const condition = getConditionState(decision);
  ids.bannerOptimalItem.dataset.state = condition.state;
  ids.bannerOptimalStatus.textContent = condition.text;
}

function setServiceStatusFromDecision(decision, timestamp) {
  const stamp = timestamp ? new Date(timestamp).toLocaleTimeString() : null;
  const condition = getConditionState(decision);
  ids.serviceStatus.textContent = stamp
    ? `${condition.detail} Last update: ${stamp}`
    : condition.detail;
}

async function requestJson(url, options = {}, timeoutMs = 8000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const text = await response.text();
    const payload = text ? JSON.parse(text) : {};

    if (!response.ok) {
      const message = payload.error || payload.message || `Request failed (${response.status})`;
      throw new Error(message);
    }

    return payload;
  } finally {
    window.clearTimeout(timer);
  }
}

function setManualMode(enabled) {
  isManualMode = enabled;
  syncManualUiState();

  if (enabled) {
    if (lastLiveReading) {
      document.getElementById("cab_pm25").value = lastLiveReading.pm25 ?? "";
      document.getElementById("cab_aqi").value = lastLiveReading.aqi ?? "";
      document.getElementById("cab_co2").value = lastLiveReading.co2 ?? "";
      document.getElementById("cab_temperature").value = lastLiveReading.temperature ?? "";
      document.getElementById("cab_humidity").value = lastLiveReading.humidity ?? "";
    }
    if (pollTimer) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
    ids.serviceStatus.textContent = "Manual input mode - live polling paused.";
    return;
  }

  if (!pollTimer) {
    fetchCurrent();
    pollTimer = window.setInterval(fetchCurrent, pollIntervalMs);
  }
  ids.serviceStatus.textContent = "Live monitoring active.";
}

function setRiskClass(riskLevel) {
  ids.risk.classList.remove("risk-low", "risk-moderate", "risk-high", "risk-critical");
  const className = `risk-${String(riskLevel || "low").toLowerCase()}`;
  ids.risk.classList.add(className);
}

function updateMetrics(reading) {
  lastLiveReading = reading;
  ids.pm25.textContent = `${reading.pm25} ug/m3`;
  ids.aqi.textContent = `${reading.aqi}`;
  ids.co2.textContent = `${reading.co2} ppm`;
  ids.temperature.textContent = `${reading.temperature} °C`;
  ids.humidity.textContent = `${reading.humidity} %`;
}

function updateBannerDecision(decision) {
  const banner = document.getElementById("driverBanner");
  const bannerMode = document.getElementById("bannerMode");
  const bannerIcon = document.getElementById("bannerIcon");
  const bannerConfidence = document.getElementById("bannerConfidence");
  const bannerRisk = document.getElementById("bannerRisk");
  const bannerTrigger = document.getElementById("bannerTrigger");
  const riskLevel = String(decision.risk_level || "low").toLowerCase();
  const confidenceRaw = Number(decision.confidence || 0.55);
  const confidenceClamped = Number.isFinite(confidenceRaw)
    ? Math.max(0.2, Math.min(1, confidenceRaw))
    : 0.55;

  banner.classList.remove("mode-fresh-air", "mode-recirculation");
  banner.dataset.mode = decision.mode || "idle";
  banner.dataset.risk = riskLevel;
  banner.style.setProperty("--banner-confidence", confidenceClamped.toFixed(3));

  if (decision.mode === "fresh_air") {
    banner.classList.add("mode-fresh-air");
    bannerIcon.textContent = "\u2B06";  // ⬆ up arrow
    bannerMode.textContent = "FRESH AIR MODE";
  } else if (decision.mode === "recirculation") {
    banner.classList.add("mode-recirculation");
    bannerIcon.textContent = "\u21BA";  // ↺ recirculate
    bannerMode.textContent = "RECIRCULATION MODE";
  } else {
    bannerIcon.textContent = "\u2014";
    bannerMode.textContent = "AWAITING DATA\u2026";
  }

  bannerConfidence.textContent = decision.confidence
    ? `${(Number(decision.confidence) * 100).toFixed(1)}%`
    : "--";
  bannerRisk.textContent = (decision.risk_level || "--").toUpperCase();
  bannerRisk.classList.remove("risk-low", "risk-moderate", "risk-high", "risk-critical");
  bannerRisk.classList.add(`risk-${riskLevel}`);
  const trigger = decision.priority_trigger || "";
  bannerTrigger.textContent = TRIGGER_LABELS[trigger] || trigger || "--";
  updateBannerCondition(decision);
}

const TRIGGER_LABELS = {
  co2_critical:                  "CO2 Critical",
  extreme_pollution:             "Extreme Pollution",
  co2_priority_over_pollution:   "Conflict → CO2 Wins",
  pollution_priority_over_co2:   "Conflict → Pollution Wins",
  co2_elevated:                  "CO2 Elevated",
  comfort_out_of_range:          "Comfort Out of Range",
  pm25_aqi_elevated:             "PM2.5 / AQI Elevated",
  co2_mildly_elevated:           "CO2 Mildly Elevated",
  stable_conditions:             "Stable Conditions",
  manual_recirculation_override: "Manual Override",
};

function updateDecision(decision) {
  const effectiveDecision = decision;
  lastRecommendedDecision = effectiveDecision;
  lastDecisionTimestamp = effectiveDecision.timestamp || lastLiveReading?.timestamp || null;
  lastEffectiveMode = effectiveDecision.mode || "idle";
  syncUserModeUiState();

  // Update decision banner
  updateBannerDecision(effectiveDecision);

  const confidenceValue = Math.max(0.25, Math.min(1, Number(effectiveDecision.confidence || 0.45)));
  ids.decisionPanel.dataset.mode = effectiveDecision.mode || "idle";
  ids.decisionPanel.dataset.risk = String(effectiveDecision.risk_level || "low").toLowerCase();
  ids.decisionPanel.style.setProperty("--decision-confidence", confidenceValue.toFixed(3));

  ids.mode.textContent = formatMode(effectiveDecision.mode);
  ids.confidence.textContent = `${(Number(effectiveDecision.confidence || 0) * 100).toFixed(1)}%`;
  ids.risk.textContent = String(effectiveDecision.risk_level || "--").toUpperCase();
  setRiskClass(effectiveDecision.risk_level);
  ids.reason.textContent = effectiveDecision.reason || "No reason available.";

  // Priority trigger
  const triggerEl = document.getElementById("triggerValue");
  const trigger = effectiveDecision.priority_trigger || "";
  triggerEl.textContent = TRIGGER_LABELS[trigger] || trigger || "--";
  triggerEl.className = "decision-value trigger-label";
  if (trigger.startsWith("co2_critical") || trigger === "extreme_pollution") {
    triggerEl.classList.add("trigger-critical");
  } else if (trigger.includes("conflict") || trigger.includes("priority_over")) {
    triggerEl.classList.add("trigger-conflict");
  }

  // Threat scores
  const scores = effectiveDecision.threat_scores || {};
  document.getElementById("co2ThreatValue").textContent =
    scores.co2_threat !== undefined ? (scores.co2_threat * 100).toFixed(1) + "% " + _threatBar(scores.co2_threat) : "--";
  document.getElementById("pollThreatValue").textContent =
    scores.pollution_threat !== undefined ? (scores.pollution_threat * 100).toFixed(1) + "% " + _threatBar(scores.pollution_threat) : "--";

  // Conflict banner
  const conflictBanner = document.getElementById("conflictBanner");
  if (effectiveDecision.conflict_detected) {
    conflictBanner.classList.remove("hidden");
  } else {
    conflictBanner.classList.add("hidden");
  }

  ids.alertsList.innerHTML = "";
  const alerts = Array.isArray(effectiveDecision.alerts) ? effectiveDecision.alerts : [];
  if (!alerts.length) {
    const li = document.createElement("li");
    li.textContent = "No active alerts.";
    ids.alertsList.appendChild(li);
    return;
  }

  alerts.forEach((alert) => {
    const li = document.createElement("li");
    li.textContent = alert;
    ids.alertsList.appendChild(li);
  });
}

function _threatBar(score) {
  const pct = Math.min(1, score);
  const filled = Math.round(pct * 8);
  return "["+"█".repeat(filled)+"░".repeat(8 - filled)+"]";
}

async function loadHistory() {
  const payload = await requestJson("/api/history?limit=12");
  const history = payload.history || [];

  ids.historyBody.innerHTML = "";
  if (!history.length) {
    ids.historyBody.innerHTML = "<tr><td colspan='6'>No records yet.</td></tr>";
    return;
  }

  history
    .slice()
    .reverse()
    .forEach((entry) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${new Date(entry.timestamp).toLocaleString()}</td>
        <td>${formatMode(entry.mode)}</td>
        <td>${String(entry.risk_level || "").toUpperCase()}</td>
        <td>${entry.pm25}</td>
        <td>${entry.aqi}</td>
        <td>${entry.co2}</td>
      `;
      ids.historyBody.appendChild(tr);
    });
}

async function fetchCurrent() {
  ids.serviceStatus.textContent = "Fetching live sample...";
  try {
    const payload = await requestJson("/api/current");
    updateMetrics(payload.reading);
    updateDecision(payload.decision);
    lastDecisionTimestamp = payload.reading?.timestamp || payload.decision?.timestamp || null;
    setServiceStatusFromDecision(payload.decision, payload.reading?.timestamp);
    
    // Trigger extended features update
    if (window.onDecisionUpdated) {
      window.onDecisionUpdated(payload.reading, payload.decision);
    }
    
    await loadHistory();
  } catch (error) {
    console.error(error);
    ids.serviceStatus.textContent = "Live data fetch failed. Retrying...";
    throw error;
  }
}

async function bootstrap() {
  try {
    const config = await requestJson("/api/config");
    const sec = Number(config.poll_interval_seconds || 4);
    pollIntervalMs = Math.max(2, sec) * 1000;

    await fetchCurrent();
    pollTimer = window.setInterval(async () => {
      try {
        await fetchCurrent();
      } catch (_err) {
        // Keep polling after transient errors.
      }
    }, pollIntervalMs);
  } catch (error) {
    console.error(error);
    ids.serviceStatus.textContent = "Unable to connect to ARIA service.";
  }
}

ids.refreshBtn.addEventListener("click", async () => {
  if (isManualMode) {
    setManualMode(false);
  }
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
  try {
    await fetchCurrent();
  } catch (_err) {
    // Status is handled in fetchCurrent.
  }
  pollTimer = window.setInterval(async () => {
    try {
      await fetchCurrent();
    } catch (_err) {
      // Keep polling after transient errors.
    }
  }, pollIntervalMs);
});

ids.freshModeBtn.addEventListener("click", () => {
  selectedUserMode = "fresh_air";
  syncUserModeUiState();
  updateBannerCondition(lastRecommendedDecision);
  setServiceStatusFromDecision(lastRecommendedDecision, lastDecisionTimestamp);
});

ids.recirculationModeBtn.addEventListener("click", () => {
  selectedUserMode = "recirculation";
  syncUserModeUiState();
  updateBannerCondition(lastRecommendedDecision);
  setServiceStatusFromDecision(lastRecommendedDecision, lastDecisionTimestamp);
});

// ======================================
// LIVE / MANUAL TOGGLE
// ======================================
document.getElementById("liveToggle").addEventListener("click", () => {
  setManualMode(false);
});

document.getElementById("manualToggle").addEventListener("click", () => {
  setManualMode(true);
});

// ======================================
// INLINE CABIN FORM SUBMIT
// ======================================
document.getElementById("cabinForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("cabinAnalyseBtn");
  btn.disabled = true;
  btn.textContent = "Analysing\u2026";

  const payload = {
    pm25: parseFloat(document.getElementById("cab_pm25").value),
    aqi: parseFloat(document.getElementById("cab_aqi").value),
    co2: parseFloat(document.getElementById("cab_co2").value),
    temperature: parseFloat(document.getElementById("cab_temperature").value),
    humidity: parseFloat(document.getElementById("cab_humidity").value),
  };

  const allValuesValid = Object.values(payload).every((value) => Number.isFinite(value));
  if (!allValuesValid) {
    alert("Please enter valid numeric values for all fields.");
    btn.disabled = false;
    btn.textContent = "\u25B6 Analyse These Conditions";
    return;
  }

  // Reflect the entered values in the metric display cards
  ids.pm25.textContent = `${payload.pm25} ug/m3`;
  ids.aqi.textContent = `${payload.aqi}`;
  ids.co2.textContent = `${payload.co2} ppm`;
  ids.temperature.textContent = `${payload.temperature} \u00b0C`;
  ids.humidity.textContent = `${payload.humidity} %`;

  try {
    const data = await requestJson("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    updateDecision(data.decision);
    
    // Trigger extended features update
    if (window.onDecisionUpdated) {
      window.onDecisionUpdated(payload, data.decision);
    }
    
    await loadHistory();
    lastLiveReading = data.reading || payload;
    lastDecisionTimestamp = data.reading?.timestamp || data.decision?.timestamp || null;
    setServiceStatusFromDecision(data.decision, lastDecisionTimestamp);
  } catch (err) {
    console.error(err);
    alert(`Error getting recommendation: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "\u25B6 Analyse These Conditions";
  }
});

syncUserModeUiState();
bootstrap();

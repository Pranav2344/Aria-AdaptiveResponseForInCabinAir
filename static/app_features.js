/* ═══════════════════════════════════════════════════════════════════════════ */
/* ARIA DASHBOARD - EXTENDED FEATURES */
/* Dark Mode, Statistics, Health Recommendations, Settings, Exports, & More */
/* ═══════════════════════════════════════════════════════════════════════════ */

// ───────────────────────────────────────────────────────────────────────────
// 1. DARK MODE TOGGLE
// ───────────────────────────────────────────────────────────────────────────

function initDarkMode() {
  const darkModeToggle = document.getElementById("darkModeToggle");
  const isDarkMode = localStorage.getItem("aria-dark-mode") === "true";
  
  if (isDarkMode) {
    document.body.classList.add("dark-mode");
    darkModeToggle.textContent = "☀️";
  } else {
    darkModeToggle.textContent = "🌙";
  }
  
  darkModeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    const now = document.body.classList.contains("dark-mode");
    localStorage.setItem("aria-dark-mode", now);
    darkModeToggle.textContent = now ? "☀️" : "🌙";
  });
}

// ───────────────────────────────────────────────────────────────────────────
// 2. AIR QUALITY SCORE (0-100)
// ───────────────────────────────────────────────────────────────────────────

function calculateAirQualityScore(reading) {
  if (!reading) return 0;
  
  const pm25 = reading.pm25 || 0;
  const aqi = reading.aqi || 0;
  const co2 = reading.co2 || 0;
  
  let score = 100;
  
  // PM2.5 contribution (0-40 points)
  if (pm25 > 120) score -= 40;
  else if (pm25 > 85) score -= 32;
  else if (pm25 > 50) score -= 20;
  else if (pm25 > 35) score -= 10;
  
  // AQI contribution (0-35 points)
  if (aqi > 220) score -= 35;
  else if (aqi > 170) score -= 28;
  else if (aqi > 120) score -= 18;
  else if (aqi > 100) score -= 9;
  
  // CO2 contribution (0-25 points)
  if (co2 > 1800) score -= 25;
  else if (co2 > 1450) score -= 18;
  else if (co2 > 1200) score -= 12;
  else if (co2 > 1000) score -= 6;
  
  return Math.max(0, Math.round(score));
}

function updateAirQualityScore(reading) {
  if (!reading) return;
  
  const score = calculateAirQualityScore(reading);
  const scoreEl = document.getElementById("aqScore");
  const descEl = document.getElementById("aqScoreDesc");
  
  if (scoreEl) {
    scoreEl.textContent = score;
    const parent = scoreEl.closest(".aq-score-box");
    
    if (score >= 80) {
      descEl.textContent = "Excellent Air Quality";
      parent.className = "aq-score-box good";
    } else if (score >= 60) {
      descEl.textContent = "Good Air Quality";
      parent.className = "aq-score-box good";
    } else if (score >= 40) {
      descEl.textContent = "Moderate Air Quality";
      parent.className = "aq-score-box moderate";
    } else {
      descEl.textContent = "Poor Air Quality";
      parent.className = "aq-score-box poor";
    }
  }
}

// ───────────────────────────────────────────────────────────────────────────
// 3. HEALTH RECOMMENDATIONS
// ───────────────────────────────────────────────────────────────────────────

function generateHealthRecommendations(reading, decision) {
  const recommendations = [];
  
  if (!reading) {
    recommendations.push("Monitor cabin conditions for real-time guidance");
    return recommendations;
  }
  
  // CO2-based recommendations
  if (reading.co2 > 1800) {
    recommendations.push("⚠️ CRITICAL CO2 - Open vents immediately for fresh air");
  } else if (reading.co2 > 1450) {
    recommendations.push("High CO2 levels - Enable fresh air mode to restore oxygen");
  } else if (reading.co2 > 1200) {
    recommendations.push("CO2 is elevated - Switch to fresh air mode soon");
  }
  
  // PM2.5 / AQI recommendations
  if (reading.pm25 > 120 || reading.aqi > 220) {
    recommendations.push("🚫 Extreme outdoor pollution - Use recirculation mode");
    recommendations.push("Keep cabin windows sealed and filter clean");
  } else if (reading.pm25 > 85 || reading.aqi > 170) {
    recommendations.push("High outdoor pollution - Avoid fresh air mode");
    recommendations.push("Clean or replace cabin filter periodically");
  } else if (reading.pm25 > 50 || reading.aqi > 120) {
    recommendations.push("Moderate pollution detected - Monitor air quality");
  }
  
  // Comfort recommendations
  if (reading.temperature < 18 || reading.temperature > 30) {
    recommendations.push("Adjust cabin temperature for better comfort");
  }
  if (reading.humidity < 30 || reading.humidity > 70) {
    recommendations.push("Humidity out of comfort range - adjust climate control");
  }
  
  // General recommendations
  if (recommendations.length === 0) {
    recommendations.push("✅ All parameters within safe ranges - good air quality");
    recommendations.push("Monitor readings regularly for optimal health");
  }
  
  return recommendations;
}

function updateHealthRecommendations(reading, decision) {
  const recsList = document.getElementById("healthRecsList");
  if (!recsList) return;
  
  const recommendations = generateHealthRecommendations(reading, decision);
  recsList.innerHTML = recommendations.map(rec => `<li>${rec}</li>`).join("");
}

// ───────────────────────────────────────────────────────────────────────────
// 4. STATISTICS DASHBOARD
// ───────────────────────────────────────────────────────────────────────────

let decisionHistory = [];

function updateStatistics() {
  if (decisionHistory.length === 0) return;
  
  const totalCount = decisionHistory.length;
  const freshAirCount = decisionHistory.filter(d => d.mode === "fresh_air").length;
  const freshAirPercent = totalCount > 0 ? ((freshAirCount / totalCount) * 100).toFixed(1) : "--";
  
  const confidences = decisionHistory
    .map(d => parseFloat(d.confidence) || 0)
    .filter(c => c > 0);
  const avgConf = confidences.length > 0 ? (confidences.reduce((a, b) => a + b) / confidences.length * 100).toFixed(1) : "--";
  
  const highRiskCount = decisionHistory.filter(d => d.risk_level === "high" || d.risk_level === "critical").length;
  
  const co2Values = decisionHistory
    .map(d => parseFloat(d.co2) || 0)
    .filter(v => v > 0);
  const avgCo2 = co2Values.length > 0 ? (co2Values.reduce((a, b) => a + b) / co2Values.length).toFixed(0) : "--";
  
  const pm25Values = decisionHistory
    .map(d => parseFloat(d.pm25) || 0)
    .filter(v => v > 0);
  const avgPm25 = pm25Values.length > 0 ? (pm25Values.reduce((a, b) => a + b) / pm25Values.length).toFixed(1) : "--";
  
  const update = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  
  update("totalDecisions", totalCount);
  update("freshAirPercent", freshAirPercent + "%");
  update("avgConfidence", avgConf + "%");
  update("highRiskCount", highRiskCount);
  update("avgCo2", avgCo2 + " ppm");
  update("avgPm25", avgPm25 + " µg/m³");
}

// ───────────────────────────────────────────────────────────────────────────
// 5. THREAT LEVEL GAUGES
// ───────────────────────────────────────────────────────────────────────────

function updateThreatGauges(decision) {
  if (!decision) return;
  
  const co2Threat = (decision.threat_scores?.co2_threat || 0) * 100;
  const pollThreat = (decision.threat_scores?.pollution_threat || 0) * 100;
  
  const co2Bar = document.getElementById("co2ThreatBar");
  const pollBar = document.getElementById("pollThreatBar");
  
  if (co2Bar) {
    co2Bar.style.width = co2Threat + "%";
    document.getElementById("co2ThreatLabel").textContent = 
      co2Threat > 50 ? "🔴 High Threat" : (co2Threat > 25 ? "🟡 Moderate" : "🟢 Low");
  }
  
  if (pollBar) {
    pollBar.style.width = pollThreat + "%";
    document.getElementById("pollThreatLabel").textContent = 
      pollThreat > 50 ? "🔴 High Threat" : (pollThreat > 25 ? "🟡 Moderate" : "🟢 Low");
  }
}

// ───────────────────────────────────────────────────────────────────────────
// 6. FILTER EFFICIENCY TRACKER
// ───────────────────────────────────────────────────────────────────────────

let filterUseCounter = 0;

function updateFilterEfficiency() {
  // Estimate filter efficiency based on cycle count and pollution exposure
  let efficiency = 100;
  efficiency -= (filterUseCounter * 0.5); // Degrades with use
  efficiency = Math.max(40, efficiency); // Never below 40%
  
  const effBar = document.getElementById("filterEfficBar");
  const status = document.getElementById("filterStatus");
  
  if (effBar) {
    effBar.style.width = efficiency + "%";
    let statusText = "Filter ";
    if (efficiency >= 80) {
      statusText += "in excellent condition — " + efficiency.toFixed(0) + "% effectiveness";
    } else if (efficiency >= 60) {
      statusText += "in good condition — " + efficiency.toFixed(0) + "% effectiveness";
    } else if (efficiency >= 40) {
      statusText += "degrading — " + efficiency.toFixed(0) + "% effectiveness. Consider replacement soon.";
    } else {
      statusText += "needs replacement — " + efficiency.toFixed(0) + "% effectiveness";
    }
    if (status) status.textContent = statusText;
  }
}

// ───────────────────────────────────────────────────────────────────────────
// 7. EXPORT TO CSV
// ───────────────────────────────────────────────────────────────────────────

function exportDecisionsToCSV() {
  if (decisionHistory.length === 0) {
    alert("No decision history to export yet.");
    return;
  }
  
  const headers = ["Time (UTC)", "Mode", "Confidence", "Risk Level", "PM2.5", "AQI", "CO2", "Temperature", "Humidity", "Trigger"];
  const rows = decisionHistory.map(d => [
    d.timestamp || "--",
    d.mode || "--",
    (d.confidence * 100).toFixed(1) + "%" || "--",
    d.risk_level || "--",
    d.pm25 || "--",
    d.aqi || "--",
    d.co2 || "--",
    d.temperature || "--",
    d.humidity || "--",
    d.priority_trigger || "--"
  ]);
  
  const csv = [headers, ...rows]
    .map(row => row.map(cell => `"${cell}"`).join(","))
    .join("\n");
  
  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `aria-decisions-${new Date().toISOString().split("T")[0]}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
}

// ───────────────────────────────────────────────────────────────────────────
// 8. EXPORT BUTTON
// ───────────────────────────────────────────────────────────────────────────

function initExportButton() {
  const exportBtn = document.getElementById("exportBtn");

  if (exportBtn) {
    exportBtn.addEventListener("click", exportDecisionsToCSV);
  }
}

// ───────────────────────────────────────────────────────────────────────────
// 9. INTEGRATE WITH EXISTING DECISION UPDATES
// ───────────────────────────────────────────────────────────────────────────

function onDecisionUpdated(reading, decision) {
  // Store decision in history
  if (decision && reading) {
    decisionHistory.push({
      timestamp: decision.timestamp,
      mode: decision.mode,
      confidence: decision.confidence,
      risk_level: decision.risk_level,
      priority_trigger: decision.priority_trigger,
      pm25: reading.pm25,
      aqi: reading.aqi,
      co2: reading.co2,
      temperature: reading.temperature,
      humidity: reading.humidity
    });
    
    filterUseCounter++;
  }
  
  // Update all features
  updateAirQualityScore(reading);
  updateHealthRecommendations(reading, decision);
  updateStatistics();
  updateThreatGauges(decision);
  updateFilterEfficiency();
}

// ───────────────────────────────────────────────────────────────────────────
// 10. INITIALIZE ALL FEATURES ON PAGE LOAD
// ───────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initDarkMode();
  initExportButton();
});

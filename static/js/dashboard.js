let trendChart = null;
let pieChart = null;
let stats = { total: 0, toxic: 0, warning: 0, safe: 0 };
let history = [];

fetch("/api/auth/me")
  .then((res) => res.json())
  .then((data) => {
    if (!data.authenticated) window.location.href = "/login";
    else {
      document.getElementById("username").innerHTML =
        `<i class="fas fa-user-circle"></i> ${data.username}`;
      loadAnalytics();
    }
  });

async function loadAnalytics() {
  try {
    const res = await fetch("/api/analytics");
    const data = await res.json();

    stats = {
      total: data.total || 0,
      toxic: data.toxic_count || 0,
      warning: data.warning_count || 0,
      safe: data.safe_count || 0,
    };

    document.getElementById("totalAnalyses").textContent = stats.total;
    document.getElementById("toxicCount").textContent = stats.toxic;
    document.getElementById("warningCount").textContent = stats.warning;
    document.getElementById("safeCount").textContent = stats.safe;

    updateCharts(data);

    if (data.recent && data.recent.length > 0) {
      const recentList = document.getElementById("recentList");
      recentList.innerHTML = data.recent
        .map(
          (item) => `
                <div class="recent-item">
                    <div class="recent-text">${escapeHtml(item.text)}</div>
                    <div class="recent-score score-${item.level.toLowerCase()}">${item.level} (${item.score}%)</div>
                </div>
            `,
        )
        .join("");
    }
  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

function updateCharts(data) {
  const dates = data.dates || [];
  const toxicData = data.toxic_data || [];
  const warningData = data.warning_data || [];
  const safeData = data.safe_data || [];

  if (trendChart) trendChart.destroy();
  const ctx = document.getElementById("trendChart").getContext("2d");
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Toxic",
          data: toxicData,
          borderColor: "#f44336",
          backgroundColor: "rgba(244,67,54,0.1)",
          tension: 0.4,
          fill: true,
        },
        {
          label: "Warning",
          data: warningData,
          borderColor: "#ff9800",
          backgroundColor: "rgba(255,152,0,0.1)",
          tension: 0.4,
          fill: true,
        },
        {
          label: "Safe",
          data: safeData,
          borderColor: "#00c853",
          backgroundColor: "rgba(0,200,83,0.1)",
          tension: 0.4,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { position: "bottom", labels: { color: "#b0b0d0" } } },
      scales: {
        y: { grid: { color: "#2d2d4a" }, ticks: { color: "#b0b0d0" } },
        x: { grid: { color: "#2d2d4a" }, ticks: { color: "#b0b0d0" } },
      },
    },
  });

  if (pieChart) pieChart.destroy();
  const pieCtx = document.getElementById("pieChart").getContext("2d");
  pieChart = new Chart(pieCtx, {
    type: "doughnut",
    data: {
      labels: ["Toxic", "Warning", "Safe"],
      datasets: [
        {
          data: [stats.toxic, stats.warning, stats.safe],
          backgroundColor: ["#f44336", "#ff9800", "#00c853"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { position: "bottom", labels: { color: "#b0b0d0" } } },
    },
  });
}

async function analyzeText() {
  const text = document.getElementById("textInput").value.trim();
  if (!text) {
    alert("Please enter some text");
    return;
  }

  const btn = document.querySelector(".analyze-btn");
  const originalText = btn.innerHTML;
  btn.innerHTML = '<span class="loading"></span> Analyzing...';
  btn.disabled = true;

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (res.ok) displayResult(data);
    else alert(data.error || "Analysis failed");
  } catch (err) {
    alert("Connection error");
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function displayResult(data) {
  const resultDiv = document.getElementById("result");
  const analysis = data.analysis;
  const color = analysis.color;

  resultDiv.innerHTML = `
        <div class="result-level" style="color: ${color}"><strong>${analysis.toxicity_level}</strong></div>
        <div class="result-score" style="color: ${color}">${analysis.toxicity_score}%</div>
        <div class="result-confidence">ML Confidence: ${analysis.ml_confidence}%</div>
        <div class="result-confidence">ML Prediction: ${analysis.ml_prediction}</div>
        ${data.explicit_toxic_words?.length > 0 ? `<div style="margin-top: 10px;"><strong>Toxic words:</strong> ${data.explicit_toxic_words.join(", ")}</div>` : '<div style="margin-top: 10px;">No toxic words found</div>'}
    `;
  resultDiv.classList.add("show");
  loadAnalytics();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function logout() {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
}

document.getElementById("textInput")?.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") analyzeText();
});

setInterval(loadAnalytics, 30000);

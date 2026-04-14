// ToxiScan AI - Main JavaScript
document.addEventListener("DOMContentLoaded", function () {
  console.log("✅ ToxiScan AI loaded");

  // Get DOM elements
  const textInput = document.getElementById("textInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const clearBtn = document.getElementById("clearBtn");
  const sampleBtn = document.getElementById("sampleBtn");
  const charCount = document.getElementById("charCount");
  const toxicityPercent = document.getElementById("toxicityPercent");
  const toxicityLine = document.getElementById("toxicityLine");
  const toxicityDot = document.getElementById("toxicityDot");
  const statusDot = document.querySelector(".status-dot");
  const statusText = document.querySelector(".status-text");
  const verdictIcon = document.getElementById("verdictIcon");
  const verdictTitle = document.getElementById("verdictTitle");
  const verdictDescription = document.getElementById("verdictDescription");
  const confidenceFill = document.getElementById("confidenceFill");
  const confidenceValue = document.getElementById("confidenceValue");
  const toxicWordsDiv = document.getElementById("toxicWords");
  const patternTags = document.getElementById("patternTags");
  const historyList = document.getElementById("historyList");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const themeToggle = document.querySelector(".theme-toggle");

  // Sample texts
  const sampleTexts = [
    "Great job on the presentation! Very informative and well-organized.",
    "I appreciate your help with this project. Thank you for your support!",
    "This is an interesting perspective I hadn't considered before.",
    "You're an idiot who doesn't know what they're talking about.",
    "This is complete garbage. You should be ashamed of this work.",
    "I hate you and everything you stand for. You're worthless.",
  ];

  // Load history from localStorage
  let analysisHistory =
    JSON.parse(localStorage.getItem("toxicityHistory")) || [];

  // Update character count
  function updateCharCount() {
    const count = textInput.value.length;
    charCount.textContent = count;
    if (count > 400) charCount.style.color = "#f44336";
    else if (count > 300) charCount.style.color = "#ff9800";
    else charCount.style.color = "var(--text-secondary)";
  }

  // Clear input
  function clearInput() {
    textInput.value = "";
    updateCharCount();
    resetResults();
    updateStatus("ready", "Ready to analyze");
    showNotification("Input cleared", "info");
  }

  // Load sample text
  function loadSampleText() {
    const randomText =
      sampleTexts[Math.floor(Math.random() * sampleTexts.length)];
    textInput.value = randomText;
    updateCharCount();
    showNotification("Sample text loaded! Click Analyze to test.", "info");
  }

  // Reset results display
  function resetResults() {
    toxicityPercent.textContent = "0%";
    toxicityPercent.style.color = "#00c853";
    toxicityLine.style.width = "0%";
    toxicityDot.style.left = "0%";
    confidenceValue.textContent = "--%";
    confidenceFill.style.width = "0%";
    verdictIcon.innerHTML = '<i class="fas fa-question-circle"></i>';
    verdictIcon.style.color = "#ff9800";
    verdictTitle.textContent = "Awaiting Analysis";
    verdictDescription.textContent =
      'Enter text and click "Analyze Text" to check for toxicity.';
    toxicWordsDiv.innerHTML =
      '<span class="no-toxic-words">No text analyzed yet</span>';
    patternTags.innerHTML =
      '<span class="pattern-tag safe">No analysis performed</span>';
  }

  // Update status
  function updateStatus(state, message) {
    const colors = {
      ready: "#00c853",
      analyzing: "#ff9800",
      complete: "#6c63ff",
      error: "#f44336",
    };
    statusDot.style.background = colors[state] || colors.ready;
    statusText.textContent = message;
  }

  // Show notification
  function showNotification(message, type) {
    const existing = document.querySelector(".notification");
    if (existing) existing.remove();

    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    const icon =
      type === "success"
        ? "fa-check-circle"
        : type === "warning"
          ? "fa-exclamation-triangle"
          : "fa-info-circle";
    notification.innerHTML = `<i class="fas ${icon}"></i><span>${message}</span>`;
    document.body.appendChild(notification);

    setTimeout(() => notification.classList.add("show"), 10);
    setTimeout(() => {
      notification.classList.remove("show");
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Show/hide loading
  function showLoading(show) {
    loadingOverlay.style.display = show ? "flex" : "none";
  }

  // Display results
  function displayResults(data) {
    const analysis = data.analysis;

    // Update toxicity meter
    toxicityPercent.textContent = `${Math.round(analysis.toxicity_score)}%`;
    toxicityPercent.style.color = analysis.color;

    setTimeout(() => {
      toxicityLine.style.width = `${analysis.toxicity_score}%`;
      toxicityDot.style.left = `${analysis.toxicity_score}%`;
      toxicityDot.style.background = analysis.color;
    }, 100);

    // Update confidence
    confidenceValue.textContent = `${Math.round(analysis.ml_confidence)}%`;
    setTimeout(() => {
      confidenceFill.style.width = `${analysis.ml_confidence}%`;
    }, 300);

    // Update verdict
    const iconMap = {
      Safe: "fa-check-circle",
      Warning: "fa-exclamation-triangle",
      Toxic: "fa-skull-crossbones",
    };
    verdictIcon.innerHTML = `<i class="fas ${iconMap[analysis.toxicity_level]}"></i>`;
    verdictIcon.style.color = analysis.color;
    verdictTitle.textContent = analysis.toxicity_level;
    verdictTitle.style.color = analysis.color;
    verdictDescription.textContent = `ML Confidence: ${analysis.ml_confidence}% | Prediction: ${analysis.ml_prediction}`;

    // Update toxic words
    if (data.explicit_toxic_words && data.explicit_toxic_words.length > 0) {
      toxicWordsDiv.innerHTML = data.explicit_toxic_words
        .map((w) => `<span class="toxic-word">${w}</span>`)
        .join("");
    } else {
      toxicWordsDiv.innerHTML =
        '<span class="no-toxic-words">No explicit toxic words found</span>';
    }

    // Update patterns
    patternTags.innerHTML = `<span class="pattern-tag ${analysis.toxicity_level.toLowerCase()}">${analysis.toxicity_level} Content Detected</span>`;

    // Update status dot
    statusDot.style.background = analysis.color;
  }

  // Add to history
  function addToHistory(text, data) {
    const analysis = data.analysis;
    const historyItem = {
      id: Date.now(),
      text: text.length > 80 ? text.substring(0, 80) + "..." : text,
      fullText: text,
      score: analysis.toxicity_score,
      level: analysis.toxicity_level,
      timestamp: new Date().toLocaleString(),
    };

    analysisHistory.unshift(historyItem);
    if (analysisHistory.length > 10) analysisHistory.pop();
    localStorage.setItem("toxicityHistory", JSON.stringify(analysisHistory));
    loadHistory();
  }

  // Load history
  function loadHistory() {
    if (!historyList) return;

    if (analysisHistory.length === 0) {
      historyList.innerHTML =
        '<div class="history-item"><div class="history-text">No analysis history yet</div></div>';
      return;
    }

    historyList.innerHTML = analysisHistory
      .map(
        (item) => `
            <div class="history-item ${item.level.toLowerCase()}" onclick="document.getElementById('textInput').value = '${item.fullText.replace(/'/g, "\\'")}'; updateCharCount(); document.getElementById('detector').scrollIntoView({ behavior: 'smooth' });">
                <div class="history-text" title="${item.fullText}">${item.text}</div>
                <div class="history-stats">
                    <div class="history-confidence ${item.level.toLowerCase()}">${Math.round(item.score)}%</div>
                    <div class="history-level">${item.level}</div>
                </div>
            </div>
        `,
      )
      .join("");
  }

  // Analyze text - MAIN FUNCTION
  async function analyzeText() {
    const text = textInput.value.trim();

    if (!text) {
      showNotification("Please enter some text to analyze", "warning");
      return;
    }

    showLoading(true);
    updateStatus("analyzing", "Analyzing text...");

    try {
      console.log("Sending request to /api/analyze");

      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });

      const data = await response.json();
      console.log("Response:", data);

      if (response.ok) {
        displayResults(data);
        addToHistory(text, data);
        updateStatus("complete", "Analysis complete");
        showNotification(
          `Analysis complete: ${data.analysis.toxicity_level} (${data.analysis.toxicity_score}%)`,
          "success",
        );
      } else {
        throw new Error(data.error || "Analysis failed");
      }
    } catch (error) {
      console.error("Error:", error);
      showNotification("Analysis failed: " + error.message, "error");
      updateStatus("error", "Error");
    } finally {
      showLoading(false);
    }
  }

  // Theme toggle
  function toggleTheme() {
    const currentTheme = document.body.getAttribute("data-theme") || "dark";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.body.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    const icon = themeToggle.querySelector("i");
    icon.className = newTheme === "dark" ? "fas fa-moon" : "fas fa-sun";
  }

  // Event listeners
  textInput.addEventListener("input", updateCharCount);
  analyzeBtn.addEventListener("click", analyzeText);
  clearBtn.addEventListener("click", clearInput);
  sampleBtn.addEventListener("click", loadSampleText);
  if (themeToggle) themeToggle.addEventListener("click", toggleTheme);

  // Example buttons
  document.querySelectorAll(".example-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const text = this.getAttribute("data-text");
      if (text) {
        textInput.value = text;
        updateCharCount();
        analyzeText();
      }
    });
  });

  // Ctrl+Enter to analyze
  textInput.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key === "Enter") analyzeText();
  });

  // Load saved theme
  const savedTheme = localStorage.getItem("theme") || "dark";
  document.body.setAttribute("data-theme", savedTheme);
  if (themeToggle) {
    const icon = themeToggle.querySelector("i");
    icon.className = savedTheme === "dark" ? "fas fa-moon" : "fas fa-sun";
  }

  // Add notification styles
  if (!document.querySelector("#notification-styles")) {
    const style = document.createElement("style");
    style.id = "notification-styles";
    style.textContent = `
            .notification {
                position: fixed; top: 100px; right: 20px; background: var(--card-bg);
                border-left: 4px solid; padding: 1rem 1.5rem; border-radius: 12px;
                display: flex; align-items: center; gap: 1rem; box-shadow: 0 10px 30px var(--shadow-color);
                transform: translateX(150%); transition: transform 0.3s ease; z-index: 3000;
            }
            .notification.show { transform: translateX(0); }
            .notification.success { border-color: #00c853; }
            .notification.warning { border-color: #ff9800; }
            .notification.danger { border-color: #f44336; }
            .notification.info { border-color: #6c63ff; }
            .notification i { font-size: 1.2rem; }
            .no-toxic-words { color: var(--text-secondary); font-style: italic; }
            .history-item { cursor: pointer; transition: all 0.3s; }
            .history-item:hover { transform: translateX(5px); background: var(--bg-light); }
            .history-level { background: var(--border-color); padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.9rem; }
            .pattern-tag.toxic { background: #f44336; }
            .pattern-tag.warning { background: #ff9800; }
            .pattern-tag.safe { background: #00c853; }
        `;
    document.head.appendChild(style);
  }

  // Initialize
  updateCharCount();
  loadHistory();
  resetResults();
  updateStatus("ready", "Ready to analyze");
  console.log("✅ ToxiScan AI ready to analyze text");
});

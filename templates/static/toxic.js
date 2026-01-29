// Toxicity Detection Website JavaScript
document.addEventListener("DOMContentLoaded", function () {
  // DOM Elements
  const textInput = document.getElementById("textInput");
  const charCount = document.getElementById("charCount");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const clearBtn = document.getElementById("clearBtn");
  const sampleBtn = document.getElementById("sampleBtn");
  const toxicityPercent = document.getElementById("toxicityPercent");
  const toxicityLine = document.getElementById("toxicityLine");
  const toxicityDot = document.getElementById("toxicityDot");
  const statusIndicator = document.getElementById("statusIndicator");
  const statusDot = statusIndicator.querySelector(".status-dot");
  const statusText = statusIndicator.querySelector(".status-text");
  const verdictIcon = document.getElementById("verdictIcon");
  const verdictTitle = document.getElementById("verdictTitle");
  const verdictDescription = document.getElementById("verdictDescription");
  const confidenceFill = document.getElementById("confidenceFill");
  const confidenceValue = document.getElementById("confidenceValue");
  const patternTags = document.getElementById("patternTags");
  const toxicWords = document.getElementById("toxicWords");
  const historyList = document.getElementById("historyList");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const themeToggle = document.querySelector(".theme-toggle");
  const exampleButtons = document.querySelectorAll(".example-btn");
  const navLinks = document.querySelectorAll(".nav-link");

  // Explicit toxic words (same as Python)
  const EXPLICIT_TOXIC_WORDS = new Set([
    "hate",
    "stupid",
    "suck",
    "terrible",
    "worst",
    "fuck",
    "fucking",
    "motherfucker",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "slut",
    "whore",
    "idiot",
    "moron",
    "retard",
    "dumb",
    "loser",
  ]);

  // Toxic patterns for detection
  const TOXIC_PATTERNS = {
    "personal-attack": ["you are", "you're a", "worthless", "pathetic"],
    "hate-speech": ["hate", "despise", "loathe"],
    profanity: ["fuck", "shit", "damn", "hell"],
    insult: ["stupid", "idiot", "moron", "retard"],
    threat: ["kill", "hurt", "die", "burn"],
    discriminatory: ["racist", "sexist", "homophobic", "transphobic"],
  };

  // Sample texts for demonstration
  const SAMPLE_TEXTS = [
    "Great job on the project! I really appreciate your hard work and dedication.",
    "This is okay, but could be improved. Let's work together to make it better.",
    "You are completely wrong and have no idea what you're talking about.",
    "I hate you and everything you stand for. You're a terrible person.",
    "The presentation was informative and well-structured. Good work!",
    "This is the worst thing I've ever seen. You should be ashamed.",
    "Thank you for your help. I couldn't have done it without you!",
    "Your argument is flawed and doesn't make any sense at all.",
    "Amazing effort! The results exceeded all expectations.",
    "You're such an idiot for thinking that way. Get a brain!",
  ];

  // Analysis history
  let analysisHistory =
    JSON.parse(localStorage.getItem("toxicityHistory")) || [];

  // Initialize
  init();

  // Initialize the application
  function init() {
    updateCharCount();
    loadHistory();
    setupEventListeners();
    updateStatus("ready", "Ready to analyze");

    // Check API connection
    checkAPIConnection();
  }

  // Check API connection
  async function checkAPIConnection() {
    try {
      const response = await fetch("/health");
      if (response.ok) {
        console.log("✅ API is connected");
      } else {
        console.warn("⚠️ API connection issue");
      }
    } catch (error) {
      console.warn("⚠️ API not available, using simulation mode");
    }
  }

  // Set up event listeners
  function setupEventListeners() {
    // Text input events
    textInput.addEventListener("input", updateCharCount);

    // Button events
    analyzeBtn.addEventListener("click", analyzeText);
    clearBtn.addEventListener("click", clearInput);
    sampleBtn.addEventListener("click", loadSampleText);

    // Example button events
    exampleButtons.forEach((btn) => {
      btn.addEventListener("click", function () {
        const text = this.getAttribute("data-text");
        textInput.value = text;
        updateCharCount();
      });
    });

    // Theme toggle
    themeToggle.addEventListener("click", toggleTheme);

    // Navigation smooth scroll
    navLinks.forEach((link) => {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        const targetId = this.getAttribute("href");
        const targetSection = document.querySelector(targetId);

        // Update active nav link
        navLinks.forEach((l) => l.classList.remove("active"));
        this.classList.add("active");

        // Scroll to section
        if (targetSection) {
          targetSection.scrollIntoView({ behavior: "smooth" });
        }
      });
    });

    // Analyze on Enter (Ctrl+Enter)
    textInput.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.key === "Enter") {
        analyzeText();
      }
    });
  }

  // Update character count
  function updateCharCount() {
    const count = textInput.value.length;
    charCount.textContent = count;

    // Change color based on length
    if (count > 400) {
      charCount.style.color = "var(--danger-color)";
    } else if (count > 300) {
      charCount.style.color = "var(--warning-color)";
    } else {
      charCount.style.color = "var(--text-secondary)";
    }
  }

  // Clear input
  function clearInput() {
    textInput.value = "";
    updateCharCount();
    resetResults();
    updateStatus("ready", "Ready to analyze");
  }

  // Load sample text
  function loadSampleText() {
    const randomText =
      SAMPLE_TEXTS[Math.floor(Math.random() * SAMPLE_TEXTS.length)];
    textInput.value = randomText;
    updateCharCount();
  }

  // Analyze text for toxicity
  async function analyzeText() {
    const text = textInput.value.trim();

    if (!text) {
      showNotification("Please enter some text to analyze", "warning");
      return;
    }

    // Show loading
    showLoading(true);
    updateStatus("analyzing", "Analyzing text...");

    try {
      // Call the Python backend API - FIXED URL
      const response = await fetch("/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: text }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      // Process and display results
      displayResultsFromAPI(result);
      addToHistory(text, result);
      showLoading(false);
      updateStatus("complete", "Analysis complete");

      // Show notification
      showNotification(
        `Text analyzed: ${result.analysis.toxicity_level}`,
        result.analysis.toxicity_level === "Toxic"
          ? "danger"
          : result.analysis.toxicity_level === "Warning"
            ? "warning"
            : "success",
      );
    } catch (error) {
      console.error("Error calling API:", error);

      // Fallback to simulation if API fails
      showNotification("API connection failed, using simulation", "warning");
      const simulatedResult = simulateToxicityAnalysis(text);
      displayResults(simulatedResult);
      addToHistory(text, simulatedResult);
      showLoading(false);
      updateStatus("complete", "Analysis complete (simulated)");
    }
  }

  // Simulate toxicity analysis (fallback)
  function simulateToxicityAnalysis(text) {
    const cleanedText = text.toLowerCase().trim();
    const words = cleanedText.split(/\s+/);

    // Check for explicit toxic words
    const foundToxicWords = words.filter((word) =>
      EXPLICIT_TOXIC_WORDS.has(word.replace(/[^a-z]/g, "")),
    );

    // Detect toxic patterns
    const detectedPatterns = [];
    for (const [pattern, keywords] of Object.entries(TOXIC_PATTERNS)) {
      if (keywords.some((keyword) => cleanedText.includes(keyword))) {
        detectedPatterns.push(pattern);
      }
    }

    // Calculate toxicity score based on various factors
    let toxicityScore = 0;

    // Factor 1: Explicit toxic words (40% weight)
    if (foundToxicWords.length > 0) {
      toxicityScore += Math.min(foundToxicWords.length * 10, 40);
    }

    // Factor 2: Toxic patterns (30% weight)
    if (detectedPatterns.length > 0) {
      toxicityScore += Math.min(detectedPatterns.length * 8, 30);
    }

    // Factor 3: Text characteristics (30% weight)
    const negativeIndicators = [
      "no",
      "not",
      "never",
      "worst",
      "bad",
      "terrible",
      "awful",
      "hate",
      "dislike",
      "stupid",
      "idiot",
      "dumb",
    ];

    const negativeCount = negativeIndicators.filter((word) =>
      cleanedText.includes(word),
    ).length;

    toxicityScore += Math.min(negativeCount * 3, 30);

    // Add some randomness for demonstration (remove in production)
    toxicityScore += Math.random() * 10;
    toxicityScore = Math.min(Math.max(toxicityScore, 0), 100);

    // Determine toxicity level
    let toxicityLevel, color;
    if (toxicityScore < 30) {
      toxicityLevel = "Safe";
      color = "var(--safe-color)";
    } else if (toxicityScore < 70) {
      toxicityLevel = "Warning";
      color = "var(--warning-color)";
    } else {
      toxicityLevel = "Toxic";
      color = "var(--danger-color)";
    }

    // Calculate confidence (ML model simulation)
    const confidence = 85 + Math.random() * 10; // 85-95% confidence

    return {
      text,
      toxicityScore,
      toxicityLevel,
      color,
      confidence,
      foundToxicWords,
      detectedPatterns,
      timestamp: new Date().toISOString(),
    };
  }

  // Display results from API
  function displayResultsFromAPI(result) {
    const analysis = result.analysis;

    // Update toxicity meter
    toxicityPercent.textContent = `${Math.round(analysis.toxicity_score)}%`;
    toxicityPercent.style.color = analysis.color;

    // Animate the meter
    setTimeout(() => {
      toxicityLine.style.width = `${analysis.toxicity_score}%`;
      toxicityDot.style.left = `${analysis.toxicity_score}%`;
      toxicityDot.style.background = analysis.color;
      toxicityDot.style.boxShadow = `0 0 25px ${analysis.color}90`;
    }, 100);

    // Update confidence meter
    confidenceValue.textContent = `${Math.round(analysis.ml_confidence)}%`;
    setTimeout(() => {
      confidenceFill.style.width = `${analysis.ml_confidence}%`;
    }, 300);

    // Update verdict
    updateVerdictFromAPI(analysis);

    // Update toxic words
    updateToxicWords(result.explicit_toxic_words);

    // Update detected patterns
    updatePatternsFromAPI(result);

    // Update status dot color
    statusDot.style.background = analysis.color;
  }

  // Display simulated results
  function displayResults(result) {
    // Update toxicity meter
    toxicityPercent.textContent = `${Math.round(result.toxicityScore)}%`;
    toxicityPercent.style.color = result.color;

    // Animate the meter
    setTimeout(() => {
      toxicityLine.style.width = `${result.toxicityScore}%`;
      toxicityDot.style.left = `${result.toxicityScore}%`;
      toxicityDot.style.background = result.color;
      toxicityDot.style.boxShadow = `0 0 25px ${result.color}90`;
    }, 100);

    // Update confidence meter
    confidenceValue.textContent = `${Math.round(result.confidence)}%`;
    setTimeout(() => {
      confidenceFill.style.width = `${result.confidence}%`;
    }, 300);

    // Update verdict
    updateVerdict(result);

    // Update toxic words
    updateToxicWords(result.foundToxicWords);

    // Update detected patterns
    updatePatterns(result.detectedPatterns);

    // Update status dot color
    statusDot.style.background = result.color;
  }

  // Update verdict from API result
  function updateVerdictFromAPI(analysis) {
    const iconMap = {
      Safe: "fa-check-circle",
      Warning: "fa-exclamation-triangle",
      Toxic: "fa-skull-crossbones",
    };

    const descriptions = {
      Safe: "This text appears to be non-toxic and safe for most audiences.",
      Warning:
        "This text contains some concerning elements that may require moderation.",
      Toxic:
        "This text contains harmful content that violates community guidelines.",
    };

    verdictIcon.innerHTML = `<i class="fas ${iconMap[analysis.toxicity_level]}"></i>`;
    verdictIcon.style.color = analysis.color;

    verdictTitle.textContent = analysis.toxicity_level;
    verdictTitle.style.color = analysis.color;

    verdictDescription.textContent =
      descriptions[analysis.toxicity_level] ||
      `ML Prediction: ${analysis.ml_prediction} (${analysis.ml_confidence}% confidence)`;

    // Update verdict card border
    const verdictCard = document.querySelector(".verdict-card");
    verdictCard.style.borderLeftColor = analysis.color;
  }

  // Update verdict display
  function updateVerdict(result) {
    const iconMap = {
      Safe: "fa-check-circle",
      Warning: "fa-exclamation-triangle",
      Toxic: "fa-skull-crossbones",
    };

    const descriptions = {
      Safe: "This text appears to be non-toxic and safe for most audiences.",
      Warning:
        "This text contains some concerning elements that may require moderation.",
      Toxic:
        "This text contains harmful content that violates community guidelines.",
    };

    verdictIcon.innerHTML = `<i class="fas ${iconMap[result.toxicityLevel]}"></i>`;
    verdictIcon.style.color = result.color;

    verdictTitle.textContent = result.toxicityLevel;
    verdictTitle.style.color = result.color;

    verdictDescription.textContent = descriptions[result.toxicityLevel];

    // Update verdict card border
    const verdictCard = document.querySelector(".verdict-card");
    verdictCard.style.borderLeftColor = result.color;
  }

  // Update toxic words display
  function updateToxicWords(words) {
    toxicWords.innerHTML = "";

    if (!words || words.length === 0) {
      toxicWords.innerHTML =
        '<span class="no-toxic-words">No explicit toxic words found</span>';
      return;
    }

    words.forEach((word) => {
      const span = document.createElement("span");
      span.className = "toxic-word";
      span.textContent = word;
      toxicWords.appendChild(span);
    });
  }

  // Update detected patterns from API
  function updatePatternsFromAPI(result) {
    patternTags.innerHTML = "";

    if (
      !result.explicit_toxic_words ||
      result.explicit_toxic_words.length === 0
    ) {
      patternTags.innerHTML =
        '<span class="pattern-tag safe">No harmful patterns detected</span>';
      return;
    }

    // Create tags based on toxicity level
    const span = document.createElement("span");
    span.className = "pattern-tag";

    if (result.analysis.toxicity_level === "Toxic") {
      span.classList.add("toxic");
      span.textContent = "Explicit Language";
    } else if (result.analysis.toxicity_level === "Warning") {
      span.classList.add("warning");
      span.textContent = "Warning Signs";
    } else {
      span.classList.add("safe");
      span.textContent = "Clean Text";
    }

    patternTags.appendChild(span);
  }

  // Update detected patterns
  function updatePatterns(patterns) {
    patternTags.innerHTML = "";

    if (patterns.length === 0) {
      patternTags.innerHTML =
        '<span class="pattern-tag safe">No harmful patterns detected</span>';
      return;
    }

    patterns.forEach((pattern) => {
      const span = document.createElement("span");
      span.className = "pattern-tag";

      // Assign appropriate class based on severity
      if (["personal-attack", "threat", "hate-speech"].includes(pattern)) {
        span.classList.add("toxic");
      } else if (["profanity", "insult"].includes(pattern)) {
        span.classList.add("warning");
      } else {
        span.classList.add("safe");
      }

      // Format pattern name for display
      const formattedName = pattern
        .replace("-", " ")
        .replace(/\b\w/g, (l) => l.toUpperCase());
      span.textContent = formattedName;
      patternTags.appendChild(span);
    });
  }

  // Add analysis to history
  function addToHistory(text, result) {
    const toxicityLevel = result.analysis
      ? result.analysis.toxicity_level
      : result.toxicityLevel;
    const toxicityScore = result.analysis
      ? result.analysis.toxicity_score
      : result.toxicityScore;
    const confidence = result.analysis
      ? result.analysis.ml_confidence
      : result.confidence;

    const historyItem = {
      id: Date.now(),
      text: text.length > 100 ? text.substring(0, 100) + "..." : text,
      fullText: text,
      score: toxicityScore,
      level: toxicityLevel,
      confidence: confidence,
      timestamp: new Date().toISOString(),
    };

    analysisHistory.unshift(historyItem);

    // Keep only last 10 items
    if (analysisHistory.length > 10) {
      analysisHistory = analysisHistory.slice(0, 10);
    }

    // Save to localStorage
    localStorage.setItem("toxicityHistory", JSON.stringify(analysisHistory));

    // Update history display
    loadHistory();
  }

  // Load and display history
  function loadHistory() {
    historyList.innerHTML = "";

    if (analysisHistory.length === 0) {
      historyList.innerHTML = `
                <div class="history-item">
                    <div class="history-text">No analysis history yet</div>
                </div>
            `;
      return;
    }

    analysisHistory.forEach((item) => {
      const historyItem = document.createElement("div");
      historyItem.className = `history-item ${item.level.toLowerCase()}`;

      historyItem.innerHTML = `
                <div class="history-text" title="${item.fullText}">${item.text}</div>
                <div class="history-stats">
                    <div class="history-confidence ${item.level.toLowerCase()}">${Math.round(item.score)}%</div>
                    <div class="history-level">${item.level}</div>
                </div>
            `;

      // Click to load text
      historyItem.addEventListener("click", () => {
        textInput.value = item.fullText;
        updateCharCount();

        // Scroll to detector
        document
          .getElementById("detector")
          .scrollIntoView({ behavior: "smooth" });
      });

      historyList.appendChild(historyItem);
    });
  }

  // Reset results display
  function resetResults() {
    toxicityPercent.textContent = "0%";
    toxicityPercent.style.color = "var(--safe-color)";
    toxicityLine.style.width = "0%";
    toxicityDot.style.left = "0%";
    toxicityDot.style.background = "white";

    confidenceValue.textContent = "--%";
    confidenceFill.style.width = "0%";

    verdictIcon.innerHTML = '<i class="fas fa-question-circle"></i>';
    verdictIcon.style.color = "var(--warning-color)";
    verdictTitle.textContent = "Awaiting Analysis";
    verdictTitle.style.color = "var(--text-primary)";
    verdictDescription.textContent =
      'Enter text and click "Analyze Text" to check for toxicity.';

    toxicWords.innerHTML =
      '<span class="no-toxic-words">No text analyzed yet</span>';
    patternTags.innerHTML =
      '<span class="pattern-tag safe">No analysis performed</span>';
  }

  // Update status indicator
  function updateStatus(state, message) {
    const colors = {
      ready: "var(--safe-color)",
      analyzing: "var(--warning-color)",
      complete: "var(--primary-color)",
      error: "var(--danger-color)",
    };

    statusDot.style.background = colors[state] || colors.ready;
    statusText.textContent = message;
  }

  // Toggle theme
  function toggleTheme() {
    const currentTheme = document.body.getAttribute("data-theme") || "dark";
    const newTheme = currentTheme === "dark" ? "light" : "dark";

    document.body.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);

    // Update icon
    const icon = themeToggle.querySelector("i");
    icon.className = newTheme === "dark" ? "fas fa-moon" : "fas fa-sun";
  }

  // Show loading overlay
  function showLoading(show) {
    loadingOverlay.style.display = show ? "flex" : "none";
  }

  // Show notification
  function showNotification(message, type = "info") {
    // Remove existing notification
    const existingNotification = document.querySelector(".notification");
    if (existingNotification) {
      existingNotification.remove();
    }

    // Create notification
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
            <i class="fas ${
              type === "success"
                ? "fa-check-circle"
                : type === "warning"
                  ? "fa-exclamation-triangle"
                  : type === "danger"
                    ? "fa-times-circle"
                    : "fa-info-circle"
            }"></i>
            <span>${message}</span>
        `;

    // Add to DOM
    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.classList.add("show");
    }, 10);

    // Remove after delay
    setTimeout(() => {
      notification.classList.remove("show");
      setTimeout(() => {
        notification.remove();
      }, 300);
    }, 3000);
  }

  // Load saved theme
  const savedTheme = localStorage.getItem("theme") || "dark";
  document.body.setAttribute("data-theme", savedTheme);

  // Update theme icon
  const themeIcon = themeToggle.querySelector("i");
  themeIcon.className = savedTheme === "dark" ? "fas fa-moon" : "fas fa-sun";

  // Add notification styles
  const style = document.createElement("style");
  style.textContent = `
        .notification {
            position: fixed;
            top: 100px;
            right: 20px;
            background: var(--card-bg);
            border-left: 4px solid;
            padding: 1rem 1.5rem;
            border-radius: var(--border-radius);
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: 0 10px 30px var(--shadow-color);
            transform: translateX(150%);
            transition: transform 0.3s ease;
            z-index: 3000;
            max-width: 350px;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification.success {
            border-color: var(--safe-color);
        }
        
        .notification.warning {
            border-color: var(--warning-color);
        }
        
        .notification.danger {
            border-color: var(--danger-color);
        }
        
        .notification.info {
            border-color: var(--primary-color);
        }
        
        .notification i {
            font-size: 1.2rem;
        }
        
        .notification.success i {
            color: var(--safe-color);
        }
        
        .notification.warning i {
            color: var(--warning-color);
        }
        
        .notification.danger i {
            color: var(--danger-color);
        }
        
        .notification.info i {
            color: var(--primary-color);
        }
        
        .no-toxic-words {
            color: var(--text-secondary);
            font-style: italic;
        }
        
        .history-item {
            cursor: pointer;
            transition: var(--transition);
        }
        
        .history-item:hover {
            transform: translateX(5px);
            background: var(--bg-light);
        }
        
        .history-level {
            background: var(--border-color);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }
    `;
  document.head.appendChild(style);
});

/**
 * canopus-humanizer Frontend Script
 * Connects to local FastAPI backend (http://127.0.0.1:8080)
 * with client-side fallback.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Use current origin if served via HTTP(S) (e.g., http://localhost:8080), or fallback for direct file opening
  const API_BASE = window.location.protocol.startsWith("http")
    ? window.location.origin
    : "http://localhost:8080";
  let isApiOnline = false;
  let selectedStyle = "academic";

  // Elements
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("apiStatusText");
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const themeIcon = document.getElementById("themeIcon");

  const modePills = document.querySelectorAll(".mode-pill");
  const intensitySlider = document.getElementById("intensitySlider");
  const intensityVal = document.getElementById("intensityVal");
  const togglePreserveBtn = document.getElementById("togglePreserveBtn");
  const preserveDrawer = document.getElementById("preserveDrawer");
  const protectedTermsInput = document.getElementById("protectedTermsInput");

  const inputText = document.getElementById("inputText");
  const outputText = document.getElementById("outputText");
  const inputStats = document.getElementById("inputStats");
  const outputStats = document.getElementById("outputStats");
  const scoreText = document.getElementById("scoreText");

  const pasteBtn = document.getElementById("pasteBtn");
  const sampleBtn = document.getElementById("sampleBtn");
  const fileUploadInput = document.getElementById("fileUploadInput");
  const clearBtn = document.getElementById("clearBtn");
  const fileUploadNotice = document.getElementById("fileUploadNotice");
  const fileNoticeName = document.getElementById("fileNoticeName");
  const removeFileNoticeBtn = document.getElementById("removeFileNoticeBtn");

  const copyBtn = document.getElementById("copyBtn");
  const downloadBtn = document.getElementById("downloadBtn");
  const humanizeBtn = document.getElementById("humanizeBtn");
  const btnIcon = document.getElementById("btnIcon");
  const btnLabel = document.getElementById("btnLabel");

  // ==========================================================================
  // 1. BACKEND HEALTH CHECK
  // ==========================================================================
  async function checkBackendHealth() {
    try {
      const res = await fetch(`${API_BASE}/v1/health`, { method: "GET", signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        isApiOnline = true;
        if (statusDot) {
          statusDot.style.background = "var(--success)";
          statusDot.style.boxShadow = "0 0 8px var(--success)";
        }
        if (statusText) statusText.textContent = "Engine Ready";
        return;
      }
    } catch (e) {
      // Offline fallback available
    }
    isApiOnline = false;
    if (statusDot) {
      statusDot.style.background = "var(--warning)";
      statusDot.style.boxShadow = "0 0 8px var(--warning)";
    }
    if (statusText) statusText.textContent = "Offline Ready";
  }

  checkBackendHealth();
  setInterval(checkBackendHealth, 15000);

  // ==========================================================================
  // 2. THEME SWITCHER (DARK / LIGHT)
  // ==========================================================================
  function setTheme(isLight) {
    if (isLight) {
      document.body.classList.add("light-mode");
      localStorage.setItem("canopus_theme", "light");
      if (themeIcon) {
        themeIcon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
      }
    } else {
      document.body.classList.remove("light-mode");
      localStorage.setItem("canopus_theme", "dark");
      if (themeIcon) {
        themeIcon.innerHTML = `
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        `;
      }
    }
  }

  const savedTheme = localStorage.getItem("canopus_theme");
  setTheme(savedTheme === "light");

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const isLight = document.body.classList.contains("light-mode");
      setTheme(!isLight);
    });
  }

  // ==========================================================================
  // 3. WRITING MODE & TOOLBAR CONTROLS
  // ==========================================================================
  modePills.forEach(pill => {
    pill.addEventListener("click", () => {
      modePills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      selectedStyle = pill.getAttribute("data-mode");
    });
  });

  if (intensitySlider && intensityVal) {
    intensitySlider.addEventListener("input", (e) => {
      intensityVal.textContent = `${e.target.value}%`;
    });
  }

  if (togglePreserveBtn && preserveDrawer) {
    togglePreserveBtn.addEventListener("click", () => {
      const isHidden = preserveDrawer.style.display === "none";
      preserveDrawer.style.display = isHidden ? "block" : "none";
      togglePreserveBtn.classList.toggle("active", isHidden);
      if (isHidden && protectedTermsInput) {
        protectedTermsInput.focus();
      }
    });
  }

  // ==========================================================================
  // 4. TEXT STATS & EDITOR HELPERS
  // ==========================================================================
  function updateStats() {
    const raw = inputText ? inputText.value : "";
    const trimmed = raw.trim();
    const words = trimmed ? trimmed.split(/\s+/).length : 0;
    const chars = raw.length;

    if (inputStats) {
      inputStats.textContent = `${words} words • ${chars} characters`;
    }
  }

  function updateOutputStats() {
    const raw = outputText ? outputText.value.trim() : "";
    const words = raw ? raw.split(/\s+/).length : 0;
    if (outputStats) {
      outputStats.textContent = `${words} words`;
    }
  }

  if (inputText) {
    inputText.addEventListener("input", updateStats);
  }

  // Paste Action
  if (pasteBtn && inputText) {
    pasteBtn.addEventListener("click", async () => {
      try {
        const clipText = await navigator.clipboard.readText();
        if (clipText) {
          inputText.value = clipText;
          updateStats();
          inputText.focus();
          return;
        }
      } catch (err) {
        // Fallback: prompt or focus
      }
      inputText.focus();
    });
  }

  // Sample Text
  const SAMPLE_TEXT = 
    "Furthermore, it is important to analyze modern artificial intelligence. " +
    "This study plays a key role in demonstrating that machine learning algorithms " +
    "continue to evolve rapidly. In conclusion, findings reveal that optimization " +
    "remains essential, due to the fact that empirical inquiries require rigorous validation.";

  if (sampleBtn && inputText) {
    sampleBtn.addEventListener("click", () => {
      inputText.value = SAMPLE_TEXT;
      updateStats();
      inputText.focus();
    });
  }

  // Clear Action
  if (clearBtn && inputText && outputText) {
    clearBtn.addEventListener("click", () => {
      inputText.value = "";
      outputText.value = "";
      updateStats();
      updateOutputStats();
      if (fileUploadNotice) fileUploadNotice.style.display = "none";
      if (fileUploadInput) fileUploadInput.value = "";
      if (scoreText) scoreText.textContent = "Ready";
    });
  }

  // File Upload Handling
  if (fileUploadInput && inputText) {
    fileUploadInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        const reader = new FileReader();

        reader.onload = (evt) => {
          inputText.value = evt.target.result;
          updateStats();
          if (fileUploadNotice && fileNoticeName) {
            fileNoticeName.textContent = `Loaded: ${file.name}`;
            fileUploadNotice.style.display = "flex";
          }
        };

        reader.readAsText(file);
      }
    });
  }

  if (removeFileNoticeBtn && fileUploadNotice && fileUploadInput) {
    removeFileNoticeBtn.addEventListener("click", () => {
      fileUploadNotice.style.display = "none";
      fileUploadInput.value = "";
    });
  }

  // Copy Output
  if (copyBtn && outputText) {
    copyBtn.addEventListener("click", () => {
      if (!outputText.value) return;
      navigator.clipboard.writeText(outputText.value);
      const orig = copyBtn.innerHTML;
      copyBtn.innerHTML = '<span>✓</span> Copied!';
      copyBtn.style.color = "var(--success)";
      setTimeout(() => {
        copyBtn.innerHTML = orig;
        copyBtn.style.color = "";
      }, 2000);
    });
  }

  // Download Output
  if (downloadBtn && outputText) {
    downloadBtn.addEventListener("click", () => {
      if (!outputText.value) return;
      const blob = new Blob([outputText.value], { type: "text/plain;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "humanized_text.txt";
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  // ==========================================================================
  // 5. HUMANIZATION EXECUTION (Direct REST API + Local Fallback)
  // ==========================================================================
  if (humanizeBtn) {
    humanizeBtn.addEventListener("click", async () => {
      const rawText = inputText ? inputText.value.trim() : "";
      if (!rawText) {
        if (inputText) inputText.focus();
        return;
      }

      // UI Loading State
      humanizeBtn.disabled = true;
      if (btnIcon) btnIcon.innerHTML = '<span class="spinner"></span>';
      if (btnLabel) btnLabel.textContent = "Processing...";

      const intensity = intensitySlider ? parseFloat(intensitySlider.value) : 75.0;
      const protectedTerms = (protectedTermsInput && protectedTermsInput.value)
        ? protectedTermsInput.value.split(",").map(t => t.trim()).filter(Boolean)
        : [];

      const payload = {
        text: rawText,
        intensity: intensity,
        style: selectedStyle,
        protected_terms: protectedTerms
      };

      try {
        const response = await fetch(`${API_BASE}/v1/humanize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(8000)
        });

        if (response.ok) {
          const data = await response.json();
          if (outputText) outputText.value = data.humanized_text;
          updateOutputStats();
          if (scoreText) scoreText.textContent = "Transformation Complete";
        } else {
          throw new Error("API non-200 status");
        }
      } catch (err) {
        // Fallback local transformation
        const fallback = runClientSideDisruption(rawText);
        if (outputText) outputText.value = fallback;
        updateOutputStats();
        if (scoreText) scoreText.textContent = "Transformation Complete";
      } finally {
        humanizeBtn.disabled = false;
        if (btnIcon) btnIcon.textContent = "⚡";
        if (btnLabel) btnLabel.textContent = "Humanize Text";
      }
    });
  }

  // Client-Side Fallback Engine
  function runClientSideDisruption(raw) {
    let text = raw;

    const rewrites = [
      [/\bFurthermore,?\b/gi, "Also,"],
      [/\bMoreover,?\b/gi, "In addition,"],
      [/\bIn conclusion,?\b/gi, "To summarize,"],
      [/\bit is important to delve into\b/gi, "we examine closely"],
      [/\bdelve into\b/gi, "examine"],
      [/\bcomprehensive tapestry\b/gi, "broad synthesis"],
      [/\bplays a pivotal role in illustrating\b/gi, "clearly demonstrates"],
      [/\bplays a pivotal role\b/gi, "occupies a key position"],
      [/\bstands as a testament to\b/gi, "substantiates"],
      [/\bdue to the fact that\b/gi, "because"],
      [/\bin order to\b/gi, "to"],
      [/\bthis research paper\b/gi, "the present work"],
      [/\bwas carried out\b/gi, "was undertaken"],
      [/\bdemonstrate that\b/gi, "reveal that"],
      [/\brobust framework\b/gi, "sound methodology"]
    ];

    rewrites.forEach(([pattern, replacement]) => {
      text = text.replace(pattern, replacement);
    });

    return text;
  }
});

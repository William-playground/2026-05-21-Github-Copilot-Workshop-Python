/* ポモドーロタイマー: カスタマイズ機能対応
 * - タイマー時間（作業: 15/25/35/45分, 休憩: 5/10/15分）
 * - テーマ切り替え（dark / light / focus）
 * - サウンド（開始音 / 終了音 / tick音 のオン/オフ）
 * 設定は localStorage に保存される。
 */
(function () {
  "use strict";

  const STORAGE_KEY = "pomodoro.settings.v1";

  const DEFAULTS = {
    focusMinutes: 25,
    breakMinutes: 5,
    theme: "light", // "light" | "dark" | "focus"
    sounds: {
      start: true,
      end: true,
      tick: false,
    },
  };

  const FOCUS_OPTIONS = [15, 25, 35, 45];
  const BREAK_OPTIONS = [5, 10, 15];
  const THEME_OPTIONS = ["light", "dark", "focus"];

  function loadSettings() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...DEFAULTS, sounds: { ...DEFAULTS.sounds } };
      const parsed = JSON.parse(raw);
      return {
        focusMinutes: FOCUS_OPTIONS.includes(parsed.focusMinutes)
          ? parsed.focusMinutes
          : DEFAULTS.focusMinutes,
        breakMinutes: BREAK_OPTIONS.includes(parsed.breakMinutes)
          ? parsed.breakMinutes
          : DEFAULTS.breakMinutes,
        theme: THEME_OPTIONS.includes(parsed.theme) ? parsed.theme : DEFAULTS.theme,
        sounds: {
          start: parsed.sounds && typeof parsed.sounds.start === "boolean" ? parsed.sounds.start : DEFAULTS.sounds.start,
          end: parsed.sounds && typeof parsed.sounds.end === "boolean" ? parsed.sounds.end : DEFAULTS.sounds.end,
          tick: parsed.sounds && typeof parsed.sounds.tick === "boolean" ? parsed.sounds.tick : DEFAULTS.sounds.tick,
        },
      };
    } catch (_) {
      return { ...DEFAULTS, sounds: { ...DEFAULTS.sounds } };
    }
  }

  function saveSettings(settings) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (_) {
      /* ignore */
    }
  }

  // --- Sound (Web Audio API でビープを生成。音源ファイル不要) ---
  let audioCtx = null;
  function getAudioCtx() {
    if (audioCtx) return audioCtx;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
    return audioCtx;
  }

  function beep({ frequency = 880, durationMs = 120, volume = 0.15, type = "sine" } = {}) {
    const ctx = getAudioCtx();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = frequency;
    gain.gain.value = volume;
    osc.connect(gain).connect(ctx.destination);
    const now = ctx.currentTime;
    gain.gain.setValueAtTime(volume, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + durationMs / 1000);
    osc.start(now);
    osc.stop(now + durationMs / 1000 + 0.02);
  }

  // --- Timer 本体 ---
  function createTimer({ settings, elements, sound }) {
    let mode = "focus"; // "focus" | "break"
    let remaining = settings.focusMinutes * 60;
    let total = remaining;
    let intervalId = null;
    let running = false;

    function format(sec) {
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    function render() {
      elements.time.textContent = format(remaining);
      const progress = total > 0 ? ((total - remaining) / total) * 100 : 0;
      elements.ring.style.background = `conic-gradient(var(--accent) 0 ${progress}%, var(--ring-base) ${progress}% 100%)`;
      elements.ring.setAttribute("aria-label", `進捗 ${Math.round(progress)}%`);
      elements.status.textContent = mode === "focus" ? "作業中" : "休憩中";
      elements.startBtn.textContent = running ? "一時停止" : "開始";
    }

    function durationFor(currentMode) {
      return (currentMode === "focus" ? settings.focusMinutes : settings.breakMinutes) * 60;
    }

    function applyDurationsFromSettings() {
      if (!running) {
        total = durationFor(mode);
        remaining = total;
        render();
      }
    }

    function tick() {
      remaining = Math.max(0, remaining - 1);
      if (settings.sounds.tick && remaining > 0) sound.tick();
      render();
      if (remaining === 0) {
        stop();
        if (settings.sounds.end) sound.end();
        // モードを切り替えて待機状態へ
        mode = mode === "focus" ? "break" : "focus";
        total = durationFor(mode);
        remaining = total;
        render();
      }
    }

    function start() {
      if (running) {
        // 一時停止
        stop();
        return;
      }
      if (settings.sounds.start) sound.start();
      running = true;
      intervalId = window.setInterval(tick, 1000);
      render();
    }

    function stop() {
      running = false;
      if (intervalId !== null) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
      render();
    }

    function reset() {
      stop();
      mode = "focus";
      total = durationFor(mode);
      remaining = total;
      render();
    }

    render();

    return { start, stop, reset, applyDurationsFromSettings };
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  function setupOptionButtons(container, options, selectedValue, onChange) {
    container.innerHTML = "";
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip" + (opt === selectedValue ? " chip-active" : "");
      btn.dataset.value = String(opt);
      btn.textContent = typeof opt === "number" ? `${opt}分` : opt;
      btn.setAttribute("aria-pressed", opt === selectedValue ? "true" : "false");
      btn.addEventListener("click", () => {
        container.querySelectorAll(".chip").forEach((el) => {
          el.classList.remove("chip-active");
          el.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("chip-active");
        btn.setAttribute("aria-pressed", "true");
        onChange(opt);
      });
      container.appendChild(btn);
    });
  }

  function setupThemeButtons(container, selectedTheme, onChange) {
    const labels = { light: "ライト", dark: "ダーク", focus: "フォーカス" };
    container.innerHTML = "";
    THEME_OPTIONS.forEach((theme) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip" + (theme === selectedTheme ? " chip-active" : "");
      btn.dataset.value = theme;
      btn.textContent = labels[theme];
      btn.setAttribute("aria-pressed", theme === selectedTheme ? "true" : "false");
      btn.addEventListener("click", () => {
        container.querySelectorAll(".chip").forEach((el) => {
          el.classList.remove("chip-active");
          el.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("chip-active");
        btn.setAttribute("aria-pressed", "true");
        onChange(theme);
      });
      container.appendChild(btn);
    });
  }

  function init() {
    const settings = loadSettings();
    applyTheme(settings.theme);

    const elements = {
      time: document.querySelector(".time"),
      ring: document.querySelector(".ring"),
      status: document.querySelector(".status"),
      startBtn: document.querySelector('[data-action="start"]'),
      resetBtn: document.querySelector('[data-action="reset"]'),
      settingsToggle: document.querySelector('[data-action="toggle-settings"]'),
      settingsPanel: document.querySelector(".settings-panel"),
      focusOptions: document.querySelector('[data-options="focus"]'),
      breakOptions: document.querySelector('[data-options="break"]'),
      themeOptions: document.querySelector('[data-options="theme"]'),
      soundStart: document.querySelector('[data-sound="start"]'),
      soundEnd: document.querySelector('[data-sound="end"]'),
      soundTick: document.querySelector('[data-sound="tick"]'),
    };

    const sound = {
      start: () => beep({ frequency: 660, durationMs: 140, volume: 0.18 }),
      end: () => {
        beep({ frequency: 880, durationMs: 180, volume: 0.2 });
        setTimeout(() => beep({ frequency: 1175, durationMs: 240, volume: 0.2 }), 200);
      },
      tick: () => beep({ frequency: 1500, durationMs: 30, volume: 0.05, type: "square" }),
    };

    const timer = createTimer({ settings, elements, sound });

    elements.startBtn.addEventListener("click", () => timer.start());
    elements.resetBtn.addEventListener("click", () => timer.reset());

    if (elements.settingsToggle && elements.settingsPanel) {
      elements.settingsToggle.addEventListener("click", () => {
        const isOpen = elements.settingsPanel.hasAttribute("data-open");
        if (isOpen) {
          elements.settingsPanel.removeAttribute("data-open");
          elements.settingsToggle.setAttribute("aria-expanded", "false");
        } else {
          elements.settingsPanel.setAttribute("data-open", "");
          elements.settingsToggle.setAttribute("aria-expanded", "true");
        }
      });
    }

    setupOptionButtons(elements.focusOptions, FOCUS_OPTIONS, settings.focusMinutes, (val) => {
      settings.focusMinutes = val;
      saveSettings(settings);
      timer.applyDurationsFromSettings();
    });

    setupOptionButtons(elements.breakOptions, BREAK_OPTIONS, settings.breakMinutes, (val) => {
      settings.breakMinutes = val;
      saveSettings(settings);
      timer.applyDurationsFromSettings();
    });

    setupThemeButtons(elements.themeOptions, settings.theme, (theme) => {
      settings.theme = theme;
      saveSettings(settings);
      applyTheme(theme);
    });

    function bindSoundToggle(checkbox, key) {
      if (!checkbox) return;
      checkbox.checked = settings.sounds[key];
      checkbox.addEventListener("change", () => {
        settings.sounds[key] = checkbox.checked;
        saveSettings(settings);
      });
    }

    bindSoundToggle(elements.soundStart, "start");
    bindSoundToggle(elements.soundEnd, "end");
    bindSoundToggle(elements.soundTick, "tick");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

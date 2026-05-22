/**
 * ポモドーロタイマー フロント実装（Phase 7 準MVP）
 *
 * 機能:
 * - 25分作業 / 5分短休憩 / 15分長休憩（4セッション毎）の最小タイマー
 * - START / PAUSE / RESUME / RESET（endTimestamp 逆算方式でズレを軽減）
 * - localStorage によるセッション復元
 * - 完了通知（通知音 + ブラウザ通知）
 * - キーボード操作（Space: 開始/一時停止/再開、R: リセット、N: 通知許可）
 */
(function () {
  "use strict";

  const STORAGE_KEY = "pomodoro.session.v1";
  const STATS_KEY = "pomodoro.stats.v1";

  const CONFIG = {
    work: 25 * 60,
    shortBreak: 5 * 60,
    longBreak: 15 * 60,
    longBreakEvery: 4,
  };

  const STATUS_LABEL = {
    work: "作業中",
    short_break: "短休憩中",
    long_break: "長休憩中",
  };

  let state = {
    type: "work",
    status: "idle",
    remainingMs: CONFIG.work * 1000,
    endTimestamp: null,
    completedWorkCount: 0,
  };

  let tickHandle = null;

  // ---------- DOM ----------
  const timeEl = document.querySelector(".time");
  const statusEl = document.querySelector(".status");
  const ringEl = document.querySelector(".ring");
  const startBtn = document.querySelector('[data-action="start"]');
  const resetBtn = document.querySelector('[data-action="reset"]');
  const summaryCountEl = document.querySelector('[data-summary="count"]');
  const summaryFocusEl = document.querySelector('[data-summary="focus"]');
  const liveRegion = document.querySelector("[data-live]");

  // ---------- 永続化 ----------
  function saveState() {
    try {
      const snapshot = { ...state, savedAt: Date.now() };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } catch (e) {
      // localStorage 不可環境では黙って続行
    }
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (!saved || typeof saved !== "object") return;

      state.type = saved.type || "work";
      state.completedWorkCount = saved.completedWorkCount | 0;

      if (saved.status === "running" && typeof saved.endTimestamp === "number") {
        const remaining = saved.endTimestamp - Date.now();
        if (remaining > 0) {
          state.status = "running";
          state.endTimestamp = saved.endTimestamp;
          state.remainingMs = remaining;
        } else {
          state.status = "idle";
          state.remainingMs = 0;
          handleSessionComplete({ silent: true });
          return;
        }
      } else if (saved.status === "paused") {
        state.status = "paused";
        state.remainingMs = Math.max(0, saved.remainingMs | 0);
        state.endTimestamp = null;
      } else {
        state.status = "idle";
        state.remainingMs = (saved.remainingMs | 0) || durationMsFor(state.type);
        state.endTimestamp = null;
      }
    } catch (e) {
      // 破損データは無視
    }
  }

  function loadStats() {
    try {
      const raw = localStorage.getItem(STATS_KEY);
      if (!raw) return { date: todayKey(), count: 0, focusSec: 0 };
      const parsed = JSON.parse(raw);
      if (parsed.date !== todayKey()) {
        return { date: todayKey(), count: 0, focusSec: 0 };
      }
      return parsed;
    } catch (e) {
      return { date: todayKey(), count: 0, focusSec: 0 };
    }
  }

  function saveStats(stats) {
    try {
      localStorage.setItem(STATS_KEY, JSON.stringify(stats));
    } catch (e) {
      // ignore
    }
  }

  function todayKey() {
    const d = new Date();
    return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
  }

  // ---------- ロジック ----------
  function durationMsFor(type) {
    return (
      {
        work: CONFIG.work,
        short_break: CONFIG.shortBreak,
        long_break: CONFIG.longBreak,
      }[type] * 1000
    );
  }

  function nextType(currentType, completedWorkCount) {
    if (currentType === "work") {
      return completedWorkCount % CONFIG.longBreakEvery === 0
        ? "long_break"
        : "short_break";
    }
    return "work";
  }

  function start() {
    if (state.status === "running") return;
    if (state.remainingMs <= 0) state.remainingMs = durationMsFor(state.type);
    state.endTimestamp = Date.now() + state.remainingMs;
    state.status = "running";
    startTick();
    saveState();
    render();
    announce(`${STATUS_LABEL[state.type]}を開始しました`);
  }

  function pause() {
    if (state.status !== "running") return;
    state.remainingMs = Math.max(0, (state.endTimestamp || 0) - Date.now());
    state.endTimestamp = null;
    state.status = "paused";
    stopTick();
    saveState();
    render();
    announce("一時停止しました");
  }

  function resume() {
    if (state.status !== "paused") return;
    start();
  }

  function reset() {
    stopTick();
    state.endTimestamp = null;
    state.status = "idle";
    state.remainingMs = durationMsFor(state.type);
    saveState();
    render();
    announce("リセットしました");
  }

  function handleSessionComplete(opts) {
    const options = opts || {};
    const completedType = state.type;
    stopTick();

    if (completedType === "work") {
      state.completedWorkCount += 1;
      const stats = loadStats();
      stats.count += 1;
      stats.focusSec += CONFIG.work;
      saveStats(stats);
    }

    state.type = nextType(completedType, state.completedWorkCount);
    state.status = "idle";
    state.remainingMs = durationMsFor(state.type);
    state.endTimestamp = null;
    saveState();
    render();

    if (!options.silent) {
      notifyCompletion(completedType);
    }
    announce(
      `${STATUS_LABEL[completedType]}が完了しました。次は${STATUS_LABEL[state.type]}です。`
    );
  }

  // ---------- Tick ----------
  function startTick() {
    stopTick();
    tickHandle = setInterval(onTick, 250);
  }

  function stopTick() {
    if (tickHandle !== null) {
      clearInterval(tickHandle);
      tickHandle = null;
    }
  }

  function onTick() {
    if (state.status !== "running" || state.endTimestamp == null) return;
    state.remainingMs = Math.max(0, state.endTimestamp - Date.now());
    if (state.remainingMs <= 0) {
      handleSessionComplete();
    } else {
      render();
    }
  }

  // ---------- 通知 ----------
  function notifyCompletion(completedType) {
    playBeep();
    const title =
      completedType === "work" ? "作業セッション完了！" : "休憩終了！";
    const body =
      completedType === "work"
        ? "お疲れさまでした。休憩を取りましょう。"
        : "次の作業セッションを始めましょう。";

    if ("Notification" in window && Notification.permission === "granted") {
      try {
        new Notification(title, { body });
      } catch (e) {
        // iOS Safari 等で失敗する場合は無視
      }
    }
  }

  function playBeep() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = 880;
      osc.connect(gain);
      gain.connect(ctx.destination);
      const now = ctx.currentTime;
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.3, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);
      osc.start(now);
      osc.stop(now + 0.65);
      osc.onended = function () {
        ctx.close();
      };
    } catch (e) {
      // ignore
    }
  }

  function ensureNotificationPermission() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") {
      try {
        Notification.requestPermission().catch(function () {});
      } catch (e) {
        // ignore
      }
    }
  }

  // ---------- 描画 ----------
  function formatTime(ms) {
    const totalSec = Math.ceil(ms / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function render() {
    if (!timeEl) return;
    const total = durationMsFor(state.type);
    const remaining = state.remainingMs;
    const progress = total === 0 ? 0 : 1 - remaining / total;
    const pct = Math.max(0, Math.min(100, Math.round(progress * 100)));

    timeEl.textContent = formatTime(remaining);
    if (statusEl) statusEl.textContent = STATUS_LABEL[state.type];

    if (ringEl) {
      ringEl.style.background = `conic-gradient(var(--accent) 0 ${pct}%, var(--ring-base) ${pct}% 100%)`;
      ringEl.setAttribute("aria-label", `進捗 ${pct}%`);
      ringEl.setAttribute("aria-valuenow", String(pct));
    }

    if (startBtn) {
      if (state.status === "running") {
        startBtn.textContent = "一時停止";
        startBtn.dataset.mode = "pause";
        startBtn.setAttribute("aria-label", "タイマーを一時停止");
      } else if (state.status === "paused") {
        startBtn.textContent = "再開";
        startBtn.dataset.mode = "resume";
        startBtn.setAttribute("aria-label", "タイマーを再開");
      } else {
        startBtn.textContent = "開始";
        startBtn.dataset.mode = "start";
        startBtn.setAttribute("aria-label", "タイマーを開始");
      }
    }

    const stats = loadStats();
    if (summaryCountEl) summaryCountEl.textContent = String(stats.count);
    if (summaryFocusEl) {
      const h = Math.floor(stats.focusSec / 3600);
      const m = Math.floor((stats.focusSec % 3600) / 60);
      summaryFocusEl.textContent = h > 0 ? `${h}時間${m}分` : `${m}分`;
    }

    document.title = `${formatTime(remaining)} - ${STATUS_LABEL[state.type]}`;
  }

  function announce(message) {
    if (liveRegion) liveRegion.textContent = message;
  }

  // ---------- イベント ----------
  function handlePrimary() {
    if (state.status === "running") pause();
    else if (state.status === "paused") resume();
    else start();
    ensureNotificationPermission();
  }

  function bindEvents() {
    if (startBtn) startBtn.addEventListener("click", handlePrimary);
    if (resetBtn) resetBtn.addEventListener("click", reset);

    document.addEventListener("keydown", function (e) {
      const target = e.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          ["INPUT", "TEXTAREA", "SELECT"].indexOf(target.tagName) !== -1)
      ) {
        return;
      }
      // ボタンへの Space/Enter のデフォルト動作は維持
      if (
        target instanceof HTMLElement &&
        target.tagName === "BUTTON" &&
        (e.code === "Space" || e.key === "Enter")
      ) {
        return;
      }
      if (e.code === "Space") {
        e.preventDefault();
        handlePrimary();
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        reset();
      } else if (e.key === "n" || e.key === "N") {
        ensureNotificationPermission();
      }
    });

    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && state.status === "running") {
        onTick();
      }
    });

    window.addEventListener("beforeunload", saveState);
  }

  // ---------- 起動 ----------
  function init() {
    loadState();
    bindEvents();
    if (state.status === "running") {
      startTick();
    }
    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

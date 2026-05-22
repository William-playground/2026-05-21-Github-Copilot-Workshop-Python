"use strict";

(() => {
  // ---- 状態 -----------------------------------------------------------------
  const DEFAULT_SETTINGS = Object.freeze({
    focus_minutes: 25,
    short_break_minutes: 5,
    long_break_minutes: 15,
    long_break_interval: 4,
  });

  let settings = { ...DEFAULT_SETTINGS };
  // 次セッションに反映するための保留中設定（実行中は即時適用しない）
  let pendingSettings = null;

  let phase = "focus"; // "focus" | "short_break" | "long_break"
  let completedFocusInSet = 0;

  let runState = "idle"; // "idle" | "running" | "paused"
  let totalSeconds = settings.focus_minutes * 60;
  let remainingSeconds = totalSeconds;
  let endTimestamp = null;
  let tickHandle = null;

  // ---- 要素 -----------------------------------------------------------------
  const $status = document.getElementById("status");
  const $time = document.getElementById("time");
  const $ring = document.getElementById("ring");
  const $primary = document.getElementById("primary-btn");
  const $reset = document.getElementById("reset-btn");
  const $error = document.getElementById("error-banner");
  const $count = document.getElementById("summary-count");
  const $focus = document.getElementById("summary-focus");
  const $form = document.getElementById("settings-form");

  // ---- ユーティリティ --------------------------------------------------------
  function formatMMSS(seconds) {
    const s = Math.max(0, Math.round(seconds));
    const mm = Math.floor(s / 60).toString().padStart(2, "0");
    const ss = (s % 60).toString().padStart(2, "0");
    return `${mm}:${ss}`;
  }

  function formatFocusTotal(seconds) {
    const total = Math.max(0, Math.floor(seconds / 60));
    if (total < 60) return `${total}分`;
    const h = Math.floor(total / 60);
    const m = total % 60;
    return m === 0 ? `${h}時間` : `${h}時間${m}分`;
  }

  function phaseLabel() {
    if (phase === "focus") return "作業中";
    if (phase === "short_break") return "短休憩中";
    return "長休憩中";
  }

  function phaseDurationSeconds() {
    if (phase === "focus") return settings.focus_minutes * 60;
    if (phase === "short_break") return settings.short_break_minutes * 60;
    return settings.long_break_minutes * 60;
  }

  function showError(message) {
    if (!$error) return;
    $error.textContent = message;
    $error.dataset.kind = "error";
    $error.hidden = false;
  }

  function showInfo(message) {
    if (!$error) return;
    $error.textContent = message;
    $error.dataset.kind = "info";
    $error.hidden = false;
  }

  function clearMessage() {
    if (!$error) return;
    $error.textContent = "";
    delete $error.dataset.kind;
    $error.hidden = true;
  }

  // ---- 表示更新 --------------------------------------------------------------
  function render() {
    if ($status) $status.textContent = phaseLabel();
    if ($time) $time.textContent = formatMMSS(remainingSeconds);
    if ($ring) {
      const progress = totalSeconds > 0
        ? Math.min(100, Math.max(0, ((totalSeconds - remainingSeconds) / totalSeconds) * 100))
        : 0;
      $ring.style.background = `conic-gradient(var(--accent) 0 ${progress}%, var(--ring-base) ${progress}% 100%)`;
      $ring.setAttribute("aria-label", `進捗 ${Math.round(progress)}%`);
    }
    if ($primary) {
      if (runState === "running") $primary.textContent = "一時停止";
      else if (runState === "paused") $primary.textContent = "再開";
      else $primary.textContent = "開始";
    }
  }

  function renderStats(stats) {
    if ($count) $count.textContent = String(stats.completed_count ?? 0);
    if ($focus) $focus.textContent = formatFocusTotal(stats.focus_seconds_total ?? 0);
  }

  function renderSettingsForm(s) {
    if (!$form) return;
    for (const key of Object.keys(DEFAULT_SETTINGS)) {
      const input = $form.elements.namedItem(key);
      if (input) input.value = String(s[key]);
    }
  }

  // ---- タイマー --------------------------------------------------------------
  function stopTick() {
    if (tickHandle !== null) {
      window.clearInterval(tickHandle);
      tickHandle = null;
    }
  }

  function startTick() {
    stopTick();
    tickHandle = window.setInterval(() => {
      if (runState !== "running" || endTimestamp === null) return;
      remainingSeconds = Math.max(0, Math.round((endTimestamp - Date.now()) / 1000));
      render();
      if (remainingSeconds <= 0) {
        handleCompletion();
      }
    }, 250);
  }

  function applyPendingSettingsIfAny() {
    if (pendingSettings) {
      settings = pendingSettings;
      pendingSettings = null;
    }
  }

  function resetTimer(nextPhase) {
    stopTick();
    runState = "idle";
    if (nextPhase) phase = nextPhase;
    applyPendingSettingsIfAny();
    totalSeconds = phaseDurationSeconds();
    remainingSeconds = totalSeconds;
    endTimestamp = null;
    render();
  }

  function startTimer() {
    if (runState === "idle") {
      totalSeconds = phaseDurationSeconds();
      remainingSeconds = totalSeconds;
    }
    endTimestamp = Date.now() + remainingSeconds * 1000;
    runState = "running";
    startTick();
    render();
  }

  function pauseTimer() {
    if (runState !== "running" || endTimestamp === null) return;
    remainingSeconds = Math.max(0, Math.round((endTimestamp - Date.now()) / 1000));
    runState = "paused";
    endTimestamp = null;
    stopTick();
    render();
  }

  function nextPhaseAfterFocus() {
    completedFocusInSet += 1;
    if (
      settings.long_break_interval > 0 &&
      completedFocusInSet % settings.long_break_interval === 0
    ) {
      return "long_break";
    }
    return "short_break";
  }

  async function handleCompletion() {
    stopTick();
    const finishedPhase = phase;
    const duration = totalSeconds;
    runState = "idle";
    endTimestamp = null;

    try {
      await postSession({
        type: finishedPhase === "focus" ? "focus" : "break",
        duration_seconds: duration,
        completed_at: new Date().toISOString(),
      });
      clearMessage();
      await refreshStats();
    } catch (err) {
      showError(`セッション記録に失敗しました: ${err.message}`);
    }

    const next = finishedPhase === "focus" ? nextPhaseAfterFocus() : "focus";
    resetTimer(next);
  }

  // ---- API -----------------------------------------------------------------
  async function fetchJson(url, options) {
    let res;
    try {
      res = await fetch(url, options);
    } catch (_err) {
      throw new Error("ネットワークエラー（サーバーに接続できません）");
    }
    let body = null;
    try {
      body = await res.json();
    } catch (_) {
      // 空ボディは許容
    }
    if (!res.ok) {
      const detail = body && body.error ? body.error : `HTTP ${res.status}`;
      throw new Error(detail);
    }
    return body;
  }

  function postSession(payload) {
    return fetchJson("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function refreshStats() {
    try {
      const stats = await fetchJson("/api/stats/today");
      renderStats(stats);
    } catch (err) {
      showError(`今日の進捗の取得に失敗しました: ${err.message}`);
    }
  }

  async function loadSettings() {
    try {
      const data = await fetchJson("/api/settings");
      settings = { ...DEFAULT_SETTINGS, ...data };
      renderSettingsForm(settings);
      if (runState === "idle") {
        totalSeconds = phaseDurationSeconds();
        remainingSeconds = totalSeconds;
      }
      render();
    } catch (err) {
      showError(`設定の取得に失敗しました: ${err.message}`);
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    if (!$form) return;
    const data = new FormData($form);
    const payload = {};
    for (const key of Object.keys(DEFAULT_SETTINGS)) {
      const v = Number(data.get(key));
      if (!Number.isInteger(v) || v <= 0) {
        showError(`${key} は 1 以上の整数を入力してください`);
        return;
      }
      payload[key] = v;
    }
    try {
      const saved = await fetchJson("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      // 実行中・一時停止中は次セッションに反映するため pending に積む
      if (runState === "idle") {
        settings = { ...DEFAULT_SETTINGS, ...saved };
        totalSeconds = phaseDurationSeconds();
        remainingSeconds = totalSeconds;
        render();
        showInfo("設定を保存しました。");
      } else {
        pendingSettings = { ...DEFAULT_SETTINGS, ...saved };
        showInfo("設定を保存しました。次のセッションから反映されます。");
      }
    } catch (err) {
      showError(`設定の保存に失敗しました: ${err.message}`);
    }
  }

  // ---- イベント --------------------------------------------------------------
  if ($primary) {
    $primary.addEventListener("click", () => {
      if (runState === "running") pauseTimer();
      else startTimer();
    });
  }
  if ($reset) {
    $reset.addEventListener("click", () => resetTimer());
  }
  if ($form) {
    $form.addEventListener("submit", saveSettings);
  }

  // ---- 初期化 ---------------------------------------------------------------
  render();
  loadSettings().then(refreshStats);
})();

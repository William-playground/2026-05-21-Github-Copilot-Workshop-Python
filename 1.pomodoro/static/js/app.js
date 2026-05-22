/**
 * Phase 2: フロント単体タイマー（API未接続）
 *
 * UI と TimerEngine を接続する。
 * - START / PAUSE / RESUME / RESET ボタン操作
 * - 残り時間 mm:ss 表示
 * - 円形プログレス（CSS 変数 --progress を更新）
 * - 状態表示（作業中 / 休憩中）
 *
 * 完了時は作業 ↔ 休憩 を切り替え、自動開始はせず idle 状態に戻る。
 * セッション完了の集計や永続化はフェーズ4以降で API 接続時に行う。
 */
(function () {
  "use strict";

  var FOCUS_SECONDS = 25 * 60;
  var BREAK_SECONDS = 5 * 60;

  document.addEventListener("DOMContentLoaded", function () {
    var timeEl = document.getElementById("timer-time");
    var statusEl = document.getElementById("timer-status");
    var ringEl = document.getElementById("timer-ring");
    var primaryBtn = document.getElementById("btn-primary-action");
    var resetBtn = document.getElementById("btn-reset");

    if (!timeEl || !statusEl || !ringEl || !primaryBtn || !resetBtn) {
      return;
    }

    var mode = "focus"; // "focus" | "break"

    var engine = new window.TimerEngine({
      durationSeconds: FOCUS_SECONDS,
      onTick: render,
      onComplete: onComplete,
    });

    primaryBtn.addEventListener("click", function () {
      var state = engine.getState();
      if (state === "running") {
        engine.pause();
      } else if (state === "paused") {
        engine.resume();
      } else {
        engine.start();
      }
    });

    resetBtn.addEventListener("click", function () {
      mode = "focus";
      engine.setDurationSeconds(FOCUS_SECONDS);
      engine.reset();
    });

    render();

    function onComplete() {
      // フェーズ2の範囲では自動連鎖はせず、モードだけ切り替えて idle に戻す。
      mode = mode === "focus" ? "break" : "focus";
      engine.setDurationSeconds(mode === "focus" ? FOCUS_SECONDS : BREAK_SECONDS);
      engine.reset();
    }

    function render() {
      var remaining = engine.getRemainingSeconds();
      timeEl.textContent = window.TimerEngine.formatMmSs(remaining);

      var pct = Math.round(engine.getProgress() * 100);
      ringEl.style.setProperty("--progress", pct + "%");
      ringEl.setAttribute("aria-label", "進捗 " + pct + "%");

      statusEl.textContent = mode === "focus" ? "作業中" : "休憩中";

      var state = engine.getState();
      if (state === "running") {
        primaryBtn.textContent = "一時停止";
      } else if (state === "paused") {
        primaryBtn.textContent = "再開";
      } else {
        primaryBtn.textContent = "開始";
      }
    }
  });
})();

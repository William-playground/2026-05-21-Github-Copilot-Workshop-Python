/**
 * TimerEngine
 *
 * 残り時間を `endTimestamp` から逆算する方式で管理するタイマーエンジン。
 * `setInterval` による加算ではなく現在時刻との差分を都度求めるため、
 * タブ非アクティブ時のドリフトを抑制できる。
 *
 * 状態:
 *   - "idle"    : 未開始 / リセット直後
 *   - "running" : 動作中
 *   - "paused"  : 一時停止中（残り時間を保持）
 *   - "done"    : 残り0秒に到達
 *
 * 副作用は `setInterval` / `clearInterval` と `onTick` / `onComplete` のみで、
 * 時刻取得は `now()` を差し替えることでテスト可能。
 */
(function (global) {
  "use strict";

  function TimerEngine(options) {
    options = options || {};
    this._durationSeconds = options.durationSeconds || 25 * 60;
    this._now = options.now || function () { return Date.now(); };
    this._onTick = options.onTick || function () {};
    this._onComplete = options.onComplete || function () {};
    this._tickIntervalMs = options.tickIntervalMs || 250;

    this._state = "idle";
    this._endTimestamp = null;
    this._remainingMs = this._durationSeconds * 1000;
    this._intervalId = null;
  }

  TimerEngine.prototype.getState = function () {
    return this._state;
  };

  TimerEngine.prototype.getDurationSeconds = function () {
    return this._durationSeconds;
  };

  TimerEngine.prototype.setDurationSeconds = function (seconds) {
    this._durationSeconds = seconds;
    if (this._state === "idle") {
      this._remainingMs = seconds * 1000;
    }
  };

  TimerEngine.prototype.getRemainingMs = function () {
    if (this._state === "running") {
      return Math.max(0, this._endTimestamp - this._now());
    }
    return this._remainingMs;
  };

  TimerEngine.prototype.getRemainingSeconds = function () {
    return Math.ceil(this.getRemainingMs() / 1000);
  };

  /** 経過率 (0..1) を返す */
  TimerEngine.prototype.getProgress = function () {
    var total = this._durationSeconds * 1000;
    if (total <= 0) return 0;
    var elapsed = total - this.getRemainingMs();
    if (elapsed < 0) return 0;
    if (elapsed > total) return 1;
    return elapsed / total;
  };

  TimerEngine.prototype.start = function () {
    if (this._state === "running") return;
    if (this._state === "idle" || this._state === "done") {
      this._remainingMs = this._durationSeconds * 1000;
    }
    this._endTimestamp = this._now() + this._remainingMs;
    this._state = "running";
    this._scheduleTicks();
    this._onTick(this);
  };

  TimerEngine.prototype.pause = function () {
    if (this._state !== "running") return;
    this._remainingMs = Math.max(0, this._endTimestamp - this._now());
    this._state = "paused";
    this._clearTicks();
    this._onTick(this);
  };

  TimerEngine.prototype.resume = function () {
    if (this._state !== "paused") return;
    this._endTimestamp = this._now() + this._remainingMs;
    this._state = "running";
    this._scheduleTicks();
    this._onTick(this);
  };

  TimerEngine.prototype.reset = function () {
    this._clearTicks();
    this._state = "idle";
    this._endTimestamp = null;
    this._remainingMs = this._durationSeconds * 1000;
    this._onTick(this);
  };

  TimerEngine.prototype._scheduleTicks = function () {
    var self = this;
    this._clearTicks();
    this._intervalId = global.setInterval(function () {
      self._tick();
    }, this._tickIntervalMs);
  };

  TimerEngine.prototype._clearTicks = function () {
    if (this._intervalId !== null) {
      global.clearInterval(this._intervalId);
      this._intervalId = null;
    }
  };

  TimerEngine.prototype._tick = function () {
    if (this._state !== "running") return;
    var remaining = this._endTimestamp - this._now();
    if (remaining <= 0) {
      this._remainingMs = 0;
      this._state = "done";
      this._clearTicks();
      this._onTick(this);
      this._onComplete(this);
      return;
    }
    this._onTick(this);
  };

  /** "mm:ss" 形式にフォーマット */
  TimerEngine.formatMmSs = function (totalSeconds) {
    var s = Math.max(0, Math.floor(totalSeconds));
    var m = Math.floor(s / 60);
    var r = s % 60;
    return String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
  };

  global.TimerEngine = TimerEngine;
})(typeof window !== "undefined" ? window : globalThis);

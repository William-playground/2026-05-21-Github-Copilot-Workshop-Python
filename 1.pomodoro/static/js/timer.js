/*
 * ポモドーロタイマー: 視覚的フィードバック
 *
 * - SVG ベースの円形プログレスバーを滑らかにアニメーションさせる
 * - 残り時間に応じてリング色を青→黄→赤にグラデーション変化させる
 * - 集中時間中は背景にパーティクル/波紋アニメーションを表示する
 */
(function () {
  "use strict";

  const WORK_DURATION_SEC = 25 * 60;

  // r=54 の円周。HTML/CSS の値と一致させる必要がある。
  const RING_CIRCUMFERENCE = 2 * Math.PI * 54;

  const timeEl = document.querySelector(".time");
  const ringEl = document.querySelector(".ring");
  const ringProgress = document.querySelector(".ring-progress");
  const statusEl = document.querySelector(".status");
  const startBtn = document.querySelector('[data-action="start"]');
  const resetBtn = document.querySelector('[data-action="reset"]');
  const canvas = document.querySelector(".bg-fx");

  if (!timeEl || !ringProgress || !startBtn || !resetBtn) {
    return;
  }

  // ストロークの dasharray を実値で設定（CSS の値と整合させる）
  ringProgress.style.strokeDasharray = String(RING_CIRCUMFERENCE);

  let totalSec = WORK_DURATION_SEC;
  let remainingSec = WORK_DURATION_SEC;
  let endTimestamp = null; // 実時間ベースの終了時刻 (ms)
  let rafId = null;
  let running = false;

  function formatTime(sec) {
    const s = Math.max(0, Math.ceil(sec));
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  }

  /**
   * 経過率 (0.0 〜 1.0) に応じて HSL を補間して色を決定する。
   * 0.0: 青 (h=220) / 0.5: 黄 (h=50) / 1.0: 赤 (h=0)
   */
  function colorFor(elapsedRatio) {
    const t = Math.min(1, Math.max(0, elapsedRatio));
    let h;
    if (t < 0.5) {
      h = 220 + (50 - 220) * (t / 0.5);
    } else {
      h = 50 + (0 - 50) * ((t - 0.5) / 0.5);
    }
    const s = 78;
    const l = 56;
    return {
      stroke: `hsl(${h.toFixed(1)}, ${s}%, ${l}%)`,
      glow: `hsla(${h.toFixed(1)}, ${s}%, ${l}%, 0.55)`,
    };
  }

  function render() {
    const elapsedRatio = 1 - remainingSec / totalSec;
    // 残り時間を可視化するため、経過分だけ dashoffset を進める
    const offset = RING_CIRCUMFERENCE * elapsedRatio;
    ringProgress.style.strokeDashoffset = String(offset);

    const { stroke, glow } = colorFor(elapsedRatio);
    ringProgress.style.setProperty("--ring-color", stroke);
    ringProgress.style.setProperty("--ring-glow", glow);

    timeEl.textContent = formatTime(remainingSec);
    if (ringEl) {
      const percent = Math.round((1 - elapsedRatio) * 100);
      ringEl.setAttribute("aria-label", `進捗 ${percent}%`);
    }
  }

  function tick() {
    if (!running || endTimestamp == null) return;
    const now = Date.now();
    remainingSec = Math.max(0, (endTimestamp - now) / 1000);
    render();
    if (remainingSec <= 0) {
      finish();
      return;
    }
    rafId = requestAnimationFrame(tick);
  }

  function start() {
    if (running) return;
    running = true;
    endTimestamp = Date.now() + remainingSec * 1000;
    startBtn.textContent = "一時停止";
    statusEl.textContent = "作業中";
    document.body.classList.add("is-focusing");
    fx.start();
    rafId = requestAnimationFrame(tick);
  }

  function pause() {
    if (!running) return;
    running = false;
    if (rafId != null) cancelAnimationFrame(rafId);
    rafId = null;
    endTimestamp = null;
    startBtn.textContent = "再開";
    document.body.classList.remove("is-focusing");
    fx.stop();
  }

  function reset() {
    running = false;
    if (rafId != null) cancelAnimationFrame(rafId);
    rafId = null;
    endTimestamp = null;
    remainingSec = totalSec;
    startBtn.textContent = "開始";
    statusEl.textContent = "作業中";
    document.body.classList.remove("is-focusing");
    fx.stop();
    render();
  }

  function finish() {
    running = false;
    if (rafId != null) cancelAnimationFrame(rafId);
    rafId = null;
    endTimestamp = null;
    remainingSec = 0;
    statusEl.textContent = "完了";
    startBtn.textContent = "開始";
    document.body.classList.remove("is-focusing");
    fx.stop();
    render();
  }

  startBtn.addEventListener("click", function () {
    if (running) pause();
    else start();
  });
  resetBtn.addEventListener("click", reset);

  // --- 背景エフェクト (パーティクル + 波紋) ----------------------------------
  const fx = (function () {
    if (!canvas || !canvas.getContext) {
      return { start() {}, stop() {} };
    }
    const ctx = canvas.getContext("2d");
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    let particles = [];
    let ripples = [];
    let rippleTimer = null;
    let animId = null;
    let active = false;

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function spawnParticles() {
      const count = 36;
      particles = [];
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * window.innerWidth,
          y: Math.random() * window.innerHeight,
          r: 1 + Math.random() * 2.5,
          vx: (Math.random() - 0.5) * 0.25,
          vy: -0.15 - Math.random() * 0.35,
          a: 0.25 + Math.random() * 0.45,
          twinkle: Math.random() * Math.PI * 2,
        });
      }
    }

    function emitRipple() {
      if (!active) return;
      ripples.push({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2,
        r: 40,
        maxR: Math.max(window.innerWidth, window.innerHeight) * 0.55,
        a: 0.35,
      });
    }

    function draw() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      ctx.clearRect(0, 0, w, h);

      for (let i = ripples.length - 1; i >= 0; i--) {
        const rp = ripples[i];
        rp.r += 1.8;
        rp.a *= 0.985;
        if (rp.r > rp.maxR || rp.a < 0.01) {
          ripples.splice(i, 1);
          continue;
        }
        ctx.beginPath();
        ctx.arc(rp.x, rp.y, rp.r, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 255, 255, ${rp.a.toFixed(3)})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.twinkle += 0.04;
        if (p.y < -10) {
          p.y = h + 10;
          p.x = Math.random() * w;
        }
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
        const alpha = p.a * (0.7 + 0.3 * Math.sin(p.twinkle));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha.toFixed(3)})`;
        ctx.fill();
      }

      if (active) {
        animId = requestAnimationFrame(draw);
      }
    }

    function start() {
      if (active || prefersReducedMotion) return;
      active = true;
      resize();
      spawnParticles();
      ripples = [];
      emitRipple();
      rippleTimer = window.setInterval(emitRipple, 4500);
      animId = requestAnimationFrame(draw);
    }

    function stop() {
      active = false;
      if (animId != null) cancelAnimationFrame(animId);
      animId = null;
      if (rippleTimer != null) clearInterval(rippleTimer);
      rippleTimer = null;
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    window.addEventListener("resize", function () {
      if (active) {
        resize();
        spawnParticles();
      }
    });

    return { start, stop };
  })();

  // 初期表示
  render();
})();

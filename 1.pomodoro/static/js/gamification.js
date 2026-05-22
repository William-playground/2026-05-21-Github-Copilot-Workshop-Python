// Gamification UI: fetch summary and stats, then render XP / streak / badges / chart.
(function () {
  "use strict";

  const els = {
    level: document.getElementById("g-level"),
    xpBar: document.getElementById("g-xp-bar"),
    xpFill: document.getElementById("g-xp-fill"),
    xpText: document.getElementById("g-xp-text"),
    streak: document.getElementById("g-streak"),
    successRate: document.getElementById("g-success-rate"),
    badges: document.getElementById("g-badges"),
    statsTotals: document.getElementById("g-stats-totals"),
    statsChart: document.getElementById("g-stats-chart"),
    tabs: document.querySelectorAll(".stats-tab"),
  };

  function formatPercent(value) {
    return Math.round((value || 0) * 100) + "%";
  }

  function formatMinutes(seconds) {
    const total = Math.round((seconds || 0) / 60);
    const h = Math.floor(total / 60);
    const m = total % 60;
    return h > 0 ? h + "時間" + m + "分" : m + "分";
  }

  function renderSummary(data) {
    const xp = data.xp || {};
    const level = xp.level || 1;
    const into = xp.xp_into_level || 0;
    const per = xp.xp_for_next_level || 100;
    els.level.textContent = "Lv. " + level;
    const pct = Math.min(100, (into / per) * 100);
    els.xpFill.style.width = pct + "%";
    els.xpBar.setAttribute("aria-valuenow", String(Math.round(pct)));
    els.xpText.textContent = into + " / " + per + " XP";

    els.streak.textContent = String(data.streak_days || 0);
    els.successRate.textContent = formatPercent(data.success_rate);

    els.badges.innerHTML = "";
    (data.badges || []).forEach(function (badge) {
      const li = document.createElement("li");
      li.className = "badge-item " + (badge.earned ? "is-earned" : "is-locked");
      li.setAttribute("aria-label", badge.name + (badge.earned ? "（獲得済み）" : "（未獲得）"));
      const name = document.createElement("span");
      name.className = "badge-name";
      name.textContent = (badge.earned ? "★ " : "☆ ") + badge.name;
      const desc = document.createElement("span");
      desc.className = "badge-desc";
      desc.textContent = badge.description;
      li.appendChild(name);
      li.appendChild(desc);
      els.badges.appendChild(li);
    });
  }

  function renderStats(data) {
    const totals = data.totals || {};
    els.statsTotals.innerHTML =
      "完了 <strong>" + (totals.focus_count || 0) + "</strong> 回 ・ " +
      "集中時間 <strong>" + formatMinutes(totals.focus_seconds) + "</strong> ・ " +
      "成功率 <strong>" + formatPercent(totals.success_rate) + "</strong>";

    const daily = data.daily || [];
    const max = daily.reduce(function (acc, d) {
      return Math.max(acc, d.focus_count || 0);
    }, 0);

    els.statsChart.innerHTML = "";
    daily.forEach(function (d) {
      const bar = document.createElement("div");
      const count = d.focus_count || 0;
      const heightPct = max > 0 ? (count / max) * 100 : 0;
      bar.className = "stats-bar" + (count === 0 ? " is-empty" : "");
      bar.style.height = Math.max(heightPct, 4) + "%";
      bar.title = d.date + ": " + count + " 回";
      els.statsChart.appendChild(bar);
    });
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("Request failed: " + res.status);
    return res.json();
  }

  async function refreshSummary() {
    try {
      const data = await fetchJSON("/api/gamification/summary");
      renderSummary(data);
    } catch (err) {
      console.warn("gamification summary failed", err);
    }
  }

  async function refreshStats(range) {
    try {
      const data = await fetchJSON("/api/gamification/stats?range=" + encodeURIComponent(range));
      renderStats(data);
    } catch (err) {
      console.warn("gamification stats failed", err);
    }
  }

  els.tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      els.tabs.forEach(function (t) {
        t.classList.remove("is-active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("is-active");
      tab.setAttribute("aria-selected", "true");
      refreshStats(tab.dataset.range || "week");
    });
  });

  refreshSummary();
  refreshStats("week");
})();

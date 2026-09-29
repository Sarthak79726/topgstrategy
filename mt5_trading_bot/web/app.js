// Pure Real-Time Live Dashboard Controller for MT5 Algorithmic Trading Engine
document.addEventListener("DOMContentLoaded", () => {
  const ctx = document.getElementById("liveChart").getContext("2d");

  const liveChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "XAUUSD M5 Live Price",
          data: [],
          borderColor: "#00f2fe",
          backgroundColor: "rgba(0, 242, 254, 0.08)",
          fill: true,
          tension: 0.15,
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: "#00f2fe"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { family: "Inter", size: 12 } }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", maxTicksLimit: 12 }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        }
      }
    }
  });

  // 1. Fetch Real-Time Account Status
  async function fetchStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return;
      const data = await res.json();

      // Mode Badge
      const btn = document.getElementById("toggle-mode-btn");
      if (btn) {
        if (data.is_live) {
          btn.style.backgroundColor = "rgba(16, 185, 129, 0.2)";
          btn.style.borderColor = "#10b981";
          btn.style.color = "#10b981";
          btn.innerHTML = `<span class="mode-icon">🚀</span> Mode: REAL LIVE TRADING`;
        } else {
          btn.style.backgroundColor = "rgba(245, 158, 11, 0.15)";
          btn.style.borderColor = "#f59e0b";
          btn.style.color = "#f59e0b";
          btn.innerHTML = `<span class="mode-icon">🛡️</span> Mode: DRY-RUN / PAPER`;
        }
      }

      // Header status
      const statusAcc = document.getElementById("status-account");
      if (statusAcc && data.account) {
        statusAcc.innerText = `MT5 IPC CONNECTED (${data.account} - ${data.company})`;
      }

      // Account Balance & Equity
      const balEl = document.getElementById("stat-balance");
      const eqEl = document.getElementById("stat-equity");
      const freeMargEl = document.getElementById("stat-free-margin");

      if (balEl && data.balance !== undefined) {
        balEl.innerText = `$${parseFloat(data.balance).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      }
      if (eqEl && data.equity !== undefined) {
        eqEl.innerText = `$${parseFloat(data.equity).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      }
      if (freeMargEl && data.free_margin !== undefined) {
        freeMargEl.innerText = `Free Margin: $${parseFloat(data.free_margin).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      }

      // Floating PnL
      const pnlEl = document.getElementById("stat-pnl");
      const openPosEl = document.getElementById("stat-open-positions");
      if (pnlEl && data.floating_pnl !== undefined) {
        const pnlVal = parseFloat(data.floating_pnl);
        const prefix = pnlVal >= 0 ? "+$" : "-$";
        pnlEl.innerText = `${prefix}${Math.abs(pnlVal).toFixed(2)}`;
        pnlEl.style.color = pnlVal > 0 ? "#10b981" : (pnlVal < 0 ? "#ef4444" : "#f8fafc");
      }
      if (openPosEl) {
        openPosEl.innerText = `${data.open_positions} Active Open Positions`;
      }

      // Activity
      const actEl = document.getElementById("stat-activity");
      if (actEl) {
        actEl.innerText = `${data.total_signals} Signals / ${data.total_trades} Trades`;
      }

      const headerSym = document.getElementById("header-symbol");
      if (headerSym && data.symbol && data.timeframe) {
        headerSym.innerText = `${data.symbol} | ${data.timeframe}`;
      }
    } catch (err) {
      console.error("Status fetch error:", err);
    }
  }

  // 2. Fetch Open MT5 Positions
  async function fetchPositions() {
    try {
      const res = await fetch("/api/positions");
      if (!res.ok) return;
      const positions = await res.json();

      const listContainer = document.getElementById("open-positions-list");
      if (!listContainer) return;

      if (!positions || positions.length === 0) {
        listContainer.innerHTML = `
          <div class="telemetry-item" style="justify-content: center; color: #94a3b8; padding: 15px 0;">
            <span>No open positions on MT5 right now.</span>
          </div>
        `;
        return;
      }

      let html = "";
      positions.forEach(p => {
        const isBuy = p.type === "BUY";
        const color = isBuy ? "#10b981" : "#ef4444";
        const pnl = parseFloat(p.profit || 0);
        const pnlStr = pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`;
        const pnlColor = pnl >= 0 ? "#10b981" : "#ef4444";

        html += `
          <div class="telemetry-item" style="border-left: 3px solid ${color}; padding-left: 12px; margin-bottom: 6px;">
            <div style="display:flex; flex-direction:column;">
              <strong style="color: ${color}; font-size: 0.9rem;">${p.type} ${p.volume} Lots (${p.symbol})</strong>
              <span style="font-size: 0.78rem; color: #94a3b8;">Ticket #${p.ticket} | Open: ${p.price_open.toFixed(2)} | Current: ${p.price_current.toFixed(2)}</span>
            </div>
            <div style="font-weight: 700; font-size: 1rem; color: ${pnlColor};">
              ${pnlStr}
            </div>
          </div>
        `;
      });
      listContainer.innerHTML = html;
    } catch (err) {
      console.error("Positions fetch error:", err);
    }
  }

  // 3. Fetch Real-Time Strategy Levels & Trend
  async function fetchLevels() {
    try {
      const res = await fetch("/api/levels");
      if (!res.ok) return;
      const data = await res.json();

      // Trend Card
      const trendEl = document.getElementById("stat-trend");
      if (trendEl && data.trend) {
        trendEl.innerText = data.trend;
        trendEl.style.color = data.trend === "BULLISH" ? "#10b981" : (data.trend === "BEARISH" ? "#ef4444" : "#38bdf8");
      }

      // Levels Panel
      const levelsContainer = document.getElementById("live-levels-container");
      if (!levelsContainer) return;

      const levels = data.active_levels || [];
      if (levels.length === 0) {
        levelsContainer.innerHTML = `
          <div class="telemetry-item" style="justify-content: center; color: #94a3b8; padding: 15px 0;">
            <span>No active level bounds detected on current bar structure.</span>
          </div>
        `;
        return;
      }

      let html = "";
      levels.forEach(lv => {
        const isBull = lv.dir === 1;
        const col = isBull ? "#10b981" : "#ef4444";
        const badgeBg = isBull ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)";

        html += `
          <div class="telemetry-item" style="border-left: 3px solid ${col}; padding-left: 10px; margin-bottom: 6px;">
            <span class="t-label" style="font-weight: 600; color: #f8fafc;">${lv.txt}</span>
            <span class="t-value" style="color: ${col}; background: ${badgeBg}; padding: 2px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
              ${lv.bot.toFixed(2)} - ${lv.top.toFixed(2)}
            </span>
          </div>
        `;
      });

      // Include EMA 132 row
      if (data.ema132) {
        html += `
          <div class="telemetry-item" style="border-left: 3px solid #f59e0b; padding-left: 10px; margin-top: 8px;">
            <span class="t-label" style="color: #94a3b8;">EMA Filter Level</span>
            <span class="t-value" style="color: #f59e0b; font-family: 'JetBrains Mono', monospace;">
              ${data.ema132.toFixed(2)} (${data.ema_status})
            </span>
          </div>
        `;
      }

      levelsContainer.innerHTML = html;
    } catch (err) {
      console.error("Levels fetch error:", err);
    }
  }

  // 4. Fetch Signals & Trade Logs Table
  async function fetchTradeLogs() {
    try {
      const resSig = await fetch("/api/signals");
      const signals = resSig.ok ? await resSig.json() : [];

      const tbody = document.getElementById("trade-log-body");
      if (!tbody) return;

      if (!signals || signals.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align: center; color: #94a3b8; padding: 25px;">
              No strategy signals or trades recorded yet. Bot actively listening to closed M5 bars...
            </td>
          </tr>
        `;
        return;
      }

      let html = "";
      const reversed = [...signals].reverse();
      reversed.forEach(sig => {
        const isBuy = sig.direction === "BUY";
        const badgeClass = isBuy ? "buy" : "sell";
        const entry = parseFloat(sig.entry || 0).toFixed(2);
        const sl = parseFloat(sig.stop_loss || 0).toFixed(2);
        const tp = parseFloat(sig.take_profit || 0).toFixed(2);
        const timeStr = sig.timestamp ? sig.timestamp.replace("T", " ").substring(0, 19) : "-";

        html += `
          <tr>
            <td>${timeStr}</td>
            <td>${sig.symbol || "XAUUSD"}</td>
            <td><span class="badge ${badgeClass}">${sig.direction}</span></td>
            <td>${entry}</td>
            <td>${sl}</td>
            <td>${tp}</td>
            <td>Auto Risk (1.0%)</td>
            <td>${sig.strategy_component || sig.reason || "Level Retest"}</td>
            <td><span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981;">LIVE EXECUTION</span></td>
          </tr>
        `;
      });

      tbody.innerHTML = html;
    } catch (err) {
      console.error("Logs fetch error:", err);
    }
  }

  // 5. Fetch Live Market Rates for Chart
  async function fetchRates() {
    try {
      const res = await fetch("/api/rates");
      if (!res.ok) return;
      const rates = await res.json();
      if (!rates || rates.length === 0) return;

      const labels = rates.map(r => r.time ? r.time.substring(11, 16) : "");
      const prices = rates.map(r => r.close);

      liveChart.data.labels = labels;
      liveChart.data.datasets[0].data = prices;
      liveChart.update();

      const lastPrice = prices[prices.length - 1];
      const livePriceEl = document.getElementById("live-price");
      if (livePriceEl && lastPrice) {
        livePriceEl.innerText = `$${lastPrice.toFixed(2)}`;
      }
    } catch (err) {
      console.error("Rates fetch error:", err);
    }
  }

  // Initial Poll & Fast Periodical Refreshes
  fetchStatus();
  fetchPositions();
  fetchLevels();
  fetchTradeLogs();
  fetchRates();

  setInterval(fetchStatus, 2000);
  setInterval(fetchPositions, 2000);
  setInterval(fetchLevels, 3000);
  setInterval(fetchTradeLogs, 3000);
  setInterval(fetchRates, 3000);
});

// Interactive Chart & Live Telemetry Controller for MT5 Trading Engine
document.addEventListener("DOMContentLoaded", () => {
  const ctx = document.getElementById("liveChart").getContext("2d");

  // Sample historical prices for chart
  const timeLabels = ["01:00", "01:05", "01:10", "01:15", "01:20", "01:25", "01:30", "01:35"];
  const priceData = [2642.50, 2645.10, 2643.80, 2648.20, 2652.00, 2650.50, 2653.90, 2654.80];
  const emaData = [2640.10, 2641.50, 2642.80, 2644.20, 2646.00, 2647.50, 2648.80, 2650.20];

  const liveChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: timeLabels,
      datasets: [
        {
          label: "XAUUSD M5 Price",
          data: priceData,
          borderColor: "#00f2fe",
          backgroundColor: "rgba(0, 242, 254, 0.08)",
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 4,
          pointBackgroundColor: "#00f2fe"
        },
        {
          label: "EMA 132 Filter",
          data: emaData,
          borderColor: "#ffb703",
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0,
          fill: false
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
          ticks: { color: "#94a3b8" }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" }
        }
      }
    }
  });

  // Dynamic Tick Updater Simulation
  setInterval(() => {
    const lastPrice = priceData[priceData.length - 1];
    const delta = (Math.random() - 0.48) * 1.5;
    const newPrice = parseFloat((lastPrice + delta).toFixed(2));
    
    priceData[priceData.length - 1] = newPrice;
    liveChart.update();

    document.getElementById("live-price").innerText = `$${newPrice.toFixed(2)}`;
  }, 2000);
});

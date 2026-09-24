# TopGStrategy - Automated MT5 Algorithmic Trading Engine

Production-grade automated trading system converting TradingView Pine Script v6 indicator logic (**"RM'S JADU TONA"**) into a Python algorithmic execution engine for MetaTrader 5.

---

## Overview

**TopGStrategy** is an algorithmic trading system designed to parse, analyze, and execute Smart Money Concepts (SMC) and price action market structure rules on MetaTrader 5.

It translates Pine Script v6 state machine logic into Python:
* **Market Structure Engine**: Bar-by-bar state machine tracking market trend, swing highs/lows (`runHigh`, `runLow`), BOS, CHOCH, Dual-CHOCH, TJL, QML, and 4-State ISS (Initial Structure Shift) logic.
* **Smart Money Concepts (SMC)**: Fair Value Gaps (FVG) and Supply/Demand Order Blocks (OB) with tap-based deletion logic.
* **MetaTrader 5 Integration**: Real-time tick and M5 OHLCV market data streaming, account protection, and order execution via the official `MetaTrader5` Python package.
* **Web Telemetry Dashboard**: Modern dark-mode web dashboard for real-time indicator visualization, account metrics, and trade execution tracking.

---

## Key Features

- **MetaTrader 5 Integration**: Full support for official `MetaTrader5` Python package (v5.0.6180+).
- **Centralized Connection Management**: Non-blocking IPC attachment, terminal process state tracking, and process discovery.
- **Strict Account Protection**: Automatic verification of connected MT5 account number and server against `EXPECTED_MT5_ACCOUNT` and `EXPECTED_MT5_SERVER`.
- **Zero Automatic Account Switching**: The bot attaches exclusively to the currently logged-in MT5 terminal. `mt5.login()` is never invoked automatically to force account switches.
- **Controlled IPC Error Recovery**: Automatic recovery from `-10004` IPC drops using bounded exponential backoff (`2s` $\rightarrow$ `5s` $\rightarrow$ `10s` $\rightarrow$ `20s`).
- **Safe Dry-Run / Paper Trading Mode**: Hard safety guard blocking `mt5.order_send()` calls while calculating real-time indicators, signals, risk amounts, and position sizes.
- **Dynamic Position Sizing**: Equity-based risk calculation (`RISK_PERCENT`) normalized to broker volume constraints and pip values.
- **Fidelity Validation Engine**: Built-in validation suite comparing Python indicator calculations against Pine Script v6 reference data.
- **Web Telemetry Dashboard**: Responsive dark glassmorphism web interface (HTML5, CSS3, Chart.js) for live strategy telemetry and portfolio presentation.

---

## System Architecture

```
                               ┌───────────────────────────┐
                               │  MetaTrader 5 Terminal    │
                               │      (terminal64.exe)     │
                               └─────────────┬─────────────┘
                                             │ IPC Shared Memory
                                             ▼
                               ┌───────────────────────────┐
                               │   MT5 Connection Manager  │
                               │  (State & Account Check)  │
                               └─────────────┬─────────────┘
                                             │ OHLCV M5 Bars
                                             ▼
                               ┌───────────────────────────┐
                               │  Pine Script State Engine │
                               │ (BOS, CHOCH, FVG, OB, ISS)│
                               └─────────────┬─────────────┘
                                             │ Trading Signals
                                             ▼
                               ┌───────────────────────────┐
                               │ Risk & Position Sizer     │
                               │ (Equity % & SL Pips Math) │
                               └─────────────┬─────────────┘
                                             │ Verified Order
                                             ▼
                               ┌───────────────────────────┐
                               │    Execution Manager      │
                               │  [Dry-Run / Live MT5]     │
                               └───────────────────────────┘
```

---

## Tech Stack

* **Core Logic**: Python 3.14+
* **Market SDK**: MetaTrader 5 Python SDK (`MetaTrader5`)
* **Data Processing**: Pandas, NumPy, SciPy
* **Validation & Config**: Pydantic, PyYAML, python-dotenv
* **Testing Suite**: Pytest
* **Web Telemetry**: HTML5, Vanilla CSS3, JavaScript (Chart.js)

---

## Repository Structure

```
topgstrategy/
├── mt5_trading_bot/
│   ├── backtest/            # Historical backtesting engine
│   ├── engine/              # Trading loop & strategy engine
│   ├── execution/           # Trade manager & order routing
│   ├── mt5/                 # MT5 connection, discovery, & execution
│   ├── risk/                # Risk manager & position sizing
│   ├── signals/             # Signal data models
│   ├── strategy/            # Pine Script indicator & structure math
│   ├── tests/               # Pytest unit test suite
│   ├── utils/               # Logging & time utilities
│   ├── validation/          # Pine vs Python fidelity validator
│   ├── web/                 # Web dashboard (HTML, CSS, JS)
│   ├── config.py            # Pydantic configuration loader
│   └── main.py              # CLI entry point
├── run_bot_live.bat         # 1-Click batch script for live mode
├── run_bot_paper.bat        # 1-Click batch script for paper mode
├── requirements.txt         # Project dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore configuration
└── README.md                # Documentation
```

---

## Installation & Setup

### 1. Clone Repository
```powershell
git clone https://github.com/YOUR_USERNAME/topgstrategy.git
cd topgstrategy
```

### 2. Create Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` and set your expected account details and MT5 executable path:
```env
EXPECTED_MT5_ACCOUNT=5056283582
EXPECTED_MT5_SERVER=MetaQuotes-Demo
MT5_PATH=C:/Program Files/MetaTrader 5/terminal64.exe
```
> **IMPORTANT**: `.env` contains local configuration and credentials. It is listed in `.gitignore` and must **NEVER** be committed to Git.

### 5. Install & Prepare MetaTrader 5
1. Install MetaTrader 5 desktop application (`terminal64.exe`).
2. Log into your demo or live broker account inside MT5.
3. Open Market Watch (`Ctrl + M`) and add your trading symbol (e.g. `XAUUSD`).
4. Enable Algorithmic Trading (`Tools` $\rightarrow$ `Options` $\rightarrow$ `Expert Advisors` $\rightarrow$ `Allow Algorithmic Trading`).

---

## Connection Verification

Before running trading operations, verify the terminal connection and account protection:

```powershell
python -m mt5_trading_bot.main test-connection
```

This command performs:
1. MetaTrader 5 Python package verification
2. IPC terminal attachment
3. Account number & server protection match check
4. Symbol (`XAUUSD`) availability check
5. M5 candle retrieval test

---

## Execution Commands

### 1. Safe Paper / Dry-Run Trading Mode
Runs the live market polling loop and strategy engine, calculates signals, risk amounts, and lot sizes, but **blocks real `mt5.order_send()` calls**:
```powershell
python -m mt5_trading_bot.main paper
```
*Or double-click `run_bot_paper.bat`.*

### 2. Live Trading Mode
Runs the trading loop and executes real market orders on MetaTrader 5 when strategy conditions trigger:
```powershell
python -m mt5_trading_bot.main live --confirm-live
```
*Or double-click `run_bot_live.bat`.*

### 3. Pine-vs-Python Fidelity Validation
Verifies strategy calculations against synthetic datasets:
```powershell
python -m mt5_trading_bot.main validate
```

### 4. Unit Test Suite
Runs the full Pytest test suite:
```powershell
python -m pytest mt5_trading_bot/tests
```

### 5. Web Telemetry Dashboard
Launches the local web server and opens the dashboard in your default browser:
```powershell
python -m mt5_trading_bot.main web
```

---

## Safety & Account Protection

* **Account Verification**: The bot checks `account_info.login` and `account_info.server` against `EXPECTED_MT5_ACCOUNT` and `EXPECTED_MT5_SERVER`. If an account mismatch occurs, trading is **halted immediately**.
* **Zero Automatic Login**: `mt5.login()` is never called to force account changes.
* **Hard Order Safety Guard**: In dry-run mode, `OrderExecutionManager.send_order()` returns a skipped response without invoking `mt5.order_send()`.

---

## Disclaimer

This software project is created for **educational, analytical, and research purposes only**. Automated financial trading involves substantial risk of loss. Past performance of strategy calculations or backtests does not guarantee future results.

# TradingView Pine Script ("RM'S JADU TONA") to MT5 Automated Python System

Production-quality automated trading system converting the TradingView Pine Script v6 indicator **"RM'S JADU TONA"** into an MT5-compatible Python algorithmic system.

## 1. What the Project Does

This system reproduces the complete Pine Script market structure logic in Python:
- **State Machine Strategy Engine**: Sequential bar-by-bar state machine tracking market trend, phase, swing highs/lows (`runHigh`, `runLow`, `lastCH`, `lastCL`), BOS, CHOCH, Dual-CHOCH, TJL 1, TJL 2, QML, SBR, RBS, Double Top (DT), Double Bottom (DB), and 4-State ISS (Initial Structure Shift) logic.
- **Smart Money Concepts (SMC)**: Fair Value Gap (FVG) and Supply/Demand Order Blocks (OB) with tap deletion.
- **MetaTrader 5 Integration**: Live tick/OHLCV data fetching, symbol resolution (handling broker suffixes like `XAUUSDm`, `GOLD`), lot size normalization, and order execution via the official `MetaTrader5` Python package.
- **Backtesting & Visualization**: Sequential historical backtesting engine with equity curve charting, performance metrics (Sharpe, Drawdown, Win Rate, Profit Factor, Expectancy), and trade CSV export.
- **Paper Trading & Safety Controls**: Safe default configuration (`ENABLE_TRADING=false`), paper trading simulation mode, and double-confirmation requirements for live execution (`--confirm-live`).
- **Validation Framework**: Signal comparator comparing TradingView CSV alert exports against Python engine output.

---

## 2. Project Architecture

```
mt5_trading_bot/
├── main.py                     # CLI entrypoint (test-connection, backtest, paper, live, validate)
├── config.py                   # Pydantic configuration loader
├── requirements.txt            # Package dependencies
├── .env.example                # Environment settings template
├── README.md                   # Documentation
│
├── mt5/                        # MetaTrader 5 API Layer
│   ├── connection.py           # MT5 initialization & reconnection logic
│   ├── market_data.py          # OHLCV data & tick fetching
│   ├── execution.py            # Order sending, closing, position management
│   ├── account.py              # Account info, equity, balance
│   └── symbols.py              # Dynamic symbol resolution & lot normalization
│
├── strategy/                   # Pure Strategy & State Machine Engine
│   ├── strategy.py             # StrategyEngine coordinating process_bar()
│   ├── state.py                # Persistent state objects (Snap, Level, FVG, OB, StrategyState)
│   ├── ema.py                  # EMA 132 + optional smoothing (SMA, BB, EMA, RMA, WMA, VWMA)
│   ├── levels.py               # Level management (add, update, tap, trim, promote)
│   ├── structure.py            # Snap helpers & swing tracking
│   ├── bos_choch.py            # BOS, CHOCH & Dual-CHOCH detection
│   ├── tjl.py                  # TJL 1 & TJL 2 level logic
│   ├── qml.py                  # QML & Best Level promotion
│   ├── sbr_rbs.py              # SBR & RBS level logic
│   ├── double_patterns.py      # Double Top (DT) & Double Bottom (DB) logic
│   ├── iss.py                  # 4-State ISS state machine (Bullish & Bearish ISS 1-4)
│   ├── fvg.py                  # Fair Value Gap detection & tap deletion
│   ├── order_blocks.py         # Order Block detection & tap deletion
│   ├── kill_zones.py           # UTC London & NY Kill Zone filters
│   ├── mtf.py                  # Multi-Timeframe Trend Dashboard calculations
│   ├── analyzer.py             # Level Accuracy Analyzer
│   └── candles.py              # Candle zone calculation (f_candleZone body % padding)
│
├── signals/                    # Signal Generation Layer
│   ├── signal.py               # Signal dataclass with unique ID
│   └── signal_generator.py     # Converts level taps & CHOCH/ISS events into signals
│
├── risk/                       # Risk Management
│   ├── position_sizing.py      # Risk % to lot size calculator
│   ├── stop_loss.py            # SL calculation & buffer
│   ├── take_profit.py          # TP calculation & R:R ratio
│   └── risk_manager.py         # Max spread, max positions, daily drawdown controls
│
├── execution/                  # Execution Layer
│   ├── order_manager.py        # Retry order placement logic
│   └── trade_manager.py        # Orchestrates signals, risk checks & paper/live execution
│
├── backtest/                   # Historical Backtester
│   ├── engine.py               # Sequential backtest engine
│   ├── metrics.py              # Performance metrics
│   └── runner.py               # Backtest CLI runner & matplotlib visualizer
│
├── validation/                 # Pine vs Python Validator
│   └── validator.py            # CSV comparator & match rate reporter
│
├── utils/                      # Utilities & Logging
│   ├── logger.py               # Console + file logging (bot.log, signals.csv, trades.csv)
│   ├── time_utils.py           # Timezone & timeframe conversions
│   └── validators.py           # DataFrame validation
│
└── tests/                      # Pytest Test Suite
    ├── test_ema.py
    ├── test_structure.py
    ├── test_bos_choch.py
    ├── test_tjl.py
    ├── test_qml.py
    ├── test_iss.py
    ├── test_fvg.py
    ├── test_order_blocks.py
    ├── test_risk.py
    └── test_signals.py
```

---

## 3. Installation & Setup

### Requirements
- Python 3.11 or 3.12
- MetaTrader 5 Terminal (for live/demo data & execution)

### 1. Virtual Environment & Package Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Install dependencies
pip install -r mt5_trading_bot/requirements.txt
```

### 2. Configuration (`.env`)

Copy `.env.example` to `.env` inside `mt5_trading_bot/`:

```bash
cp mt5_trading_bot/.env.example mt5_trading_bot/.env
```

Configure your credentials:
```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Demo
MT5_PATH=C:/Program Files/MetaTrader 5/terminal64.exe

SYMBOL=XAUUSD
TIMEFRAME=M5
ENABLE_TRADING=false
PAPER_MODE=true
```

---

## 4. Usage Commands

### Test Connection
Verify connection to MT5 terminal and account:
```bash
python -m mt5_trading_bot.main --mode test-connection
```

### Download Historical Data
Download MT5 candles to `logs/XAUUSD_M5_data.csv`:
```bash
python -m mt5_trading_bot.main --mode download-data --symbol XAUUSD --timeframe M5 --bars 5000
```

### Run Backtest
Run backtest with equity curve chart visualization:
```bash
python -m mt5_trading_bot.main --mode backtest --symbol XAUUSD --timeframe M5 --bars 2000
```

### Run Paper Trading Mode
Simulate trading signals on closed candles without placing real orders:
```bash
python -m mt5_trading_bot.main --mode paper --symbol XAUUSD --timeframe M5
```

### Run Validation Against TradingView
Compare TradingView exported signals with Python:
```bash
python -m mt5_trading_bot.main --mode validate --tv-csv path/to/tv_signals.csv
```

### Run Live Demo/Real Trading
> [!WARNING]
> Live trading requires `ENABLE_TRADING=true` in `.env` AND `--confirm-live` in CLI!

```bash
python -m mt5_trading_bot.main --mode live --confirm-live
```

---

## 5. Running Unit Tests

Execute the complete pytest test suite:

```bash
python -m pytest mt5_trading_bot/tests/ -v
```

---

## 6. How Pine and Python Logic Correspond

| Pine Script Concept | Python Implementation |
|---|---|
| `var` persistent variables | `StrategyState` dataclass attributes |
| `type Level`, `Snap`, `FVGLevel`, `OBLevel` | Python `@dataclass` models |
| `f_candleZone()` | `strategy.candles.candle_zone()` |
| `f_isTapped()` | `strategy.candles.is_tapped()` |
| `f_updateLevels()` | `strategy.levels.update_levels()` |
| `f_promoteLastChochLevelsToBest()` | `strategy.levels.promote_last_choch_levels_to_best()` |
| ISS 4-State Machine | `strategy.iss.update_iss_state()` |
| `ta.ema()` / `f_emaMa()` | `strategy.ema.calculate_ema_system()` |
| `request.security()` | `mt5.market_data.MarketDataManager` multi-timeframe fetching |

---

## 7. Known Pine-to-Python Differences & Notes

1. **Drawing Objects (`box.new`, `label.new`, `line.new`)**: In Python, visual drawings are replaced by structured Level/Snap objects and Matplotlib rendering in the backtest visualizer.
2. **Bar State Execution**: Pine Script re-executes on tick or bar close. Python defaults strictly to **closed candles** (`barstate.isconfirmed`) to avoid intra-candle repainting.
3. **Pip Size Handling**: Python dynamically queries MT5 `symbol_info` for digits/point instead of hardcoding `0.0001` or `0.1`.

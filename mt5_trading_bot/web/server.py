import os
import json
import csv
import http.server
import socketserver
import webbrowser
from pathlib import Path
from typing import Dict, Any, List

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from ..config import Config
from ..mt5.connection import MT5Connection
from ..mt5.account import AccountManager
from ..mt5.market_data import MT5MarketData
from ..engine.strategy_engine import StrategyEngine

LOGS_DIR = Path(__file__).parent.parent / "logs"
SIGNALS_CSV = LOGS_DIR / "signals.csv"
TRADES_CSV = LOGS_DIR / "trades.csv"
WEB_DIR = Path(__file__).parent

class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler serving live REST APIs for MT5 Real-Time Trading Engine."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/status":
            self.handle_api_status()
        elif self.path == "/api/positions":
            self.handle_api_positions()
        elif self.path == "/api/signals":
            self.handle_api_signals()
        elif self.path == "/api/trades":
            self.handle_api_trades()
        elif self.path == "/api/rates":
            self.handle_api_rates()
        elif self.path == "/api/levels":
            self.handle_api_levels()
        else:
            super().do_GET()

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api_status(self):
        cfg = Config()
        conn = MT5Connection(expected_account=cfg.EXPECTED_MT5_ACCOUNT, path=cfg.MT5_PATH)
        info = None
        open_pos_count = 0
        floating_pnl = 0.0

        if conn.initialize():
            info = AccountManager.get_account_info()
            if MT5_AVAILABLE:
                pos_list = mt5.positions_get(symbol=cfg.SYMBOL) or ()
                open_pos_count = len(pos_list)
                floating_pnl = sum(getattr(p, "profit", 0.0) for p in pos_list)
            conn.shutdown()

        info = info or {}

        balance = info.get("balance", 0.0)
        equity = info.get("equity", balance)
        margin = info.get("margin", 0.0)
        free_margin = info.get("free_margin", balance)
        login = info.get("login", cfg.EXPECTED_MT5_ACCOUNT or 0)
        company = info.get("company", cfg.EXPECTED_MT5_SERVER or "MetaQuotes")

        # Read signal count
        signal_count = 0
        if SIGNALS_CSV.exists():
            with open(SIGNALS_CSV, mode="r", encoding="utf-8") as f:
                signal_count = max(0, sum(1 for _ in f) - 1)

        # Read trade count
        trade_count = 0
        if TRADES_CSV.exists():
            with open(TRADES_CSV, mode="r", encoding="utf-8") as f:
                trade_count = max(0, sum(1 for _ in f) - 1)

        is_live = (cfg.ENABLE_TRADING and not cfg.PAPER_MODE and not cfg.DRY_RUN)

        data = {
            "is_live": is_live,
            "mode": "REAL LIVE TRADING" if is_live else "DRY-RUN / PAPER",
            "account": login,
            "company": company,
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "free_margin": free_margin,
            "floating_pnl": floating_pnl,
            "open_positions": open_pos_count,
            "symbol": cfg.SYMBOL,
            "timeframe": cfg.TIMEFRAME,
            "risk_percent": cfg.RISK_PERCENT,
            "total_signals": signal_count,
            "total_trades": trade_count
        }
        self.send_json(data)

    def handle_api_positions(self):
        cfg = Config()
        conn = MT5Connection(expected_account=cfg.EXPECTED_MT5_ACCOUNT, path=cfg.MT5_PATH)
        positions = []
        if conn.initialize():
            if MT5_AVAILABLE:
                pos_list = mt5.positions_get(symbol=cfg.SYMBOL)
                if pos_list:
                    for p in pos_list:
                        positions.append({
                            "ticket": p.ticket,
                            "symbol": p.symbol,
                            "type": "BUY" if p.type == 0 else "SELL",
                            "volume": p.volume,
                            "price_open": p.price_open,
                            "price_current": p.price_current,
                            "sl": p.sl,
                            "tp": p.tp,
                            "profit": p.profit,
                            "time": p.time
                        })
            conn.shutdown()
        self.send_json(positions)

    def handle_api_signals(self):
        signals: List[Dict[str, str]] = []
        if SIGNALS_CSV.exists():
            with open(SIGNALS_CSV, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    signals.append(row)
        self.send_json(signals[-50:])

    def handle_api_trades(self):
        trades: List[Dict[str, str]] = []
        if TRADES_CSV.exists():
            with open(TRADES_CSV, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trades.append(row)
        self.send_json(trades[-50:])

    def handle_api_rates(self):
        cfg = Config()
        conn = MT5Connection(expected_account=cfg.EXPECTED_MT5_ACCOUNT, path=cfg.MT5_PATH)
        rates_data = []
        if conn.initialize():
            md = MT5MarketData(conn)
            df = md.get_rates_dataframe(cfg.SYMBOL, cfg.TIMEFRAME, 50)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    rates_data.append({
                        "time": str(row["time"]),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"])
                    })
            conn.shutdown()
        self.send_json(rates_data)

    def handle_api_levels(self):
        cfg = Config()
        conn = MT5Connection(expected_account=cfg.EXPECTED_MT5_ACCOUNT, path=cfg.MT5_PATH)
        payload = {
            "trend": "NEUTRAL",
            "current_price": 0.0,
            "ema132": 0.0,
            "ema_status": "NEUTRAL",
            "active_levels": []
        }

        if conn.initialize():
            md = MT5MarketData(conn)
            df = md.get_rates_dataframe(cfg.SYMBOL, cfg.TIMEFRAME, 500)
            if df is not None and not df.empty:
                engine = StrategyEngine(symbol=cfg.SYMBOL, timeframe=cfg.TIMEFRAME)
                engine.process_data(df)

                current_price = float(df["close"].iloc[-1])
                ema_val = float(df["ema100"].iloc[-1]) if "ema100" in df else current_price

                trend_str = "BULLISH" if engine.state.trend == 1 else ("BEARISH" if engine.state.trend == -1 else "NEUTRAL")
                ema_status = "ABOVE" if current_price >= ema_val else "BELOW"

                active_lvls = []
                for lv in engine.state.levels:
                    if lv.active and not lv.deleted:
                        active_lvls.append({
                            "txt": lv.txt,
                            "top": round(lv.top, 2),
                            "bot": round(lv.bot, 2),
                            "dir": lv.dir
                        })

                payload = {
                    "trend": trend_str,
                    "current_price": round(current_price, 2),
                    "ema132": round(ema_val, 2),
                    "ema_status": ema_status,
                    "active_levels": active_lvls[-10:]  # Latest 10 active levels
                }
            conn.shutdown()

        self.send_json(payload)

def start_web_server(port: int = 8000):
    """Start local web server with custom live dashboard handler."""
    cfg = Config()
    handler = DashboardHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Live Trading Dashboard available at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

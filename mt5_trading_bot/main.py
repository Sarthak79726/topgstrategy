import os
import argparse
import sys
import pandas as pd
import numpy as np
from pathlib import Path

from .config import Config
from .mt5.connection import MT5Connection
from .mt5.account import AccountManager
from .mt5.market_data import MT5MarketData
from .engine.trading_loop import LiveTradingLoop
from .backtest.backtester import Backtester
from .validation.pine_vs_python import PineVsPythonValidator
from .utils.logger import logger
from .mt5.discovery import diagnose_mt5_installation

def generate_synthetic_data(bars: int = 500) -> pd.DataFrame:
    """Generate clean synthetic OHLCV data for backtesting/testing when MT5 is offline."""
    dates = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=bars, freq="5min")
    np.random.seed(42)
    returns = np.random.randn(bars) * 0.001
    price = 2000.0 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        "time": dates,
        "open": price,
        "high": price + np.random.uniform(0.1, 1.5, size=bars),
        "low": price - np.random.uniform(0.1, 1.5, size=bars),
        "close": price + np.random.uniform(-0.5, 0.5, size=bars),
        "tick_volume": np.random.randint(100, 1000, size=bars),
        "spread": [10] * bars,
        "real_volume": [0] * bars
    })
    return df

def cmd_test_connection(config: Config):
    """Test MT5 terminal connection, account verification, symbol availability, and candle retrieval."""
    logger.info("=== Testing MetaTrader 5 Connection ===")

    # Run pre-connection diagnostics
    diag = diagnose_mt5_installation(config)
    logger.info(f"MetaTrader5 Python package: {'OK (' + str(diag['mt5_package_version']) + ')' if diag['mt5_package_installed'] else 'NOT INSTALLED'}")

    conn = MT5Connection(
        expected_account=config.EXPECTED_MT5_ACCOUNT,
        expected_server=config.EXPECTED_MT5_SERVER,
        path=config.MT5_PATH,
        timeout=config.MT5_TIMEOUT
    )

    success = conn.initialize_and_verify()

    if success:
        info = AccountManager.get_account_info()

        # Test symbol availability and candle retrieval
        import MetaTrader5 as mt5
        sym = config.SYMBOL
        sym_info = mt5.symbol_info(sym)
        sym_available = sym_info is not None
        if sym_available:
            mt5.symbol_select(sym, True)
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 5)
            rates_ok = rates is not None and len(rates) > 0
        else:
            rates_ok = False

        logger.info("")
        logger.info("=== MT5 Connection Successful ===")
        if info:
            logger.info(f"Account:          {info.get('login')}")
            logger.info(f"Server / Company: {info.get('company')}")
            logger.info(f"Balance:          ${info.get('balance', 0):.2f}")
            logger.info(f"Equity:           ${info.get('equity', 0):.2f}")
            logger.info(f"Currency:         {info.get('currency')}")
            logger.info(f"Terminal Status:  Connected")
            logger.info(f"Trade Allowed:    {info.get('trade_allowed')}")
            logger.info(f"Symbol ({sym}):   {'AVAILABLE' if sym_available else 'UNAVAILABLE'}")
            logger.info(f"M5 Candle Fetch:  {'SUCCESS (' + str(len(rates)) + ' bars)' if rates_ok else 'FAILED'}")
        else:
            logger.info("Terminal connected successfully (Account info pending).")
        logger.info("")
        conn.shutdown()
    else:
        err_details = conn.last_error_details or {}
        code = err_details.get("code", "UNKNOWN")
        msg = err_details.get("message", "Unknown error")
        category = err_details.get("category", "UNKNOWN")

        logger.error("")
        logger.error("=== MT5 Connection Failed ===")
        logger.error(f"Error category: {category}")
        logger.error(f"Error code:     {code}")
        logger.error(f"Error details:  {msg}")
        logger.error("")
        logger.error("--- Diagnostic Summary ---")
        logger.error(f"OS:                     {diag['os']}")
        logger.error(f"Python:                 {diag['python_version']}")
        logger.error(f"MetaTrader5 Package:    {diag['mt5_package_version']}")
        logger.error(f"Configured MT5 Path:    {diag['configured_path']}")
        logger.error(f"Resolved Path:          {diag['resolved_path']}")
        logger.error(f"Executable Exists:      {'YES' if diag['path_exists'] else 'NO'}")
        logger.error(f"Detected Installations: {len(diag['detected_installations'])}")
        for idx, inst in enumerate(diag['detected_installations'], 1):
            logger.error(f"  [{idx}] {inst}")
        logger.error(f"Terminal Process:       {'RUNNING' if diag['terminal_running'] else 'NOT RUNNING'}")
        logger.error(f"Expected Account:       {config.EXPECTED_MT5_ACCOUNT or 'Not specified'}")
        logger.error(f"Expected Server:        {config.EXPECTED_MT5_SERVER or 'Not specified'}")
        logger.error(f"Timeout (ms):           {diag['timeout_ms']}")
        logger.error("")

        # Targeted recommendations
        if category == "ACCOUNT_MISMATCH":
            logger.error("💡 Recommendation: Please manually open MetaTrader 5 desktop terminal and log into the expected account.")
        elif category == "IPC_TIMEOUT":
            logger.error("💡 Recommendation: Check that terminal64.exe is running, responsive, and not locked by another process.")
        elif category == "MISSING_EXECUTABLE":
            logger.error("💡 Recommendation: Ensure MT5 terminal64.exe path is correct in MT5_PATH .env setting.")
        
        conn.shutdown()



def cmd_backtest(config: Config, bars: int = 2000):
    """Run historical strategy backtest."""
    logger.info(f"=== Running Strategy Backtest on {config.SYMBOL} ({config.TIMEFRAME}) ===")
    conn = MT5Connection(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER, path=config.MT5_PATH)
    data = None
    if conn.initialize():
        md = MT5MarketData(conn)
        data = md.get_rates_dataframe(config.SYMBOL, config.TIMEFRAME, bars)
        conn.shutdown()

    if data is None or data.empty:
        logger.info("Using synthetic OHLCV dataset for backtest demonstration.")
        data = generate_synthetic_data(bars)

    bt = Backtester(config)
    bt.run(data)

def cmd_paper(config: Config):
    """Run safe paper / dry-run trading mode."""
    config.PAPER_MODE = True
    config.DRY_RUN = True
    runner = LiveTradingLoop(config, dry_run=True)
    runner.start()

def cmd_live(config: Config, confirm_live: bool = False, dry_run: bool = True):
    """Run live loop in dry-run or real execution mode."""
    if dry_run:
        logger.info("Executing Live Loop in SAFE DRY-RUN mode (order_send() blocked).")
        config.PAPER_MODE = True
        config.DRY_RUN = True
        runner = LiveTradingLoop(config, dry_run=True)
        runner.start()
    else:
        if not confirm_live:
            logger.error("🛑 LIVE TRADING BLOCKED: You must specify --confirm-live flag to execute real trades.")
            sys.exit(1)
        config.PAPER_MODE = False
        config.DRY_RUN = False
        config.ENABLE_TRADING = True
        runner = LiveTradingLoop(config, dry_run=False)
        runner.start(confirm_live=True)

def cmd_validate(config: Config):
    """Run Pine Script vs Python fidelity validation."""
    logger.info("=== Running Pine-vs-Python Fidelity Validation ===")
    df = generate_synthetic_data(1000)
    validator = PineVsPythonValidator()
    results = validator.run_full_validation(df)
    if results["all_passed"]:
        logger.info("✅ ALL VALIDATION CHECKS PASSED!")
    else:
        logger.error("❌ VALIDATION CHECKS FAILED!")

def cmd_test():
    """Run pytest suite."""
    import pytest
    logger.info("=== Executing Unit Test Suite ===")
    test_dir = str(Path(__file__).parent / "tests")
    exit_code = pytest.main([test_dir, "-v"])
    if exit_code == 0:
        logger.info("✅ All unit tests passed!")
    else:
        logger.error(f"❌ Test failures detected (Exit code: {exit_code})")

def cmd_web():
    """Launch local web server for trading dashboard and portfolio showcase."""
    import http.server
    import socketserver
    import webbrowser

    web_dir = Path(__file__).parent / "web"
    port = 8000
    os.chdir(web_dir)

    logger.info(f"🌐 Launching Trading Engine Web Dashboard at http://localhost:{port}...")
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass

    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Web server stopped by user.")

def main():
    parser = argparse.ArgumentParser(description="Python MT5 Trading Bot - Pine Script Translation System")
    parser.add_argument("command", choices=["test-connection", "backtest", "paper", "live", "validate", "test", "web"],
                        help="Action command to execute.")
    parser.add_argument("--confirm-live", action="store_true", help="Explicit confirmation flag required for live real trading.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run live loop in safe dry-run mode (order_send blocked).")
    parser.add_argument("--bars", type=int, default=2000, help="Number of historical bars for backtesting.")

    args = parser.parse_args()
    config = Config()

    if args.command == "test-connection":
        cmd_test_connection(config)
    elif args.command == "backtest":
        cmd_backtest(config, args.bars)
    elif args.command == "paper":
        cmd_paper(config)
    elif args.command == "live":
        is_dry = True if not args.confirm_live else False
        cmd_live(config, confirm_live=args.confirm_live, dry_run=is_dry)
    elif args.command == "validate":
        cmd_validate(config)
    elif args.command == "test":
        cmd_test()
    elif args.command == "web":
        cmd_web()



if __name__ == "__main__":
    main()

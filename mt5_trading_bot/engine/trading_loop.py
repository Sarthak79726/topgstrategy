import time
import pandas as pd
from typing import Optional, Dict, Any
from ..config import Config
from ..mt5.connection import MT5Connection
from ..mt5.market_data import MT5MarketData
from ..mt5.execution import OrderExecutionManager
from ..mt5.account import AccountManager
from ..strategy.candles import candle_zone
from .strategy_engine import StrategyEngine, TradingSignal
from ..utils.logger import logger, log_signal_to_csv, log_trade_to_csv
from ..risk.position_sizing import calculate_position_size
from ..mt5.connection import MT5Connection, ConnectionState

class LiveTradingLoop:
    """
    Live / Paper Trading Runner.
    Polls MT5 for historical + latest bars, updates StrategyEngine, and handles order execution / paper trading.
    """

    def __init__(self, config: Config, dry_run: Optional[bool] = None):
        self.config = config
        self.dry_run = dry_run if dry_run is not None else (config.DRY_RUN or config.PAPER_MODE or not config.ENABLE_TRADING)
        self.connection = MT5Connection(
            expected_account=config.EXPECTED_MT5_ACCOUNT,
            expected_server=config.EXPECTED_MT5_SERVER,
            path=config.MT5_PATH,
            timeout=config.MT5_TIMEOUT
        )
        self.market_data = MT5MarketData(connection=self.connection)
        self.account_info = AccountManager()
        self.execution = OrderExecutionManager(
            magic_number=config.MAGIC_NUMBER,
            dry_run=self.dry_run
        )

        self.engine = StrategyEngine(
            symbol=config.SYMBOL,
            timeframe=config.TIMEFRAME,
            max_bars=config.MAX_BARS,
            zone_body_pct=config.ZONE_BODY_PCT,
            tap_source=config.TAP_SOURCE,
            stop_on_tap=config.STOP_ON_TAP,
            stop_iss_34_by_wick_tap=config.STOP_ISS_34_BY_WICK_TAP
        )

        self.last_processed_bar_time: Optional[pd.Timestamp] = None
        self.processed_signal_keys = set()
        self.last_heartbeat_time: float = 0.0

    def start(self, confirm_live: bool = False):
        """Start polling loop."""
        logger.info("## MT5 CONNECTION CHECK")
        logger.info(f"Terminal:         {self.config.MT5_PATH or 'Auto-discovered'}")
        logger.info(f"Expected Account: {self.config.EXPECTED_MT5_ACCOUNT or 'Any logged in'}")
        logger.info(f"Expected Server:  {self.config.EXPECTED_MT5_SERVER or 'Any logged in'}")
        logger.info(f"Symbol:           {self.config.SYMBOL}")
        logger.info(f"Timeframe:        {self.config.TIMEFRAME}")
        logger.info(f"Execution Mode:   {'SAFE DRY-RUN (order_send BLOCKED)' if self.dry_run else 'LIVE REAL TRADING'}")

        if not self.dry_run and self.config.ENABLE_TRADING and not confirm_live:
            raise ValueError("Live trading requires explicit --confirm-live argument.")


        connected = self.connection.initialize_and_verify()
        if not connected:
            if self.connection.state == ConnectionState.ACCOUNT_MISMATCH:
                logger.error("🛑 TRADING BLOCKED: Connected MT5 account does not match expected account. Trading disabled for safety.")
                return
            else:
                logger.warning("MT5 terminal unavailable or account check failed. Operating in offline simulation mode.")

        try:
            while True:
                if self.connection.state == ConnectionState.ACCOUNT_MISMATCH or self.connection.state == ConnectionState.FAILED:
                    logger.error(f"🛑 Stopping trading loop safely due to connection state: {self.connection.state}")
                    break

                self.tick()
                time.sleep(self.config.POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Trading loop stopped by user.")
        finally:
            self.connection.shutdown()


    def tick(self):
        """Fetch latest candles, update strategy, process new signals."""
        df = self.market_data.get_rates_dataframe(
            symbol=self.config.SYMBOL,
            timeframe=self.config.TIMEFRAME,
            count=self.config.MAX_BARS
        )

        if df is None or df.empty:
            logger.debug("No candle data returned from MT5.")
            return

        latest_bar_time = df["time"].iloc[-1]

        # Periodic Heartbeat Log (Every 30s)
        now = time.time()
        if now - self.last_heartbeat_time >= 30.0:
            self.last_heartbeat_time = now
            logger.info(f"⏳ Polling {self.config.SYMBOL} ({self.config.TIMEFRAME}) | Latest Bar: {latest_bar_time} | Status: Active & Listening...")

        signals = self.engine.process_data(df)

        for sig in signals:
            sig_key = f"{sig.timestamp}_{sig.direction}_{sig.level_kind}_{sig.level_top:.4f}"
            if sig_key in self.processed_signal_keys:
                continue

            self.processed_signal_keys.add(sig_key)
            self._handle_signal(sig)

    def _handle_signal(self, sig: TradingSignal):
        """Handle signal logging and order routing."""
        logger.info(f"⚡ SIGNAL GENERATED: [{sig.direction}] Symbol={sig.symbol} Entry={sig.entry_price:.5f} SL={sig.stop_loss:.5f} TP={sig.take_profit:.5f} Reason={sig.reason}")

        # Log signal to CSV
        log_signal_to_csv({
            "timestamp": str(sig.timestamp),
            "symbol": sig.symbol,
            "timeframe": sig.timeframe,
            "signal_id": f"SIG_{sig.bar_index}_{sig.direction}",
            "direction": sig.direction,
            "entry": sig.entry_price,
            "stop_loss": sig.stop_loss,
            "take_profit": sig.take_profit,
            "strategy_component": sig.level_text,
            "reason": sig.reason
        })

        # Calculate position size based on account equity and risk %
        equity = AccountManager.get_equity()
        volume = calculate_position_size(
            equity=equity,
            risk_percent=self.config.RISK_PERCENT,
            entry_price=sig.entry_price,
            stop_loss=sig.stop_loss
        )

        if self.dry_run or self.config.PAPER_MODE or not self.config.ENABLE_TRADING:
            risk_amount = equity * (self.config.RISK_PERCENT / 100.0)
            acc_info = AccountManager.get_account_info() or {}
            acc_num = acc_info.get("login", "5056283582")
            acc_srv = acc_info.get("company", "MetaQuotes-Demo")

            logger.info("")
            logger.info("==================================================================")
            logger.info("[DRY RUN / SIMULATION]")
            logger.info(f"Account:         {acc_num}")
            logger.info(f"Server:          {acc_srv}")
            logger.info(f"Symbol:          {sig.symbol}")
            logger.info(f"Timeframe:       {sig.timeframe}")
            logger.info(f"Signal:          {sig.direction}")
            logger.info(f"Entry:           {sig.entry_price:.5f}")
            logger.info(f"Stop Loss:       {sig.stop_loss:.5f}")
            logger.info(f"Take Profit:     {sig.take_profit:.5f}")
            logger.info(f"Lot Size:        {volume:.2f}")
            logger.info(f"Risk:            ${risk_amount:.2f} ({self.config.RISK_PERCENT}%)")
            logger.info("Order execution: SKIPPED - DRY RUN")
            logger.info("==================================================================")
            logger.info("")

            log_trade_to_csv({
                "timestamp": str(sig.timestamp),
                "ticket": 9999000 + sig.bar_index,
                "symbol": sig.symbol,
                "order_type": sig.direction,
                "volume": volume,
                "price": sig.entry_price,
                "sl": sig.stop_loss,
                "tp": sig.take_profit,
                "profit": 0.0,
                "status": "SIMULATED_PAPER"
            })
            return

        if self.config.ENABLE_TRADING and not self.dry_run:
            logger.info(f"🚀 EXECUTING LIVE ORDER on MT5: {sig.direction} {volume} Lots on {sig.symbol} (Entry: {sig.entry_price:.5f}, SL: {sig.stop_loss:.5f}, TP: {sig.take_profit:.5f})")
            res = self.execution.send_order(
                symbol=sig.symbol,
                order_type=sig.direction,
                volume=volume,
                price=sig.entry_price,
                sl=sig.stop_loss,
                tp=sig.take_profit,
                comment=f"Bot_{sig.level_text}"
            )
            if res:
                logger.info(f"✅ Live Order executed successfully! Ticket: {res.get('ticket') or res.get('order')}")
            else:
                logger.error("❌ Live Order execution failed.")


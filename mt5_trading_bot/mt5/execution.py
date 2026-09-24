from typing import Optional, Dict, Any, List
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from ..utils.logger import logger, log_trade_to_csv

class OrderExecutionManager:
    """Handles MT5 trade execution, position management, SL/TP modification, and closing."""

    def __init__(self, magic_number: int = 26091901, dry_run: bool = True):
        self.magic_number = magic_number
        self.dry_run = dry_run

    def send_order(self, symbol: str, order_type: str, volume: float, price: float,
                   sl: Optional[float] = None, tp: Optional[float] = None,
                   comment: str = "JaduTona Bot") -> Optional[Dict[str, Any]]:
        """Send market or pending order to MT5 and validate response retcode."""
        if self.dry_run:
            logger.info(f"[DRY RUN] order_send() BLOCKED for safety: {symbol} {order_type} Vol={volume} Price={price} SL={sl} TP={tp}")
            return {
                "retcode": 10009, # TRADE_RETCODE_DONE
                "ticket": 99999999,
                "deal": 99999999,
                "volume": volume,
                "price": price,
                "comment": "SKIPPED - DRY RUN"
            }

        if not MT5_AVAILABLE:
            logger.warning("[PAPER/OFFLINE] Order placement simulated.")
            return {
                "retcode": 10009, # TRADE_RETCODE_DONE
                "ticket": 12345678,
                "deal": 12345678,
                "volume": volume,
                "price": price,
                "comment": "Paper Trading Success"
            }

        type_flag = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL

        # Get current tick for accurate price if needed
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            price = tick.ask if order_type.upper() == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": type_flag,
            "price": price,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if sl is not None and sl > 0:
            request["sl"] = float(sl)
        if tp is not None and tp > 0:
            request["tp"] = float(tp)

        logger.info(f"Sending MT5 Order: {symbol} {order_type} Vol={volume} Price={price} SL={sl} TP={tp}")
        result = mt5.order_send(request)

        if result is None:
            err = mt5.last_error()
            logger.error(f"MT5 order_send returned None. Error: {err}")
            return None

        trade_log = {
            "timestamp": result.request.time if hasattr(result, "request") else "",
            "symbol": symbol,
            "ticket": result.order,
            "order_type": order_type,
            "volume": result.volume,
            "price": result.price,
            "sl": sl or 0.0,
            "tp": tp or 0.0,
            "retcode": result.retcode,
            "result_comment": result.comment
        }
        log_trade_to_csv(trade_log)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed with retcode {result.retcode}: {result.comment}")
            return None

        logger.info(f"Order executed successfully! Ticket: {result.order}, Deal: {result.deal}, Executed Price: {result.price}")
        return {
            "retcode": result.retcode,
            "ticket": result.order,
            "deal": result.deal,
            "volume": result.volume,
            "price": result.price,
            "comment": result.comment
        }

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch active positions filtered by magic number and optional symbol."""
        if not MT5_AVAILABLE:
            return []

        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return []

        result = []
        for pos in positions:
            if pos.magic == self.magic_number:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "magic": pos.magic,
                    "time": pos.time
                })
        return result

    def close_position(self, ticket: int) -> bool:
        """Close an open position by ticket."""
        if self.dry_run:
            logger.info(f"[DRY RUN] close_position() BLOCKED for safety: Ticket {ticket}")
            return True

        if not MT5_AVAILABLE:
            return True

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            logger.warning(f"Position ticket {ticket} not found for closure.")
            return False

        pos = positions[0]
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "magic": self.magic_number,
            "comment": "Close Position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Closed position ticket {ticket} successfully.")
            return True
        else:
            logger.error(f"Failed to close position ticket {ticket}: {result.comment if result else mt5.last_error()}")
            return False

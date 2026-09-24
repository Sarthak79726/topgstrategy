import time
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from ..utils.logger import logger
from .discovery import resolve_mt5_executable, is_terminal_running, diagnose_mt5_installation


class ConnectionState:
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
    FAILED = "FAILED"


class MT5Connection:
    """
    Centralized MT5 Connection Manager.
    
    Responsibilities:
    - MT5 terminal initialization (WITHOUT calling mt5.login)
    - Strict account protection and verification against expected account/server
    - Connection state tracking (CONNECTED, DISCONNECTED, RECONNECTING, ACCOUNT_MISMATCH, FAILED)
    - Controlled reconnection with bounded backoff on IPC errors (-10004)
    - Clean shutdown handling
    """

    def __init__(
        self,
        expected_account: int = 0,
        expected_server: str = "",
        path: str = "",
        timeout: int = 120000,
        login: int = 0,       # Backward compatibility fallback
        password: str = "",   # Unused - passwords never used to switch accounts
        server: str = ""      # Backward compatibility fallback
    ):
        self.expected_account = expected_account or login
        self.expected_server = expected_server or server
        self.path = path
        self.timeout = timeout
        
        self.state = ConnectionState.DISCONNECTED
        self.last_error_details: Optional[Dict[str, Any]] = None
        self.resolved_executable_path: str = ""

    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    def initialize(self) -> bool:
        """
        Initialize IPC connection to the running MT5 terminal executable.
        NOTE: NEVER calls mt5.login() to force an account change.
        """
        self.last_error_details = None

        if not MT5_AVAILABLE:
            msg = "PACKAGE ERROR: MetaTrader5 Python package could not be imported."
            logger.error(f"[MT5] {msg}")
            self.last_error_details = {"code": -1, "message": msg, "category": "PACKAGE_ERROR"}
            self.state = ConnectionState.FAILED
            return False

        # Resolve executable path
        resolved_path, status_code, status_msg = resolve_mt5_executable(self.path)
        self.resolved_executable_path = resolved_path

        if status_code == "INVALID_PATH":
            msg = f"MISSING EXECUTABLE: Configured MT5 executable was not found ('{self.path}')."
            logger.error(f"[MT5] {msg}")
            self.last_error_details = {"code": -2, "message": msg, "category": "MISSING_EXECUTABLE"}
            self.state = ConnectionState.FAILED
            return False

        if status_code == "NOT_FOUND":
            msg = "MISSING EXECUTABLE: No MetaTrader 5 executable found. Please configure MT5_PATH in .env."
            logger.error(f"[MT5] {msg}")
            self.last_error_details = {"code": -3, "message": msg, "category": "MISSING_EXECUTABLE"}
            self.state = ConnectionState.FAILED
            return False

        logger.info("[MT5] Initializing MT5 terminal...")
        logger.info(f"[MT5] Executable path: {resolved_path}")
        logger.info(f"[MT5] Process state:   {'RUNNING' if is_terminal_running() else 'NOT RUNNING'}")
        logger.info(f"[MT5] Timeout:         {self.timeout / 1000:.0f}s")

        init_kwargs = {"timeout": self.timeout}
        if resolved_path:
            init_kwargs["path"] = resolved_path

        # Perform IPC initialization without mt5.login
        initialized = mt5.initialize(**init_kwargs)

        if not initialized:
            err_code, err_msg = mt5.last_error()
            if err_code == -10005 or "timeout" in str(err_msg).lower() or "ipc" in str(err_msg).lower():
                category = "IPC_TIMEOUT"
                msg = (
                    f"IPC TIMEOUT: MT5 terminal did not respond within {self.timeout / 1000:.0f}s. "
                    f"Ensure MT5 is running and responsive."
                )
            else:
                category = "TERMINAL_ERROR"
                msg = f"TERMINAL ERROR: MT5 terminal process did not respond ({err_code}, {err_msg})."

            logger.error(f"[MT5] {msg}")
            self.last_error_details = {"code": err_code, "message": err_msg, "category": category, "detailed_msg": msg}
            self.state = ConnectionState.DISCONNECTED
            return False

        logger.info("[MT5] IPC connection established successfully.")
        self.state = ConnectionState.CONNECTED
        return True

    def verify_account(
        self,
        expected_account: Optional[int] = None,
        expected_server: Optional[str] = None
    ) -> bool:
        """
        Verify the currently connected account against expected account/server values.
        Stops trading immediately if a mismatch is detected. NEVER calls mt5.login().
        """
        if not MT5_AVAILABLE or self.state != ConnectionState.CONNECTED:
            return False

        account_info = mt5.account_info()
        if account_info is None:
            err_code, err_msg = mt5.last_error()
            msg = f"Failed to retrieve account_info() from MT5 terminal ({err_code}, {err_msg})."
            logger.error(f"[MT5] {msg}")
            self.last_error_details = {"code": err_code, "message": err_msg, "category": "NO_ACCOUNT_INFO"}
            self.state = ConnectionState.FAILED
            return False

        target_account = expected_account if expected_account is not None else self.expected_account
        target_server = expected_server if expected_server is not None else self.expected_server

        logger.info(f"[MT5] Connected account: {account_info.login}")
        logger.info(f"[MT5] Connected server:  {account_info.server}")
        logger.info(f"[MT5] Connected company: {account_info.company}")
        logger.info(f"[MT5] Account balance:   ${account_info.balance:.2f}")
        logger.info(f"[MT5] Account equity:    ${account_info.equity:.2f}")

        # Verify account number match
        if target_account and target_account > 0 and account_info.login != target_account:
            logger.error("")
            logger.error("==================================================================")
            logger.error("🛑 WRONG MT5 ACCOUNT DETECTED!")
            logger.error(f"   Expected account:  {target_account}")
            logger.error(f"   Connected account: {account_info.login}")
            logger.error("   Trading disabled for safety. Please manually switch account in MT5.")
            logger.error("==================================================================")
            logger.error("")
            self.state = ConnectionState.ACCOUNT_MISMATCH
            self.last_error_details = {
                "code": -4,
                "message": f"Account mismatch: Expected {target_account}, got {account_info.login}",
                "category": "ACCOUNT_MISMATCH"
            }
            return False

        # Verify server match (fuzzy matching allowed for sub-servers e.g. MetaQuotes-Demo vs MetaQuotes Ltd)
        if target_server and target_server.strip():
            srv_clean = target_server.strip().lower()
            actual_srv = account_info.server.strip().lower()
            actual_comp = account_info.company.strip().lower()

            if srv_clean not in actual_srv and srv_clean not in actual_comp and actual_srv not in srv_clean:
                logger.error("")
                logger.error("==================================================================")
                logger.error("🛑 WRONG MT5 SERVER DETECTED!")
                logger.error(f"   Expected server:  {target_server}")
                logger.error(f"   Connected server: {account_info.server} ({account_info.company})")
                logger.error("   Trading disabled for safety. Please manually switch server in MT5.")
                logger.error("==================================================================")
                logger.error("")
                self.state = ConnectionState.ACCOUNT_MISMATCH
                self.last_error_details = {
                    "code": -5,
                    "message": f"Server mismatch: Expected {target_server}, got {account_info.server}",
                    "category": "ACCOUNT_MISMATCH"
                }
                return False

        logger.info("[MT5] Account verification: PASS")
        self.state = ConnectionState.CONNECTED
        return True

    def initialize_and_verify(
        self,
        expected_account: Optional[int] = None,
        expected_server: Optional[str] = None
    ) -> bool:
        """Initialize IPC connection and perform strict account protection verification."""
        if not self.initialize():
            return False
        return self.verify_account(expected_account, expected_server)

    def reconnect(self, max_attempts: int = 4) -> bool:
        """
        Controlled reconnection procedure with bounded backoff.
        Triggered when an IPC connection loss (-10004) is detected.
        NEVER calls mt5.login().
        """
        if self.state == ConnectionState.ACCOUNT_MISMATCH:
            logger.error("[MT5] Cannot auto-reconnect due to ACCOUNT_MISMATCH. Please switch accounts manually in MT5.")
            return False

        self.state = ConnectionState.RECONNECTING
        backoff_delays = [2, 5, 10, 20]

        logger.warning(f"[MT5] IPC connection lost. Initiating controlled reconnection procedure (Max {max_attempts} attempts)...")

        for attempt in range(1, max_attempts + 1):
            delay = backoff_delays[min(attempt - 1, len(backoff_delays) - 1)]
            logger.info(f"[MT5] Reconnection attempt {attempt}/{max_attempts} (waiting {delay}s)...")

            if MT5_AVAILABLE:
                try:
                    mt5.shutdown()
                except Exception:
                    pass

            time.sleep(delay)

            if self.initialize():
                if self.verify_account():
                    logger.info(f"[MT5] ✅ Reconnection successful! Resuming trading loop.")
                    self.state = ConnectionState.CONNECTED
                    return True
                elif self.state == ConnectionState.ACCOUNT_MISMATCH:
                    logger.error("[MT5] Reconnection aborted due to account mismatch.")
                    return False

        self.state = ConnectionState.FAILED
        logger.error(f"[MT5] ❌ Reconnection failed after {max_attempts} attempts. Stopping trading loop safely.")
        return False

    def handle_ipc_error(self, err_code: int, err_msg: str) -> bool:
        """Handle IPC errors (-10004) by initiating controlled reconnection."""
        logger.error(f"[MT5] IPC error detected ({err_code}, '{err_msg}'). Initiating recovery...")
        return self.reconnect()

    def shutdown(self):
        """Cleanly shutdown MT5 connection."""
        if MT5_AVAILABLE:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self.state = ConnectionState.DISCONNECTED
        logger.info("[MT5] MT5 shutdown completed.")

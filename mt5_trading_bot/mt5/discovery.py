import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


def discover_mt5_installations() -> List[str]:
    """
    Safely discover terminal64.exe installations on Windows.
    Returns a list of valid existing file paths.
    """
    candidates = []
    
    # Standard installation directories
    standard_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe",
        str(Path(__file__).parent.parent / "terminal64.exe"),
        str(Path.cwd() / "terminal64.exe")
    ]
    
    # Check standard paths
    for path_str in standard_paths:
        try:
            p = Path(path_str).resolve()
            if p.is_file() and str(p) not in candidates:
                candidates.append(str(p))
        except Exception:
            pass

    # Dynamic search in Program Files for broker-customized MT5 folders
    program_dirs = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    
    for base_dir in program_dirs:
        if not base_dir or not os.path.exists(base_dir):
            continue
        try:
            for entry in os.listdir(base_dir):
                if "metatrader" in entry.lower() or "mt5" in entry.lower():
                    t_path = os.path.join(base_dir, entry, "terminal64.exe")
                    p = Path(t_path).resolve()
                    if p.is_file() and str(p) not in candidates:
                        candidates.append(str(p))
        except Exception:
            pass

    # Try Windows Registry search if on Windows
    if sys.platform == "win32":
        try:
            import winreg
            for hkey in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    reg_key = winreg.OpenKey(hkey, r"Software\MetaQuotes\Terminal")
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(reg_key, i)
                            i += 1
                            try:
                                subkey = winreg.OpenKey(reg_key, subkey_name)
                                path_val, _ = winreg.QueryValueEx(subkey, "Main Path")
                                t_path = str(Path(path_val) / "terminal64.exe")
                                if Path(t_path).is_file() and t_path not in candidates:
                                    candidates.append(t_path)
                            except Exception:
                                pass
                        except OSError:
                            break
                except Exception:
                    pass
        except Exception:
            pass

    return candidates


def resolve_mt5_executable(configured_path: str) -> Tuple[str, str, str]:
    """
    Resolve which MT5 executable to use based on priority:
    1. MT5_PATH from .env (if provided)
    2. Auto-detected installation
    3. Fail cleanly

    Returns:
        (selected_path, status_code, description)
    """
    cleaned_path = configured_path.strip().strip('"').strip("'") if configured_path else ""

    if cleaned_path:
        p = Path(cleaned_path)
        if p.is_file():
            return (str(p.resolve()), "CONFIGURED", "Using MT5_PATH specified in .env.")
        else:
            return (cleaned_path, "INVALID_PATH", f"Configured MT5_PATH '{cleaned_path}' was not found or is not a file.")

    # Auto discovery if path not explicitly set
    installations = discover_mt5_installations()
    if installations:
        return (installations[0], "AUTO_DISCOVERED", f"Auto-discovered MT5 terminal at '{installations[0]}'.")

    return ("", "NOT_FOUND", "No MetaTrader 5 executable found on system. Please configure MT5_PATH in .env.")


def is_terminal_running() -> bool:
    """Check if terminal64.exe process is currently running on the system."""
    if sys.platform == "win32":
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq terminal64.exe"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            return "terminal64.exe" in output.lower()
        except Exception:
            pass
    return False


def diagnose_mt5_installation(config: Any) -> Dict[str, Any]:
    """
    Generate comprehensive diagnostic dictionary without revealing credentials.
    """
    configured_path = getattr(config, "MT5_PATH", "")
    resolved_path, status_code, status_msg = resolve_mt5_executable(configured_path)
    all_detected = discover_mt5_installations()
    running = is_terminal_running()

    login = getattr(config, "MT5_LOGIN", 0)
    server = getattr(config, "MT5_SERVER", "")
    password = getattr(config, "MT5_PASSWORD", "")
    timeout = getattr(config, "MT5_TIMEOUT", 120000)

    last_err = mt5.last_error() if MT5_AVAILABLE and mt5 else (None, "Package not loaded")

    return {
        "os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "python_version": sys.version.split()[0],
        "mt5_package_installed": MT5_AVAILABLE,
        "mt5_package_version": getattr(mt5, "__version__", "N/A") if MT5_AVAILABLE else "NOT INSTALLED",
        "configured_path": configured_path or "NOT SET",
        "resolved_path": resolved_path or "NONE",
        "path_status": status_code,
        "path_message": status_msg,
        "path_exists": Path(resolved_path).is_file() if resolved_path else False,
        "detected_installations": all_detected,
        "terminal_running": running,
        "login_configured": str(login) if login else "NOT SET",
        "server_configured": server or "NOT SET",
        "password_configured": "YES" if bool(password) else "NO",
        "timeout_ms": timeout,
        "last_error": last_err
    }

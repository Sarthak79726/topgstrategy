@echo off
TITLE MT5 Trading Bot - Live Real Trading Mode
cd /d "%~dp0.."
echo ===================================================
echo   Starting MT5 Automated Trading Bot (LIVE MODE)
echo ===================================================
python -m mt5_trading_bot.main live --confirm-live
pause

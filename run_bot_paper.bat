@echo off
TITLE MT5 Trading Bot - Safe Paper Trading Mode
cd /d "%~dp0.."
echo ===================================================
echo   Starting MT5 Automated Trading Bot (PAPER MODE)
echo ===================================================
python -m mt5_trading_bot.main paper
pause

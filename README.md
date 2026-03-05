# 🥇 Gold Trading Bot

A comprehensive Python-based trading bot for automated gold (XAUUSD) trading on MetaTrader 5.

## Features

### Trading Strategies
- **Technical Analysis**: RSI, MACD, EMA crossovers, Bollinger Bands
- **Trend Following**: EMA crossovers, Golden Cross/Death Cross, ADX-based trends
- **Fundamental Analysis**: Fed rate expectations, inflation data, geopolitical risk, dollar strength

### Risk Management
- Position sizing with multiple methods (fixed fractional, Kelly criterion, ATR-based)
- Stop loss and take profit with ATR-based dynamic stops
- Daily drawdown limits
- Maximum position limits
- Risk:reward ratio enforcement

### Additional Features
- Backtesting engine with historical data
- Telegram alerts for trade notifications
- Email alerts and daily summaries
- SQLite database for trade logging
- Real-time web dashboard with performance charts
- Paper trading mode for testing

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bot_njrj
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your MT5 credentials:
```
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_mt5_server
```

4. (Optional) Configure Telegram alerts:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

5. (Optional) Configure email alerts:
```
EMAIL_FROM=your_email@example.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=your_email@example.com
```

## Usage

### Paper Trading (Recommended for Testing)
```bash
python main.py --mode live
```

### Live Trading
Set `TRADING_MODE=live` in `.env` and run:
```bash
python main.py --mode live
```

### Backtesting
```bash
# Backtest all strategies
python main.py --mode backtest --days 30

# Backtest specific strategy
python main.py --mode backtest --strategy "Technical Analysis" --days 30
```

### Dashboard
```bash
python main.py --mode dashboard
```

Access the dashboard at: `http://127.0.0.1:8050`

## Configuration

Edit `src/config/config.py` to customize:
- Risk parameters (RISK_PER_TRADE, MAX_DAILY_DRAWDOWN)
- Strategy parameters (RSI_PERIOD, EMA periods, etc.)
- Trading settings (DEFAULT_LOT_SIZE, MAX_POSITIONS)
- Alert preferences

## Risk Warning

⚠️ **This bot involves significant financial risk. Always test with paper trading first and never trade with money you cannot afford to lose.**

- Start with micro lot sizes (0.01)
- Use paper trading mode initially
- Monitor the bot closely during live trading
- Understand all strategies before deployment
- Use appropriate risk management settings

## Project Structure

```
bot_njrj/
├── src/
│   ├── config/          # Configuration settings
│   ├── mt5/            # MetaTrader 5 integration
│   ├── strategies/     # Trading strategies
│   ├── risk/           # Risk management
│   ├── backtesting/    # Backtesting engine
│   ├── alerts/         # Telegram and email alerts
│   ├── database/       # Database manager
│   └── dashboard/      # Web dashboard
├── logs/               # Trading logs
├── data/               # Historical data
├── main.py             # Main entry point
└── requirements.txt    # Dependencies
```

## Strategies

1. **Technical Analysis Strategy**: Uses RSI, MACD, EMA, and Bollinger Bands for signal generation
2. **RSI Mean Reversion**: Trades oversold/overbought conditions
3. **Bollinger Band Breakout**: Trades price breakouts from BB bands
4. **Trend Following Strategy**: Trades pullbacks in established trends
5. **Golden Cross/Death Cross**: Trades EMA crossover signals
6. **ADX Trend Strategy**: Trades strong trends based on ADX indicator
7. **Fundamental Strategy**: Based on macroeconomic factors
8. **News Based Strategy**: Trades based on news sentiment
9. **Macro Trend Strategy**: Uses real yields and dollar index trends

## Monitoring

### Telegram Alerts
Real-time notifications for:
- New trade entries
- Position closures
- Stop loss hits
- Take profit hits
- Daily summaries
- Error alerts

### Email Alerts
Daily reports including:
- End-of-day summary
- Weekly performance report
- Risk alerts
- System status

### Web Dashboard
Real-time visualization of:
- Account balance and equity
- Open positions
- Trade history
- Strategy performance
- Daily statistics

## Troubleshooting

### MT5 Connection Issues
- Ensure MT5 is running
- Verify login credentials in `.env`
- Check that XAUUSD symbol is available in Market Watch

### Strategy Not Generating Signals
- Check if enough historical data is available
- Verify strategy parameters in config
- Review logs for errors

### Telegram Alerts Not Working
- Verify bot token and chat ID
- Ensure bot is started and has permission to send messages

## License

This project is for educational purposes. Use at your own risk.

## Disclaimer

This software is provided "as is" without warranty of any kind. The authors are not responsible for any financial losses incurred while using this bot. Trading involves substantial risk of loss and is not suitable for every investor.

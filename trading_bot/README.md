# Trading Bot

A modular, extensible trading bot with backtesting, paper trading, and live trading capabilities.

## Features

- **Trading Strategies**: EMA Crossover (default), RSI, MACD, Bollinger Bands
- **Backtesting Engine**: Test strategies with historical data
- **Paper Trading**: Simulate trades without real money
- **Risk Management**: Stop-loss, take-profit, max drawdown protection, trailing stops
- **Smart Order Handling**: Limit/market orders, slippage simulation, retry logic
- **Logging and Notifications**: File logs, Telegram/email alerts, console dashboard

## Project Structure

```
trading_bot/
├── config/                  # Configuration files
│   └── config.yaml          # Main configuration
├── data/                    # Historical and market data
├── logs/                    # Trading and error logs
├── src/                     # Source code
│   ├── strategies/          # Trading strategies
│   ├── indicators/          # Technical indicators
│   ├── backtesting/         # Backtesting engine
│   ├── exchange/            # Exchange connectors
│   ├── risk/                # Risk management
│   ├── utils/               # Utility functions
│   └── notifications/       # Notification services
├── tests/                   # Unit and integration tests
└── main.py                  # Entry point
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure the bot in `config/config.yaml`

## Usage

### Backtesting

```bash
python main.py --mode backtest --config config/config.yaml
```

### Paper Trading

```bash
python main.py --mode paper --config config/config.yaml
```

### Live Trading

```bash
python main.py --mode live --config config/config.yaml
```

## Configuration

Edit `config/config.yaml` to customize:
- Trading pairs/symbols
- Timeframes
- Strategy parameters
- Risk management settings
- Exchange API credentials

## Extending the Bot

### Adding New Strategies

Create a new strategy class in `src/strategies/` that inherits from the base Strategy class.

### Adding Exchange Connectors

Implement a new exchange connector in `src/exchange/` that follows the Exchange interface.

## License

MIT
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trading Bot - Main Entry Point

This script serves as the entry point for the trading bot application.
It parses command-line arguments, loads configuration, and initializes
the appropriate trading mode (backtest, paper, or live).
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from loguru import logger

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.backtesting.backtest_engine import BacktestEngine
from src.exchange.exchange_factory import ExchangeFactory
from src.strategies.strategy_factory import StrategyFactory
from src.utils.config_loader import ConfigLoader
from src.utils.logger_setup import setup_logger


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Trading Bot")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["backtest", "paper", "live"],
        default="backtest",
        help="Trading mode: backtest, paper, or live",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        help="Override strategy from config file",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        help="Override trading symbol from config file",
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    return parser.parse_args()


def main():
    """Main entry point for the trading bot."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config_loader = ConfigLoader(args.config)
    config = config_loader.load()
    
    # Override config with command line arguments if provided
    if args.strategy:
        config["strategy"]["name"] = args.strategy
    if args.symbol:
        config["trading"]["symbol"] = args.symbol
    if args.verbose:
        config["general"]["log_level"] = "DEBUG"
    
    # Set up logging
    log_level = config["general"]["log_level"]
    log_file = config["logging"]["file_path"]
    setup_logger(log_level, log_file, config["logging"]["file_enabled"])
    
    logger.info(f"Starting trading bot in {args.mode} mode")
    logger.info(f"Using strategy: {config['strategy']['name']}")
    logger.info(f"Trading symbol: {config['trading']['symbol']}")
    
    # Initialize strategy
    strategy_factory = StrategyFactory()
    strategy = strategy_factory.create_strategy(
        config["strategy"]["name"],
        config["strategy"]["params"][config["strategy"]["name"].lower()],
        config["trading"]["timeframe"]
    )
    
    # Initialize exchange (if not in backtest mode)
    exchange = None
    if args.mode != "backtest":
        exchange_factory = ExchangeFactory()
        exchange = exchange_factory.create_exchange(
            config["exchange"]["name"],
            config["exchange"]["api_key"],
            config["exchange"]["api_secret"],
            config["exchange"]["testnet"]
        )
    
    # Run in the appropriate mode
    if args.mode == "backtest":
        logger.info("Initializing backtesting engine")
        backtest_engine = BacktestEngine(
            strategy=strategy,
            config=config,
        )
        results = backtest_engine.run()
        backtest_engine.display_results(results)
    
    elif args.mode == "paper":
        from src.exchange.paper_trading import PaperTradingExchange
        
        logger.info("Initializing paper trading mode")
        paper_exchange = PaperTradingExchange(
            exchange_name=config["exchange"]["name"],
            initial_balance=config["backtest"]["initial_balance"],
            fee_rate=config["backtest"]["fee_rate"],
            slippage=config["backtest"]["slippage"]
        )
        
        from src.utils.trading_loop import TradingLoop
        
        trading_loop = TradingLoop(
            strategy=strategy,
            exchange=paper_exchange,
            config=config,
            is_live=False
        )
        trading_loop.run()
    
    elif args.mode == "live":
        logger.warning("LIVE TRADING MODE ACTIVATED - REAL FUNDS WILL BE USED")
        
        # Additional safety check for live trading
        confirmation = input("Are you sure you want to start live trading? (yes/no): ")
        if confirmation.lower() != "yes":
            logger.info("Live trading aborted by user")
            return
        
        from src.utils.trading_loop import TradingLoop
        
        trading_loop = TradingLoop(
            strategy=strategy,
            exchange=exchange,
            config=config,
            is_live=True
        )
        trading_loop.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Backtest Engine

This module provides functionality for backtesting trading strategies
using historical price data.
"""

import datetime
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.utils.data_loader import DataLoader
from src.utils.performance_metrics import calculate_metrics


class BacktestEngine:
    """
    Engine for backtesting trading strategies.
    
    This class provides functionality to backtest trading strategies
    using historical price data and evaluate their performance.
    """
    
    def __init__(self, strategy: BaseStrategy, config: Dict):
        """
        Initialize the backtest engine.
        
        Args:
            strategy: Trading strategy to backtest
            config: Configuration dictionary
        """
        self.strategy = strategy
        self.config = config
        self.data_loader = DataLoader()
        
        # Extract backtest configuration
        self.start_date = config["backtest"]["start_date"]
        self.end_date = config["backtest"]["end_date"]
        self.initial_balance = config["backtest"]["initial_balance"]
        self.fee_rate = config["backtest"]["fee_rate"]
        self.slippage = config["backtest"]["slippage"]
        
        # Trading parameters
        self.symbol = config["trading"]["symbol"]
        self.timeframe = config["trading"]["timeframe"]
        
        # Risk management
        self.risk_params = config["risk_management"]
        
        logger.info(f"Initialized backtest engine for {self.symbol} from {self.start_date} to {self.end_date}")
    
    def run(self) -> Dict:
        """
        Run the backtest.
        
        Returns:
            Dictionary containing backtest results
        """
        logger.info(f"Loading historical data for {self.symbol}")
        
        # Load historical data
        data = self.data_loader.load_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        if data.empty:
            logger.error("No historical data available for backtesting")
            return {"error": "No historical data available"}
        
        logger.info(f"Loaded {len(data)} historical data points")
        
        # Apply strategy to generate signals
        data = self.strategy.analyze(data)
        
        # Run the backtest simulation
        results = self._simulate_trades(data)
        
        # Calculate performance metrics
        metrics = calculate_metrics(results)
        
        # Combine results and metrics
        backtest_results = {
            "data": data,
            "trades": results["trades"],
            "equity_curve": results["equity_curve"],
            "metrics": metrics
        }
        
        logger.info(f"Backtest completed with {len(results['trades'])} trades")
        logger.info(f"Final balance: {results['equity_curve'].iloc[-1]['equity']:.2f}")
        
        return backtest_results
    
    def _simulate_trades(self, data: pd.DataFrame) -> Dict:
        """
        Simulate trades based on strategy signals.
        
        Args:
            data: DataFrame with price data and strategy signals
            
        Returns:
            Dictionary containing trades and equity curve
        """
        # Initialize variables
        balance = self.initial_balance
        position = 0  # 0: no position, 1: long, -1: short
        entry_price = 0
        entry_time = None
        stop_loss = 0
        take_profit = 0
        
        # Lists to track trades and equity
        trades = []
        equity_curve = []
        
        # Add equity at the start
        equity_curve.append({
            "timestamp": data.index[0],
            "equity": balance,
            "drawdown": 0,
        })
        
        # Track maximum equity for drawdown calculation
        max_equity = balance
        
        # Iterate through each data point
        for i, row in data.iterrows():
            current_price = row["close"]
            timestamp = i
            
            # Update equity with unrealized PnL if in position
            if position != 0:
                unrealized_pnl = position * (current_price - entry_price) * balance / entry_price
                current_equity = balance + unrealized_pnl
            else:
                current_equity = balance
            
            # Update max equity and calculate drawdown
            max_equity = max(max_equity, current_equity)
            drawdown = (max_equity - current_equity) / max_equity if max_equity > 0 else 0
            
            # Check for stop loss or take profit if in position
            if position == 1:  # Long position
                # Check for stop loss
                if current_price <= stop_loss:
                    # Close position at stop loss
                    exit_price = stop_loss * (1 - self.slippage)  # Account for slippage
                    pnl = (exit_price - entry_price) / entry_price * balance
                    fee = exit_price * self.fee_rate * balance / entry_price
                    balance = balance + pnl - fee
                    
                    # Record the trade
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": timestamp,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "position": "long",
                        "pnl": pnl,
                        "fee": fee,
                        "exit_reason": "stop_loss"
                    })
                    
                    # Reset position
                    position = 0
                    logger.debug(f"Stop loss triggered at {exit_price} (Long)")
                
                # Check for take profit
                elif current_price >= take_profit:
                    # Close position at take profit
                    exit_price = take_profit * (1 - self.slippage)  # Account for slippage
                    pnl = (exit_price - entry_price) / entry_price * balance
                    fee = exit_price * self.fee_rate * balance / entry_price
                    balance = balance + pnl - fee
                    
                    # Record the trade
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": timestamp,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "position": "long",
                        "pnl": pnl,
                        "fee": fee,
                        "exit_reason": "take_profit"
                    })
                    
                    # Reset position
                    position = 0
                    logger.debug(f"Take profit triggered at {exit_price} (Long)")
            
            elif position == -1:  # Short position
                # Check for stop loss
                if current_price >= stop_loss:
                    # Close position at stop loss
                    exit_price = stop_loss * (1 + self.slippage)  # Account for slippage
                    pnl = (entry_price - exit_price) / entry_price * balance
                    fee = exit_price * self.fee_rate * balance / entry_price
                    balance = balance + pnl - fee
                    
                    # Record the trade
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": timestamp,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "position": "short",
                        "pnl": pnl,
                        "fee": fee,
                        "exit_reason": "stop_loss"
                    })
                    
                    # Reset position
                    position = 0
                    logger.debug(f"Stop loss triggered at {exit_price} (Short)")
                
                # Check for take profit
                elif current_price <= take_profit:
                    # Close position at take profit
                    exit_price = take_profit * (1 + self.slippage)  # Account for slippage
                    pnl = (entry_price - exit_price) / entry_price * balance
                    fee = exit_price * self.fee_rate * balance / entry_price
                    balance = balance + pnl - fee
                    
                    # Record the trade
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": timestamp,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "position": "short",
                        "pnl": pnl,
                        "fee": fee,
                        "exit_reason": "take_profit"
                    })
                    
                    # Reset position
                    position = 0
                    logger.debug(f"Take profit triggered at {exit_price} (Short)")
            
            # Check for buy signal if not in position
            if position == 0 and row["buy_signal"]:
                # Enter long position
                entry_price = current_price * (1 + self.slippage)  # Account for slippage
                entry_time = timestamp
                position = 1
                
                # Calculate stop loss and take profit
                stop_loss = self.strategy.calculate_stop_loss(data.loc[:i], "long", entry_price)
                take_profit = self.strategy.calculate_take_profit(
                    entry_price, stop_loss, self.risk_params.get("risk_reward_ratio", 2.0)
                )
                
                # Pay fee
                fee = entry_price * self.fee_rate
                balance -= fee
                
                logger.debug(f"Entered long position at {entry_price}")
                logger.debug(f"Stop loss: {stop_loss}, Take profit: {take_profit}")
            
            # Check for sell signal if not in position
            elif position == 0 and row["sell_signal"]:
                # Enter short position
                entry_price = current_price * (1 - self.slippage)  # Account for slippage
                entry_time = timestamp
                position = -1
                
                # Calculate stop loss and take profit
                stop_loss = self.strategy.calculate_stop_loss(data.loc[:i], "short", entry_price)
                take_profit = self.strategy.calculate_take_profit(
                    entry_price, stop_loss, self.risk_params.get("risk_reward_ratio", 2.0)
                )
                
                # Pay fee
                fee = entry_price * self.fee_rate
                balance -= fee
                
                logger.debug(f"Entered short position at {entry_price}")
                logger.debug(f"Stop loss: {stop_loss}, Take profit: {take_profit}")
            
            # Check for exit signal if in position
            elif position == 1 and row["sell_signal"]:
                # Exit long position
                exit_price = current_price * (1 - self.slippage)  # Account for slippage
                pnl = (exit_price - entry_price) / entry_price * balance
                fee = exit_price * self.fee_rate * balance / entry_price
                balance = balance + pnl - fee
                
                # Record the trade
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": timestamp,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "position": "long",
                    "pnl": pnl,
                    "fee": fee,
                    "exit_reason": "signal"
                })
                
                # Reset position
                position = 0
                logger.debug(f"Exited long position at {exit_price} (Signal)")
            
            elif position == -1 and row["buy_signal"]:
                # Exit short position
                exit_price = current_price * (1 + self.slippage)  # Account for slippage
                pnl = (entry_price - exit_price) / entry_price * balance
                fee = exit_price * self.fee_rate * balance / entry_price
                balance = balance + pnl - fee
                
                # Record the trade
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": timestamp,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "position": "short",
                    "pnl": pnl,
                    "fee": fee,
                    "exit_reason": "signal"
                })
                
                # Reset position
                position = 0
                logger.debug(f"Exited short position at {exit_price} (Signal)")
            
            # Record equity
            equity_curve.append({
                "timestamp": timestamp,
                "equity": current_equity,
                "drawdown": drawdown,
            })
        
        # Close any open position at the end of the backtest
        if position != 0:
            current_price = data.iloc[-1]["close"]
            exit_time = data.index[-1]
            
            if position == 1:  # Long position
                exit_price = current_price * (1 - self.slippage)
                pnl = (exit_price - entry_price) / entry_price * balance
                fee = exit_price * self.fee_rate * balance / entry_price
                balance = balance + pnl - fee
                
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "position": "long",
                    "pnl": pnl,
                    "fee": fee,
                    "exit_reason": "end_of_backtest"
                })
                
                logger.debug(f"Closed long position at end of backtest: {exit_price}")
            
            elif position == -1:  # Short position
                exit_price = current_price * (1 + self.slippage)
                pnl = (entry_price - exit_price) / entry_price * balance
                fee = exit_price * self.fee_rate * balance / entry_price
                balance = balance + pnl - fee
                
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "position": "short",
                    "pnl": pnl,
                    "fee": fee,
                    "exit_reason": "end_of_backtest"
                })
                
                logger.debug(f"Closed short position at end of backtest: {exit_price}")
        
        # Convert lists to DataFrames
        trades_df = pd.DataFrame(trades)
        equity_curve_df = pd.DataFrame(equity_curve)
        
        return {
            "trades": trades_df,
            "equity_curve": equity_curve_df
        }
    
    def display_results(self, results: Dict) -> None:
        """
        Display backtest results.
        
        Args:
            results: Dictionary containing backtest results
        """
        if "error" in results:
            logger.error(f"Error in backtest: {results['error']}")
            return
        
        trades = results["trades"]
        equity_curve = results["equity_curve"]
        metrics = results["metrics"]
        
        # Print summary statistics
        print("\n===== Backtest Results =====")
        print(f"Symbol: {self.symbol}")
        print(f"Timeframe: {self.timeframe}")
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Strategy: {self.strategy.name}")
        print("\n----- Performance Metrics -----")
        print(f"Initial Balance: ${self.initial_balance:.2f}")
        print(f"Final Balance: ${equity_curve.iloc[-1]['equity']:.2f}")
        print(f"Total Return: {metrics['total_return']:.2f}%")
        print(f"Annualized Return: {metrics['annualized_return']:.2f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
        print(f"Win Rate: {metrics['win_rate']:.2f}%")
        print(f"Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Winning Trades: {metrics['winning_trades']}")
        print(f"Losing Trades: {metrics['losing_trades']}")
        print(f"Average Win: ${metrics['avg_win']:.2f}")
        print(f"Average Loss: ${metrics['avg_loss']:.2f}")
        print(f"Average Trade: ${metrics['avg_trade']:.2f}")
        
        # Plot equity curve
        self._plot_equity_curve(equity_curve)
        
        # Plot drawdown
        self._plot_drawdown(equity_curve)
        
        # Plot trade distribution
        if not trades.empty:
            self._plot_trade_distribution(trades)
    
    def _plot_equity_curve(self, equity_curve: pd.DataFrame) -> None:
        """
        Plot the equity curve.
        
        Args:
            equity_curve: DataFrame containing equity curve data
        """
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve["timestamp"], equity_curve["equity"])
        plt.title("Equity Curve")
        plt.xlabel("Date")
        plt.ylabel("Equity ($)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    def _plot_drawdown(self, equity_curve: pd.DataFrame) -> None:
        """
        Plot the drawdown.
        
        Args:
            equity_curve: DataFrame containing equity curve data
        """
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve["timestamp"], equity_curve["drawdown"] * 100)
        plt.title("Drawdown")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    def _plot_trade_distribution(self, trades: pd.DataFrame) -> None:
        """
        Plot the distribution of trade profits.
        
        Args:
            trades: DataFrame containing trade data
        """
        plt.figure(figsize=(12, 6))
        plt.hist(trades["pnl"], bins=50)
        plt.title("Trade Profit Distribution")
        plt.xlabel("Profit/Loss ($)")
        plt.ylabel("Frequency")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trading Loop

This module provides the main trading loop for paper and live trading modes.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any

import pandas as pd
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.utils.data_loader import DataLoader
from src.notifications.notification_manager import NotificationManager


class TradingLoop:
    """
    Trading loop for paper and live trading.
    
    This class implements the main trading loop that fetches market data,
    applies the trading strategy, and executes trades.
    """
    
    def __init__(self, strategy: BaseStrategy, exchange, config: Dict[str, Any], is_live: bool = False):
        """
        Initialize the trading loop.
        
        Args:
            strategy: Trading strategy to use
            exchange: Exchange connector
            config: Configuration dictionary
            is_live: Whether this is live trading (True) or paper trading (False)
        """
        self.strategy = strategy
        self.exchange = exchange
        self.config = config
        self.is_live = is_live
        
        # Extract configuration
        self.symbol = config["trading"]["symbol"]
        self.timeframe = config["trading"]["timeframe"]
        self.risk_params = config["risk_management"]
        
        # Initialize data loader
        self.data_loader = DataLoader()
        
        # Initialize notification manager if enabled
        self.notifications_enabled = config["notifications"]["enabled"]
        if self.notifications_enabled:
            self.notification_manager = NotificationManager(config["notifications"])
        
        # Trading state
        self.current_position = 0  # 0: no position, 1: long, -1: short
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.position_size = 0
        
        # Initialize trading data
        self.data = pd.DataFrame()
        
        logger.info(f"Initialized {'live' if is_live else 'paper'} trading loop for {self.symbol}")
    
    def run(self) -> None:
        """
        Run the trading loop.
        
        This method implements the main trading loop that runs indefinitely
        until interrupted by the user.
        """
        logger.info(f"Starting {'live' if self.is_live else 'paper'} trading loop")
        
        # Send notification
        if self.notifications_enabled:
            mode = "Live" if self.is_live else "Paper"
            self.notification_manager.send_notification(
                f"{mode} trading started for {self.symbol}",
                f"Trading bot started in {mode.lower()} mode for {self.symbol} using {self.strategy.name} strategy."
            )
        
        try:
            # Main trading loop
            while True:
                # Get current time
                now = datetime.now()
                
                # Fetch latest market data
                self._update_market_data()
                
                # Apply strategy to generate signals
                if not self.data.empty:
                    self.data = self.strategy.analyze(self.data)
                    
                    # Check for trading signals
                    self._check_signals()
                    
                    # Update dashboard
                    self._update_dashboard()
                
                # Sleep until next iteration
                self._sleep_until_next_candle(now)
        
        except KeyboardInterrupt:
            logger.info("Trading loop stopped by user")
            
            # Send notification
            if self.notifications_enabled:
                mode = "Live" if self.is_live else "Paper"
                self.notification_manager.send_notification(
                    f"{mode} trading stopped for {self.symbol}",
                    f"Trading bot stopped in {mode.lower()} mode for {self.symbol}."
                )
        
        except Exception as e:
            logger.exception(f"Error in trading loop: {e}")
            
            # Send notification
            if self.notifications_enabled:
                mode = "Live" if self.is_live else "Paper"
                self.notification_manager.send_notification(
                    f"Error in {mode.lower()} trading for {self.symbol}",
                    f"Trading bot encountered an error: {e}"
                )
    
    def _update_market_data(self) -> None:
        """
        Fetch and update market data.
        """
        try:
            # Fetch latest OHLCV data from exchange
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=100  # Fetch last 100 candles
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            
            # Update data
            self.data = df
            
            logger.debug(f"Updated market data for {self.symbol}, latest close: {df.iloc[-1]['close']}")
        
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            
            # Retry with exponential backoff
            for i in range(3):  # Try 3 times
                try:
                    logger.info(f"Retrying market data update (attempt {i+1}/3)")
                    time.sleep(2 ** i)  # Exponential backoff: 1, 2, 4 seconds
                    
                    # Fetch latest OHLCV data from exchange
                    ohlcv = self.exchange.fetch_ohlcv(
                        symbol=self.symbol,
                        timeframe=self.timeframe,
                        limit=100  # Fetch last 100 candles
                    )
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(
                        ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"]
                    )
                    
                    # Convert timestamp to datetime
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    
                    # Update data
                    self.data = df
                    
                    logger.info(f"Successfully updated market data on retry {i+1}")
                    break
                
                except Exception as retry_error:
                    logger.error(f"Error retrying market data update: {retry_error}")
    
    def _check_signals(self) -> None:
        """
        Check for trading signals and execute trades.
        """
        if self.data.empty:
            return
        
        # Get the latest row
        latest = self.data.iloc[-1]
        
        # Get current position from strategy
        position_type, confidence = self.strategy.get_current_position(self.data)
        
        # Current market price
        current_price = latest["close"]
        
        # Check for position entry/exit
        if position_type == "long" and self.current_position <= 0:
            # Enter long position
            self._enter_long_position(current_price)
        
        elif position_type == "short" and self.current_position >= 0:
            # Enter short position
            self._enter_short_position(current_price)
        
        elif position_type == "flat" and self.current_position != 0:
            # Exit current position
            self._exit_position(current_price, "signal")
        
        # Check for stop loss and take profit if in position
        if self.current_position == 1:  # Long position
            # Check for stop loss
            if current_price <= self.stop_loss:
                self._exit_position(self.stop_loss, "stop_loss")
            
            # Check for take profit
            elif current_price >= self.take_profit:
                self._exit_position(self.take_profit, "take_profit")
            
            # Check for trailing stop if enabled
            elif self.risk_params["trailing_stop"] and current_price > self.entry_price * (1 + self.risk_params["trailing_stop_activation"]):
                # Calculate new stop loss based on trailing distance
                new_stop_loss = current_price * (1 - self.risk_params["trailing_stop_distance"])
                
                # Update stop loss if new one is higher
                if new_stop_loss > self.stop_loss:
                    logger.info(f"Updating trailing stop from {self.stop_loss} to {new_stop_loss}")
                    self.stop_loss = new_stop_loss
        
        elif self.current_position == -1:  # Short position
            # Check for stop loss
            if current_price >= self.stop_loss:
                self._exit_position(self.stop_loss, "stop_loss")
            
            # Check for take profit
            elif current_price <= self.take_profit:
                self._exit_position(self.take_profit, "take_profit")
            
            # Check for trailing stop if enabled
            elif self.risk_params["trailing_stop"] and current_price < self.entry_price * (1 - self.risk_params["trailing_stop_activation"]):
                # Calculate new stop loss based on trailing distance
                new_stop_loss = current_price * (1 + self.risk_params["trailing_stop_distance"])
                
                # Update stop loss if new one is lower
                if new_stop_loss < self.stop_loss:
                    logger.info(f"Updating trailing stop from {self.stop_loss} to {new_stop_loss}")
                    self.stop_loss = new_stop_loss
    
    def _enter_long_position(self, price: float) -> None:
        """
        Enter a long position.
        
        Args:
            price: Entry price
        """
        # Calculate position size based on risk management
        account_balance = self.exchange.get_balance()
        max_position_size = account_balance * self.risk_params["max_position_size"]
        
        # Calculate stop loss
        stop_loss = self.strategy.calculate_stop_loss(self.data, "long", price)
        
        # Calculate take profit
        take_profit = self.strategy.calculate_take_profit(
            price, stop_loss, self.risk_params.get("risk_reward_ratio", 2.0)
        )
        
        # Calculate position size based on risk per trade
        risk_amount = account_balance * self.risk_params.get("risk_per_trade", 0.01)
        risk_per_unit = (price - stop_loss) / price
        position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Limit position size to max allowed
        position_size = min(position_size, max_position_size)
        
        # Execute trade
        try:
            # Create market buy order
            order = self.exchange.create_market_buy_order(
                symbol=self.symbol,
                amount=position_size / price
            )
            
            # Update position state
            self.current_position = 1
            self.entry_price = price
            self.stop_loss = stop_loss
            self.take_profit = take_profit
            self.position_size = position_size
            
            logger.info(f"Entered long position at {price}")
            logger.info(f"Stop loss: {stop_loss}, Take profit: {take_profit}")
            logger.info(f"Position size: {position_size}")
            
            # Send notification
            if self.notifications_enabled:
                self.notification_manager.send_notification(
                    f"Entered long position for {self.symbol}",
                    f"Entry price: {price}\nStop loss: {stop_loss}\nTake profit: {take_profit}\nPosition size: {position_size}"
                )
        
        except Exception as e:
            logger.error(f"Error entering long position: {e}")
            
            # Send notification
            if self.notifications_enabled:
                self.notification_manager.send_notification(
                    f"Error entering long position for {self.symbol}",
                    f"Error: {e}"
                )
    
    def _enter_short_position(self, price: float) -> None:
        """
        Enter a short position.
        
        Args:
            price: Entry price
        """
        # Calculate position size based on risk management
        account_balance = self.exchange.get_balance()
        max_position_size = account_balance * self.risk_params["max_position_size"]
        
        # Calculate stop loss
        stop_loss = self.strategy.calculate_stop_loss(self.data, "short", price)
        
        # Calculate take profit
        take_profit = self.strategy.calculate_take_profit(
            price, stop_loss, self.risk_params.get("risk_reward_ratio", 2.0)
        )
        
        # Calculate position size based on risk per trade
        risk_amount = account_balance * self.risk_params.get("risk_per_trade", 0.01)
        risk_per_unit = (stop_loss - price) / price
        position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Limit position size to max allowed
        position_size = min(position_size, max_position_size)
        
        # Execute trade
        try:
            # Create market sell order
            order = self.exchange.create_market_sell_order(
                symbol=self.symbol,
                amount=position_size / price
            )
            
            # Update position state
            self.current_position = -1
            self.entry_price = price
            self.stop_loss = stop_loss
            self.take_profit = take_profit
            self.position_size = position_size
            
            logger.info(f"Entered short position at {price}")
            logger.info(f"Stop loss: {stop_loss}, Take profit: {take_profit}")
            logger.info(f"Position size: {position_size}")
            
            # Send notification
            if self.notifications_enabled:
                self.notification_manager.send_notification(
                    f"Entered short position for {self.symbol}",
                    f"Entry price: {price}\nStop loss: {stop_loss}\nTake profit: {take_profit}\nPosition size: {position_size}"
                )
        
        except Exception as e:
            logger.error(f"Error entering short position: {e}")
            
            # Send notification
            if self.notifications_enabled:
                self.notification_manager.send_notification(
                    f"Error entering short position for {self.symbol}",
                    f"Error: {e}"
                )
    
    def _exit_position(self, price: float, reason: str) -> None:
        """
        Exit the current position.
        
        Args:
            price: Exit price
            reason: Reason for exiting (signal, stop_loss, take_profit)
        """
        if self.current_position == 0:
            return
        
        try:
            # Create market order to exit position
            if self.current_position == 1:  # Long position
                order = self.exchange.create_market_sell_order(
                    symbol=self.symbol,
                    amount=self.position_size / self.entry_price
                )
                
                # Calculate profit/loss
                pnl = (price - self.entry_price) / self.entry_price * self.position_size
                pnl_percent = (price - self.entry_price) / self.entry_price * 100
                
                logger.info(f"Exited long position at {price} ({reason})")
                logger.info(f"P&L: {pnl:.2f} ({pnl_percent:.2f}%)")
                
                # Send notification
                if self.notifications_enabled:
                    self.notification_manager.send_notification(
                        f"Exited long position for {self.symbol}",
                        f"Exit price: {price}\nReason: {reason}\nP&L: {pnl:.2f} ({pnl_percent:.2f}%)"
                    )
            
            elif self.current_position == -1:  # Short position
                order = self.exchange.create_market_buy_order(
                    symbol=self.symbol,
                    amount=self.position_size / self.entry_price
                )
                
                # Calculate profit/loss
                pnl = (self.entry_price - price) / self.entry_price * self.position_size
                pnl_percent = (self.entry_price - price) / self.entry_price * 100
                
                logger.info(f"Exited short position at {price} ({reason})")
                logger.info(f"P&L: {pnl:.2f} ({pnl_percent:.2f}%)")
                
                # Send notification
                if self.notifications_enabled:
                    self.notification_manager.send_notification(
                        f"Exited short position for {self.symbol}",
                        f"Exit price: {price}\nReason: {reason}\nP&L: {pnl:.2f} ({pnl_percent:.2f}%)"
                    )
            
            # Reset position state
            self.current_position = 0
            self.entry_price = 0
            self.stop_loss = 0
            self.take_profit = 0
            self.position_size = 0
        
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
            
            # Send notification
            if self.notifications_enabled:
                self.notification_manager.send_notification(
                    f"Error exiting position for {self.symbol}",
                    f"Error: {e}"
                )
    
    def _update_dashboard(self) -> None:
        """
        Update the console dashboard with current trading status.
        """
        # Get current time
        now = datetime.now()
        
        # Get current price
        current_price = self.data.iloc[-1]["close"] if not self.data.empty else 0
        
        # Get account balance
        account_balance = self.exchange.get_balance()
        
        # Calculate unrealized P&L if in position
        unrealized_pnl = 0
        unrealized_pnl_percent = 0
        
        if self.current_position == 1:  # Long position
            unrealized_pnl = (current_price - self.entry_price) / self.entry_price * self.position_size
            unrealized_pnl_percent = (current_price - self.entry_price) / self.entry_price * 100
        
        elif self.current_position == -1:  # Short position
            unrealized_pnl = (self.entry_price - current_price) / self.entry_price * self.position_size
            unrealized_pnl_percent = (self.entry_price - current_price) / self.entry_price * 100
        
        # Clear console
        print("\033c", end="")
        
        # Print dashboard header
        print("="*80)
        print(f"Trading Bot Dashboard - {self.symbol} - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Print general information
        print(f"Mode: {'Live' if self.is_live else 'Paper'} Trading")
        print(f"Strategy: {self.strategy.name}")
        print(f"Timeframe: {self.timeframe}")
        print(f"Current Price: {current_price}")
        print(f"Account Balance: {account_balance:.2f}")
        print("-"*80)
        
        # Print position information
        if self.current_position == 0:
            print("Position: None")
        elif self.current_position == 1:
            print("Position: Long")
            print(f"Entry Price: {self.entry_price}")
            print(f"Stop Loss: {self.stop_loss}")
            print(f"Take Profit: {self.take_profit}")
            print(f"Position Size: {self.position_size}")
            print(f"Unrealized P&L: {unrealized_pnl:.2f} ({unrealized_pnl_percent:.2f}%)")
        elif self.current_position == -1:
            print("Position: Short")
            print(f"Entry Price: {self.entry_price}")
            print(f"Stop Loss: {self.stop_loss}")
            print(f"Take Profit: {self.take_profit}")
            print(f"Position Size: {self.position_size}")
            print(f"Unrealized P&L: {unrealized_pnl:.2f} ({unrealized_pnl_percent:.2f}%)")
        
        print("-"*80)
        
        # Print recent signals
        print("Recent Signals:")
        if not self.data.empty and "buy_signal" in self.data.columns and "sell_signal" in self.data.columns:
            recent_data = self.data.tail(5)
            for i, row in recent_data.iterrows():
                signal = "BUY" if row["buy_signal"] else "SELL" if row["sell_signal"] else "NONE"
                print(f"{i}: {signal} - Open: {row['open']}, High: {row['high']}, Low: {row['low']}, Close: {row['close']}")
        
        print("="*80)
    
    def _sleep_until_next_candle(self, current_time: datetime) -> None:
        """
        Sleep until the next candle.
        
        Args:
            current_time: Current time
        """
        # Calculate time until next candle based on timeframe
        if self.timeframe == "1m":
            next_minute = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
            sleep_seconds = (next_minute - current_time).total_seconds()
        elif self.timeframe == "5m":
            current_minute = current_time.minute
            next_5min = current_time.replace(minute=(current_minute // 5 + 1) * 5 % 60, second=0, microsecond=0)
            if next_5min.minute < current_minute:
                next_5min = next_5min + timedelta(hours=1)
            sleep_seconds = (next_5min - current_time).total_seconds()
        elif self.timeframe == "15m":
            current_minute = current_time.minute
            next_15min = current_time.replace(minute=(current_minute // 15 + 1) * 15 % 60, second=0, microsecond=0)
            if next_15min.minute < current_minute:
                next_15min = next_15min + timedelta(hours=1)
            sleep_seconds = (next_15min - current_time).total_seconds()
        elif self.timeframe == "30m":
            current_minute = current_time.minute
            next_30min = current_time.replace(minute=(current_minute // 30 + 1) * 30 % 60, second=0, microsecond=0)
            if next_30min.minute < current_minute:
                next_30min = next_30min + timedelta(hours=1)
            sleep_seconds = (next_30min - current_time).total_seconds()
        elif self.timeframe == "1h":
            next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            sleep_seconds = (next_hour - current_time).total_seconds()
        elif self.timeframe == "4h":
            current_hour = current_time.hour
            next_4hour = current_time.replace(hour=(current_hour // 4 + 1) * 4 % 24, minute=0, second=0, microsecond=0)
            if next_4hour.hour < current_hour:
                next_4hour = next_4hour + timedelta(days=1)
            sleep_seconds = (next_4hour - current_time).total_seconds()
        elif self.timeframe == "1d":
            next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            sleep_seconds = (next_day - current_time).total_seconds()
        else:
            # Default to 1 minute if timeframe is not recognized
            sleep_seconds = 60
        
        # Add a small buffer to ensure we're past the candle close
        sleep_seconds += 1
        
        # Sleep until next candle
        logger.debug(f"Sleeping for {sleep_seconds:.2f} seconds until next candle")
        time.sleep(sleep_seconds)
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EMA Crossover Strategy

Implements a trading strategy based on the crossover of two Exponential Moving Averages (EMA).
Buy signal: Fast EMA crosses above Slow EMA
Sell signal: Fast EMA crosses below Slow EMA
"""

from typing import Dict

import numpy as np
import pandas as pd
from loguru import logger
from ta.trend import EMAIndicator

from src.strategies.base_strategy import BaseStrategy


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy implementation.
    
    This strategy generates buy signals when the fast EMA crosses above the slow EMA,
    and sell signals when the fast EMA crosses below the slow EMA.
    """
    
    def __init__(self, params: Dict, timeframe: str):
        """
        Initialize the EMA Crossover strategy.
        
        Args:
            params: Strategy parameters including fast_ema and slow_ema periods
            timeframe: Trading timeframe
        """
        super().__init__("EMA_Crossover", params, timeframe)
        
        # Extract parameters with defaults
        self.fast_ema_period = params.get("fast_ema", 9)
        self.slow_ema_period = params.get("slow_ema", 21)
        
        # Validate parameters
        if self.fast_ema_period >= self.slow_ema_period:
            logger.warning("Fast EMA period should be less than slow EMA period")
        
        logger.info(f"EMA Crossover strategy initialized with fast EMA: {self.fast_ema_period}, "
                   f"slow EMA: {self.slow_ema_period}")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the fast and slow EMAs.
        
        Args:
            data: OHLCV price data
            
        Returns:
            DataFrame with added EMA columns
        """
        # Make a copy to avoid modifying the original dataframe
        df = data.copy()
        
        # Calculate fast EMA
        fast_ema = EMAIndicator(close=df["close"], window=self.fast_ema_period)
        df["fast_ema"] = fast_ema.ema_indicator()
        
        # Calculate slow EMA
        slow_ema = EMAIndicator(close=df["close"], window=self.slow_ema_period)
        df["slow_ema"] = slow_ema.ema_indicator()
        
        # Calculate EMA difference
        df["ema_diff"] = df["fast_ema"] - df["slow_ema"]
        
        return df
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals based on EMA crossovers.
        
        Buy signal: Fast EMA crosses above Slow EMA
        Sell signal: Fast EMA crosses below Slow EMA
        
        Args:
            data: OHLCV price data with EMA indicators
            
        Returns:
            DataFrame with added signal columns
        """
        # Make a copy to avoid modifying the original dataframe
        df = data.copy()
        
        # Initialize signal columns
        df["buy_signal"] = False
        df["sell_signal"] = False
        
        # Previous EMA difference (shifted by 1)
        df["prev_ema_diff"] = df["ema_diff"].shift(1)
        
        # Buy signal: EMA diff crosses from negative to positive
        df.loc[(df["prev_ema_diff"] < 0) & (df["ema_diff"] > 0), "buy_signal"] = True
        
        # Sell signal: EMA diff crosses from positive to negative
        df.loc[(df["prev_ema_diff"] > 0) & (df["ema_diff"] < 0), "sell_signal"] = True
        
        # Drop NaN values (first rows where indicators couldn't be calculated)
        df = df.dropna()
        
        return df
    
    def calculate_stop_loss(self, data: pd.DataFrame, position: str, entry_price: float) -> float:
        """
        Calculate the stop loss price based on recent volatility.
        
        Args:
            data: OHLCV price data
            position: 'long' or 'short'
            entry_price: Entry price for the trade
            
        Returns:
            Stop loss price
        """
        # Calculate Average True Range (ATR) for volatility-based stop loss
        # Use the last 14 periods for ATR calculation
        high = data["high"].tail(14)
        low = data["low"].tail(14)
        close = data["close"].tail(14).shift(1)
        
        # True Range calculation
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.mean()
        
        # Set stop loss at 2 ATR from entry price
        if position == "long":
            stop_loss = entry_price - (2 * atr)
        else:  # short position
            stop_loss = entry_price + (2 * atr)
        
        return stop_loss
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float, risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate the take profit price based on risk-reward ratio.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            risk_reward_ratio: Desired risk-reward ratio (default: 2.0)
            
        Returns:
            Take profit price
        """
        # Calculate risk (distance from entry to stop loss)
        risk = abs(entry_price - stop_loss)
        
        # Calculate reward (distance from entry to take profit)
        reward = risk * risk_reward_ratio
        
        # Calculate take profit price
        if entry_price > stop_loss:  # Long position
            take_profit = entry_price + reward
        else:  # Short position
            take_profit = entry_price - reward
        
        return take_profit
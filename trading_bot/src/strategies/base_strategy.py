#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base Strategy Class

This module defines the base class for all trading strategies.
All concrete strategy implementations should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from loguru import logger


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    
    This abstract class defines the interface that all strategy implementations
    must follow. It provides common functionality and requires subclasses to
    implement strategy-specific methods.
    """
    
    def __init__(self, name: str, params: Dict, timeframe: str):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
            params: Strategy parameters
            timeframe: Trading timeframe (e.g., '1m', '5m', '1h', '1d')
        """
        self.name = name
        self.params = params
        self.timeframe = timeframe
        self.indicators = {}
        logger.info(f"Initialized {name} strategy with timeframe {timeframe}")
        logger.debug(f"Strategy parameters: {params}")
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators required by the strategy.
        
        Args:
            data: OHLCV price data
            
        Returns:
            DataFrame with added indicator columns
        """
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals based on the calculated indicators.
        
        Args:
            data: OHLCV price data with indicators
            
        Returns:
            DataFrame with added signal columns (buy_signal, sell_signal)
        """
        pass
    
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze price data and generate trading signals.
        
        This method combines indicator calculation and signal generation.
        
        Args:
            data: OHLCV price data
            
        Returns:
            DataFrame with added indicator and signal columns
        """
        # Ensure we have the required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Calculate indicators
        data_with_indicators = self.calculate_indicators(data)
        
        # Generate signals
        data_with_signals = self.generate_signals(data_with_indicators)
        
        return data_with_signals
    
    def get_position_size(self, account_balance: float, risk_per_trade: float, 
                         entry_price: float, stop_loss_price: float) -> float:
        """
        Calculate the position size based on risk management parameters.
        
        Args:
            account_balance: Current account balance
            risk_per_trade: Percentage of account to risk per trade (0-1)
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price for the trade
            
        Returns:
            Position size in base currency
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            logger.warning("Invalid entry or stop loss price")
            return 0
        
        # Calculate risk amount in account currency
        risk_amount = account_balance * risk_per_trade
        
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss_price)
        
        if risk_per_unit == 0:
            logger.warning("Risk per unit is zero, cannot calculate position size")
            return 0
        
        # Calculate position size
        position_size = risk_amount / risk_per_unit
        
        return position_size
    
    def get_current_position(self, data: pd.DataFrame) -> Tuple[str, float]:
        """
        Determine the current position based on the latest signals.
        
        Args:
            data: DataFrame with signal columns
            
        Returns:
            Tuple of (position_type, confidence)
            position_type is one of: 'long', 'short', 'flat'
            confidence is a value between 0 and 1
        """
        if data.empty:
            return 'flat', 0.0
        
        # Get the latest row
        latest = data.iloc[-1]
        
        # Check for buy signal
        if 'buy_signal' in latest and latest['buy_signal']:
            return 'long', 1.0
        
        # Check for sell signal
        if 'sell_signal' in latest and latest['sell_signal']:
            return 'short', 1.0
        
        # Default to flat position
        return 'flat', 0.0
    
    def __str__(self) -> str:
        """
        String representation of the strategy.
        
        Returns:
            Strategy description string
        """
        return f"{self.name} Strategy (timeframe: {self.timeframe})"
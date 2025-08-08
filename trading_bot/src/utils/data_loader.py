#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data Loader

This module provides functionality for loading historical price data
from various sources (CSV files, APIs, etc.).
"""

import os
from datetime import datetime
from typing import Optional, Union

import ccxt
import pandas as pd
from loguru import logger


class DataLoader:
    """
    Data loader for fetching historical price data.
    
    This class provides methods to load historical OHLCV (Open, High, Low, Close, Volume)
    price data from various sources, including local CSV files and exchange APIs.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the data loader.
        
        Args:
            data_dir: Directory for storing/loading data files
        """
        self.data_dir = data_dir
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
    
    def load_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        source: str = "csv"
    ) -> pd.DataFrame:
        """
        Load historical OHLCV data.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '1h', '1d')
            start_date: Start date for historical data
            end_date: End date for historical data
            source: Data source ('csv', 'binance', 'alpaca', etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        if source == "csv":
            return self._load_from_csv(symbol, timeframe, start_date, end_date)
        elif source == "binance":
            return self._load_from_binance(symbol, timeframe, start_date, end_date)
        elif source == "alpaca":
            return self._load_from_alpaca(symbol, timeframe, start_date, end_date)
        else:
            raise ValueError(f"Unsupported data source: {source}")
    
    def _load_from_csv(self, symbol: str, timeframe: str, start_date: Union[str, datetime], 
                      end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Load historical data from a CSV file.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data
        """
        # Convert symbol to filename-friendly format
        filename = symbol.replace("/", "_").replace("-", "_").lower()
        filepath = os.path.join(self.data_dir, f"{filename}_{timeframe}.csv")
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.warning(f"CSV file not found: {filepath}")
            return pd.DataFrame()
        
        # Load data from CSV
        try:
            df = pd.read_csv(filepath)
            
            # Convert timestamp to datetime if it's not already
            if "timestamp" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            # Set timestamp as index if it exists
            if "timestamp" in df.columns:
                df.set_index("timestamp", inplace=True)
            
            # Filter by date range
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Ensure all required columns exist
            required_columns = ["open", "high", "low", "close", "volume"]
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"Required column '{col}' not found in CSV file")
                    return pd.DataFrame()
            
            return df
        
        except Exception as e:
            logger.error(f"Error loading data from CSV: {e}")
            return pd.DataFrame()
    
    def _load_from_binance(self, symbol: str, timeframe: str, start_date: Union[str, datetime], 
                          end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Load historical data from Binance API.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert dates to timestamps
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # Initialize Binance client
            exchange = ccxt.binance({
                'enableRateLimit': True,
            })
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=start_timestamp,
                limit=1000  # Maximum limit per request
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            
            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Save to CSV for future use
            filename = symbol.replace("/", "_").replace("-", "_").lower()
            filepath = os.path.join(self.data_dir, f"{filename}_{timeframe}.csv")
            df.to_csv(filepath)
            
            logger.info(f"Loaded {len(df)} data points from Binance and saved to {filepath}")
            
            return df
        
        except Exception as e:
            logger.error(f"Error loading data from Binance: {e}")
            return pd.DataFrame()
    
    def _load_from_alpaca(self, symbol: str, timeframe: str, start_date: Union[str, datetime], 
                         end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Load historical data from Alpaca API.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # This is a placeholder for Alpaca API integration
            # In a real implementation, you would use the Alpaca API client
            # to fetch historical data
            
            logger.warning("Alpaca API integration not implemented yet")
            return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error loading data from Alpaca: {e}")
            return pd.DataFrame()
    
    def download_and_save_data(self, symbol: str, timeframe: str, start_date: Union[str, datetime], 
                              end_date: Union[str, datetime], source: str = "binance") -> bool:
        """
        Download historical data and save to CSV.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            source: Data source
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if source == "binance":
                df = self._load_from_binance(symbol, timeframe, start_date, end_date)
            elif source == "alpaca":
                df = self._load_from_alpaca(symbol, timeframe, start_date, end_date)
            else:
                logger.error(f"Unsupported data source for downloading: {source}")
                return False
            
            if df.empty:
                logger.error("No data downloaded")
                return False
            
            # Save to CSV
            filename = symbol.replace("/", "_").replace("-", "_").lower()
            filepath = os.path.join(self.data_dir, f"{filename}_{timeframe}.csv")
            df.to_csv(filepath)
            
            logger.info(f"Downloaded and saved {len(df)} data points to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            return False
    
    def generate_sample_data(self, symbol: str, timeframe: str, start_date: str, 
                           end_date: str, save: bool = True) -> pd.DataFrame:
        """
        Generate sample OHLCV data for testing purposes.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            save: Whether to save the generated data to CSV
            
        Returns:
            DataFrame with generated OHLCV data
        """
        # Convert dates to datetime
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Generate date range based on timeframe
        if timeframe == "1d":
            dates = pd.date_range(start=start, end=end, freq="D")
        elif timeframe == "1h":
            dates = pd.date_range(start=start, end=end, freq="H")
        elif timeframe == "15m":
            dates = pd.date_range(start=start, end=end, freq="15min")
        elif timeframe == "5m":
            dates = pd.date_range(start=start, end=end, freq="5min")
        elif timeframe == "1m":
            dates = pd.date_range(start=start, end=end, freq="1min")
        else:
            logger.error(f"Unsupported timeframe for sample data: {timeframe}")
            return pd.DataFrame()
        
        # Generate random price data
        import numpy as np
        
        # Start with a base price
        base_price = 100.0
        
        # Generate random price movements
        np.random.seed(42)  # For reproducibility
        price_changes = np.random.normal(0, 1, len(dates)) * 0.01
        
        # Calculate prices
        closes = [base_price]
        for change in price_changes[:-1]:
            closes.append(closes[-1] * (1 + change))
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(dates):
            close = closes[i]
            # Generate random high, low, open around close
            high = close * (1 + abs(np.random.normal(0, 1)) * 0.005)
            low = close * (1 - abs(np.random.normal(0, 1)) * 0.005)
            open_price = close * (1 + np.random.normal(0, 1) * 0.003)
            # Ensure high >= open, close >= low
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            # Generate random volume
            volume = abs(np.random.normal(0, 1)) * 1000 + 500
            
            data.append([date, open_price, high, low, close, volume])
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df.set_index("timestamp", inplace=True)
        
        # Save to CSV if requested
        if save:
            filename = symbol.replace("/", "_").replace("-", "_").lower()
            filepath = os.path.join(self.data_dir, f"{filename}_{timeframe}.csv")
            df.to_csv(filepath)
            logger.info(f"Generated and saved sample data to {filepath}")
        
        return df
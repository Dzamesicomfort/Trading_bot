#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Strategy Factory

This module provides a factory for creating strategy instances based on strategy name.
"""

from typing import Dict, Type

from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.strategies.ema_crossover import EMACrossoverStrategy


class StrategyFactory:
    """
    Factory class for creating strategy instances.
    
    This class maintains a registry of available strategies and provides
    methods to create strategy instances based on strategy name.
    """
    
    def __init__(self):
        """
        Initialize the strategy factory with a registry of available strategies.
        """
        self.strategies = {
            "EMA_Crossover": EMACrossoverStrategy,
            # Add more strategies here as they are implemented
            # "RSI": RSIStrategy,
            # "MACD": MACDStrategy,
            # "BollingerBands": BollingerBandsStrategy,
        }
    
    def get_available_strategies(self) -> list:
        """
        Get a list of available strategy names.
        
        Returns:
            List of strategy names
        """
        return list(self.strategies.keys())
    
    def create_strategy(self, strategy_name: str, params: Dict, timeframe: str) -> BaseStrategy:
        """
        Create a strategy instance based on strategy name.
        
        Args:
            strategy_name: Name of the strategy to create
            params: Strategy parameters
            timeframe: Trading timeframe
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy_name is not recognized
        """
        if strategy_name not in self.strategies:
            available = ", ".join(self.get_available_strategies())
            raise ValueError(
                f"Unknown strategy: {strategy_name}. Available strategies: {available}"
            )
        
        strategy_class = self.strategies[strategy_name]
        logger.info(f"Creating {strategy_name} strategy")
        
        return strategy_class(params, timeframe)
    
    def register_strategy(self, strategy_name: str, strategy_class: Type[BaseStrategy]) -> None:
        """
        Register a new strategy class.
        
        Args:
            strategy_name: Name to register the strategy under
            strategy_class: Strategy class to register
            
        Raises:
            ValueError: If strategy_name is already registered
        """
        if strategy_name in self.strategies:
            raise ValueError(f"Strategy {strategy_name} is already registered")
        
        self.strategies[strategy_name] = strategy_class
        logger.info(f"Registered new strategy: {strategy_name}")
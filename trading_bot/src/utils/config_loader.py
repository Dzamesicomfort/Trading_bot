#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Loader

This module provides functionality for loading and validating configuration files.
"""

import os
from typing import Dict, Any

import yaml
from loguru import logger


class ConfigLoader:
    """
    Configuration loader for the trading bot.
    
    This class provides methods to load and validate configuration files
    in YAML format.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
    
    def load(self) -> Dict[str, Any]:
        """
        Load the configuration file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file is invalid
        """
        # Check if the configuration file exists
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        # Load the configuration file
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Validate the configuration
            self._validate_config(config)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate the configuration.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for required sections
        required_sections = ["general", "trading", "strategy", "risk_management", "exchange"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate general section
        if "mode" not in config["general"]:
            raise ValueError("Missing 'mode' in general configuration")
        
        if config["general"]["mode"] not in ["backtest", "paper", "live"]:
            raise ValueError(f"Invalid mode: {config['general']['mode']}")
        
        # Validate trading section
        if "symbol" not in config["trading"]:
            raise ValueError("Missing 'symbol' in trading configuration")
        
        if "timeframe" not in config["trading"]:
            raise ValueError("Missing 'timeframe' in trading configuration")
        
        # Validate strategy section
        if "name" not in config["strategy"]:
            raise ValueError("Missing 'name' in strategy configuration")
        
        if "params" not in config["strategy"]:
            raise ValueError("Missing 'params' in strategy configuration")
        
        # Validate risk management section
        if "max_position_size" not in config["risk_management"]:
            raise ValueError("Missing 'max_position_size' in risk management configuration")
        
        # Validate exchange section
        if "name" not in config["exchange"]:
            raise ValueError("Missing 'name' in exchange configuration")
        
        # Validate backtest section if in backtest mode
        if config["general"]["mode"] == "backtest":
            if "backtest" not in config:
                raise ValueError("Missing 'backtest' section for backtest mode")
            
            if "start_date" not in config["backtest"]:
                raise ValueError("Missing 'start_date' in backtest configuration")
            
            if "end_date" not in config["backtest"]:
                raise ValueError("Missing 'end_date' in backtest configuration")
            
            if "initial_balance" not in config["backtest"]:
                raise ValueError("Missing 'initial_balance' in backtest configuration")
    
    def save(self, config: Dict[str, Any], config_path: str = None) -> None:
        """
        Save the configuration to a file.
        
        Args:
            config: Configuration dictionary
            config_path: Path to save the configuration file (defaults to self.config_path)
            
        Raises:
            IOError: If the configuration file can't be written
        """
        if config_path is None:
            config_path = self.config_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Save the configuration
        try:
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Saved configuration to {config_path}")
        
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
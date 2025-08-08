#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Performance Metrics

This module provides functions for calculating trading performance metrics
such as Sharpe ratio, drawdown, win rate, etc.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union


def calculate_metrics(results: Dict) -> Dict:
    """
    Calculate performance metrics from backtest results.
    
    Args:
        results: Dictionary containing trades and equity curve
        
    Returns:
        Dictionary of performance metrics
    """
    trades = results["trades"]
    equity_curve = results["equity_curve"]
    
    # Initialize metrics dictionary
    metrics = {}
    
    # Return empty metrics if no trades or equity data
    if trades.empty or equity_curve.empty:
        return metrics
    
    # Basic metrics
    initial_equity = equity_curve.iloc[0]["equity"]
    final_equity = equity_curve.iloc[-1]["equity"]
    
    # Total return
    total_return = ((final_equity / initial_equity) - 1) * 100
    metrics["total_return"] = total_return
    
    # Annualized return
    days = (equity_curve.iloc[-1]["timestamp"] - equity_curve.iloc[0]["timestamp"]).days
    if days > 0:
        annualized_return = ((1 + total_return / 100) ** (365 / days) - 1) * 100
        metrics["annualized_return"] = annualized_return
    else:
        metrics["annualized_return"] = 0
    
    # Maximum drawdown
    max_drawdown = equity_curve["drawdown"].max() * 100
    metrics["max_drawdown"] = max_drawdown
    
    # Sharpe ratio (assuming risk-free rate of 0%)
    if len(equity_curve) > 1:
        # Calculate daily returns
        equity_curve["daily_return"] = equity_curve["equity"].pct_change()
        
        # Annualized Sharpe ratio
        daily_returns = equity_curve["daily_return"].dropna()
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
            metrics["sharpe_ratio"] = sharpe_ratio
        else:
            metrics["sharpe_ratio"] = 0
    else:
        metrics["sharpe_ratio"] = 0
    
    # Trade metrics
    if not trades.empty:
        # Total trades
        total_trades = len(trades)
        metrics["total_trades"] = total_trades
        
        # Winning trades
        winning_trades = len(trades[trades["pnl"] > 0])
        metrics["winning_trades"] = winning_trades
        
        # Losing trades
        losing_trades = len(trades[trades["pnl"] <= 0])
        metrics["losing_trades"] = losing_trades
        
        # Win rate
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        metrics["win_rate"] = win_rate
        
        # Average win
        avg_win = trades[trades["pnl"] > 0]["pnl"].mean() if winning_trades > 0 else 0
        metrics["avg_win"] = avg_win
        
        # Average loss
        avg_loss = trades[trades["pnl"] <= 0]["pnl"].mean() if losing_trades > 0 else 0
        metrics["avg_loss"] = avg_loss
        
        # Average trade
        avg_trade = trades["pnl"].mean()
        metrics["avg_trade"] = avg_trade
        
        # Profit factor
        gross_profit = trades[trades["pnl"] > 0]["pnl"].sum() if winning_trades > 0 else 0
        gross_loss = abs(trades[trades["pnl"] <= 0]["pnl"].sum()) if losing_trades > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        metrics["profit_factor"] = profit_factor
        
        # Maximum consecutive wins
        trades["win"] = trades["pnl"] > 0
        trades["streak"] = (trades["win"] != trades["win"].shift(1)).cumsum()
        win_streaks = trades[trades["win"]].groupby("streak").size()
        max_consecutive_wins = win_streaks.max() if not win_streaks.empty else 0
        metrics["max_consecutive_wins"] = max_consecutive_wins
        
        # Maximum consecutive losses
        loss_streaks = trades[~trades["win"]].groupby("streak").size()
        max_consecutive_losses = loss_streaks.max() if not loss_streaks.empty else 0
        metrics["max_consecutive_losses"] = max_consecutive_losses
        
        # Average holding time
        trades["holding_time"] = (trades["exit_time"] - trades["entry_time"]).dt.total_seconds() / 3600  # in hours
        avg_holding_time = trades["holding_time"].mean()
        metrics["avg_holding_time"] = avg_holding_time
    
    # Return on Maximum Drawdown (RoMaD)
    if max_drawdown > 0:
        romad = total_return / max_drawdown
        metrics["romad"] = romad
    else:
        metrics["romad"] = float('inf')
    
    # Calmar ratio (annualized return / maximum drawdown)
    if max_drawdown > 0:
        calmar_ratio = annualized_return / max_drawdown
        metrics["calmar_ratio"] = calmar_ratio
    else:
        metrics["calmar_ratio"] = float('inf')
    
    return metrics


def calculate_drawdown(equity_curve: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate drawdown from equity curve.
    
    Args:
        equity_curve: DataFrame with equity values
        
    Returns:
        DataFrame with drawdown values
    """
    # Make a copy to avoid modifying the original dataframe
    df = equity_curve.copy()
    
    # Calculate running maximum
    df["running_max"] = df["equity"].cummax()
    
    # Calculate drawdown
    df["drawdown"] = (df["running_max"] - df["equity"]) / df["running_max"]
    
    return df


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """
    Calculate Sharpe ratio.
    
    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annualized)
        periods_per_year: Number of periods in a year (252 for daily, 12 for monthly, etc.)
        
    Returns:
        Sharpe ratio
    """
    # Convert risk-free rate to per-period rate
    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    
    # Calculate excess returns
    excess_returns = returns - rf_per_period
    
    # Calculate Sharpe ratio
    if excess_returns.std() > 0:
        sharpe = np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std()
    else:
        sharpe = 0
    
    return sharpe


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """
    Calculate Sortino ratio (similar to Sharpe but only considers downside risk).
    
    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annualized)
        periods_per_year: Number of periods in a year
        
    Returns:
        Sortino ratio
    """
    # Convert risk-free rate to per-period rate
    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    
    # Calculate excess returns
    excess_returns = returns - rf_per_period
    
    # Calculate downside deviation (only negative returns)
    downside_returns = excess_returns[excess_returns < 0]
    downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0
    
    # Calculate Sortino ratio
    if downside_deviation > 0:
        sortino = np.sqrt(periods_per_year) * excess_returns.mean() / downside_deviation
    else:
        sortino = float('inf') if excess_returns.mean() > 0 else 0
    
    return sortino


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        equity_curve: Series of equity values
        
    Returns:
        Maximum drawdown as a percentage
    """
    # Calculate running maximum
    running_max = equity_curve.cummax()
    
    # Calculate drawdown
    drawdown = (running_max - equity_curve) / running_max
    
    # Get maximum drawdown
    max_drawdown = drawdown.max()
    
    return max_drawdown * 100  # Convert to percentage
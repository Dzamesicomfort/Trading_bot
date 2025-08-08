#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Notification Manager

This module provides notification functionality for the trading bot,
including Telegram and email notifications.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

import requests
from loguru import logger


class NotificationManager:
    """
    Manages notifications for the trading bot.
    
    Supports Telegram and email notifications for trading events,
    errors, and other important information.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the notification manager.
        
        Args:
            config: Notification configuration dictionary
        """
        self.config = config
        
        # Telegram configuration
        self.telegram_enabled = config.get("telegram", {}).get("enabled", False)
        self.telegram_bot_token = config.get("telegram", {}).get("bot_token", "")
        self.telegram_chat_id = config.get("telegram", {}).get("chat_id", "")
        
        # Email configuration
        self.email_enabled = config.get("email", {}).get("enabled", False)
        self.smtp_server = config.get("email", {}).get("smtp_server", "")
        self.smtp_port = config.get("email", {}).get("smtp_port", 587)
        self.email_username = config.get("email", {}).get("username", "")
        self.email_password = config.get("email", {}).get("password", "")
        self.email_from = config.get("email", {}).get("from_email", "")
        self.email_to = config.get("email", {}).get("to_email", "")
        
        logger.info(f"Notification manager initialized - Telegram: {self.telegram_enabled}, Email: {self.email_enabled}")
    
    def send_notification(self, title: str, message: str, priority: str = "normal") -> None:
        """
        Send a notification via all enabled channels.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level (low, normal, high, critical)
        """
        logger.info(f"Sending notification: {title}")
        
        # Send Telegram notification
        if self.telegram_enabled:
            self._send_telegram_notification(title, message, priority)
        
        # Send email notification
        if self.email_enabled:
            self._send_email_notification(title, message, priority)
        
        # Log the notification
        logger.info(f"Notification sent - Title: {title}, Priority: {priority}")
    
    def _send_telegram_notification(self, title: str, message: str, priority: str) -> None:
        """
        Send a Telegram notification.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram notification skipped - missing bot token or chat ID")
            return
        
        try:
            # Format message with priority emoji
            priority_emoji = {
                "low": "ℹ️",
                "normal": "📊",
                "high": "⚠️",
                "critical": "🚨"
            }.get(priority, "📊")
            
            formatted_message = f"{priority_emoji} *{title}*\n\n{message}"
            
            # Telegram API URL
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            # Prepare payload
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            
            # Send request
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.debug("Telegram notification sent successfully")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram notification: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification: {e}")
    
    def _send_email_notification(self, title: str, message: str, priority: str) -> None:
        """
        Send an email notification.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level
        """
        if not all([self.smtp_server, self.email_username, self.email_password, self.email_from, self.email_to]):
            logger.warning("Email notification skipped - missing configuration")
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.email_from
            msg["To"] = self.email_to
            msg["Subject"] = f"[{priority.upper()}] Trading Bot - {title}"
            
            # Format message body
            body = f"""
            Trading Bot Notification
            
            Title: {title}
            Priority: {priority.upper()}
            Time: {self._get_current_time()}
            
            Message:
            {message}
            
            ---
            This is an automated message from your trading bot.
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                server.send_message(msg)
            
            logger.debug("Email notification sent successfully")
        
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email notification: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error sending email notification: {e}")
    
    def send_trade_notification(self, trade_type: str, symbol: str, price: float, 
                              quantity: float, reason: str = "") -> None:
        """
        Send a trade-specific notification.
        
        Args:
            trade_type: Type of trade (buy, sell, stop_loss, take_profit)
            symbol: Trading symbol
            price: Trade price
            quantity: Trade quantity
            reason: Reason for the trade
        """
        title = f"{trade_type.upper()} Order Executed - {symbol}"
        
        message = f"""
        Trade Details:
        Symbol: {symbol}
        Type: {trade_type.upper()}
        Price: {price}
        Quantity: {quantity}
        """
        
        if reason:
            message += f"\nReason: {reason}"
        
        # Determine priority based on trade type
        priority = "high" if trade_type in ["stop_loss", "take_profit"] else "normal"
        
        self.send_notification(title, message, priority)
    
    def send_error_notification(self, error_type: str, error_message: str, 
                              context: Optional[str] = None) -> None:
        """
        Send an error notification.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context about the error
        """
        title = f"Trading Bot Error - {error_type}"
        
        message = f"""
        Error Details:
        Type: {error_type}
        Message: {error_message}
        """
        
        if context:
            message += f"\nContext: {context}"
        
        self.send_notification(title, message, "critical")
    
    def send_performance_notification(self, period: str, metrics: Dict[str, float]) -> None:
        """
        Send a performance summary notification.
        
        Args:
            period: Performance period (daily, weekly, monthly)
            metrics: Performance metrics dictionary
        """
        title = f"Trading Bot Performance - {period.title()} Summary"
        
        message = f"""
        Performance Summary ({period}):
        
        Total Return: {metrics.get('total_return', 0):.2f}%
        Win Rate: {metrics.get('win_rate', 0):.2f}%
        Profit Factor: {metrics.get('profit_factor', 0):.2f}
        Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%
        Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
        
        Total Trades: {metrics.get('total_trades', 0)}
        Winning Trades: {metrics.get('winning_trades', 0)}
        Losing Trades: {metrics.get('losing_trades', 0)}
        """
        
        self.send_notification(title, message, "normal")
    
    def send_system_notification(self, event: str, details: str = "") -> None:
        """
        Send a system event notification.
        
        Args:
            event: System event (startup, shutdown, restart, etc.)
            details: Additional details about the event
        """
        title = f"Trading Bot System - {event.title()}"
        
        message = f"""
        System Event: {event.title()}
        Time: {self._get_current_time()}
        """
        
        if details:
            message += f"\nDetails: {details}"
        
        priority = "high" if event in ["error", "crash", "emergency_stop"] else "normal"
        
        self.send_notification(title, message, priority)
    
    def test_notifications(self) -> Dict[str, bool]:
        """
        Test all enabled notification channels.
        
        Returns:
            Dictionary with test results for each channel
        """
        results = {}
        
        # Test Telegram
        if self.telegram_enabled:
            try:
                self._send_telegram_notification(
                    "Test Notification",
                    "This is a test message from your trading bot.",
                    "normal"
                )
                results["telegram"] = True
                logger.info("Telegram notification test successful")
            except Exception as e:
                results["telegram"] = False
                logger.error(f"Telegram notification test failed: {e}")
        
        # Test Email
        if self.email_enabled:
            try:
                self._send_email_notification(
                    "Test Notification",
                    "This is a test message from your trading bot.",
                    "normal"
                )
                results["email"] = True
                logger.info("Email notification test successful")
            except Exception as e:
                results["email"] = False
                logger.error(f"Email notification test failed: {e}")
        
        return results
    
    def _get_current_time(self) -> str:
        """
        Get current time as formatted string.
        
        Returns:
            Formatted time string
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def is_enabled(self) -> bool:
        """
        Check if any notification channel is enabled.
        
        Returns:
            True if any notification channel is enabled
        """
        return self.telegram_enabled or self.email_enabled
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get notification manager status.
        
        Returns:
            Status dictionary
        """
        return {
            "telegram_enabled": self.telegram_enabled,
            "email_enabled": self.email_enabled,
            "any_enabled": self.is_enabled(),
            "telegram_configured": bool(self.telegram_bot_token and self.telegram_chat_id),
            "email_configured": bool(all([
                self.smtp_server, self.email_username, 
                self.email_password, self.email_from, self.email_to
            ]))
        }
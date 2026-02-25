"""
AE-Trader Configuration Management
Handles environment variables, Firebase initialization, and global settings with validation.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TradingConfig:
    """Configuration for trading parameters with validation."""
    initial_capital: float = 10000.0
    max_position_size: float = 0.1  # 10% of capital per trade
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.05  # 5% take profit
    max_daily_loss: float = 0.03  # 3% max daily drawdown
    trading_fee: float = 0.001  # 0.1% trading fee
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if not 0 < self.max_position_size <= 1:
            raise ValueError("max_position_size must be between 0 and 1")
        if self.stop_loss_pct <= 0:
            raise ValueError("stop_loss_pct must be positive")
        if self.take_profit_pct <= self.stop_loss_pct:
            raise ValueError("take_profit_pct must be greater than stop_loss_pct")

class ConfigManager:
    """Centralized configuration management with Firebase integration."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config_cache: Dict[str, Any] = {}
        self._firebase_app = None
        self._db = None
        
        # Initialize configurations
        self.trading_config = TradingConfig()
        self.trading_config.validate()
        
        # Initialize Firebase if credentials are available
        self._init_firebase()
    
    def _init_firebase(self) -> None:
        """Initialize Firebase Admin SDK with error handling."""
        try:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if cred_path and Path(cred_path).exists():
                cred = credentials.Certificate(cred_path)
                self._firebase_app = firebase_admin.initialize_app(cred)
                self._db = firestore.client()
                self.logger.info("Firebase initialized successfully")
            else:
                self.logger.warning("Firebase credentials not found. Running in local mode.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase: {e}")
    
    def get_firestore_db(self):
        """Get Firestore database instance."""
        if not self._db:
            raise RuntimeError("Firebase not initialized")
        return self._db
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with caching."""
        if key in self._config_cache:
            return self._config_cache[key]
        
        # Try to get from environment
        value = os.getenv(key)
        if value is not None:
            try:
                # Try to parse as JSON if it looks like JSON
                if value.startswith('{') or value.startswith('['):
                    value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Keep as string
            
            self._config_cache[key] = value
            return value
        
        return default
    
    def update_config(self, key: str, value: Any) -> None:
        """Update configuration in cache and optionally Firebase."""
        self._config_cache[key] = value
        
        # Also update in Firebase if available
        if self._db:
            try:
                doc_ref = self._db.collection("system_config").document("active")
                doc_ref.set({key: value}, merge=True)
            except Exception as e:
                self.logger.error(f"Failed to update config in Firebase: {e}")

# Global configuration instance
config = ConfigManager()
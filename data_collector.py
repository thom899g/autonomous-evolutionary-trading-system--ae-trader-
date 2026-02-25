"""
Real-time Market Data Collector
Fetches and processes market data from multiple sources with retry logic and error handling.
"""
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from enum import Enum

class DataSource(Enum):
    """Supported data sources."""
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    CCXT = "ccxt"  # For cryptocurrency
    YFINANCE = "yfinance"  # Fallback

class MarketDataCollector:
    """Collects and processes market data from various sources."""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache
        
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def fetch_ohlcv(self, 
                         symbol: str, 
                         interval: str = '1h',
                         limit: int = 100,
                         source: DataSource = DataSource.ALPHA_VANTAGE) -> pd.DataFrame:
        """
        Fetch OHLCV data with retry logic and validation.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            interval: Time interval ('1m
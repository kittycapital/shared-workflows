"""
fetch_utils.py - Shared utilities for dashboard data fetching

Copy this file to your repo or install via:
  pip install git+https://github.com/kittycapital/shared-workflows.git

Usage:
    from fetch_utils import fetch_with_retry, get_coingecko_price, save_json, get_kst_timestamp
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
import requests

# ============================================================================
# TIMEZONE HELPERS
# ============================================================================

KST = timezone(timedelta(hours=9))

def get_kst_timestamp(fmt: str = "%Y-%m-%d %H:%M:%S KST") -> str:
    """Get current time in KST formatted string."""
    return datetime.now(KST).strftime(fmt)

def get_kst_date(fmt: str = "%Y-%m-%d") -> str:
    """Get current date in KST."""
    return datetime.now(KST).strftime(fmt)

# ============================================================================
# HTTP FETCH WITH RETRY
# ============================================================================

def fetch_with_retry(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    max_retries: int = 3,
    base_delay: float = 2.0,
    timeout: int = 30,
    method: str = "GET",
    json_body: Optional[dict] = None,
) -> Optional[requests.Response]:
    """
    Fetch URL with exponential backoff retry.
    
    Args:
        url: Target URL
        params: Query parameters
        headers: HTTP headers
        max_retries: Maximum retry attempts
        base_delay: Initial delay between retries (doubles each time)
        timeout: Request timeout in seconds
        method: HTTP method (GET, POST)
        json_body: JSON body for POST requests
    
    Returns:
        Response object or None if all retries failed
    """
    headers = headers or {}
    
    for attempt in range(max_retries):
        try:
            if method.upper() == "POST":
                resp = requests.post(url, params=params, headers=headers, 
                                    json=json_body, timeout=timeout)
            else:
                resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            # Success
            if resp.status_code == 200:
                return resp
            
            # Rate limited - wait longer
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", base_delay * (2 ** attempt)))
                print(f"⏳ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            
            # Client error (4xx except 429) - don't retry
            if 400 <= resp.status_code < 500:
                print(f"❌ Client error {resp.status_code}: {url}")
                return None
            
            # Server error (5xx) - retry
            print(f"⚠️ Server error {resp.status_code}, attempt {attempt + 1}/{max_retries}")
            
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout, attempt {attempt + 1}/{max_retries}")
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ Connection error: {e}, attempt {attempt + 1}/{max_retries}")
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}, attempt {attempt + 1}/{max_retries}")
        
        # Exponential backoff
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            print(f"   Retrying in {delay}s...")
            time.sleep(delay)
    
    print(f"❌ All {max_retries} attempts failed for: {url}")
    return None

# ============================================================================
# COINGECKO API (FREE TIER)
# ============================================================================

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_cg_last_call = 0
_CG_RATE_LIMIT = 12  # seconds between calls for free tier

def _coingecko_rate_limit():
    """Enforce CoinGecko rate limiting."""
    global _cg_last_call
    elapsed = time.time() - _cg_last_call
    if elapsed < _CG_RATE_LIMIT:
        time.sleep(_CG_RATE_LIMIT - elapsed)
    _cg_last_call = time.time()

def get_coingecko_price(
    coin_ids: list[str],
    vs_currencies: str = "usd",
    include_24h_change: bool = True
) -> Optional[dict]:
    """
    Get current prices from CoinGecko.
    
    Args:
        coin_ids: List of CoinGecko coin IDs (e.g., ["bitcoin", "ethereum"])
        vs_currencies: Currency to price against
        include_24h_change: Include 24h price change percentage
    
    Returns:
        Dict of {coin_id: {usd: price, usd_24h_change: pct}} or None
    """
    _coingecko_rate_limit()
    
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": vs_currencies,
        "include_24hr_change": str(include_24h_change).lower()
    }
    
    resp = fetch_with_retry(f"{COINGECKO_BASE}/simple/price", params=params)
    if resp:
        return resp.json()
    return None

def get_coingecko_market_data(
    coin_ids: list[str],
    vs_currency: str = "usd"
) -> Optional[list[dict]]:
    """
    Get detailed market data from CoinGecko.
    
    Returns list of coins with: current_price, market_cap, total_volume,
    price_change_percentage_24h, etc.
    """
    _coingecko_rate_limit()
    
    params = {
        "ids": ",".join(coin_ids),
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "sparkline": "false"
    }
    
    resp = fetch_with_retry(f"{COINGECKO_BASE}/coins/markets", params=params)
    if resp:
        return resp.json()
    return None

def get_coingecko_historical(
    coin_id: str,
    days: int = 365,
    vs_currency: str = "usd"
) -> Optional[dict]:
    """
    Get historical price data from CoinGecko.
    
    Note: Free tier limited to 365 days max.
    
    Returns:
        Dict with 'prices', 'market_caps', 'total_volumes' arrays
        Each array contains [timestamp_ms, value] pairs
    """
    _coingecko_rate_limit()
    
    # Free tier caps at 365 days
    days = min(days, 365)
    
    params = {
        "vs_currency": vs_currency,
        "days": str(days)
    }
    
    resp = fetch_with_retry(f"{COINGECKO_BASE}/coins/{coin_id}/market_chart", params=params)
    if resp:
        return resp.json()
    return None

# ============================================================================
# BINANCE API (PUBLIC)
# ============================================================================

BINANCE_BASE = "https://api.binance.com/api/v3"

def get_binance_price(symbol: str = "BTCUSDT") -> Optional[float]:
    """Get current price from Binance."""
    resp = fetch_with_retry(f"{BINANCE_BASE}/ticker/price", params={"symbol": symbol})
    if resp:
        return float(resp.json()["price"])
    return None

def get_binance_prices(symbols: list[str]) -> dict[str, float]:
    """Get multiple prices from Binance."""
    resp = fetch_with_retry(f"{BINANCE_BASE}/ticker/price")
    if resp:
        data = {item["symbol"]: float(item["price"]) for item in resp.json()}
        return {s: data.get(s, 0) for s in symbols}
    return {}

# ============================================================================
# DEFILLAMA API (FREE, NO KEY)
# ============================================================================

DEFILLAMA_BASE = "https://api.llama.fi"

def get_defillama_tvl(protocol: str) -> Optional[dict]:
    """Get TVL data for a protocol."""
    resp = fetch_with_retry(f"{DEFILLAMA_BASE}/protocol/{protocol}")
    if resp:
        return resp.json()
    return None

def get_defillama_fees(exclude_charts: bool = True) -> Optional[dict]:
    """Get all protocol fees/revenue data."""
    params = {}
    if exclude_charts:
        params["excludeTotalDataChart"] = "true"
        params["excludeTotalDataChartBreakdown"] = "true"
    
    resp = fetch_with_retry(f"{DEFILLAMA_BASE}/overview/fees", params=params)
    if resp:
        return resp.json()
    return None

def get_defillama_yields() -> Optional[dict]:
    """Get yield pools data."""
    resp = fetch_with_retry(f"{DEFILLAMA_BASE}/pools")
    if resp:
        return resp.json()
    return None

# ============================================================================
# KOREAN GOVERNMENT API HELPERS
# ============================================================================

def build_data_go_kr_url(base_url: str, api_key: str, params: dict) -> str:
    """
    Build URL for data.go.kr API with proper encoding.
    
    data.go.kr API keys are pre-URL-encoded, so we must inject them directly
    into the URL to avoid double-encoding.
    """
    # Build query string for other params (requests will encode these)
    query_parts = [f"serviceKey={api_key}"]  # API key injected raw
    for key, value in params.items():
        query_parts.append(f"{key}={value}")
    
    return f"{base_url}?{'&'.join(query_parts)}"

# ============================================================================
# FILE I/O
# ============================================================================

def save_json(data: Any, filepath: str, indent: int = 2) -> bool:
    """
    Save data to JSON file, creating directories if needed.
    
    Returns True on success, False on failure.
    """
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        print(f"✅ Saved: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Failed to save {filepath}: {e}")
        return False

def load_json(filepath: str, default: Any = None) -> Any:
    """Load JSON file, returning default if file doesn't exist or is invalid."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        print(f"⚠️ Invalid JSON in {filepath}: {e}")
        return default

def ensure_data_dir(dirname: str = "data") -> Path:
    """Create data directory if it doesn't exist."""
    path = Path(dirname)
    path.mkdir(parents=True, exist_ok=True)
    return path

# ============================================================================
# ENVIRONMENT HELPERS
# ============================================================================

def get_env(key: str, default: str = "", required: bool = False) -> str:
    """Get environment variable with optional requirement check."""
    value = os.environ.get(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value

def is_github_actions() -> bool:
    """Check if running in GitHub Actions."""
    return os.environ.get("GITHUB_ACTIONS") == "true"

# ============================================================================
# NUMBER FORMATTING
# ============================================================================

def format_number(n: float, precision: int = 2) -> str:
    """Format number with commas: 1234567.89 -> '1,234,567.89'"""
    return f"{n:,.{precision}f}"

def format_korean_number(n: float) -> str:
    """Format number in Korean style: 123456789 -> '1.23억'"""
    if abs(n) >= 1_0000_0000:  # 억
        return f"{n / 1_0000_0000:.2f}억"
    elif abs(n) >= 1_0000:  # 만
        return f"{n / 1_0000:.1f}만"
    else:
        return f"{n:,.0f}"

def format_usd(n: float, precision: int = 0) -> str:
    """Format as USD: 1234567 -> '$1,234,567'"""
    return f"${n:,.{precision}f}"

def format_percent(n: float, precision: int = 2, show_sign: bool = True) -> str:
    """Format as percentage: 0.1234 -> '+12.34%'"""
    pct = n * 100 if abs(n) < 1 else n  # Handle both 0.12 and 12 as input
    if show_sign and pct > 0:
        return f"+{pct:.{precision}f}%"
    return f"{pct:.{precision}f}%"

# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    print(f"🕐 Current time: {get_kst_timestamp()}")
    print(f"📅 Current date: {get_kst_date()}")
    
    # Test CoinGecko
    print("\n📊 Testing CoinGecko...")
    prices = get_coingecko_price(["bitcoin", "ethereum"])
    if prices:
        for coin, data in prices.items():
            print(f"  {coin}: {format_usd(data['usd'])}")
    
    print("\n✅ fetch_utils.py is working!")

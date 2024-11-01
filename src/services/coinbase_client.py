from typing import Optional, List, Dict
import aiohttp
import asyncio
from datetime import datetime, timedelta
import time


class CoinbaseClient:
    def __init__(
        self, max_retries: int = 3, retry_delay: float = 0.5, rate_limit: int = 30
    ):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://api.coinbase.com/v2"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit = rate_limit
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        headers = {"Accept": "application/json", "User-Agent": "CoinbaseClient/1.0"}
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        async with self._lock:
            now = time.time()
            # Remove old requests from tracking
            self._request_times = [t for t in self._request_times if now - t < 1.0]

            if len(self._request_times) >= self.rate_limit:
                sleep_time = 1.0 - (now - self._request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            self._request_times.append(now)

    async def _make_request(
        self, endpoint: str, method: str = "GET", params: None | Dict = None
    ) -> Dict:
        """Make an API request with retries and error handling"""
        if not self.session:
            raise RuntimeError(
                "Client session not initialized. Use 'async with' context manager."
            )

        await self._enforce_rate_limit()

        for attempt in range(self.max_retries):
            try:
                async with self.session.request(
                    method, f"{self.base_url}/{endpoint}", params=params
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limit exceeded
                        retry_after = float(
                            response.headers.get("Retry-After", self.retry_delay)
                        )
                        await asyncio.sleep(retry_after)
                    elif response.status >= 500:  # Server error
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        error_data = await response.json()
                        raise aiohttp.ClientError(
                            f"API Error: {error_data.get('message', 'Unknown error')}"
                        )

            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                continue
            except Exception as e:
                raise

        raise aiohttp.ClientError(f"Failed after {self.max_retries} attempts")

    async def get_price(self, ticker: str) -> Optional[float]:
        """Get current token price in USD"""
        try:
            data = await self._make_request(f"prices/{ticker}-USD/spot")
            return float(data["data"]["amount"])
        except (KeyError, ValueError) as e:
            return None
        except Exception as e:
            return None

    async def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[float]]:
        async with asyncio.TaskGroup() as group:  # Python 3.11+
            tasks = [group.create_task(self.get_price(ticker)) for ticker in tickers]
        return dict(zip(tickers, [t.result() for t in tasks]))

    # async def get_multiple_prices(self, tickers: List[str]) -> Dict[str, Optional[float]]:
    #    """Get prices for multiple tokens concurrently"""
    #    async def get_single_price(ticker: str) -> tuple[str, Optional[float]]:
    #        price = await self.get_price(ticker)
    #        return ticker, price

    #    tasks = [get_single_price(ticker) for ticker in tickers]
    #    results = await asyncio.gather(*tasks, return_exceptions=True)

    #    return {
    #        ticker: price for ticker, price in results
    #        if not isinstance(price, Exception)
    #    }

    async def get_price_history(
        self, ticker: str, days: int = 7
    ) -> Optional[List[Dict]]:
        """Get historical price data"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        params = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "granularity": "86400",  # Daily candles
        }

        try:
            data = await self._make_request(
                f"prices/{ticker}-USD/historic", params=params
            )
            return data["data"]
        except Exception as e:
            return None

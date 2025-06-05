#!/usr/bin/env python3
"""
Concurrency Manager for Livia Chatbot
-------------------------------------
Manages rate limiting, semaphores, and retry logic for OpenAI and Zapier APIs.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log
)
import openai

logger = logging.getLogger(__name__)

@dataclass
class APILimits:
    """Configuration for API rate limits and concurrency."""
    max_concurrent: int = 5  # Maximum concurrent requests
    requests_per_minute: int = 60  # Rate limit per minute
    requests_per_hour: int = 3600  # Rate limit per hour
    retry_attempts: int = 5  # Maximum retry attempts
    min_wait: float = 1.0  # Minimum wait time for exponential backoff
    max_wait: float = 60.0  # Maximum wait time for exponential backoff

@dataclass
class ConcurrencyStats:
    """Statistics for monitoring concurrency performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    concurrent_requests: int = 0
    average_response_time: float = 0.0
    last_reset_time: float = field(default_factory=time.time)

class ConcurrencyManager:
    """
    Centralized manager for handling concurrency, rate limiting, and retries
    across OpenAI and Zapier APIs.
    """
    
    def __init__(self):
        # API-specific configurations
        self.api_configs = {
            "openai": APILimits(
                max_concurrent=8,  # OpenAI supports ~8 concurrent requests
                requests_per_minute=500,
                requests_per_hour=10000,
                retry_attempts=5,
                min_wait=1.0,
                max_wait=60.0
            ),
            "zapier": APILimits(
                max_concurrent=3,  # Conservative for Zapier MCPs
                requests_per_minute=60,  # 80 calls/hour = ~1.3/minute, be conservative
                requests_per_hour=75,   # Leave some buffer
                retry_attempts=3,
                min_wait=2.0,
                max_wait=30.0
            )
        }
        
        # Semaphores for controlling concurrent requests
        self.semaphores = {
            api: asyncio.Semaphore(config.max_concurrent)
            for api, config in self.api_configs.items()
        }
        
        # Rate limiting tracking
        self.rate_trackers = {
            api: {
                "minute_requests": [],
                "hour_requests": []
            }
            for api in self.api_configs.keys()
        }
        
        # Statistics tracking
        self.stats = {
            api: ConcurrencyStats()
            for api in self.api_configs.keys()
        }
        
        logger.info("ConcurrencyManager initialized with API limits:")
        for api, config in self.api_configs.items():
            logger.info(f"  {api}: {config.max_concurrent} concurrent, "
                       f"{config.requests_per_minute}/min, {config.requests_per_hour}/hour")

    async def execute_with_concurrency_control(
        self,
        api_name: str,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str = "API call"
    ) -> Any:
        """
        Execute an API operation with concurrency control, rate limiting, and retry logic.
        
        Args:
            api_name: Name of the API ("openai" or "zapier")
            operation: Async function to execute
            operation_name: Human-readable name for logging
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If operation fails after all retries
        """
        if api_name not in self.api_configs:
            raise ValueError(f"Unknown API: {api_name}. Available: {list(self.api_configs.keys())}")
        
        config = self.api_configs[api_name]
        semaphore = self.semaphores[api_name]
        stats = self.stats[api_name]
        
        # Check rate limits before attempting
        await self._check_rate_limits(api_name)
        
        # Acquire semaphore for concurrency control
        async with semaphore:
            stats.concurrent_requests += 1
            start_time = time.time()
            
            try:
                # Create retry decorator with API-specific configuration
                retry_decorator = retry(
                    wait=wait_exponential(
                        multiplier=1,
                        min=config.min_wait,
                        max=config.max_wait
                    ),
                    stop=stop_after_attempt(config.retry_attempts),
                    retry=retry_if_exception_type((
                        openai.RateLimitError,
                        openai.APITimeoutError,
                        openai.APIConnectionError,
                        ConnectionError,
                        TimeoutError
                    )),
                    before_sleep=before_sleep_log(logger, logging.WARNING),
                    reraise=True
                )
                
                # Execute operation with retry logic
                result = await retry_decorator(operation)()
                
                # Update statistics
                end_time = time.time()
                response_time = end_time - start_time
                stats.successful_requests += 1
                stats.total_requests += 1
                
                # Update average response time
                if stats.successful_requests == 1:
                    stats.average_response_time = response_time
                else:
                    stats.average_response_time = (
                        (stats.average_response_time * (stats.successful_requests - 1) + response_time)
                        / stats.successful_requests
                    )
                
                # Track rate limiting
                self._track_request(api_name)
                
                logger.debug(f"✅ {operation_name} completed successfully in {response_time:.2f}s")
                return result
                
            except Exception as e:
                stats.failed_requests += 1
                stats.total_requests += 1
                logger.error(f"❌ {operation_name} failed after {config.retry_attempts} attempts: {e}")
                raise
                
            finally:
                stats.concurrent_requests -= 1

    async def _check_rate_limits(self, api_name: str) -> None:
        """Check if we're within rate limits for the API."""
        config = self.api_configs[api_name]
        tracker = self.rate_trackers[api_name]
        current_time = time.time()
        
        # Clean old requests from tracking
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        tracker["minute_requests"] = [
            req_time for req_time in tracker["minute_requests"]
            if req_time > minute_ago
        ]
        tracker["hour_requests"] = [
            req_time for req_time in tracker["hour_requests"]
            if req_time > hour_ago
        ]
        
        # Check limits
        minute_count = len(tracker["minute_requests"])
        hour_count = len(tracker["hour_requests"])
        
        if minute_count >= config.requests_per_minute:
            wait_time = 60 - (current_time - min(tracker["minute_requests"]))
            logger.warning(f"Rate limit reached for {api_name} (minute): waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            
        if hour_count >= config.requests_per_hour:
            wait_time = 3600 - (current_time - min(tracker["hour_requests"]))
            logger.warning(f"Rate limit reached for {api_name} (hour): waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

    def _track_request(self, api_name: str) -> None:
        """Track a request for rate limiting purposes."""
        current_time = time.time()
        tracker = self.rate_trackers[api_name]
        
        tracker["minute_requests"].append(current_time)
        tracker["hour_requests"].append(current_time)

    def get_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if api_name:
            if api_name not in self.stats:
                return {}
            stats = self.stats[api_name]
            return {
                "api": api_name,
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "success_rate": (
                    stats.successful_requests / stats.total_requests * 100
                    if stats.total_requests > 0 else 0
                ),
                "concurrent_requests": stats.concurrent_requests,
                "average_response_time": stats.average_response_time
            }
        else:
            return {
                api: self.get_stats(api)
                for api in self.api_configs.keys()
            }

    def reset_stats(self, api_name: Optional[str] = None) -> None:
        """Reset performance statistics."""
        if api_name:
            if api_name in self.stats:
                self.stats[api_name] = ConcurrencyStats()
        else:
            for api in self.api_configs.keys():
                self.stats[api] = ConcurrencyStats()
        
        logger.info(f"Statistics reset for {api_name or 'all APIs'}")

# Global instance
concurrency_manager = ConcurrencyManager()

"""Rate limiting utilities for API calls."""

import time
from typing import Optional
from collections import deque


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""
    
    def __init__(self, max_calls: int, time_window: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds (default: 1 hour)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove calls outside the time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()
        
        # If at limit, wait until oldest call expires
        if len(self.calls) >= self.max_calls:
            sleep_time = self.calls[0] + self.time_window - now + 1
            if sleep_time > 0:
                time.sleep(sleep_time)
                # Clean up again after sleep
                while self.calls and self.calls[0] < now - self.time_window:
                    self.calls.popleft()
        
        # Record this call
        self.calls.append(time.time())
    
    def can_proceed(self) -> bool:
        """Check if a call can proceed without waiting."""
        now = time.time()
        
        # Remove calls outside the time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()
        
        return len(self.calls) < self.max_calls


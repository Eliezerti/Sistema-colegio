"""Account and origin/account cooldowns; loopback is never globally banned."""
import math
import threading
import time


class LoginLimiter:
    def __init__(self, now=None):
        self.now = now or time.monotonic
        self.lock = threading.Lock()
        self.accounts = {}
        self.origins = {}
        # Bound simultaneous costly password checks, without a lasting IP ban.
        self.checks = threading.BoundedSemaphore(2)

    def _prune(self, tick):
        for mapping in (self.accounts, self.origins):
            for key, (_, _, seen) in list(mapping.items()):
                if tick - seen >= 900:
                    mapping.pop(key, None)

    def wait(self, origin, username):
        with self.lock:
            tick = self.now()
            self._prune(tick)
            values = [self.accounts.get(username), self.origins.get((origin, username))]
            return max([0] + [math.ceil(v[1] - tick) for v in values if v])

    def failure(self, origin, username):
        with self.lock:
            tick = self.now()
            self._prune(tick)
            for mapping, key in ((self.accounts, username), (self.origins, (origin, username))):
                count = mapping.get(key, (0, 0, tick))[0] + 1
                delay = min(60, 5 * 2 ** min(4, max(0, count - 5))) if count >= 5 else 0
                mapping[key] = (count, tick + delay, tick)

    def success(self, origin, username):
        with self.lock:
            self.accounts.pop(username, None)
            for key in list(self.origins):
                if key[1] == username:
                    self.origins.pop(key, None)

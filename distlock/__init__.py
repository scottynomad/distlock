from functools import partial
import os
from redis import StrictRedis
import time


__version__ = '0.1.0'
VERSION = tuple(map(int, __version__.split('.')))


class DistributedLock(object):
    in_use = False
    is_locked = False

    def __init__(self, redis, key, sleep_ms=50, timeout=0):
        self.r = redis
        self.key = key
        self.sleep_ms = sleep_ms
        self.timeout = timeout

    @property
    def id(self):
        return str(id(self))

    def lock(self, sleep_fn=None):
        if self.in_use:
            raise RuntimeError("Locked re-entered")
        self.in_use = True
        self.r.rpush(self.key, self.id)
        while True:
            l = self.r.lrange(self.key, 0, 0)
            if not l:
                raise RuntimeError("Lock Timeout (key not found)")
            if l[0] == self.id:
                break
            if sleep_fn:
                # hook for inspection of state by tests
                sleep_fn(self)
            else:
                time.sleep(self.sleep_ms / 1000.0)
        self.is_locked = True
        self.r.expire(self.key, self.timeout)
        return self

    def release(self):
        assert self.r.lpop(self.key) == self.id
        self.in_use = self.is_locked = False

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, *exc_details):
        self.release()


class DistributedLockFactory(object):
    redis_dsn = os.environ.get('REDIS_DSN', 'redis://localhost:6379/0')

    def __init__(self, prefix='distlock.', timeout=3600, sleep_ms=50,
                 redis=None):
        redis = redis or StrictRedis.from_url(self.redis_dsn)
        self.prefix = prefix
        self._factory = partial(DistributedLock, redis,
                                sleep_ms=sleep_ms, timeout=timeout)

    def __call__(self, key='lock'):
        return self._factory(key=self.prefix + key)



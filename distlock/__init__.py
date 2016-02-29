from functools import partial
import os
from redis import StrictRedis
import time


class DistributedLock(object):
    """DistributedLock - Redis-backed locking primitive

    May be optionally used as a context manager:

    >>> redis = getfixture('redis')
    >>> with DistributedLock(redis, 'lock_ctxt') as l:
    ...     # protected block
    ...     assert l.is_locked

    or used directly:

    >>> redis = getfixture('redis')
    >>> l = DistributedLock(redis, 'lock_it')
    >>> l.lock()
    >>> assert l.is_locked # my protected code
    >>> l.release()
    >>> assert l.is_locked is False

    See *DistributedLockFactory* for a friendlier interface if you
    will be using many locks.

    :param redis: Redis client handle
    :param key: Key in the redis data store where locks are stored.
    :param timeout: TTL of the lock. default=None
    :param sleep_ms: Sleeps *sleep_ms* between attempts to get the lock.
                    [default=50]

    Raises *RuntimeError* if *timeout* is exceeded or if the lock's
    state vanishes from Redis.
    """
    in_use = False
    is_locked = False

    def __init__(self, redis, key, timeout=None, sleep_ms=50):
        self.r = redis
        self.key = unicode(key)
        self.timeout = timeout
        self.sleep_ms = sleep_ms

    @property
    def id(self):
        return str(id(self))

    def lock(self, sleep_fn=None):
        """Acquire the lock.

        :param sleep_fn: Optional callback function during spin sleep.
                         Handy for progress reporting and testing.
        """
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
        if self.timeout:
            self.r.expire(self.key, self.timeout)

    def release(self):
        """Release the lock."""
        assert self.r.lpop(self.key) == self.id
        self.in_use = self.is_locked = False

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, *exc_details):
        self.release()


class DistributedLockFactory(object):
    """DistributedLockFactory - Helper factory for *DistributedLock*

    :param prefix: Common prefix applied to all locks.  [default=distlock.]
    :param timeout: Lock TTL. Passed to lock instance.  [default=None]
    :param sleep_ms: Spin sleep interval. Passed to lock. [default=50]
    :param redis: Optional redis handle. If None this factory will
                  attempt to create one based on the *REDIS_DSN*
                  environment variable, falling back to the default
                  local redis: redis://localhost:6379/0.

    Call the factory as a context manager:

    >>> redis = getfixture('redis')
    >>> f = DistributedLockFactory(prefix="locks", redis=redis)
    >>> with f(12345) as l:
    ...     assert l.is_locked
    ...     assert l.key == 'locks12345'

    Or call it directly:

    >>> redis = getfixture('redis')
    >>> f = DistributedLockFactory(redis=redis)
    >>> l = f('lock1')
    >>> l.key
    u'distlock.lock1'
    >>> l.is_locked
    False

    """
    redis_dsn = os.environ.get('REDIS_DSN', 'redis://localhost:6379/0')

    def __init__(self, prefix='distlock.', timeout=None, sleep_ms=50,
                 redis=None):
        redis = redis or StrictRedis.from_url(self.redis_dsn)
        self.prefix = unicode(prefix)
        self._factory = partial(DistributedLock, redis,
                                sleep_ms=sleep_ms, timeout=timeout)

    def __call__(self, key='lock'):
        """Instantiates lock with key *key*.

        :param key: Lock identifier. Must be coercible to unicode string.
        """
        return self._factory(key=self.prefix + unicode(key))

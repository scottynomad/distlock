from datetime import datetime
from distlock import DistributedLock, DistributedLockFactory
import pytest


def test_lock_basic(redis):
    lock = DistributedLock(redis, 'test', sleep_ms=40, timeout=5)
    assert lock.key == 'test'
    assert lock.sleep_ms == 40
    assert lock.timeout == 5
    with lock as l:
        assert l.in_use and l.is_locked
        assert redis.lrange('test', 0, 99) == [l.id]
    assert redis.lrange('test', 0, 99) == []


def test_contention(redis):
    lock1 = DistributedLock(redis, 'test', timeout=10)
    lock2 = DistributedLock(redis, 'test', timeout=10)

    def _sleep_cb(lock):
        assert lock is lock2
        assert redis.lrange('test', 0, 99) == [lock1.id, lock2.id]
        assert lock.in_use
        assert not lock.is_locked
        lock1.release()

    lock1.lock()
    assert redis.lrange('test', 0, 99) == [lock1.id]
    lock2.lock(_sleep_cb)
    assert lock2.in_use and lock2.is_locked
    assert redis.lrange('test', 0, 99) == [lock2.id]
    lock2.release()


def test_timeout(redis):
    lock1 = DistributedLock(redis, 'test', timeout=1)
    lock2 = DistributedLock(redis, 'test', timeout=1)
    lock1.lock()
    with pytest.raises(RuntimeError):
        with lock2:
            #  We never get here.  So many context managers!
            assert False, 'Lock guard failed.'


def test_factory_basic(redis):
    factory = DistributedLockFactory(redis=redis)
    with factory() as l:
        assert redis.lrange('distlock.lock', 0, 99) == [l.id]
        assert l.is_locked
    assert not (l.is_locked or l.in_use)
    assert redis.lrange('distlock.lock', 0, 99) == []


def test_factory_prefix(redis):
    factory = DistributedLockFactory(prefix='foo|', redis=redis)
    lock1 = factory('l1').lock()
    lock2 = factory('l2').lock()
    assert redis.lrange('foo|l1', 0, 99) == [lock1.id]
    assert redis.lrange('foo|l2', 0, 99) == [lock2.id]

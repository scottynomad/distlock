from datetime import datetime, timedelta
import pytest
from redis import StrictRedis


class FakeRedis(object):

    def __init__(self):
        self._data = {}
        self._expiry = {}

    @staticmethod
    def from_url(self, url):
        pass

    def _do_expiry(self, key):
        expires = self._expiry.get(key)
        if expires and expires < datetime.now():
            del self._data[key]
            del self._expiry[key]

    def get(self, key):
        self._do_expiry(key)
        return self._data.get(key)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def set(self, key, value):
        self._data[key] = str(value)

    def __setitem__(self, key, value):
        self.set(key, value)

    def exists(self, key):
        try:
            _ = self[key]
            return True
        except KeyError:
            return False
    __contains__ = exists

    def incr(self, key, amount=1):
        if key not in self:
            self[key] = 0
        self[key] += amount
        return self[key]

    def decr(self, key, amount=1):
        return self.incr(key, -amount)

    def _get_list(self, key, create=True):
        l = self.get(key)
        if l is None and create:
            l = []
            self._data[key] = l
        return l

    def lpush(self, key, *values):
        l = self._get_list(key)
        for v in values:
            l.insert(0, v)

    def lpop(self, key):
        l = self._get_list(key)
        return l.pop(0)

    def rpush(self, key, *values):
        l = self._get_list(key)
        l.extend(values)

    def rpop(self, key):
        l = self._get_list(key)
        return l.pop(-1)

    def lrange(self, key, start, stop):
        l = self._get_list(key, create=False)
        if not l or start >= len(l):
            return []
        if stop > len(l):
            stop = len(l)
        return l[start:stop+1]

    def llen(self, key):
        l = self._get_list(key)
        return len(l)

    def expire(self, key, timeout):
        if isinstance(timeout, int):
            timeout = timedelta(seconds=timeout)
        self._expiry[key] = datetime.now() + timeout

    def flushdb(self):
        self._data = {}
        self._expiry = {}


def pytest_addoption(parser):
    parser.addoption("--redis-dsn", action="store",
                     help="redis-dsn: optional DSN of a real redis server")


@pytest.fixture()
def redis_dsn(request):
    return request.config.getoption("--redis-dsn")


@pytest.fixture()
def redis(redis_dsn):
    if redis_dsn:
        r = StrictRedis.from_url(redis_dsn)
    else:
        r = FakeRedis()
    r.flushdb()
    return r

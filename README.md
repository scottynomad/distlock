# DistLock

A very simple distributed advisory locking primitive using [Redis](http://redis.io/).

## Briefly

```python
>>> redis = getfixture('redis')
>>> f = DistributedLockFactory(prefix="locks", redis=redis)
>>> with f(12345) as l:
...     assert l.is_locked
...     assert l.key == 'locks12345'
```

## Back Story

Distlock is in use as a very simple mechanism to avoid race conditions among instances of
microservices which can in partial failure conditions try to start the same
chunk of work.
 
[Redis](http://redis.io/) affords us a very mechanism for atomic synchronisation 
among network-attached processes.  Because it is a single-process 
event-driven service, all individual operations on it are by definition atomic
enabling us to build a locking mechanism over it.

## Build Status

`master` | [![Build
Status](https://travis-ci.org/scottynomad/distlock.svg?branch=master)](https://travis-ci.org/scottynomad/distlock)

## TODO

- [ ] Python3 support
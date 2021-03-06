# Copyright 2019, OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
a script which uses our integratiosn and prints memory statistics.
a very coarsely grained way of seeing how things are used.
"""


# stdlib
import itertools
import logging
import time
import sys

# 3p
import pylibmc
import pympler.tracker
import psycopg2
import redis


# project
import oteltrace
from tests.contrib import config


# verbosity
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

oteltrace.patch_all()
oteltrace.tracer.writer = None


class KitchenSink(object):

    def __init__(self):
        self._redis = redis.Redis(**config.REDIS_CONFIG)
        self._pg = psycopg2.connect(**config.POSTGRES_CONFIG)

        url = '%s:%s' % (
            config.MEMCACHED_CONFIG['host'],
            config.MEMCACHED_CONFIG['port'])
        self._pylibmc = pylibmc.Client([url])

    def ping(self, i):
        self._ping_redis(i)
        self._ping_pg(i)
        self._ping_pylibmc(i)

    def _ping_redis(self, i):
        with self._redis.pipeline() as p:
            p.get('a')
        self._redis.set('a', 'b')
        self._redis.get('a')

    def _ping_pg(self, i):
        cur = self._pg.cursor()
        try:
            cur.execute("select 'asdf'")
            cur.fetchall()
        finally:
            cur.close()

    def _ping_pylibmc(self, i):
        self._pylibmc.set('a', 1)
        self._pylibmc.incr('a', 2)
        self._pylibmc.decr('a', 1)


if __name__ == '__main__':
    k = KitchenSink()
    t = pympler.tracker.SummaryTracker()
    for i in itertools.count():
        # do the work
        k.ping(i)

        # periodically print stats
        if i % 500 == 0:
            t.print_diff()
        time.sleep(0.0001)

# -*- coding: utf-8 -*-
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

import redis

from oteltrace import Pin, compat
from oteltrace.constants import ANALYTICS_SAMPLE_RATE_KEY
from oteltrace.contrib.redis import get_traced_redis
from oteltrace.contrib.redis.patch import patch, unpatch

from ..config import REDIS_CONFIG
from ...test_tracer import get_dummy_tracer
from ...base import BaseTracerTestCase


def test_redis_legacy():
    # ensure the old interface isn't broken, but doesn't trace
    tracer = get_dummy_tracer()
    TracedRedisCache = get_traced_redis(tracer, 'foo')
    r = TracedRedisCache(port=REDIS_CONFIG['port'])
    r.set('a', 'b')
    got = r.get('a')
    assert compat.to_unicode(got) == 'b'
    assert not tracer.writer.pop()


class TestRedisPatch(BaseTracerTestCase):

    TEST_SERVICE = 'redis-patch'
    TEST_PORT = REDIS_CONFIG['port']

    def setUp(self):
        super(TestRedisPatch, self).setUp()
        patch()
        r = redis.Redis(port=self.TEST_PORT)
        r.flushall()
        Pin.override(r, service=self.TEST_SERVICE, tracer=self.tracer)
        self.r = r

    def tearDown(self):
        unpatch()
        super(TestRedisPatch, self).tearDown()

    def test_long_command(self):
        self.r.mget(*range(1000))

        spans = self.get_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.service == self.TEST_SERVICE
        assert span.name == 'redis.command'
        assert span.span_type == 'redis'
        assert span.error == 0
        meta = {
            'out.host': u'localhost',
            'out.port': str(self.TEST_PORT),
            'out.redis_db': u'0',
        }
        for k, v in meta.items():
            assert span.get_tag(k) == v

        assert span.get_tag('redis.raw_command').startswith(u'MGET 0 1 2 3')
        assert span.get_tag('redis.raw_command').endswith(u'...')

    def test_basics(self):
        us = self.r.get('cheese')
        assert us is None
        spans = self.get_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.service == self.TEST_SERVICE
        assert span.name == 'redis.command'
        assert span.span_type == 'redis'
        assert span.error == 0
        assert span.get_tag('out.redis_db') == '0'
        assert span.get_tag('out.host') == 'localhost'
        assert span.get_tag('redis.raw_command') == u'GET cheese'
        assert span.get_metric('redis.args_length') == 2
        assert span.resource == 'GET cheese'
        assert span.get_metric(ANALYTICS_SAMPLE_RATE_KEY) is None

    def test_analytics_without_rate(self):
        with self.override_config(
            'redis',
            dict(analytics_enabled=True)
        ):
            us = self.r.get('cheese')
            assert us is None
            spans = self.get_spans()
            assert len(spans) == 1
            span = spans[0]
            assert span.get_metric(ANALYTICS_SAMPLE_RATE_KEY) == 1.0

    def test_analytics_with_rate(self):
        with self.override_config(
            'redis',
            dict(analytics_enabled=True, analytics_sample_rate=0.5)
        ):
            us = self.r.get('cheese')
            assert us is None
            spans = self.get_spans()
            assert len(spans) == 1
            span = spans[0]
            assert span.get_metric(ANALYTICS_SAMPLE_RATE_KEY) == 0.5

    def test_pipeline_traced(self):
        with self.r.pipeline(transaction=False) as p:
            p.set('blah', 32)
            p.rpush('foo', u'éé')
            p.hgetall('xxx')
            p.execute()

        spans = self.get_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.service == self.TEST_SERVICE
        assert span.name == 'redis.command'
        assert span.resource == u'SET blah 32\nRPUSH foo éé\nHGETALL xxx'
        assert span.span_type == 'redis'
        assert span.error == 0
        assert span.get_tag('out.redis_db') == '0'
        assert span.get_tag('out.host') == 'localhost'
        assert span.get_tag('redis.raw_command') == u'SET blah 32\nRPUSH foo éé\nHGETALL xxx'
        assert span.get_metric('redis.pipeline_length') == 3
        assert span.get_metric('redis.pipeline_length') == 3
        assert span.get_metric(ANALYTICS_SAMPLE_RATE_KEY) is None

    def test_pipeline_immediate(self):
        with self.r.pipeline() as p:
            p.set('a', 1)
            p.immediate_execute_command('SET', 'a', 1)
            p.execute()

        spans = self.get_spans()
        assert len(spans) == 2
        span = spans[0]
        assert span.service == self.TEST_SERVICE
        assert span.name == 'redis.command'
        assert span.resource == u'SET a 1'
        assert span.span_type == 'redis'
        assert span.error == 0
        assert span.get_tag('out.redis_db') == '0'
        assert span.get_tag('out.host') == 'localhost'

    def test_meta_override(self):
        r = self.r
        pin = Pin.get_from(r)
        if pin:
            pin.clone(tags={'cheese': 'camembert'}).onto(r)

        r.get('cheese')
        spans = self.get_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.service == self.TEST_SERVICE
        assert 'cheese' in span.meta and span.meta['cheese'] == 'camembert'

    def test_patch_unpatch(self):
        tracer = get_dummy_tracer()
        writer = tracer.writer

        # Test patch idempotence
        patch()
        patch()

        r = redis.Redis(port=REDIS_CONFIG['port'])
        Pin.get_from(r).clone(tracer=tracer).onto(r)
        r.get('key')

        spans = writer.pop()
        assert spans, spans
        assert len(spans) == 1

        # Test unpatch
        unpatch()

        r = redis.Redis(port=REDIS_CONFIG['port'])
        r.get('key')

        spans = writer.pop()
        assert not spans, spans

        # Test patch again
        patch()

        r = redis.Redis(port=REDIS_CONFIG['port'])
        Pin.get_from(r).clone(tracer=tracer).onto(r)
        r.get('key')

        spans = writer.pop()
        assert spans, spans
        assert len(spans) == 1

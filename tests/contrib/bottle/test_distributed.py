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

import bottle
import webtest

import oteltrace
from oteltrace import compat
from oteltrace.contrib.bottle import TracePlugin

from ...base import BaseTracerTestCase

SERVICE = 'bottle-app'


class TraceBottleDistributedTest(BaseTracerTestCase):
    """
    Ensures that Bottle is properly traced.
    """
    def setUp(self):
        super(TraceBottleDistributedTest, self).setUp()

        # provide a dummy tracer
        self._original_tracer = oteltrace.tracer
        oteltrace.tracer = self.tracer
        # provide a Bottle app
        self.app = bottle.Bottle()

    def tearDown(self):
        # restore the tracer
        oteltrace.tracer = self._original_tracer

    def _trace_app_distributed(self, tracer=None):
        self.app.install(TracePlugin(service=SERVICE, tracer=tracer))
        self.app = webtest.TestApp(self.app)

    def _trace_app_not_distributed(self, tracer=None):
        self.app.install(TracePlugin(service=SERVICE, tracer=tracer, distributed_tracing=False))
        self.app = webtest.TestApp(self.app)

    def test_distributed(self):
        # setup our test app
        @self.app.route('/hi/<name>')
        def hi(name):
            return 'hi %s' % name
        self._trace_app_distributed(self.tracer)

        # make a request
        headers = {'x-datadog-trace-id': '123',
                   'x-datadog-parent-id': '456'}
        resp = self.app.get('/hi/dougie', headers=headers)
        assert resp.status_int == 200
        assert compat.to_unicode(resp.body) == u'hi dougie'

        # validate it's traced
        spans = self.tracer.writer.pop()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == 'bottle.request'
        assert s.service == 'bottle-app'
        assert s.resource == 'GET /hi/<name>'
        assert s.get_tag('http.status_code') == '200'
        assert s.get_tag('http.method') == 'GET'
        # check distributed headers
        assert 123 == s.trace_id
        assert 456 == s.parent_id

    def test_not_distributed(self):
        # setup our test app
        @self.app.route('/hi/<name>')
        def hi(name):
            return 'hi %s' % name
        self._trace_app_not_distributed(self.tracer)

        # make a request
        headers = {'x-datadog-trace-id': '123',
                   'x-datadog-parent-id': '456'}
        resp = self.app.get('/hi/dougie', headers=headers)
        assert resp.status_int == 200
        assert compat.to_unicode(resp.body) == u'hi dougie'

        # validate it's traced
        spans = self.tracer.writer.pop()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == 'bottle.request'
        assert s.service == 'bottle-app'
        assert s.resource == 'GET /hi/<name>'
        assert s.get_tag('http.status_code') == '200'
        assert s.get_tag('http.method') == 'GET'
        # check distributed headers
        assert 123 != s.trace_id
        assert 456 != s.parent_id

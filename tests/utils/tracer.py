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

from oteltrace.internal.writer import AgentWriter
from oteltrace.tracer import Tracer


class DummyWriter(AgentWriter):
    """DummyWriter is a small fake writer used for tests. not thread-safe."""

    def __init__(self, *args, **kwargs):
        # original call
        super(DummyWriter, self).__init__(*args, **kwargs)

        # dummy components
        self.spans = []
        self.traces = []
        self.services = {}

    def write(self, spans=None, services=None):
        if spans:
            # the traces encoding expect a list of traces so we
            # put spans in a list like we do in the real execution path
            # with both encoders
            trace = [spans]
            self.spans += spans
            self.traces += trace

        if services:
            self.services.update(services)

    def pop(self):
        # dummy method
        s = self.spans
        self.spans = []
        return s

    def pop_traces(self):
        # dummy method
        traces = self.traces
        self.traces = []
        return traces

    def pop_services(self):
        # dummy method

        # Setting service info has been deprecated, we want to make sure nothing ever gets written here
        assert self.services == {}
        s = self.services
        self.services = {}
        return s


class DummyTracer(Tracer):
    """
    DummyTracer is a tracer which uses the DummyWriter by default
    """
    def __init__(self):
        super(DummyTracer, self).__init__()
        self._update_writer()

    def _update_writer(self):
        if hasattr(self, 'writer'):
            self.writer = DummyWriter(
                    filters=self.writer._filters,
                    priority_sampler=self.writer._priority_sampler,
            )
        else:
            self.writer = DummyWriter()

    def configure(self, *args, **kwargs):
        super(DummyTracer, self).configure(*args, **kwargs)
        # `.configure()` may reset the writer
        self._update_writer()

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

import abc
import threading
from oteltrace.vendor import six

from .logger import get_logger
from ..context import Context

log = get_logger(__name__)

try:
    from contextvars import ContextVar
    _OTEL_CONTEXTVAR = ContextVar('opentelemetry_contextvar', default=None)
    CONTEXTVARS_IS_AVAILABLE = True
except ImportError:
    CONTEXTVARS_IS_AVAILABLE = False


class BaseContextManager(six.with_metaclass(abc.ABCMeta)):
    def __init__(self, reset=True):
        if reset:
            self.reset()

    @abc.abstractmethod
    def _has_active_context(self):
        pass

    @abc.abstractmethod
    def set(self, ctx):
        pass

    @abc.abstractmethod
    def get(self):
        pass

    def reset(self):
        pass


class ThreadLocalContext(BaseContextManager):
    """
    ThreadLocalContext can be used as a tracer global reference to create
    a different ``Context`` for each thread. In synchronous tracer, this
    is required to prevent multiple threads sharing the same ``Context``
    in different executions.
    """
    def __init__(self, reset=True):
        # always initialize a new thread-local context holder
        super(ThreadLocalContext, self).__init__(reset=True)

    def _has_active_context(self):
        """
        Determine whether we have a currently active context for this thread

        :returns: Whether an active context exists
        :rtype: bool
        """
        ctx = getattr(self._locals, 'context', None)
        return ctx is not None

    def set(self, ctx):
        setattr(self._locals, 'context', ctx)

    def get(self):
        ctx = getattr(self._locals, 'context', None)
        if not ctx:
            # create a new Context if it's not available
            ctx = Context()
            self._locals.context = ctx

        return ctx

    def reset(self):
        self._locals = threading.local()


class ContextVarContextManager(BaseContextManager):
    """
    _ContextVarContext can be used in place of the ThreadLocalContext for Python
    3.7 and above to manage different ``Context`` objects for each thread and
    async task.
    """
    def _has_active_context(self):
        ctx = _OTEL_CONTEXTVAR.get()
        return ctx is not None

    def set(self, ctx):
        _OTEL_CONTEXTVAR.set(ctx)

    def get(self):
        ctx = _OTEL_CONTEXTVAR.get()
        if not ctx:
            ctx = Context()
            self.set(ctx)

        return ctx

    def reset(self):
        _OTEL_CONTEXTVAR.set(None)


if CONTEXTVARS_IS_AVAILABLE:
    DefaultContextManager = ContextVarContextManager
else:
    DefaultContextManager = ThreadLocalContext

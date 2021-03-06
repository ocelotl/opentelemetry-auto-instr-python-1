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
This integration provides the ``AsyncioContextProvider`` that follows the execution
flow of a ``Task``, making possible to trace asynchronous code built on top
of ``asyncio``. To trace asynchronous execution, you must::

    import asyncio
    from oteltrace import tracer
    from oteltrace.contrib.asyncio import context_provider

    # enable asyncio support
    tracer.configure(context_provider=context_provider)

    async def some_work():
        with tracer.trace('asyncio.some_work'):
            # do something

    # launch your coroutines as usual
    loop = asyncio.get_event_loop()
    loop.run_until_complete(some_work())
    loop.close()

If ``contextvars`` is available, we use the
:class:`oteltrace.provider.DefaultContextProvider`, otherwise we use the legacy
:class:`oteltrace.contrib.asyncio.provider.AsyncioContextProvider`.

In addition, helpers are provided to simplify how the tracing ``Context`` is
handled between scheduled coroutines and ``Future`` invoked in separated
threads:

    * ``set_call_context(task, ctx)``: attach the context to the given ``Task``
      so that it will be available from the ``tracer.get_call_context()``
    * ``ensure_future(coro_or_future, *, loop=None)``: wrapper for the
      ``asyncio.ensure_future`` that attaches the current context to a new
      ``Task`` instance
    * ``run_in_executor(loop, executor, func, *args)``: wrapper for the
      ``loop.run_in_executor`` that attaches the current context to the
      new thread so that the trace can be resumed regardless when
      it's executed
    * ``create_task(coro)``: creates a new asyncio ``Task`` that inherits
      the current active ``Context`` so that generated traces in the new task
      are attached to the main trace

A ``patch(asyncio=True)`` is available if you want to automatically use above
wrappers without changing your code. In that case, the patch method **must be
called before** importing stdlib functions.
"""
from ...utils.importlib import require_modules


required_modules = ['asyncio']

with require_modules(required_modules) as missing_modules:
    if not missing_modules:
        from .provider import AsyncioContextProvider
        from ...internal.context_manager import CONTEXTVARS_IS_AVAILABLE
        from ...provider import DefaultContextProvider

        if CONTEXTVARS_IS_AVAILABLE:
            context_provider = DefaultContextProvider()
        else:
            context_provider = AsyncioContextProvider()

        from .helpers import set_call_context, ensure_future, run_in_executor
        from .patch import patch

        __all__ = [
            'context_provider',
            'set_call_context',
            'ensure_future',
            'run_in_executor',
            'patch'
        ]

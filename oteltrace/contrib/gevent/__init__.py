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
To trace a request in a ``gevent`` environment, configure the tracer to use the greenlet
context provider, rather than the default one that relies on a thread-local storaging.

This allows the tracer to pick up a transaction exactly where it left off as greenlets
yield the context to another one.

The simplest way to trace a ``gevent`` application is to configure the tracer and
patch ``gevent`` **before importing** the library::

    # patch before importing gevent
    from oteltrace import patch, tracer
    patch(gevent=True)

    # use gevent as usual with or without the monkey module
    from gevent import monkey; monkey.patch_thread()

    def my_parent_function():
        with tracer.trace("web.request") as span:
            span.service = "web"
            gevent.spawn(worker_function)

    def worker_function():
        # then trace its child
        with tracer.trace("greenlet.call") as span:
            span.service = "greenlet"
            ...

            with tracer.trace("greenlet.child_call") as child:
                ...
"""
from ...utils.importlib import require_modules


required_modules = ['gevent']

with require_modules(required_modules) as missing_modules:
    if not missing_modules:
        from .provider import GeventContextProvider
        from .patch import patch, unpatch

        context_provider = GeventContextProvider()

        __all__ = [
            'patch',
            'unpatch',
            'context_provider',
        ]

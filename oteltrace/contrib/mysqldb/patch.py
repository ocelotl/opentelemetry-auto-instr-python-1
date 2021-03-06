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

# 3p
import MySQLdb

from oteltrace.vendor.wrapt import wrap_function_wrapper as _w

# project
from oteltrace import Pin
from oteltrace.contrib.dbapi import TracedConnection

from ...ext import net, db, AppTypes
from ...utils.wrappers import unwrap as _u

KWPOS_BY_TAG = {
    net.TARGET_HOST: ('host', 0),
    db.USER: ('user', 1),
    db.NAME: ('db', 3),
}


def patch():
    # patch only once
    if getattr(MySQLdb, '__opentelemetry_patch', False):
        return
    setattr(MySQLdb, '__opentelemetry_patch', True)

    # `Connection` and `connect` are aliases for
    # `Connect`; patch them too
    _w('MySQLdb', 'Connect', _connect)
    if hasattr(MySQLdb, 'Connection'):
        _w('MySQLdb', 'Connection', _connect)
    if hasattr(MySQLdb, 'connect'):
        _w('MySQLdb', 'connect', _connect)


def unpatch():
    if not getattr(MySQLdb, '__opentelemetry_patch', False):
        return
    setattr(MySQLdb, '__opentelemetry_patch', False)

    # unpatch MySQLdb
    _u(MySQLdb, 'Connect')
    if hasattr(MySQLdb, 'Connection'):
        _u(MySQLdb, 'Connection')
    if hasattr(MySQLdb, 'connect'):
        _u(MySQLdb, 'connect')


def _connect(func, instance, args, kwargs):
    conn = func(*args, **kwargs)
    return patch_conn(conn, *args, **kwargs)


def patch_conn(conn, *args, **kwargs):
    tags = {t: kwargs[k] if k in kwargs else args[p]
            for t, (k, p) in KWPOS_BY_TAG.items()
            if k in kwargs or len(args) > p}
    tags[net.TARGET_PORT] = conn.port
    pin = Pin(service='mysql', app='mysql', app_type=AppTypes.db, tags=tags)

    # grab the metadata from the conn
    wrapped = TracedConnection(conn, pin=pin)
    pin.onto(wrapped)
    return wrapped

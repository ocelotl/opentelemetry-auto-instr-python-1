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

import os

from .deprecation import deprecation


def get_env(integration, variable, default=None):
    """Retrieves environment variables value for the given integration. It must be used
    for consistency between integrations. The implementation is backward compatible
    with legacy nomenclature:
        * `OPENTELEMETRY_` is a legacy prefix with lower priority
        * `OTEL_` environment variables have the highest priority
        * the environment variable is built concatenating `integration` and `variable`
          arguments
        * return `default` otherwise
    """
    key = '{}_{}'.format(integration, variable).upper()
    legacy_env = 'OPENTELEMETRY_{}'.format(key)
    env = 'OTEL_{}'.format(key)

    value = os.getenv(env)
    legacy = os.getenv(legacy_env)
    if legacy:
        # Deprecation: `OPENTELEMETRY_` variables are deprecated
        deprecation(
            name='OPENTELEMETRY_',
            message='Use `OTEL_` prefix instead',
            version='1.0.0',
        )

    value = value or legacy
    return value if value else default


def deep_getattr(obj, attr_string, default=None):
    """
    Returns the attribute of `obj` at the dotted path given by `attr_string`
    If no such attribute is reachable, returns `default`

    >>> deep_getattr(cass, 'cluster')
    <cassandra.cluster.Cluster object at 0xa20c350

    >>> deep_getattr(cass, 'cluster.metadata.partitioner')
    u'org.apache.cassandra.dht.Murmur3Partitioner'

    >>> deep_getattr(cass, 'i.dont.exist', default='default')
    'default'
    """
    attrs = attr_string.split('.')
    for attr in attrs:
        try:
            obj = getattr(obj, attr)
        except AttributeError:
            return default

    return obj


def asbool(value):
    """Convert the given String to a boolean object. Accepted
    values are `True` and `1`."""
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    return value.lower() in ('true', '1')


def flatten_dict(d, sep='.', prefix=''):
    """
    Returns a normalized dict of depth 1 with keys in order of embedding

    """
    # adapted from https://stackoverflow.com/a/19647596
    return {
        prefix + sep + k if prefix else k: v
        for kk, vv in d.items()
        for k, v in flatten_dict(vv, sep, kk).items()
    } if isinstance(d, dict) else {prefix: d}

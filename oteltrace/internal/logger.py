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

import collections
import logging

from ..utils.formats import get_env


def get_logger(name):
    """
    Retrieve or create a ``OtelLogger`` instance.

    This function mirrors the behavior of `logging.getLogger`.

    If no logger with the provided name has been fetched before then
    a new one is created.

    If a previous logger has been created then it is returned.

    DEV: We do not want to mess with `logging.setLoggerClass()`
         That will totally mess with the user's loggers, we want
         just our own, selective loggers to be OtelLoggers

    :param name: The name of the logger to fetch or create
    :type name: str
    :return: The logger instance
    :rtype: ``OtelLogger``
    """
    # DEV: `logging.Logger.manager` refers to the single root `logging.Manager` instance
    #   https://github.com/python/cpython/blob/48769a28ad6ef4183508951fa6a378531ace26a4/Lib/logging/__init__.py#L1824-L1826  # noqa
    manager = logging.Logger.manager

    # If the logger does not exist yet, create it
    # DEV: `Manager.loggerDict` is a dict mapping logger name to logger
    # DEV: This is a simplified version of `logging.Manager.getLogger`
    #   https://github.com/python/cpython/blob/48769a28ad6ef4183508951fa6a378531ace26a4/Lib/logging/__init__.py#L1221-L1253  # noqa
    if name not in manager.loggerDict:
        manager.loggerDict[name] = OtelLogger(name=name)

    # Get our logger
    logger = manager.loggerDict[name]

    # If this log manager has a `_fixupParents` method then call it on our logger
    # DEV: This helper is used to ensure our logger has an appropriate `Logger.parent` set,
    #      without this then we cannot take advantage of the root loggers handlers
    #   https://github.com/python/cpython/blob/7c7839329c2c66d051960ab1df096aed1cc9343e/Lib/logging/__init__.py#L1272-L1294  # noqa
    # DEV: `_fixupParents` has been around for awhile, but add the `hasattr` guard... just in case.
    if hasattr(manager, '_fixupParents'):
        manager._fixupParents(logger)

    # Return out logger
    return logger


class OtelLogger(logging.Logger):
    """
    Custom rate limited logger used by ``oteltrace``

    This logger class is used to rate limit the output of
    log messages from within the ``oteltrace`` package.
    """
    __slots__ = ('buckets', 'rate_limit')

    # Named tuple used for keeping track of a log lines current time bucket and the number of log lines skipped
    LoggingBucket = collections.namedtuple('LoggingBucket', ('bucket', 'skipped'))

    def __init__(self, *args, **kwargs):
        """Constructor for ``OtelLogger``"""
        super(OtelLogger, self).__init__(*args, **kwargs)

        # Dict to keep track of the current time bucket per name/level/pathname/lineno
        self.buckets = collections.defaultdict(lambda: OtelLogger.LoggingBucket(0, 0))

        # Allow 1 log record per name/level/pathname/lineno every 60 seconds by default
        # Allow configuring via `OTEL_LOGGING_RATE_LIMIT`
        # DEV: `OTEL_LOGGING_RATE_LIMIT=0` means to disable all rate limiting
        self.rate_limit = int(get_env('logging', 'rate_limit', default=60))

    def handle(self, record):
        """
        Function used to call the handlers for a log line.

        This implementation will first determine if this log line should
        be logged or rate limited, and then call the base ``logging.Logger.handle``
        function if it should be logged

        DEV: This method has all of it's code inlined to reduce on functions calls

        :param record: The log record being logged
        :type record: ``logging.LogRecord``
        """
        # If rate limiting has been disabled (`OTEL_LOGGING_RATE_LIMIT=0`) then apply no rate limit
        if not self.rate_limit:
            super(OtelLogger, self).handle(record)
            return

        # Allow 1 log record by name/level/pathname/lineno every X seconds
        # DEV: current unix time / rate (e.g. 300 seconds) = time bucket
        #      int(1546615098.8404942 / 300) = 515538
        # DEV: LogRecord `created` is a unix timestamp/float
        # DEV: LogRecord has `levelname` and `levelno`, we want `levelno` e.g. `logging.DEBUG = 10`
        current_bucket = int(record.created / self.rate_limit)

        # Limit based on logger name, record level, filename, and line number
        #   ('oteltrace.writer', 'DEBUG', '../site-packages/oteltrace/writer.py', 137)
        # This way each unique log message can get logged at least once per time period
        # DEV: LogRecord has `levelname` and `levelno`, we want `levelno` e.g. `logging.DEBUG = 10`
        key = (record.name, record.levelno, record.pathname, record.lineno)

        # Only log this message if the time bucket has changed from the previous time we ran
        logging_bucket = self.buckets[key]
        if logging_bucket.bucket != current_bucket:
            # Append count of skipped messages if we have skipped some since our last logging
            if logging_bucket.skipped:
                record.msg = '{}, {} additional messages skipped'.format(record.msg, logging_bucket.skipped)

            # Reset our bucket
            self.buckets[key] = OtelLogger.LoggingBucket(current_bucket, 0)

            # Call the base handle to actually log this record
            super(OtelLogger, self).handle(record)
        else:
            # Increment the count of records we have skipped
            # DEV: `self.buckets[key]` is a tuple which is immutable so recreate instead
            self.buckets[key] = OtelLogger.LoggingBucket(logging_bucket.bucket, logging_bucket.skipped + 1)

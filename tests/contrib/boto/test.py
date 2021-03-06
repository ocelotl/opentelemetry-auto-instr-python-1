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
import boto.ec2
import boto.s3
import boto.awslambda
import boto.sqs
import boto.kms
import boto.sts
import boto.elasticache
from moto import mock_s3, mock_ec2, mock_lambda, mock_sts

# project
from oteltrace import Pin
from oteltrace.constants import ANALYTICS_SAMPLE_RATE_KEY
from oteltrace.contrib.boto.patch import patch, unpatch
from oteltrace.ext import http

# testing
from unittest import skipUnless
from ...base import BaseTracerTestCase


class BotoTest(BaseTracerTestCase):
    """Botocore integration testsuite"""

    TEST_SERVICE = 'test-boto-tracing'

    def setUp(self):
        super(BotoTest, self).setUp()
        patch()

    @mock_ec2
    def test_ec2_client(self):
        ec2 = boto.ec2.connect_to_region('us-west-2')
        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(ec2)

        ec2.get_all_instances()
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.get_tag('aws.operation'), 'DescribeInstances')
        self.assertEqual(span.get_tag(http.STATUS_CODE), '200')
        self.assertEqual(span.get_tag(http.METHOD), 'POST')
        self.assertEqual(span.get_tag('aws.region'), 'us-west-2')
        self.assertIsNone(span.get_metric(ANALYTICS_SAMPLE_RATE_KEY))

        # Create an instance
        ec2.run_instances(21)
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.get_tag('aws.operation'), 'RunInstances')
        self.assertEqual(span.get_tag(http.STATUS_CODE), '200')
        self.assertEqual(span.get_tag(http.METHOD), 'POST')
        self.assertEqual(span.get_tag('aws.region'), 'us-west-2')
        self.assertEqual(span.service, 'test-boto-tracing.ec2')
        self.assertEqual(span.resource, 'ec2.runinstances')
        self.assertEqual(span.name, 'ec2.command')
        self.assertEqual(span.span_type, 'boto')

    @mock_ec2
    def test_analytics_enabled_with_rate(self):
        with self.override_config(
                'boto',
                dict(analytics_enabled=True, analytics_sample_rate=0.5)
        ):
            ec2 = boto.ec2.connect_to_region('us-west-2')
            writer = self.tracer.writer
            Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(ec2)

            ec2.get_all_instances()

        spans = writer.pop()
        assert spans
        span = spans[0]
        self.assertEqual(span.get_metric(ANALYTICS_SAMPLE_RATE_KEY), 0.5)

    @mock_ec2
    def test_analytics_enabled_without_rate(self):
        with self.override_config(
                'boto',
                dict(analytics_enabled=True)
        ):
            ec2 = boto.ec2.connect_to_region('us-west-2')
            writer = self.tracer.writer
            Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(ec2)

            ec2.get_all_instances()

        spans = writer.pop()
        assert spans
        span = spans[0]
        self.assertEqual(span.get_metric(ANALYTICS_SAMPLE_RATE_KEY), 1.0)

    @mock_s3
    def test_s3_client(self):
        s3 = boto.s3.connect_to_region('us-east-1')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(s3)

        s3.get_all_buckets()
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.get_tag(http.STATUS_CODE), '200')
        self.assertEqual(span.get_tag(http.METHOD), 'GET')
        self.assertEqual(span.get_tag('aws.operation'), 'get_all_buckets')

        # Create a bucket command
        s3.create_bucket('cheese')
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.get_tag(http.STATUS_CODE), '200')
        self.assertEqual(span.get_tag(http.METHOD), 'PUT')
        self.assertEqual(span.get_tag('path'), '/')
        self.assertEqual(span.get_tag('aws.operation'), 'create_bucket')

        # Get the created bucket
        s3.get_bucket('cheese')
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.get_tag(http.STATUS_CODE), '200')
        self.assertEqual(span.get_tag(http.METHOD), 'HEAD')
        self.assertEqual(span.get_tag('aws.operation'), 'head_bucket')
        self.assertEqual(span.service, 'test-boto-tracing.s3')
        self.assertEqual(span.resource, 's3.head')
        self.assertEqual(span.name, 's3.command')

        # Checking for resource incase of error
        try:
            s3.get_bucket('big_bucket')
        except Exception:
            spans = writer.pop()
            assert spans
            span = spans[0]
            self.assertEqual(span.resource, 's3.head')

    @mock_s3
    def test_s3_put(self):
        s3 = boto.s3.connect_to_region('us-east-1')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(s3)
        s3.create_bucket('mybucket')
        bucket = s3.get_bucket('mybucket')
        k = boto.s3.key.Key(bucket)
        k.key = 'foo'
        k.set_contents_from_string('bar')

        spans = writer.pop()
        assert spans
        # create bucket
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].get_tag('aws.operation'), 'create_bucket')
        self.assertEqual(spans[0].get_tag(http.STATUS_CODE), '200')
        self.assertEqual(spans[0].service, 'test-boto-tracing.s3')
        self.assertEqual(spans[0].resource, 's3.put')
        # get bucket
        self.assertEqual(spans[1].get_tag('aws.operation'), 'head_bucket')
        self.assertEqual(spans[1].resource, 's3.head')
        # put object
        self.assertEqual(spans[2].get_tag('aws.operation'), '_send_file_internal')
        self.assertEqual(spans[2].resource, 's3.put')

    @mock_lambda
    def test_unpatch(self):
        lamb = boto.awslambda.connect_to_region('us-east-2')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(lamb)
        unpatch()

        # multiple calls
        lamb.list_functions()
        spans = writer.pop()
        assert not spans, spans

    @mock_s3
    def test_double_patch(self):
        s3 = boto.s3.connect_to_region('us-east-1')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(s3)

        patch()
        patch()

        # Get the created bucket
        s3.create_bucket('cheese')
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 1)

    @mock_lambda
    def test_lambda_client(self):
        lamb = boto.awslambda.connect_to_region('us-east-2')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(lamb)

        # multiple calls
        lamb.list_functions()
        lamb.list_functions()

        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 2)
        span = spans[0]
        self.assertEqual(span.get_tag(http.STATUS_CODE), '200')
        self.assertEqual(span.get_tag(http.METHOD), 'GET')
        self.assertEqual(span.get_tag('aws.region'), 'us-east-2')
        self.assertEqual(span.get_tag('aws.operation'), 'list_functions')
        self.assertEqual(span.service, 'test-boto-tracing.lambda')
        self.assertEqual(span.resource, 'lambda.get')

    @mock_sts
    def test_sts_client(self):
        sts = boto.sts.connect_to_region('us-west-2')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(sts)

        sts.get_federation_token(12, duration=10)

        spans = writer.pop()
        assert spans
        span = spans[0]
        self.assertEqual(span.get_tag('aws.region'), 'us-west-2')
        self.assertEqual(span.get_tag('aws.operation'), 'GetFederationToken')
        self.assertEqual(span.service, 'test-boto-tracing.sts')
        self.assertEqual(span.resource, 'sts.getfederationtoken')

        # checking for protection on sts against security leak
        self.assertIsNone(span.get_tag('args.path'))

    @skipUnless(
        False,
        ('Test to reproduce the case where args sent to patched function are None,'
         'can\'t be mocked: needs AWS crendentials'),
    )
    def test_elasticache_client(self):
        elasticache = boto.elasticache.connect_to_region('us-west-2')

        writer = self.tracer.writer
        Pin(service=self.TEST_SERVICE, tracer=self.tracer).onto(elasticache)

        elasticache.describe_cache_clusters()

        spans = writer.pop()
        assert spans
        span = spans[0]
        self.assertEqual(span.get_tag('aws.region'), 'us-west-2')
        self.assertEqual(span.service, 'test-boto-tracing.elasticache')
        self.assertEqual(span.resource, 'elasticache')

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

from oteltrace import patch_all
patch_all()

from oteltrace import tracer  # noqa: E402
from oteltrace.api_otel_exporter import APIOtel  # noqa: E402
from opentelemetry.ext.jaeger import JaegerSpanExporter  # noqa: E402
from oteltrace.propagation.w3c import W3CHTTPPropagator  # noqa: E402

# create Jaeger Exporter
jaeger_exporter = JaegerSpanExporter(
    service_name='example2',
)

# configure tracer with Jaeger exporter and w3c as http propagator
tracer.configure(
    api=APIOtel(exporter=jaeger_exporter),
    http_propagator=W3CHTTPPropagator,
)

# same code of example1
from flask import Flask  # noqa: E402
import requests  # noqa: E402

app = Flask(__name__)


@app.route('/')
def hello_world():
    r1 = requests.get(url='http://localhost:8055/word1')
    r2 = requests.get(url='http://localhost:8055/word2')
    return r1.text + ' ' + r2.text


@app.route('/word1')
def hello_word1():
    r1 = requests.get(url='http://localhost:8055/word1/details')
    return 'Welcome ' + r1.text


@app.route('/word1/details')
def hello_word1_details():
    return 'to'


@app.route('/word2')
def hello_word2():
    return 'OpenTelemetry'


app.run(host='127.0.0.1', port=8055)

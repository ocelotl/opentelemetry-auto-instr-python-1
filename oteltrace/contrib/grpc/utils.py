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

def parse_method_path(method_path):
    """ Returns (package, service, method) tuple from parsing method path """
    # unpack method path based on "/{package}.{service}/{method}"
    # first remove leading "/" as unnecessary
    package_service, method_name = method_path.lstrip('/').rsplit('/', 1)

    # {package} is optional
    package_service = package_service.rsplit('.', 1)
    if len(package_service) == 2:
        return package_service[0], package_service[1], method_name

    return None, package_service[0], method_name

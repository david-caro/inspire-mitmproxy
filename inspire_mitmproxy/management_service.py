# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE-MITMPROXY.
# Copyright (C) 2018 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""Service used to orchestrate fake services."""

from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from os import environ, getcwd
from pathlib import Path
from typing import Dict, List, Optional, Union, cast
from urllib.parse import urlparse

from autosemver import get_current_version
from mitmproxy.net.http.status_codes import RESPONSES

from .base_service import BaseService
from .errors import InvalidRequest, RequestNotHandledInService


class ManagementService(BaseService):
    SERVICE_HOSTS = ['mitm-manager.local']

    def __init__(self, services: List[BaseService]) -> None:
        self.services = services
        self.config = {
            'active_scenario': None,
        }

    def process_request(self, request: dict) -> dict:
        parsed_url = urlparse(request['uri'])
        path = parsed_url.path
        method = request['method']

        if path == '/services' and method == 'GET':
            return self.build_response(200, self.get_services())
        elif path == '/scenarios' and method == 'GET':
            return self.build_response(200, self.get_scenarios())
        elif path == '/config' and method == 'GET':
            return self.build_response(200, self.get_config())
        elif path == '/config' and method == 'PUT':
            return self.build_response(204, self.put_config(request))
        elif path == '/config' and method == 'POST':
            return self.build_response(201, self.post_config(request))

        raise RequestNotHandledInService(self, request)

    def get_services(self) -> dict:
        return {
            idx: {
                'class': type(service).__name__,
                'service_hosts': service.SERVICE_HOSTS,
            }
            for idx, service in enumerate([cast(BaseService, self)] + self.services)
        }

    def get_scenarios(self) -> dict:
        path = Path(environ.get('SCENARIOS_PATH', './scenarios/'))
        response: Dict[str, Dict[str, Dict[str, List[str]]]] = {
            scenario.name: {
                'responses': {
                    service.name: [
                        response_file.name for response_file in sorted(service.iterdir())
                        if response_file.is_file() and response_file.suffix == '.yaml'
                    ]
                    for service in scenario.iterdir() if service.is_dir()
                }
            }
            for scenario in path.iterdir() if scenario.is_dir()
        }

        return response

    def get_config(self) -> dict:
        return self.config

    def put_config(self, request: dict):
        try:
            config_update = json_loads(request['body'])
            self.config.update(config_update)
        except (JSONDecodeError, ValueError):
            raise InvalidRequest(self, request)

    def post_config(self, request: dict):
        try:
            self.config = json_loads(request['body'])
        except (JSONDecodeError):
            raise InvalidRequest(self, request)

    def build_response(self, code: int, json_message: Optional[Union[dict, list]]) -> dict:
        if json_message:
            body = json_dumps(json_message, indent=2)
        else:
            body = ''

        return {
            'status': {
                'message': RESPONSES[code],
                'code': code,
            },
            'body': body,
            'headers': {
                'Content-Type': ['application/json'],
                'Server': ['inspire-mitmproxy/' + get_current_version(getcwd())]
            }
        }

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

"""Dispatcher forwards requests to Services."""

from mitmproxy.http import HTTPFlow, HTTPResponse
from typing import List

from .base_service import BaseService
from .errors import NoServicesForRequest
from .management_service import ManagementService
from .translator import request_to_dict, dict_to_response


class Dispatcher:
    def __init__(self, services: List[BaseService]):
        mgmt_service = ManagementService(services)
        self.services = [mgmt_service] + services

    def process_request(self, request: dict) -> dict:
        """Perform operations and give response."""
        for service in self.services:
            if service.handles_request(request):
                return service.process_request(request)
        raise NoServicesForRequest(request)

    def request(self, flow: HTTPFlow):
        """MITMProxy addon event interface for outgoing request."""
        try:
            request = request_to_dict(flow.request)
            response = dict_to_response(self.process_request(request))
            flow.response = response
        except NoServicesForRequest as e:
            flow.response = HTTPResponse.make(
                status_code=404,
                content=str(e),
                headers={'Content-Type': 'text/plain'}
            )
        except Exception as e:
            flow.response = HTTPResponse.make(
                status_code=500,
                content=str(e),
                headers={'Content-Type': 'text/plain'}
            )
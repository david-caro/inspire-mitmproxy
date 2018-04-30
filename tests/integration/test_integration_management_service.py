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

"""Tests for the ManagementService"""

from json import loads as json_loads
from os import environ
from typing import List

from pytest import fixture

from inspire_mitmproxy.base_service import BaseService
from inspire_mitmproxy.dispatcher import Dispatcher


@fixture(scope='function')
def dispatcher() -> Dispatcher:
    class TestService(BaseService):
        SERVICE_HOSTS = ['test-service.local']

    services: List[BaseService] = [TestService()]

    return Dispatcher(services)


@fixture
def fake_scenarios_dir(tmpdir) -> str:
    scenarios = tmpdir.mkdir('scenarios')

    scenario1 = scenarios.mkdir('scenario1')
    scenario2 = scenarios.mkdir('scenario2')

    scenario1_serviceA = scenario1.mkdir('A')
    scenario2_serviceA = scenario2.mkdir('A')
    scenario2_serviceB = scenario2.mkdir('B')

    scenario1_serviceA.join('1.yaml').ensure()
    scenario1_serviceA.join('2.yaml').ensure()

    scenario2_serviceA.join('1.yaml').ensure()
    scenario2_serviceB.join('1.yaml').ensure()
    scenario2_serviceB.join('2.yaml').ensure()
    scenario2_serviceB.join('3.yaml').ensure()

    environ['SCENARIOS_PATH'] = scenarios.strpath
    return scenarios.strpath


def test_management_service_get_services(dispatcher):
    result = dispatcher.process_request({
        'method': 'GET',
        'uri': 'http://mitm-manager.local/services',
        'body': None,
        'headers': {
            'Host': ['mitm-manager.local'],
            'Accept': ['application/json'],
        }
    })

    expected = {
        '0': {
            'class': 'ManagementService',
            'service_hosts': ['mitm-manager.local']
        },
        '1': {
            'class': 'TestService',
            'service_hosts': ['test-service.local']
        }
    }

    assert result['status'] == {'code': 200, 'message': 'OK'}
    assert json_loads(result['body']) == expected


def test_management_service_get_scenarios(fake_scenarios_dir, dispatcher):
    result = dispatcher.process_request({
        'method': 'GET',
        'uri': 'http://mitm-manager.local/scenarios',
        'body': None,
        'headers': {
            'Host': ['mitm-manager.local'],
            'Accept': ['application/json'],
        }
    })

    expected = {
        'scenario1': {
            'responses': {
                'A': ['1.yaml', '2.yaml'],
            }
        },
        'scenario2': {
            'responses': {
                'A': ['1.yaml'],
                'B': ['1.yaml', '2.yaml', '3.yaml'],
            }
        },
    }

    assert result['status'] == {'code': 200, 'message': 'OK'}
    assert json_loads(result['body']) == expected


def test_management_service_get_config(dispatcher):
    result = dispatcher.process_request({
        'method': 'GET',
        'uri': 'http://mitm-manager.local/config',
        'body': None,
        'headers': {
            'Host': ['mitm-manager.local'],
            'Accept': ['application/json'],
        }
    })

    expected = {
        'active_scenario': None,
    }

    assert result['status'] == {'code': 200, 'message': 'OK'}
    assert json_loads(result['body']) == expected


def test_management_service_post_and_put_config(dispatcher):
    post_req = dispatcher.process_request({
        'method': 'POST',
        'uri': 'http://mitm-manager.local/config',
        'body': '{"active_scenario": "a scenario", "another": "value"}',
        'headers': {
            'Host': ['mitm-manager.local'],
            'Accept': ['application/json'],
        }
    })

    assert post_req['status'] == {'code': 201, 'message': 'Created'}

    put_req = dispatcher.process_request({
        'method': 'PUT',
        'uri': 'http://mitm-manager.local/config',
        'body': '{"active_scenario": "another scenario"}',
        'headers': {
            'Host': ['mitm-manager.local'],
            'Accept': ['application/json'],
        }
    })

    assert put_req['status'] == {'code': 204, 'message': 'No Content'}

    result = dispatcher.process_request({
        'method': 'GET',
        'uri': 'http://mitm-manager.local/config',
        'body': None,
        'headers': {
            'Host': ['mitm-manager.local'],
            'Accept': ['application/json'],
        }
    })

    expected = {
        'active_scenario': 'another scenario',
        'another': 'value',
    }

    assert result['status'] == {'code': 200, 'message': 'OK'}
    assert json_loads(result['body']) == expected

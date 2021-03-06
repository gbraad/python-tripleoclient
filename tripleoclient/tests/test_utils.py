#   Copyright 2015 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

from uuid import uuid4

import mock
import os.path
import tempfile
from unittest import TestCase

from tripleoclient import exceptions
from tripleoclient.tests.v1.utils import (
    generate_overcloud_passwords_mock)
from tripleoclient import utils


class TestPasswordsUtil(TestCase):

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("passlib.utils.generate_password",
                return_value="PASSWORD")
    def test_generate_passwords(self, generate_password_mock, isfile_mock):

        mock_open = mock.mock_open()

        with mock.patch('six.moves.builtins.open', mock_open):
            passwords = utils.generate_overcloud_passwords(
                create_password_file=True)
        mock_calls = [
            mock.call('NEUTRON_METADATA_PROXY_SHARED_SECRET=PASSWORD\n'),
            mock.call('OVERCLOUD_ADMIN_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_ADMIN_TOKEN=PASSWORD\n'),
            mock.call('OVERCLOUD_AODH_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_CEILOMETER_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_CEILOMETER_SECRET=PASSWORD\n'),
            mock.call('OVERCLOUD_CINDER_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_DEMO_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_GLANCE_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_GNOCCHI_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_HAPROXY_STATS_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_HEAT_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_HEAT_STACK_DOMAIN_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_IRONIC_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_MYSQL_CLUSTERCHECK_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_NEUTRON_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_NOVA_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_RABBITMQ_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_REDIS_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_SAHARA_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_SWIFT_HASH=PASSWORD\n'),
            mock.call('OVERCLOUD_SWIFT_PASSWORD=PASSWORD\n'),
            mock.call('OVERCLOUD_TROVE_PASSWORD=PASSWORD\n'),
        ]
        self.assertEqual(sorted(mock_open().write.mock_calls), mock_calls)
        self.assertEqual(generate_password_mock.call_count, len(mock_calls))

        self.assertEqual(len(passwords), len(mock_calls))

    def test_generate_passwords_update(self):

        mock_open = mock.mock_open()

        with mock.patch('six.moves.builtins.open', mock_open):
            with self.assertRaises(exceptions.PasswordFileNotFound):
                utils.generate_overcloud_passwords()

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch("passlib.utils.generate_password",
                return_value="PASSWORD")
    def test_load_passwords(self, generate_password_mock, isfile_mock):
        PASSWORDS = [
            'OVERCLOUD_ADMIN_PASSWORD=PASSWORD\n',
            'OVERCLOUD_ADMIN_TOKEN=PASSWORD\n',
            'OVERCLOUD_AODH_PASSWORD=PASSWORD\n',
            'OVERCLOUD_CEILOMETER_PASSWORD=PASSWORD\n',
            'OVERCLOUD_CEILOMETER_SECRET=PASSWORD\n',
            'OVERCLOUD_CINDER_PASSWORD=PASSWORD\n',
            'OVERCLOUD_DEMO_PASSWORD=PASSWORD\n',
            'OVERCLOUD_GLANCE_PASSWORD=PASSWORD\n',
            'OVERCLOUD_GNOCCHI_PASSWORD=PASSWORD\n',
            'OVERCLOUD_HAPROXY_STATS_PASSWORD=PASSWORD\n',
            'OVERCLOUD_HEAT_PASSWORD=PASSWORD\n',
            'OVERCLOUD_HEAT_STACK_DOMAIN_PASSWORD=PASSWORD\n',
            'OVERCLOUD_IRONIC_PASSWORD=PASSWORD\n',
            'OVERCLOUD_MYSQL_CLUSTERCHECK_PASSWORD=PASSWORD\n',
            'OVERCLOUD_NEUTRON_PASSWORD=PASSWORD\n',
            'OVERCLOUD_NOVA_PASSWORD=PASSWORD\n',
            'OVERCLOUD_RABBITMQ_PASSWORD=PASSWORD\n',
            'OVERCLOUD_REDIS_PASSWORD=PASSWORD\n',
            'OVERCLOUD_SAHARA_PASSWORD=PASSWORD\n',
            'OVERCLOUD_SWIFT_HASH=PASSWORD\n',
            'OVERCLOUD_SWIFT_PASSWORD=PASSWORD\n',
            'OVERCLOUD_TROVE_PASSWORD=PASSWORD\n',
            'NEUTRON_METADATA_PROXY_SHARED_SECRET=PASSWORD\n',
        ]

        mock_open = mock.mock_open(read_data=''.join(PASSWORDS))
        mock_open.return_value.__iter__ = lambda self: self
        mock_open.return_value.__next__ = lambda self: self.readline()

        with mock.patch('six.moves.builtins.open', mock_open):
            passwords = utils.generate_overcloud_passwords()

        generate_password_mock.assert_not_called()
        self.assertEqual(len(passwords), len(PASSWORDS))
        for name in utils._PASSWORD_NAMES:
            self.assertEqual('PASSWORD', passwords[name])


class TestCheckHypervisorUtil(TestCase):
    def test_check_hypervisor_stats(self):

        mock_compute = mock.Mock()
        mock_stats = mock.Mock()

        return_values = [
            {'count': 0, 'memory_mb': 0, 'vcpus': 0},
            {'count': 1, 'memory_mb': 1, 'vcpus': 1},
        ]

        mock_stats.to_dict.side_effect = return_values
        mock_compute.hypervisors.statistics.return_value = mock_stats

        stats = utils.check_hypervisor_stats(
            mock_compute, nodes=1, memory=1, vcpu=1)

        self.assertEqual(stats, None)
        self.assertEqual(mock_stats.to_dict.call_count, 1)

        stats = utils.check_hypervisor_stats(
            mock_compute, nodes=1, memory=1, vcpu=1)
        self.assertEqual(stats, return_values[-1])
        self.assertEqual(mock_stats.to_dict.call_count, 2)


class TestWaitForStackUtil(TestCase):
    def setUp(self):
        self.mock_orchestration = mock.Mock()

    def mock_event(self, resource_name, id, resource_status_reason,
                   resource_status, event_time):
        e = mock.Mock()
        e.resource_name = resource_name
        e.id = id
        e.resource_status_reason = resource_status_reason
        e.resource_status = resource_status
        e.event_time = event_time
        return e

    @mock.patch("heatclient.common.event_utils.get_events")
    @mock.patch('time.sleep', return_value=None)
    def test_wait_for_stack_ready(self, sleep_mock, mock_el):
        stack = mock.Mock()
        stack.stack_name = 'stack'
        stack.stack_status = "CREATE_COMPLETE"
        self.mock_orchestration.stacks.get.return_value = stack

        complete = utils.wait_for_stack_ready(self.mock_orchestration, 'stack')
        self.assertTrue(complete)
        sleep_mock.assert_not_called()

    def test_wait_for_stack_ready_no_stack(self):
        self.mock_orchestration.stacks.get.return_value = None

        complete = utils.wait_for_stack_ready(self.mock_orchestration, 'stack')

        self.assertFalse(complete)

    @mock.patch("heatclient.common.event_utils.get_events")
    @mock.patch('time.sleep', return_value=None)
    def test_wait_for_stack_ready_failed(self, sleep_mock, mock_el):
        stack = mock.Mock()
        stack.stack_name = 'stack'
        stack.stack_status = "CREATE_FAILED"
        self.mock_orchestration.stacks.get.return_value = stack

        complete = utils.wait_for_stack_ready(self.mock_orchestration, 'stack')

        self.assertFalse(complete)

        sleep_mock.assert_not_called()

    @mock.patch("heatclient.common.event_utils.get_events")
    @mock.patch('time.sleep', return_value=None)
    def test_wait_for_stack_in_progress(self, sleep_mock, mock_el):

        mock_el.side_effect = [[
            self.mock_event('stack', 'aaa', 'Stack CREATE started',
                            'CREATE_IN_PROGRESS', '2015-10-14T02:25:21Z'),
            self.mock_event('thing', 'bbb', 'state changed',
                            'CREATE_IN_PROGRESS', '2015-10-14T02:25:21Z'),
        ], [
            self.mock_event('thing', 'ccc', 'state changed',
                            'CREATE_COMPLETE', '2015-10-14T02:25:43Z'),
            self.mock_event('stack', 'ddd',
                            'Stack CREATE completed successfully',
                            'CREATE_COMPLETE', '2015-10-14T02:25:43Z'),
        ], [], []]

        stack = mock.Mock()
        stack.stack_name = 'stack'
        stack.stack_status = 'CREATE_IN_PROGRESS'
        complete_stack = mock.Mock()
        complete_stack.stack_name = 'stack'
        complete_stack.stack_status = 'CREATE_COMPLETE'
        self.mock_orchestration.stacks.get.side_effect = [
            stack, stack, stack, complete_stack]

        utils.wait_for_stack_ready(self.mock_orchestration, 'stack')

        self.assertEqual(2, sleep_mock.call_count)

    def test_create_environment_file(self):

        json_file_path = "env.json"

        mock_open = mock.mock_open()

        with mock.patch('six.moves.builtins.open', mock_open):
            with mock.patch('json.dumps', return_value="JSON"):
                utils.create_environment_file(path=json_file_path)

                mock_open.assert_called_with('env.json', 'w+')

        mock_open().write.assert_called_with('JSON')

    @mock.patch('tripleoclient.utils.wait_for_provision_state')
    def test_set_nodes_state(self, wait_for_state_mock):

        wait_for_state_mock.return_value = True
        bm_client = mock.Mock()

        # One node already deployed, one in the manageable state after
        # introspection.
        nodes = [
            mock.Mock(uuid="ABCDEFGH", provision_state="active"),
            mock.Mock(uuid="IJKLMNOP", provision_state="manageable")
        ]

        skipped_states = ('active', 'available')
        uuids = list(utils.set_nodes_state(bm_client, nodes, 'provide',
                                           'available', skipped_states))

        bm_client.node.set_provision_state.assert_has_calls([
            mock.call('IJKLMNOP', 'provide'),
        ])

        self.assertEqual(uuids, ['IJKLMNOP', ])

    @mock.patch("subprocess.Popen")
    def test_get_hiera_key(self, mock_popen):

        process_mock = mock.Mock()
        process_mock.communicate.return_value = ["pa$$word", ""]
        mock_popen.return_value = process_mock

        value = utils.get_hiera_key('password_name')

        self.assertEqual(value, "pa$$word")

    @mock.patch("six.moves.configparser")
    @mock.patch("os.path.exists")
    def test_get_config_value(self, mock_path_exists, mock_config_parser):

        mock_path_exists.return_value = True
        mock_config_parser.ConfigParser().get.return_value = "pa$$word"

        value = utils.get_config_value('section', 'password_name')

        self.assertEqual(value, "pa$$word")

    @mock.patch("six.moves.configparser")
    @mock.patch("os.path.exists")
    def test_get_config_value_no_file(self, mock_path_exists,
                                      mock_config_parser):

        mock_path_exists.return_value = False
        self.assertRaises(exceptions.PasswordFileNotFound,
                          utils.get_config_value, 'section',
                          'password_name')

    def test_wait_for_provision_state(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = mock.Mock(
            provision_state="available", last_error=None)

        utils.wait_for_provision_state(baremetal_client, 'UUID', "available")

    def test_wait_for_provision_state_not_found(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = None

        utils.wait_for_provision_state(baremetal_client, 'UUID', "available")

    def test_wait_for_provision_state_timeout(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = mock.Mock(
            provision_state="not what we want", last_error=None)

        with self.assertRaises(exceptions.Timeout):
            utils.wait_for_provision_state(baremetal_client, 'UUID',
                                           "available", loops=1, sleep=0.01)

    def test_wait_for_provision_state_fail(self):

        baremetal_client = mock.Mock()

        baremetal_client.node.get.return_value = mock.Mock(
            provision_state="enroll",
            last_error="node on fire; returning to previous state.")

        with self.assertRaises(exceptions.StateTransitionFailed):
            utils.wait_for_provision_state(baremetal_client, 'UUID',
                                           "available", loops=1, sleep=0.01)

    @mock.patch('subprocess.check_call')
    @mock.patch('os.path.exists')
    def test_remove_known_hosts(self, mock_exists, mock_check_call):

        mock_exists.return_value = True

        utils.remove_known_hosts('192.168.0.1')
        known_hosts = os.path.expanduser("~/.ssh/known_hosts")

        mock_check_call.assert_called_with(
            ['ssh-keygen', '-R', '192.168.0.1', '-f', known_hosts])

    @mock.patch('subprocess.check_call')
    @mock.patch('os.path.exists')
    def test_remove_known_hosts_no_file(self, mock_exists, mock_check_call):

        mock_exists.return_value = False

        utils.remove_known_hosts('192.168.0.1')

        mock_check_call.assert_not_called()

    def test_empty_file_checksum(self):
        # Used a NamedTemporaryFile since it's deleted when the file is closed.
        with tempfile.NamedTemporaryFile() as empty_temp_file:
            self.assertEqual(utils.file_checksum(empty_temp_file.name),
                             'd41d8cd98f00b204e9800998ecf8427e')

    def test_non_empty_file_checksum(self):
        # Used a NamedTemporaryFile since it's deleted when the file is closed.
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b'foo')
            temp_file.flush()

            self.assertEqual(utils.file_checksum(temp_file.name),
                             'acbd18db4cc2f85cedef654fccc4a4d8')

    def test_shouldnt_checksum_open_special_files(self):
        self.assertRaises(ValueError, utils.file_checksum, '/dev/random')
        self.assertRaises(ValueError, utils.file_checksum, '/dev/zero')


class TestCheckNodesCount(TestCase):

    def setUp(self):
        self.baremetal = mock.Mock()
        self.defaults = {
            'ControllerCount': 1,
            'ComputeCount': 1,
            'ObjectStorageCount': 0,
            'BlockStorageCount': 0,
            'CephStorageCount': 0,
        }
        self.stack = mock.Mock(parameters=self.defaults)

        def ironic_node_list(*args, **kwargs):
            if kwargs.get('associated') is True:
                nodes = range(2)
            elif kwargs.get('maintenance') is False:
                nodes = range(1)
            return nodes
        self.baremetal.node.list.side_effect = ironic_node_list

    def test_check_nodes_count_deploy_enough_nodes(self):
        user_params = {'ControllerCount': 2}
        self.assertEqual((True, 3, 3),
                         utils.check_nodes_count(self.baremetal, None,
                                                 user_params, self.defaults))

    def test_check_nodes_count_deploy_too_much(self):
        user_params = {'ControllerCount': 3}
        self.assertEqual((False, 4, 3),
                         utils.check_nodes_count(self.baremetal, None,
                                                 user_params, self.defaults))

    def test_check_nodes_count_scale_enough_nodes(self):
        user_params = {'ControllerCount': 2}
        self.assertEqual((True, 3, 3),
                         utils.check_nodes_count(self.baremetal, self.stack,
                                                 user_params, self.defaults))

    def test_check_nodes_count_scale_too_much(self):
        user_params = {'ControllerCount': 3}
        self.assertEqual((False, 4, 3),
                         utils.check_nodes_count(self.baremetal, self.stack,
                                                 user_params, self.defaults))

    def test_check_default_param_not_in_stack(self):
        missing_param = 'CephStorageCount'
        self.stack.parameters = self.defaults.copy()
        del self.stack.parameters[missing_param]

        self.assertRaises(ValueError, utils.check_nodes_count,
                          self.baremetal, self.stack, dict(), self.defaults)


class TestEnsureRunAsNormalUser(TestCase):

    @mock.patch('os.geteuid')
    def test_ensure_run_as_normal_user(self, os_geteuid_mock):
        os_geteuid_mock.return_value = 1000
        self.assertEqual(utils.ensure_run_as_normal_user(), None)

    @mock.patch('os.geteuid')
    def test_ensure_run_as_normal_user_root(self, os_geteuid_mock):
        os_geteuid_mock.return_value = 0
        self.assertRaises(exceptions.RootUserExecution,
                          utils.ensure_run_as_normal_user)


class TestCreateOvercloudRC(TestCase):

    @mock.patch('tripleoclient.utils.generate_overcloud_passwords',
                new=generate_overcloud_passwords_mock)
    def test_create_overcloudrc(self):
        stack = mock.MagicMock()
        stack.stack_name = 'teststack'
        endpoint_map = {'KeystoneAdmin': {'host': 'fd00::1'}}
        stack.to_dict.return_value = {
            'outputs': [{'output_key': 'KeystoneURL',
                         'output_value': 'http://foo.com:8000/'},
                        {'output_key': 'EndpointMap',
                         'output_value': endpoint_map}]
        }

        tempdir = tempfile.mkdtemp()
        rcfile = os.path.join(tempdir, 'teststackrc')
        try:
            utils.create_overcloudrc(stack=stack,
                                     no_proxy='127.0.0.1',
                                     config_directory=tempdir)
            rc = open(rcfile, 'rt').read()
            self.assertIn('export OS_AUTH_URL=http://foo.com:8000/', rc)
            self.assertIn('export no_proxy=127.0.0.1,foo.com,[fd00::1]',
                          rc)
            self.assertIn('export OS_CLOUDNAME=teststack', rc)
            self.assertIn('export PYTHONWARNINGS="ignore:Certificate has no, '
                          'ignore:A true SSLContext object is not available"',
                          rc)
        finally:
            if os.path.exists(rcfile):
                os.unlink(rcfile)
            os.rmdir(tempdir)


class TestCreateTempestDeployerInput(TestCase):

    def test_create_tempest_deployer_input(self):
        with tempfile.NamedTemporaryFile() as cfgfile:
            filepath = cfgfile.name
            utils.create_tempest_deployer_input(filepath)
            cfg = open(filepath, 'rt').read()
            # Just make a simple test, to make sure it created a proper file:
            self.assertIn(
                '[orchestration]\nstack_owner_role = heat_stack_user', cfg)


class TestGetEndpointMap(TestCase):

    def test_get_endpoint_map(self):
        stack = mock.MagicMock()
        emap = {'KeystonePublic': {'uri': 'http://foo:8000/'}}
        stack.to_dict.return_value = {
            'outputs': [{'output_key': 'EndpointMap',
                         'output_value': emap}]
        }

        endpoint_map = utils.get_endpoint_map(stack)
        self.assertEqual(endpoint_map,
                         {'KeystonePublic': {'uri': 'http://foo:8000/'}})


class TestCreateCephxKey(TestCase):

    def test_create_cephx_key(self):
        key = utils.create_cephx_key()
        self.assertEqual(len(key), 40)


class TestNodeGetCapabilities(TestCase):
    def test_with_capabilities(self):
        node = mock.Mock(properties={'capabilities': 'x:y,foo:bar'})
        self.assertEqual({'x': 'y', 'foo': 'bar'},
                         utils.node_get_capabilities(node))

    def test_no_capabilities(self):
        node = mock.Mock(properties={})
        self.assertEqual({}, utils.node_get_capabilities(node))


class TestNodeAddCapabilities(TestCase):
    def test_add(self):
        bm_client = mock.Mock()
        node = mock.Mock(uuid='uuid1', properties={})
        new_caps = utils.node_add_capabilities(bm_client, node, x='y')
        bm_client.node.update.assert_called_once_with(
            'uuid1', [{'op': 'add', 'path': '/properties/capabilities',
                       'value': 'x:y'}])
        self.assertEqual('x:y', node.properties['capabilities'])
        self.assertEqual({'x': 'y'}, new_caps)


class FakeFlavor(object):
    def __init__(self, name, profile=''):
        self.name = name
        self.profile = name
        if profile != '':
            self.profile = profile

    def get_keys(self):
        return {
            'capabilities:boot_option': 'local',
            'capabilities:profile': self.profile
        }


class TestAssignVerifyProfiles(TestCase):
    def setUp(self):

        super(TestAssignVerifyProfiles, self).setUp()
        self.bm_client = mock.Mock(spec=['node'],
                                   node=mock.Mock(spec=['list', 'update']))
        self.nodes = []
        self.bm_client.node.list.return_value = self.nodes
        self.flavors = {name: (FakeFlavor(name), 1)
                        for name in ('compute', 'control')}

    def _get_fake_node(self, profile=None, possible_profiles=[],
                       provision_state='available'):
        caps = {'%s_profile' % p: '1'
                for p in possible_profiles}
        if profile is not None:
            caps['profile'] = profile
        caps = utils.dict_to_capabilities(caps)
        return mock.Mock(uuid=str(uuid4()),
                         properties={'capabilities': caps},
                         provision_state=provision_state,
                         spec=['uuid', 'properties', 'provision_state'])

    def _test(self, expected_errors, expected_warnings,
              assign_profiles=True, dry_run=False):
        errors, warnings = utils.assign_and_verify_profiles(self.bm_client,
                                                            self.flavors,
                                                            assign_profiles,
                                                            dry_run)
        self.assertEqual(errors, expected_errors)
        self.assertEqual(warnings, expected_warnings)

    def test_no_matching_without_scale(self):
        self.flavors = {name: (object(), 0)
                        for name in self.flavors}
        self.nodes[:] = [self._get_fake_node(profile='fake'),
                         self._get_fake_node(profile='fake')]

        self._test(0, 0)
        self.assertFalse(self.bm_client.node.update.called)

    def test_exact_match(self):
        self.nodes[:] = [self._get_fake_node(profile='compute'),
                         self._get_fake_node(profile='control')]

        self._test(0, 0)
        self.assertFalse(self.bm_client.node.update.called)

    def test_nodes_with_no_profiles_present(self):
        self.nodes[:] = [self._get_fake_node(profile='compute'),
                         self._get_fake_node(profile=None),
                         self._get_fake_node(profile='foobar'),
                         self._get_fake_node(profile='control')]

        self._test(0, 1)
        self.assertFalse(self.bm_client.node.update.called)

    def test_more_nodes_with_profiles_present(self):
        self.nodes[:] = [self._get_fake_node(profile='compute'),
                         self._get_fake_node(profile='compute'),
                         self._get_fake_node(profile='compute'),
                         self._get_fake_node(profile='control')]

        self._test(0, 1)
        self.assertFalse(self.bm_client.node.update.called)

    def test_no_nodes(self):
        # One error per each flavor
        self._test(2, 0)
        self.assertFalse(self.bm_client.node.update.called)

    def test_not_enough_nodes(self):
        self.nodes[:] = [self._get_fake_node(profile='compute')]
        self._test(1, 0)
        self.assertFalse(self.bm_client.node.update.called)

    def test_assign_profiles(self):
        self.nodes[:] = [self._get_fake_node(possible_profiles=['compute']),
                         self._get_fake_node(possible_profiles=['control']),
                         self._get_fake_node(possible_profiles=['compute'])]

        # one warning for a redundant node
        self._test(0, 1, assign_profiles=True)
        self.assertEqual(2, self.bm_client.node.update.call_count)

        actual_profiles = [utils.node_get_capabilities(node).get('profile')
                           for node in self.nodes]
        actual_profiles.sort(key=lambda x: str(x))
        self.assertEqual([None, 'compute', 'control'], actual_profiles)

    def test_assign_profiles_multiple_options(self):
        self.nodes[:] = [self._get_fake_node(possible_profiles=['compute',
                                                                'control']),
                         self._get_fake_node(possible_profiles=['compute',
                                                                'control'])]

        self._test(0, 0, assign_profiles=True)
        self.assertEqual(2, self.bm_client.node.update.call_count)

        actual_profiles = [utils.node_get_capabilities(node).get('profile')
                           for node in self.nodes]
        actual_profiles.sort(key=lambda x: str(x))
        self.assertEqual(['compute', 'control'], actual_profiles)

    def test_assign_profiles_not_enough(self):
        self.nodes[:] = [self._get_fake_node(possible_profiles=['compute']),
                         self._get_fake_node(possible_profiles=['compute']),
                         self._get_fake_node(possible_profiles=['compute'])]

        self._test(1, 1, assign_profiles=True)
        # no node update for failed flavor
        self.assertEqual(1, self.bm_client.node.update.call_count)

        actual_profiles = [utils.node_get_capabilities(node).get('profile')
                           for node in self.nodes]
        actual_profiles.sort(key=lambda x: str(x))
        self.assertEqual([None, None, 'compute'], actual_profiles)

    def test_assign_profiles_dry_run(self):
        self.nodes[:] = [self._get_fake_node(possible_profiles=['compute']),
                         self._get_fake_node(possible_profiles=['control']),
                         self._get_fake_node(possible_profiles=['compute'])]

        self._test(0, 1, dry_run=True)
        self.assertFalse(self.bm_client.node.update.called)

        actual_profiles = [utils.node_get_capabilities(node).get('profile')
                           for node in self.nodes]
        self.assertEqual([None] * 3, actual_profiles)

    def test_scale(self):
        # active nodes with assigned profiles are fine
        self.nodes[:] = [self._get_fake_node(profile='compute',
                                             provision_state='active'),
                         self._get_fake_node(profile='control')]

        self._test(0, 0, assign_profiles=True)
        self.assertFalse(self.bm_client.node.update.called)

    def test_assign_profiles_wrong_state(self):
        # active nodes are not considered for assigning profiles
        self.nodes[:] = [self._get_fake_node(possible_profiles=['compute'],
                                             provision_state='active'),
                         self._get_fake_node(possible_profiles=['control'],
                                             provision_state='cleaning'),
                         self._get_fake_node(profile='compute',
                                             provision_state='error')]

        self._test(2, 1, assign_profiles=True)
        self.assertFalse(self.bm_client.node.update.called)

    def test_no_spurious_warnings(self):
        self.nodes[:] = [self._get_fake_node(profile=None)]
        self.flavors = {'baremetal': (FakeFlavor('baremetal', None), 1)}
        self._test(0, 0)

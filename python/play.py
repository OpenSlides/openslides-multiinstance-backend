#!/usr/bin/env python

import json
import os
import random
import re
import string
from collections import namedtuple
from optparse import OptionParser
from os import path

from ansible import constants as C
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.inventory.host import Host
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars import VariableManager

from multiinstance.utils import read_json_data


def random_string(length):
    return ''.join(
        [random.SystemRandom().choice("{}{}".format(string.ascii_letters, string.digits)) for i in range(length)])


def checkRequiredArguments(opts, parser):
    missing_options = []
    for opt in parser.option_list:
        if re.match(r'^\[REQUIRED\]', opt.help) and eval('opts.' + opt.dest) == None:
            missing_options.extend(opt._long_opts)
    if len(missing_options) > 0:
        parser.error('Missing REQUIRED parameters: ' + str(missing_options))


C.DEFAULT_ROLES_PATH = [path.join(path.dirname(path.abspath(__file__)), '../roles')]


class ResultCallback(CallbackBase):
    def __init__(self, logfile):
        super(ResultCallback, self).__init__()
        self.logfile = logfile
        if path.exists(self.logfile):
            self.logs = read_json_data(self.logfile)
        else:
            self.logs = []

    def v2_runner_item_on_failed(self, result):
        pass

    def log(self, result):
        logfile = open(self.logfile, "w")
        log_entry = {result._host.get_name(): result._result}
        self.logs.append(log_entry)
        print(json.dumps(log_entry, indent=4))
        logfile.write(json.dumps(self.logs, indent=4))
        logfile.close()

    def v2_runner_on_failed(self, result, ignore_errors=False):
        logfile = open(self.logfile, "a")
        self.log(result)
        super(ResultCallback, self).v2_runner_on_failed(result, ignore_errors=ignore_errors)

    def v2_runner_on_async_failed(self, result):
        pass

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        self.log(result)


parser = OptionParser()
parser.add_option("-i", "--instance-file", dest="instance_file",
                  help="[REQUIRED] instance file container instance data", metavar="INSTANCE_FILE")
parser.add_option("-f", "--force", dest="force", action="store_true",
                  help="forces execution even if instance was created already", default=False)
parser.add_option("-d", "--instances-dir", dest="instances_dir",
                  help="[REQUIRED] directory containing instance data", metavar="INSTANCES_DIR")
parser.add_option("-p", "--sudo-password", dest="sudo_password",
                  help="[REQUIRED] sudo password required to sudo in ansible script", metavar="SUDO_PASSWORD")
parser.add_option("-r", "--role", dest="ansible_role",
                  help="[REQUIRED] ansible role to execute (openslides-add-instance, openslides-remove-instance, openslides-stop-instance)", metavar="ANSIBLE_ROLE")

(options, args) = parser.parse_args()

checkRequiredArguments(options, parser)

# read instance data
instance_file = options.instance_file
with open(instance_file, 'r') as fh:
    instance_data = json.load(fh)

Options = namedtuple('Options',
                     ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check'])
# initialize needed objects
variable_manager = VariableManager()

instance_number = instance_data['number']
variables = {
    'openslides_secure_key': random_string(50),
    'openslides_instance_db_password': random_string(12),
    'openslides_instance_systemd_port': str(23232 + instance_number * 2),
    'openslides_instance_port': str(23232 + (instance_number * 2 + 1)),
    'postgres_host': 'localhost',
    'postgres_user': 'openslides_admin',
    'postgres_password': 'asdf'
}

for instance_var in instance_data.keys():
    variables['openslides_instance_' + instance_var] = instance_data[instance_var]

# check if instance if already created
instance_path = path.join(options.instances_dir, variables['openslides_instance_id'])

is_add = options.ansible_role == 'openslides-add-instance'
if path.exists(instance_path) and is_add and not options.force:
    raise Exception("instance already created")

if is_add:
    os.makedirs(instance_path)

variables['openslides_instance_path'] = instance_path

for key, value in variables.items():
    variable_manager.set_host_variable(Host(name='localhost'), key, value)

loader = DataLoader()
playoptions = Options(connection='local', module_path='/path/to/mymodules', forks=100, become=None, become_method='sudo',
                  become_user=None, check=False)
passwords = dict(vault_pass='secret')

# Instantiate our ResultCallback for handling results as they come in
results_callback = ResultCallback(path.join(instance_path, 'ansible.log.json'))

# create inventory and pass to var manager
inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list='localhost')
variable_manager.set_inventory(inventory)

# create play with tasks
play_source = dict(
    name="Ansible Play",
    hosts='localhost',
    gather_facts='no',
    # tasks=[
    #     dict(action=dict(module='shell', args='ls'), register='shell_out'),
    #     dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}')))
    # ]
    roles=[
        dict(name=options.ansible_role, register='shell_out'),
    ]
)
play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
print(instance_file)

# actually run it
tqm = None
try:
    tqm = TaskQueueManager(
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        options=playoptions,
        passwords=passwords,
        stdout_callback=results_callback,  # Use our custom callback instead of the ``default`` callback plugin
    )
    result = tqm.run(play)
finally:
    if tqm is not None:
        tqm.cleanup()

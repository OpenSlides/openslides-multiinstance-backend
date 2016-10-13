#!/usr/bin/env python

import json
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

C.DEFAULT_ROLES_PATH = [path.join(path.dirname(path.abspath(__file__)), '../roles')]


class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """

    def v2_runner_item_on_failed(self, result):
        pass

    def v2_runner_on_failed(self, result, ignore_errors=False):
        print(json.dumps({result._host.get_name(): result._result}, indent=4))
        super(ResultCallback, self).v2_runner_on_failed(result, ignore_errors=ignore_errors)

    def v2_runner_on_async_failed(self, result):
        pass

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        print(json.dumps({host.name: result._result}, indent=4))


parser = OptionParser()
parser.add_option("-i", "--instance-file", dest="instance_file",
                  help="[REQUIRED] instance file container instance data", metavar="INSTANCE_FILE")
parser.add_option("-f", "--force", dest="force", action="store_true",
                  help="forces execution even if instance was created already", default=False)
parser.add_option("-d", "--instances-dir", dest="instances_dir",
                  help="[REQUIRED] directory containing instance data", metavar="INSTANCES_DIR")
parser.add_option("-p", "--sudo-password", dest="sudo_password",
                  help="[REQUIRED] sudo password required to sudo in ansible script", metavar="SUDO_PASSWORD")

(options, args) = parser.parse_args()

def checkRequiredArguments(opts, parser):
    missing_options = []
    for opt in parser.option_list:
        if re.match(r'^\[REQUIRED\]', opt.help) and eval('opts.' + opt.dest) == None:
            missing_options.extend(opt._long_opts)
    if len(missing_options) > 0:
        parser.error('Missing REQUIRED parameters: ' + str(missing_options))

checkRequiredArguments(options, parser)

# read instance data
instance_file = options.instance_file
with open(instance_file, 'r') as fh:
    instance_data = json.load(fh)

Options = namedtuple('Options',
                     ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check'])
# initialize needed objects
variable_manager = VariableManager()


def random_string(length):
    return ''.join(
        [random.SystemRandom().choice("{}{}".format(string.ascii_letters, string.digits)) for i in range(length)])


instance_number = instance_data['number']
variables = {
    'openslides_static_path': '/home/ab/git/OpenSlides/collected-static',
    'openslides_secure_key': random_string(50),
    'openslides_instance_db_password': random_string(12),
    'openslides_instance_systemd_port': str(23232 + instance_number * 2),
    'openslides_instance_port': str(23232 + (instance_number * 2 + 1)),
    'postgres_host': 'localhost',
    'postgres_user': 'openslides_admin',
    'postgres_password': 'asdf',
    # 'openslides_instance_id': 'asdf',
    # 'openslides_instance_event_name': 'asdf',
    # 'openslides_instance_event_description': 'asdf',
    # 'openslides_instance_event_date': 'asdf',
    # 'openslides_instance_event_location': 'asdf',
    # 'openslides_instance_event_organizer': 'asdf',
    # 'openslides_instance_slug': 'asdf',
    'ansible_become_pass': options.sudo_password
}

for instance_var in instance_data.keys():
    variables['openslides_instance_' + instance_var] = instance_data[instance_var]

# check if instance if already created
instance_path = path.join(options.instances_dir, variables['openslides_instance_slug'])

if path.exists(instance_path) and not options.force:
    raise Exception("instance already created")

variables['openslides_instance_path'] = instance_path

for key, value in variables.items():
    variable_manager.set_host_variable(Host(name='localhost'), key, value)

loader = DataLoader()
options = Options(connection='local', module_path='/path/to/mymodules', forks=100, become=None, become_method='sudo',
                  become_user=None, check=False)
passwords = dict(vault_pass='secret')

# Instantiate our ResultCallback for handling results as they come in
results_callback = ResultCallback()

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
        dict(name="openslides-add-instance", register='shell_out'),
    ]
)
play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

# actually run it
tqm = None
try:
    tqm = TaskQueueManager(
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        options=options,
        passwords=passwords,
        stdout_callback=results_callback,  # Use our custom callback instead of the ``default`` callback plugin
    )
    result = tqm.run(play)
finally:
    if tqm is not None:
        tqm.cleanup()

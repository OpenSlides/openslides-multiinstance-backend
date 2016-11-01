from collections import defaultdict

from .models import Instance, OsVersion
from .utils import get_json_data
from .systemd import Systemd
import re


class VersionListing:
    def __init__(self, directory):
        self.directory = directory

    def get(self):
        versions = []
        for version_data in get_json_data(self.directory, 'openslides_version_'):
            versions.append(OsVersion(**version_data))

        return versions

    def get_by_id(self, name):
        return next(filter(lambda v: v.data['id'] == name, self.get()), None)


class InstanceListing:
    def __init__(self, directory):
        self.directory = directory

    def get(self):
        instances = []
        unit_states = Systemd().get_instance_unit_states()

        state_map = defaultdict(dict)
        for unit_state in unit_states:
            unit_name = unit_state['name']
            if not unit_name.startswith('openslides_instance'):
                continue

            match = re.match('openslides_instance_proxy_(.+).socket', unit_name)
            if match is not None:
                state_map[match.group(1)]['proxy_socket'] = unit_state
                continue
            match = re.match('openslides_instance_proxy_(.+).service', unit_name)
            if match is not None:
                state_map[match.group(1)]['proxy_service'] = unit_state
                continue
            match = re.match('openslides_instance_(.+).service', unit_name)
            if match is not None:
                state_map[match.group(1)]['service'] = unit_state
                continue

        for instance_data in get_json_data(self.directory, 'openslides_instance_'):
            instance = Instance(**instance_data)

            if instance.data['id'] in state_map:
                state = state_map[instance.data['id']]
                socket_state = state['proxy_socket']['state']
                proxy_service_state = state['proxy_service']['state']
                service_state = state['service']['state']
                if service_state == 'active':
                    instance.data['state'] = 'active'
                elif proxy_service_state == 'active':
                    instance.data['state'] = 'starting'
                elif socket_state == 'active':
                    instance.data['state'] = 'sleeping'
                else:
                    instance.data['state'] = 'error'
            else:
                instance.data['state'] = 'installing'


            instance.data['osversion'] = VersionListing(self.directory).get_by_id(instance.osversion)
            try:
                mode = instance.data['mode']
            except KeyError:
                mode = None
            if mode == 'subdomain':
                instance.data['url'] = 'http://{}.{}/'.format(instance.data['slug'], instance.data['parent_domain'])
            else:
                instance.data['url'] = 'http://openslides.de/' + instance.data['slug']
            instances.append(instance)
        return instances

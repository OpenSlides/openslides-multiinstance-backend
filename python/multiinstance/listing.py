import os
import re
from collections import defaultdict

from multiinstance.utils import read_json_data
from .models import Instance, OsVersion, OsDomain
from .systemd import Systemd
from .utils import get_json_data


class DomainListing:
    def __init__(self, directory):
        self.directory = directory

    def get(self):
        domains = []
        for domain_data in read_json_data(self.directory, 'domains.json'):
            domains.append(OsDomain(**domain_data))
        return domains

    def get_by_id(self, identifier):
        next(filter(lambda v: v.data['id'] == identifier, self.get()), None)


class VersionListing:
    def __init__(self, directory):
        self.directory = directory

    def get(self):
        versions = []
        for version_data in read_json_data(self.directory, 'openslides_versions.json'):
            versions.append(OsVersion(**version_data))

        return versions

    def get_by_id(self, name):
        return next(filter(lambda v: v.data['id'] == name, self.get()), None)


class InstanceListing:
    def __init__(self, directory, versions_listing, domains_listing):
        self.directory = directory
        self.versions_listing = versions_listing
        self.domains_listing = domains_listing

    def get_by_id(self, id):
        instance_data = self.get_instance_data(read_json_data(self.directory, 'openslides_instance_{}.json'.format(id)))
        state_map = self.get_instance_state_map()
        instance = Instance(**instance_data)
        self.set_instance_state(instance, state_map)
        return instance

    def instance_installing(self, id):
        return not os.path.exists(os.path.join(self.directory, id, 'installed'))

    def get(self):
        instances = []
        state_map = self.get_instance_state_map()

        for instance_data in get_json_data(self.directory, 'openslides_instance_'):
            instance_data = self.get_instance_data(instance_data)
            instance = Instance(**instance_data)

            self.set_instance_state(instance, state_map)

            try:
                mode = instance.data['mode']
            except KeyError:
                mode = None
            if mode == 'subdomain':
                instance.data['url'] = 'http://{}.{}/'.format(instance.data['slug'], instance.data['parent_domain'])
            else:
                instance.data['url'] = 'http://openslides.de/' + instance.data['slug']
            if not instance.data['state'] == 'removed':
                instances.append(instance)
        return instances

    def get_instance_data(self, instance_data):
        instance_data['osversion'] = self.versions_listing.get_by_id(instance_data['osversion'])
        return instance_data

    def set_instance_state(self, instance, state_map):
        instance_id = instance.data['id']
        installing = self.instance_installing(instance_id)
        if installing:
            instance.data['state'] = 'installing'
            return

        if instance_id in state_map:
            state = state_map[instance_id]
            socket_state = state['proxy_socket']['state'] if 'proxy_socket' in state else 'stopped'
            proxy_service_state = state['proxy_service']['state'] if 'proxy_service' in state else 'stopped'
            service_state = state['service']['state']
            if service_state == 'active':
                instance.data['state'] = 'active'
            elif service_state == 'failed':
                instance.data['state'] = 'error'
            elif proxy_service_state == 'active':
                instance.data['state'] = 'starting'
            elif socket_state == 'active':
                instance.data['state'] = 'sleeping'
            else:
                instance.data['state'] = 'removed'
        else:
            instance.data['state'] = 'stopped'

    def get_instance_state_map(self):
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
        return state_map

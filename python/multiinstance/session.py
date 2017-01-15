import os
import subprocess
import uuid
from datetime import datetime
from subprocess import call, Popen
from sys import path

import jsonapi.base
from multiinstance.listing import InstanceListing, VersionListing, DomainListing
from multiinstance.models import Instance
from multiinstance.utils import generate_username, randompassword
from shutil import copyfile


class Session(jsonapi.base.database.Session):
    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args)
        self.versions = VersionListing(kwargs['versions_meta_dir'])
        self.instances = InstanceListing(kwargs['instance_meta_dir'], self.versions, DomainListing(kwargs['versions_meta_dir']))
        self.versions_meta_dir = kwargs['versions_meta_dir']
        self.instances_dir = kwargs['instances_dir']
        self.python_ansible = kwargs['python_ansible']
        self.postgres_password = kwargs['postgres_password']
        self.multiinstance_url = kwargs['multiinstance_url']
        self.instance_meta_dir = kwargs['instance_meta_dir']
        self.upload_dir = kwargs['upload_dir']

    def query_size(self, typename, *, sorting=None, limit=None, offset=None, filters=None):
        pass

    def commit(self):
        pass

    def delete(self, resources):
        for resource in resources:
            if isinstance(resource, Instance):
                cmd = self.build_play_command(resource.get_instance_filename(self.instance_meta_dir),
                                              'openslides-remove-instance')
                print(" ".join(cmd))
                call(cmd)

    def save(self, resources):
        for resource in resources:
            if isinstance(resource, Instance):
                if 'id' in resource.data:
                    self.save_instance(resource)
                else:
                    self.create_instance(resource)

    def create_instance(self, resource):
        now = datetime.now()
        instance_id = uuid.uuid4().__str__().replace('-', '')
        journal_file = os.path.join(self.instance_meta_dir, "openslides_instance.journal")
        if os.path.isfile(journal_file):
            with open(journal_file, 'rb') as fh:
                lines = fh.readlines()
                if len(lines) == 0:
                    last_number = 0
                else:
                    last = lines[-1].decode()
                    last_number = int(last.split(';')[0])
        else:
            last_number = 0
        number = last_number + 1
        with open(journal_file, 'a') as fh:
            fh.write(str(number) + ';' + instance_id + "\n")
        resource.data['id'] = instance_id
        resource.data['number'] = number
        resource.data['superadmin_password'] = randompassword()
        resource.data['admin_initial_password'] = randompassword()
        resource.data['admin_username'] = generate_username(resource.data['admin_first_name'],
                                                            resource.data['admin_last_name'])
        resource.data['created_date'] = now.strftime('%Y-%m-%d')
        instance_filename = resource.get_instance_filename(self.instance_meta_dir)
        cmd = self.build_play_command(instance_filename, 'openslides-add-instance')
        resource.data['install_cmd'] = ' '.join(cmd)
        resource.save(self.instance_meta_dir)
        self.fork(cmd)

    def fork(self, cmd):
        print(" ".join(cmd))
        Popen(['nohup'] + cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def build_play_command(self, instance_filename, role):
        playscript = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'play.py')

        cmd = [self.python_ansible, playscript, '--instances-dir', self.instances_dir,
               '--role', role,
               '--postgres-password', self.postgres_password,
               '--multiinstance-url', self.multiinstance_url,
               '--upload-dir', self.upload_dir,
               '--instance-file', instance_filename]
        return cmd

    def get(self, identifier, required=False):
        print("GETTING {} -> {}".format(*identifier))
        if identifier[0] == 'osversions':
            return self.versions.get_by_id(identifier[1])
        if identifier[0] == 'osdomains':
            return DomainListing(self.versions_meta_dir).get_by_id(identifier[1])
        if identifier[0] == 'instances':
            return self.find_instance(identifier[1])
        pass

    def find_instance(self, id):
        return self.instances.get_by_id(id)

    def query(self, typename, *, sorting=None, limit=None, offset=None, filters=None, order=None):
        if typename == 'instances':
            return self.instances.get()
        elif typename == 'osversions':
            return VersionListing(self.versions_meta_dir).get()
        elif typename == 'osdomains':
            return DomainListing(self.versions_meta_dir).get()
        pass

    def get_many(self, identifiers, required=False):
        objs = [self.get(identifier, required) for identifier in identifiers]
        return dict([((obj.type, obj.data['id']), obj) for obj in objs if obj is not None])

    def save_instance(self, instance):
        old_instance = self.find_instance(instance.data['id'])
        # only the instance state can be changed, and logo
        old_state = old_instance.data['state']
        new_state = instance.data['state']

        if old_instance.data['projector_logo'] != instance.data['projector_logo']:
            # save save to static directory
            if instance.data['projector_logo'] is not None:
                projector_logo_file_path = os.path.join(self.instances_dir, instance.data['id'],
                                                     'static', 'img', 'logo-projector.png')

                blob_file = os.path.join(self.upload_dir, instance.data['projector_logo'])
                copyfile(blob_file, projector_logo_file_path)

            instance.save(self.instance_meta_dir)

        if old_state != new_state:
            if new_state == 'stopped':
                instance_filename = instance.get_instance_filename(self.instance_meta_dir)
                cmd = self.build_play_command(instance_filename, 'openslides-stop-instance')
                call(cmd)

            if new_state == 'active':
                instance_filename = instance.get_instance_filename(self.instance_meta_dir)
                cmd = self.build_play_command(instance_filename, 'openslides-start-instance')
                call(cmd)

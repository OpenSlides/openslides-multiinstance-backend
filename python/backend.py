import copy
import json
import os
import random
import string
import uuid
from datetime import datetime
from optparse import OptionParser
from subprocess import Popen

import subprocess
from flask import Flask
from multiinstance.listing import InstanceListing, VersionListing
from multiinstance.models import Instance, OsVersion

import jsonapi.flask
from jsonapi.base.schema import Schema
from python.multiinstance.listing import DomainListing
from python.multiinstance.models import OsDomain
from python.multiinstance.utils import generate_username
from python.utils import checkRequiredArguments

parser = OptionParser()
parser.add_option("-i", "--instance-meta-dir", dest="instance_meta_dir",
                  help="[REQUIRED] directory containing instance meta files", metavar="INSTANCE_META_DIR")
parser.add_option("--versions-meta-dir", dest="versions_meta_dir",
                  help="[REQUIRED] directory containing version meta files",
                  metavar="VERSIONS_META_DIR")
parser.add_option("-d", "--instances-dir", dest="instances_dir",
                  help="[REQUIRED] directory containing instance data", metavar="INSTANCES_DIR")
parser.add_option("-a", "--python-ansible", dest="python_ansible",
                  help="[REQUIRED] python binary of ansible virtual environment", metavar="PYTHON_ANSIBLE")
parser.add_option("-p", "--sudo-password", dest="sudo_password",
                  help="[REQUIRED] sudo password required to sudo in ansible script", metavar="SUDO_PASSWORD")

(options, args) = parser.parse_args()

checkRequiredArguments(options, parser)
instance_meta_dir = options.instance_meta_dir
versions_meta_dir = options.versions_meta_dir


def randompassword():
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for x in range(10))


class Database(jsonapi.base.database.Database):
    def session(self):
        return Session(self.api)


class Session(jsonapi.base.database.Session):
    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self.instances = InstanceListing(instance_meta_dir)
        self.versions = VersionListing(versions_meta_dir)

    def query_size(self, typename, *, sorting=None, limit=None, offset=None, filters=None):
        pass

    def commit(self):
        pass

    def delete(self, resources):
        pass

    def save(self, resources):
        for resource in resources:
            if isinstance(resource, Instance):
                now = datetime.now()
                instance_id = uuid.uuid4().__str__()
                journal_file = os.path.join(instance_meta_dir, "openslides_instance.journal")
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
                instance_filename = os.path.join(instance_meta_dir, "openslides_instance_" + instance_id + '.json')
                f = open(instance_filename, "w")
                data = copy.copy(resource.data)
                data['image'] = data['osversion'].data['image']
                data['osversion'] = data['osversion'].data['id']
                data['number'] = number
                data['superadmin_password'] = randompassword()
                data['admin_initial_password'] = randompassword()
                data['admin_username'] = generate_username(data['admin_first_name'], data['admin_last_name'])
                data['created_date'] = now.strftime('%Y-%m-%d')
                playscript = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'play.py')
                cmd = [options.python_ansible, playscript, '--instances-dir', options.instances_dir,
                             '--sudo-password', options.sudo_password, '--instance-file', instance_filename]
                data['install_cmd'] = ' '.join(cmd)
                f.write(json.dumps(data, indent=4))
                f.close()
                Popen(['nohup'] + cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def get(self, identifier, required=False):
        if identifier[0] == 'osversions':
            return self.versions.get_by_id(identifier[1])
        pass

    def query(self, typename, *, sorting=None, limit=None, offset=None, filters=None, order=None):
        if typename == 'instances':
            return self.instances.get()
        elif typename == 'osversions':
            return VersionListing(versions_meta_dir).get()
        elif typename == 'osdomains':
            return DomainListing(versions_meta_dir).get()
        pass

    def get_many(self, identifiers, required=False):
        objs = [self.get(identifier, required) for identifier in identifiers]
        return dict([((obj.type, obj.data['id']), obj) for obj in objs if obj is not None])


app = Flask(__name__)

api = jsonapi.flask.FlaskAPI("/api", db=Database(), flask_app=app)

api.add_type(Schema(Instance, typename='instances'))
api.add_type(Schema(OsVersion, typename='osversions'))
api.add_type(Schema(OsDomain, typename='osdomains'))

if __name__ == "__main__":
    app.run()

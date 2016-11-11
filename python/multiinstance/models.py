import copy
import json
import os

from .schema import ObjectIDAttribute, ObjectAttribute
from .schema import ToOneRelationship


class SimpleApiObject:
    def __init__(self, *args, **kwargs):
        self.data = kwargs


class OsDomain(SimpleApiObject):
    type = 'osdomains'
    id = ObjectIDAttribute("id")
    domain = ObjectAttribute("domain")


class OsVersion(SimpleApiObject):
    type = 'osversions'
    id = ObjectIDAttribute("id")
    image = ObjectAttribute("image")
    default = ObjectAttribute("default")


class Instance(SimpleApiObject):
    type = 'instances'
    id = ObjectIDAttribute("id")
    slug = ObjectAttribute("slug")
    url = ObjectAttribute("url")
    parent_domain = ObjectAttribute("parent_domain")
    mode = ObjectAttribute("mode")
    db = ObjectAttribute("db")

    created_date = ObjectAttribute("created_date")
    install_cmd = ObjectAttribute("install_pid")

    osversion = ToOneRelationship("osversion")

    # admin properties
    admin_first_name = ObjectAttribute("admin_first_name")
    admin_last_name = ObjectAttribute("admin_last_name")
    admin_initial_password = ObjectAttribute("admin_initial_password")
    admin_username = ObjectAttribute("admin_username")

    superadmin_password = ObjectAttribute("superadmin_password")

    # event properties
    event_name = ObjectAttribute("event_name")
    event_description = ObjectAttribute("event_description")
    event_date = ObjectAttribute("event_date")
    event_location = ObjectAttribute("event_location")
    event_organizer = ObjectAttribute("event_organizer")

    projector_logo = ObjectAttribute("projector_logo")

    state = ObjectAttribute("state")

    def save(self, directory):
        instance_filename = self.get_instance_filename(directory)
        data = copy.copy(self.data)
        # image and version are serialized with id
        data['image'] = data['osversion'].data['image']
        data['osversion'] = data['osversion'].data['id']

        f = open(instance_filename, "w")
        f.write(json.dumps(data, indent=4))
        f.close()

    def get_instance_filename(self, instance_meta_dir):
        return os.path.join(instance_meta_dir, "openslides_instance_" + self.data['id'] + '.json')


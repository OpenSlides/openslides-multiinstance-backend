from .schema import ToOneRelationship
from .schema import ObjectIDAttribute, ObjectAttribute, ParentIDAttribute


class SimpleApiObject:
    def __init__(self, *args, **kwargs):
        self.data = kwargs


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

    osversion = ToOneRelationship("osversion")

    # admin properties
    admin_first_name = ObjectAttribute("admin_first_name")
    admin_last_name = ObjectAttribute("admin_last_name")
    admin_initial_password = ObjectAttribute("admin_initial_password")

    # event properties
    event_name = ObjectAttribute("event_name")
    event_description = ObjectAttribute("event_description")
    event_date = ObjectAttribute("event_date")
    event_location = ObjectAttribute("event_location")
    event_organizer = ObjectAttribute("event_organizer")

    state = ObjectAttribute("state")

import jsonapi
from jsonapi.base.schema import IDAttribute


class ToOneRelationship(jsonapi.base.schema.ToOneRelationship):
    def __init__(self, name):
        super().__init__(name=name)
        return None

    def get(self, resource):
        return resource.data.get(self.name)

    def set(self, resource, relative):
        resource.data[self.name] = relative
        return None

    def clear(self, resource):
        resource.data[self.name] = None
        return None


class ObjectAttribute(jsonapi.base.schema.Attribute):

    def __init__(self, *args, **kwargs):
        self.required = kwargs.get('required', False)
        super(ObjectAttribute, self).__init__(*args, **kwargs)

    def get(self, resource):
        return resource.data.get(self.name)

    def set(self, resource, value):
        resource.data[self.name] = value
        return None


class ObjectIDAttribute(ObjectAttribute, IDAttribute):
    pass

class ParentIDAttribute(IDAttribute):

    def __init__(self, parent_attribute, name, postfix):
        super().__init__(name=name)
        self.parent_attribute = parent_attribute
        self.postfix = postfix
        return None

    def get(self, resource):
        parent = resource.data.get(self.parent_attribute)
        return parent.data.get(self.name) + self.postfix

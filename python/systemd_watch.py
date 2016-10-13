from multiinstance.listing import InstanceListing
from multiinstance.systemd import Systemd

instance_meta_dir = '/tmp/meta'

print(InstanceListing(instance_meta_dir).get())
print(Systemd().get_instance_unit_states())

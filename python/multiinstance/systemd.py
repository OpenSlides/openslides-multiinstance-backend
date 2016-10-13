from pydbus import SystemBus


# def printit(obj):
#     print(obj)
# systemd.JobNew.connect(printit)
# GObject.MainLoop().run()
# help(systemd)

class Systemd:
    def get_instance_unit_states(self):
        bus = SystemBus()
        systemd = bus.get(".systemd1")
        manager = systemd.GetAll('org.freedesktop.systemd1.Manager')

        states = []

        for unit in systemd.ListUnits():
            (name, _, loaded, state, mounted, _, user_id, _, _, _) = unit
            states.append({
                'state': state,
                'loaded': loaded,
                'name': name
            })

        return states

from ops.charm import EventBase, ObjectEvents, EventSource


class UnitEvent(EventBase):
    def __init__(self, handle, unit_name):
        super().__init__(handle)

        self.unit_name = unit_name

    def snapshot(self):
        return {"unit_name": self.unit_name}

    def restore(self, snapshot):
        self.unit_name = snapshot["unit_name"]


class UnitAddedEvent(UnitEvent):
    pass


class UnitRemovedEvent(UnitEvent):
    pass


class GovernorEvents(ObjectEvents):
    unit_added = EventSource(UnitAddedEvent)
    unit_removed = EventSource(UnitRemovedEvent)


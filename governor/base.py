#!/usr/bin/env python3
#
# (c) 2020 Canonical Ltd. All right reservered
#

from juju.controller import Controller
from ops.charm import CharmBase, EventBase, ObjectEvents, EventSource
from ops.framework import StoredState, Object
from .governor_storage import GovernorStorage

import os
import logging
import yaml
import sys
import subprocess


def interrupt():
    sys.exit()


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
    unitadded = EventSource(UnitAddedEvent)
    unitremoved = EventSource(UnitRemovedEvent)


class GovernorEventHandler(Object):
    on = GovernorEvents()

    def __init__(self, charm, name):
        super().__init__(charm, name)
        events = charm.on
        self.gs = GovernorStorage("/home/ubuntu/gs_db")
        self.framework.observe(
            events.governorevent_action, self.on_governorevent_action
        )

    def on_governorevent_action(self, event):
        self.process_governor_events()

    def process_governor_events(self):
        events_data = self.gs.read_all_event_data()

        for event_data in events_data:
            self.emit_governor_event(event_data)

    def emit_governor_event(self, event_data):
        event_switcher = {
            "unitadded": self.on.unitadded.emit,
            "unitremoved": self.on.unitremoved.emit,
        }

        func = event_switcher.get(event_data["event_name"],
                                  lambda: "Invalid event data")

        func(event_data["event_data"])


class GovernorBase(CharmBase):
    state = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        self.geh = GovernorEventHandler(self, "geh")

        model_name = os.environ["JUJU_MODEL_NAME"] or None
        if model_name is None:
            raise Exception("Failed to find model {}".format(model_name))

        self.state.set_default(model_name=model_name)
        self.framework.observe(self.geh.on.unitadded, self.on_unitadded)
        self.framework.observe(self.geh.on.unitremoved, self.on_unitremoved)

    def on_unitadded(self, event):
        self.framework.breakpoint()
        logging.debug("Unit Added Event called")

    def on_unitremoved(self, event):
        self.framework.breakpoint()
        logging.debug("Unit Removed Event called")

    def start_governord(self):
        model_name = self.state.model_name
        creds = {
            "endpoint": self.model.config["juju_controller_address"],
            "username": self.model.config["juju_controller_user"],
            "password": self.model.config["juju_controller_password"],
            "cacert": self.model.config["juju_controller_cacert"],
            "model": model_name,
        }
        with open("/home/ubuntu/creds.yaml", "w") as creds_file:
            creds_file.write(yaml.dump(creds))

        logging.debug("current dir: {}".format(os.getcwd()))
        subprocess.Popen(
            ["nohup", "./daemon"],
            stdout=open("/dev/null", "w"),
            stderr=open("logfile.log", "a"),
            preexec_fn=os.setpgrp,
        )

    def connected(f):
        async def wrapper(*args):
            ctrl, model = await args[0].connect_juju_components()
            result = await f(*args, ctrl, model)
            await args[0].disconnect_juju_components(ctrl, model)
            return result

        return wrapper

    async def connect_juju_components(self):
        ctrl = Controller()
        await ctrl.connect(
            endpoint=self.model.config["juju_controller_address"],
            username=self.model.config["juju_controller_user"],
            password=self.model.config["juju_controller_password"],
            cacert=self.model.config["juju_controller_cacert"],
        )

        model = await ctrl.get_model(self.state.model_name)

        return ctrl, model

    async def disconnect_juju_components(self, model, ctrl):
        await model.disconnect()
        await ctrl.disconnect()

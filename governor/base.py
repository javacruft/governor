#!/usr/bin/env python3
#
# (c) 2020 Canonical Ltd. All right reservered
#
from .juju_wrapper import JujuConnection
from juju.controller import Controller
from ops.charm import CharmBase
from ops.framework import StoredState, Object
from .storage import GovernorStorage
from .events import GovernorEvents

import os
import logging
import yaml
import subprocess


class GovernorEventHandler(Object):
    on = GovernorEvents()

    def __init__(self, charm, name):
        super().__init__(charm, name)
        events = charm.on
        self.gs = GovernorStorage("/var/snap/governor-broker/common/gs_db")
        self.framework.observe(
            events.governor_event_action, self.on_governor_event_action
        )

    def on_governor_event_action(self, event):
        self.process_governor_events()

    def process_governor_events(self):
        events_data = self.gs.read_all_event_data()

        for event_data in events_data:
            self.emit_governor_event(event_data)

    def emit_governor_event(self, event_data):
        event_switcher = {
            "unit_added": self.on.unit_added.emit,
            "unit_removed": self.on.unit_removed.emit,
        }

        func = event_switcher.get(
            event_data["event_name"], lambda: "Invalid event data"
        )

        func(event_data["event_data"])


class GovernorBase(CharmBase):
    state = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        if not os.path.isdir("/var/snap/governor-broker/common"):
            os.makedirs("/var/snap/governor-broker/common")

        self.geh = GovernorEventHandler(self, "geh")

        model_name = os.environ["JUJU_MODEL_NAME"] or None
        if model_name is None:
            raise Exception("Failed to find model {}".format(model_name))

        self.state.set_default(model_name=model_name)

        if self.creds_available():
            self.juju = JujuConnection(
                self.model.config["juju_controller_address"],
                self.model.config["juju_controller_user"],
                self.model.config["juju_controller_password"],
                self.model.config["juju_controller_cacert"],
                self.state.model_name,
            )
        else:
            self.juju = None

    def start_governord(self):
        model_name = self.state.model_name
        creds = {
            "endpoint": self.model.config["juju_controller_address"],
            "username": self.model.config["juju_controller_user"],
            "password": self.model.config["juju_controller_password"],
            "cacert": self.model.config["juju_controller_cacert"],
            "model": model_name,
            "governor-charm": self.model.app.name,
        }
        with open("/var/snap/governor-broker/common/creds.yaml", "w") as creds_file:
            creds_file.write(yaml.dump(creds))

        open("/var/snap/governor-broker/common/gs_db", "w").close()

        logging.debug("current dir: {}".format(os.getcwd()))

        subprocess.run(["snap", "install", "governor-broker"], check=True)

    def creds_available(self):
        addr = self.model.config["juju_controller_address"]
        if len(addr) == 0:
            addr = os.environ["JUJU_API_ADDRESSES"].split(" ")[0]
        user = self.model.config["juju_controller_user"]
        password = self.model.config["juju_controller_password"]
        cacert = self.model.config["juju_controller_cacert"]

        return not (
            len(addr) == 0 or len(user) == 0 or len(password) == 0 or len(cacert) == 0
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

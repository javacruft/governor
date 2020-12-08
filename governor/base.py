#!/usr/bin/env python3
#
# (c) 2020 Canonical Ltd. All right reservered
#
import os
import subprocess
import yaml
import logging
import sqlite3
from time import sleep

from .juju_wrapper import JujuConnection
from ops.charm import CharmBase
from ops.framework import StoredState, Object
from .storage import GovernorStorage
from .events import GovernorEvents


class GovernorEventHandler(Object):
    """
    Governor Event Handler

    Class in charge of reacting to governor-event action, reading event data
    from Governor Storage and emmiting correct Governor Event.
    """

    on = GovernorEvents()

    def __init__(self, charm, name):
        super().__init__(charm, name)
        events = charm.on
        self.storage = GovernorStorage("/var/snap/governor-broker/common/gs_db")
        self.framework.observe(
            events.governor_event_action, self.on_governor_event_action
        )

    def on_governor_event_action(self, event):
        """ React to action and start Processing Governor Events. """
        self.process_governor_events(event)

    def process_governor_events(self, event):
        """ Read Events from Storage. """
        retries = 0

        while retries < 3:
            try:
                events_data = self.storage.read_all_event_data()
                break
            except sqlite3.OperationalError:
                logging.warning("Waiting for DB to unlock")
                sleep(3)
                retries += 1
        else:
            logging.warning("Unable to load Events, Deferring Action.")
            event.defer()
            return

        for event_data in events_data:
            self.emit_governor_event(event_data)

    def emit_governor_event(self, event_data):
        """ Map event data to governor events and emit it. """
        event_switcher = {
            "unit_added": self.on.unit_added.emit,
            "unit_removed": self.on.unit_removed.emit,
            "unit_blocked": self.on.unit_blocked.emit,
            "unit_error": self.on.unit_error.emit,
        }

        func = event_switcher.get(
            event_data["event_name"], lambda: "Invalid event data"
        )

        func(event_data["event_data"])


class GovernorBase(CharmBase):
    """
    GovernorBase

    Base class for all Governor Charms.
    """

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
        """ Create creds.yaml and starting Governor Broker. """
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

        subprocess.run(["snap", "install", "governor-broker"], check=True)

    def creds_available(self):
        """ Check if Juju credentials are available. """
        addr = self.model.config["juju_controller_address"]
        if len(addr) == 0:
            addr = os.environ["JUJU_API_ADDRESSES"].split(" ")[0]
        user = self.model.config["juju_controller_user"]
        password = self.model.config["juju_controller_password"]
        cacert = self.model.config["juju_controller_cacert"]

        return not (
            len(addr) == 0 or len(user) == 0 or len(password) == 0 or len(cacert) == 0
        )

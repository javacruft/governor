import asyncio

from juju.controller import Controller
from juju import loop
from ops.model import ModelError


class JujuConnection:
    """
    Juju Connection Class

    Class in charge of communicating with Juju through Libjuju in a Synchronous way.
    """

    def __init__(self, endpoint, username, password, cacert, model):
        loop.run(
            self.connect_juju_components(endpoint, username, password, cacert, model)
        )

    async def connect_juju_components(
        self, endpoint, username, password, cacert, model
    ):
        """ Connect to Juju controller and Juju Model. """
        self.ctrl = Controller()
        await self.ctrl.connect(
            endpoint=endpoint,
            username=username,
            password=password,
            cacert=cacert,
        )

        self.model = await self.ctrl.get_model(model)

    def get_cloud_type(self):
        return loop.run(self._get_cloud_type())

    async def _get_cloud_type(self):
        status = await self.model.get_status()
        cloud_tag = status["model"].cloud_tag
        cloud = await self.ctrl.cloud(cloud_tag)
        return cloud["cloud"].type_

    def switch_model(self, model):
        loop.run(self._switch_model(model))

    async def _switch_model(self, model):
        """ Switch the current model focus. """
        self.model = await self.ctrl.get_model(model)

    def set_config(self, app_name, **kwargs):
        """ Call application.set_config. """
        application = self.model.applications[app_name]

        loop.run(application.set_config(**kwargs))

    def get_config(self, app_name):
        """ Return the configuration for the given application. """
        application = self.model.applications[app_name]
        return loop.run(application.get_config())

    def execute_action(self, application_name, action_name, **kwargs):
        """ Execute Action synchronously. """
        loop.run(self._execute_action(application_name, action_name, **kwargs))

    async def _execute_action(self, application_name, action_name, **kwargs):
        """ Execute Action on Leader unit of Application name. """
        unit = await self._get_leader_unit(application_name)
        await unit.run_action(action_name, **kwargs)

    def deploy(self, **kwargs):
        """ Call model.deploy. """
        loop.run(self.model.deploy(**kwargs))

    def add_relation(self, rel1, rel2):
        """ Adds a new relation to the model """
        loop.run(self.model.add_relation(rel1, rel2))

    async def _add_machine(self, **kwargs):
        machine = await self.model.add_machine(**kwargs)
        return machine.id

    def add_machine(self, **kwargs):
        """ Adds a new machine to the model. Returns the machine id. """
        return loop.run(self._add_machine(**kwargs))

    async def _get_leader_unit(self, app_name):
        app = self.model.applications[app_name]
        for u in app.units:
            if await u.is_leader_from_status():
                return u
        return None

    def get_leader_unit(self, app_name):
        """ Returns the leader unit of the given application. """
        return loop.run(self._get_leader_unit(app_name))

    def get_application(self, app_name):
        """ Returns the full application for the given application. """
        return self.model.applications[app_name]

    def wait_for_deployment_to_settle(
        self, charm_name, allowed_workload_status=["active"], timeout=320
    ):
        """ Wait for deployment to settle synchronously. """
        loop.run(self._wait_for_deployment_to_settle(
            charm_name, allowed_workload_status, timeout))

    async def _wait_for_deployment_to_settle(
        self, charm_name, allowed_workload_status=["active"], timeout=320
    ):
        """
        Wait for deployment to settle to allowed workload status and ignore status of
        charm_name.
        """
        try:
            filtered_apps = []
            for name in self.model.applications:
                if charm_name == name:
                    continue
                filtered_apps.append(self.model.applications[name])
            await self.model.block_until(
                lambda: all(
                    (unit.workload_status in allowed_workload_status)
                    and unit.agent_status == "idle"
                    for application in filtered_apps
                    for unit in application.units
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise ModelError("Timed out while waiting for deployment to finish")

    async def _upgrade_application(self, app_name, **kwargs):
        app = self.model.applications[app_name]
        await app.upgrade_charm(**kwargs)

    def upgrade_application(self, app_name, **kwargs):
        loop.run(self._upgrade_application(app_name, **kwargs))

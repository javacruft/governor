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

    def set_config(self, app_name, **kwargs):
        """ Call application.set_config. """
        application = self.model.applications[app_name]

        loop.run(application.set_config(**kwargs))

    def execute_action(self, application_name, action_name, **kwargs):
        """ Execute Action synchronously. """
        loop.run(self._execute_action(application_name, action_name, **kwargs))

    async def _execute_action(self, application_name, action_name, **kwargs):
        """ Execute Action on Leader unit of Application name. """
        application = self.model.applications[application_name]

        for u in application.units:
            if await u.is_leader_from_status():
                unit = u
                break

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

    def wait_for_deployment_to_settle(
        self, charm_name, allowed_workload_status=["active"]
    ):
        """ Wait for deployment to settle synchronously. """
        loop.run(self._wait_for_deployment_to_settle(charm_name))

    async def _wait_for_deployment_to_settle(
        self, charm_name, allowed_workload_status=["active"]
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
                timeout=320,
            )
        except asyncio.TimeoutError:
            raise ModelError("Timed out while waiting for deployment to finish")

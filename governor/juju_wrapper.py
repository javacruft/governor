
from juju.controller import Controller
from juju import loop
from ops.model import ModelError
import asyncio


class JujuConnection:

    def __init__(self, endpoint, username, password, cacert, model):
        loop.run(self.connect_juju_components(endpoint,
                                              username,
                                              password,
                                              cacert,
                                              model))

    async def connect_juju_components(self, endpoint, username, password, cacert, model):
        self.ctrl = Controller()
        await self.ctrl.connect(
            endpoint=endpoint,
            username=username,
            password=password,
            cacert=cacert,
        )

        self.model = await self.ctrl.get_model(model)

    def set_config(self, application, **kwargs):
        loop.run(application.set_config(**kwargs))

    def execute_action(self, application_name, action_name, **kwargs):
        loop.run(self._execute_action(application_name, action_name, **kwargs))

    async def _execute_action(self, application_name, action_name, **kwargs):
        if not self.model.applications and application_name not in self.model.applications:
            return

        application = self.model.applications[application_name]

        for u in application.units:
            if await u.is_leader_from_status():
                unit = u

        await unit.run_action(action_name, **kwargs)

    def deploy(self, **kwargs):
        loop.run(self.model.deploy(**kwargs))

    def wait_for_deployment_to_settle(self, charm_name, allowed_workload_status=["active"]):
        loop.run(self._wait_for_deployment_to_settle(charm_name))

    async def _wait_for_deployment_to_settle(self, charm_name, allowed_workload_status=["active"]):
        try:
            filtered_apps = []
            for name in self.model.applications:
                if charm_name == name:
                    continue
                filtered_apps.append(self.model.applications[name])
            await self.model.block_until(
                lambda: all((unit.workload_status in allowed_workload_status) and
                            unit.agent_status == 'idle'
                            for application in filtered_apps
                            for unit in application.units),
                timeout=320)
        except asyncio.TimeoutError:
            raise ModelError(
                'Timed out while waiting for deployment to finish')




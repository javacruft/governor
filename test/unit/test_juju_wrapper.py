from unittest.mock import patch, PropertyMock
from unittest import TestCase

from juju.model import Model
from juju.application import Application
from juju.unit import Unit

from governor.juju_wrapper import JujuConnection


class JujuWrapperTestCase(TestCase):
    @patch("juju.controller.Controller.connect")
    @patch("juju.controller.Controller.get_model")
    def setUp(self, model_mock, connect_mock):
        model_mock.return_value = Model()
        self.juju = JujuConnection(
            endpoint="endpoint",
            username="usename",
            password="password",
            cacert="cacert",
            model="model",
        )

    @patch("juju.model.Model.get_status")
    @patch("juju.controller.Controller.cloud")
    def test_get_cloud_type(self, cloud_mock, status_mock):
        class FakeModelStatus:
            cloud_tag = "cloud_tag"

        class FakeCloud:
            type_ = "cloud_type"

        fake_model_status = FakeModelStatus()
        status_mock.return_value = {"model": fake_model_status}
        cloud_mock.return_value = {"cloud": FakeCloud()}
        cloud_type = self.juju.get_cloud_type()
        cloud_mock.assert_called_with("cloud_tag")
        assert cloud_type == "cloud_type"

    @patch("juju.model.Model.connection")
    @patch("juju.application.Application.set_config")
    def test_set_config(self, set_config_mock, model_connection_mock):
        test_config = {"key": "value"}
        with patch.object(Model, "applications", new_callable=PropertyMock) as app_mock:
            app_mock.return_value = {"test_app": Application("app", self.juju.model)}
            self.juju.set_config("test_app", config=test_config)
            set_config_mock.assert_called_with(config=test_config)

    @patch("juju.model.Model.connection")
    @patch("juju.unit.Unit.is_leader_from_status")
    @patch("juju.unit.Unit.run_action")
    def test_execute_action(self, action_mock, leader_mock, model_connection_mock):
        leader_mock.return_value = True
        with patch.object(Model, "applications", new_callable=PropertyMock) as app_mock:
            app_mock.return_value = {"test_app": Application("app", self.juju.model)}
            with patch.object(
                Application, "units", new_callable=PropertyMock
            ) as unit_mock:
                unit_mock.return_value = [
                    Unit("unit1", self.juju.model),
                    Unit("unit2", self.juju.model),
                ]
                self.juju.execute_action("test_app", "test_action")
                action_mock.assert_called_with("test_action")

    @patch("juju.model.Model.deploy")
    def test_deploy(self, deploy_mock):
        kwargs = {"entity_url": "cs:ubuntu", "application_name": "ubuntu"}
        self.juju.deploy(**kwargs)
        deploy_mock.assert_called_with(**kwargs)

    @patch("juju.model.Model.add_relation")
    def test_add_relation(self, model_mock):
        self.juju.add_relation("foo", "bar")
        model_mock.assert_called_with("foo", "bar")

    @patch("juju.model.Model.add_machine")
    def test_add_machine(self, model_mock):
        class AddMachineResult:
            id = "1"

        model_mock.return_value = AddMachineResult()

        kwargs = {"foo": "bar"}
        id = self.juju.add_machine(**kwargs)
        model_mock.assert_called_with(**kwargs)
        assert id == "1"

    @patch("juju.model.Model.block_until")
    @patch("juju.model.Model.connection")
    def test_wait_for_deployment_to_settle(self, block_mock, connection_mock):
        with patch.object(Model, "applications", new_callable=PropertyMock) as app_mock:
            app_mock.return_value = {
                "test_app": Application("app", self.juju.model),
                "governor": Application("app", self.juju.model),
            }
            expected_filtered_apps = {
                "test_app": Application("app", self.juju.model),
            }
            self.juju.wait_for_deployment_to_settle("governor")
            block_mock.asser_called_with(
                lambda: all(
                    (unit.workload_status in ["active"]) and unit.agent_status == "idle"
                    for application in expected_filtered_apps
                    for unit in application.units
                ),
                timeout=320,
            )

            self.juju.wait_for_deployment_to_settle("governor", ["active", "blocked"])
            block_mock.asser_called_with(
                lambda: all(
                    (unit.workload_status in ["active", "blocked"])
                    and unit.agent_status == "idle"
                    for application in expected_filtered_apps
                    for unit in application.units
                ),
                timeout=320,
            )

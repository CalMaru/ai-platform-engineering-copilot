import pytest
from pydantic import ValidationError

from app.schemas.build_request import BuildRequest, DeployConfig, WrapConfig


class TestBuildRequestDefaults:
    def test_defaults_applied(self):
        request = BuildRequest(
            repository_url="https://github.com/org/repo",
            registry_type="docker_hub",
            registry_url="https://registry.example.com",
            image_name="my-app",
        )
        assert request.branch == "main"
        assert request.image_tag == "latest"
        assert request.wrap is None
        assert request.deploy is None


class TestBuildRequestWithConfigs:
    def test_with_wrap_and_deploy(self):
        wrap = WrapConfig(
            base_layers=["python:3.12", "node:20"],
            target_platform="linux/amd64",
            target_registry_url="https://wrap-registry.example.com",
        )
        deploy = DeployConfig(
            host="10.0.0.1",
            ssh_user="deploy",
            ssh_key_path="/home/deploy/.ssh/id_rsa",
            compose_file_path="/opt/app/docker-compose.yml",
            service_name="web",
        )
        request = BuildRequest(
            repository_url="https://github.com/org/repo",
            registry_type="docker_hub",
            registry_url="https://registry.example.com",
            image_name="my-app",
            wrap=wrap,
            deploy=deploy,
        )
        assert request.wrap is not None
        assert request.wrap.base_layers == ["python:3.12", "node:20"]
        assert request.deploy is not None
        assert request.deploy.host == "10.0.0.1"


class TestDeployConfigDefaults:
    def test_ssh_port_default(self):
        config = DeployConfig(
            host="10.0.0.1",
            ssh_user="deploy",
            ssh_key_path="/home/deploy/.ssh/id_rsa",
            compose_file_path="/opt/app/docker-compose.yml",
            service_name="web",
        )
        assert config.ssh_port == 22


class TestBuildRequestValidation:
    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            BuildRequest()

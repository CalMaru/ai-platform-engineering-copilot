import pytest
from pydantic import ValidationError

from cicd_agent.models.request import BuildRequest


class TestBuildRequestDefaults:
    def test_defaults_applied(self):
        request = BuildRequest(
            repo_url="https://github.com/org/repo",
            image_name="my-app",
            image_tag="v1.0",
            registry="ecr",
        )
        assert request.branch == "main"
        assert request.dockerfile_path == "Dockerfile"
        assert request.deploy_target is None

    def test_custom_values(self):
        request = BuildRequest(
            repo_url="https://github.com/org/repo",
            branch="release/v2",
            dockerfile_path="docker/Dockerfile.prod",
            image_name="api-server",
            image_tag="v2.0",
            registry="ecr",
            deploy_target="prod-server",
        )
        assert request.branch == "release/v2"
        assert request.dockerfile_path == "docker/Dockerfile.prod"
        assert request.deploy_target == "prod-server"


class TestBuildRequestValidation:
    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            BuildRequest()

    def test_image_tag_required(self):
        with pytest.raises(ValidationError):
            BuildRequest(
                repo_url="https://github.com/org/repo",
                image_name="my-app",
                registry="ecr",
            )

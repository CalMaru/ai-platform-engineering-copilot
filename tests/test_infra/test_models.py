from cicd_agent.infra.models import AWSCredentials, DockerConfig, GCRCredentials, SSHConfig


class TestGCRCredentials:
    def test_create(self):
        creds = GCRCredentials(
            credentials_path="/path/to/key.json",
            project_id="my-project",
        )
        assert creds.credentials_path == "/path/to/key.json"
        assert creds.project_id == "my-project"


class TestAWSCredentials:
    def test_create(self):
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="ap-northeast-2",
        )
        assert creds.region == "ap-northeast-2"


class TestSSHConfig:
    def test_create(self):
        config = SSHConfig(key_path="/home/user/.ssh/id_rsa")
        assert config.key_path == "/home/user/.ssh/id_rsa"


class TestDockerConfig:
    def test_create(self):
        config = DockerConfig(host="unix:///var/run/docker.sock")
        assert config.host == "unix:///var/run/docker.sock"

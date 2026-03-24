import pytest

from cicd_agent.config import Settings
from cicd_agent.infra.credentials import CredentialMissingError, CredentialStore
from cicd_agent.infra.models import AWSCredentials, GCRCredentials


def _make_settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


class TestCredentialStoreGCR:
    def test_get_gcr_credentials(self):
        settings = _make_settings(
            google_application_credentials="/path/to/key.json",
            gcr_project_id="my-project",
        )
        store = CredentialStore(settings)
        creds = store.get_gcr_credentials()
        assert isinstance(creds, GCRCredentials)
        assert creds.credentials_path == "/path/to/key.json"
        assert creds.project_id == "my-project"

    def test_gcr_missing_credentials_path(self):
        settings = _make_settings(gcr_project_id="my-project")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="GOOGLE_APPLICATION_CREDENTIALS"):
            store.get_gcr_credentials()

    def test_gcr_missing_project_id(self):
        settings = _make_settings(google_application_credentials="/path/to/key.json")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="GCR_PROJECT_ID"):
            store.get_gcr_credentials()


class TestCredentialStoreECR:
    def test_get_aws_credentials(self):
        settings = _make_settings(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        store = CredentialStore(settings)
        creds = store.get_aws_credentials()
        assert isinstance(creds, AWSCredentials)
        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert creds.region == "ap-northeast-2"

    def test_ecr_missing_access_key(self):
        settings = _make_settings(aws_secret_access_key="secret")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="AWS_ACCESS_KEY_ID"):
            store.get_aws_credentials()

    def test_ecr_missing_secret_key(self):
        settings = _make_settings(aws_access_key_id="AKIAIOSFODNN7EXAMPLE")
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="AWS_SECRET_ACCESS_KEY"):
            store.get_aws_credentials()


class TestCredentialStoreRegistryDispatch:
    def test_get_registry_credentials_gcr(self):
        settings = _make_settings(
            registry_type="gcr",
            google_application_credentials="/path/to/key.json",
            gcr_project_id="my-project",
        )
        store = CredentialStore(settings)
        creds = store.get_registry_credentials()
        assert isinstance(creds, GCRCredentials)

    def test_get_registry_credentials_ecr(self):
        settings = _make_settings(
            registry_type="ecr",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        store = CredentialStore(settings)
        creds = store.get_registry_credentials()
        assert isinstance(creds, AWSCredentials)


class TestCredentialStoreSSH:
    def test_get_ssh_config(self):
        settings = _make_settings(deploy_ssh_key_path="/home/user/.ssh/id_rsa")
        store = CredentialStore(settings)
        config = store.get_ssh_config()
        assert config.key_path == "/home/user/.ssh/id_rsa"

    def test_ssh_missing(self):
        settings = _make_settings()
        store = CredentialStore(settings)
        with pytest.raises(CredentialMissingError, match="DEPLOY_SSH_KEY_PATH"):
            store.get_ssh_config()


class TestCredentialStoreDocker:
    def test_get_docker_config(self):
        settings = _make_settings(docker_host="unix:///var/run/docker.sock")
        store = CredentialStore(settings)
        config = store.get_docker_config()
        assert config.host == "unix:///var/run/docker.sock"


class TestCredentialStoreSecretValues:
    def test_collects_aws_and_llm_keys(self):
        settings = _make_settings(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            anthropic_api_key="sk-ant-api03-longenoughkey",
            openai_api_key="sk-openai-longenoughkey1",
        )
        store = CredentialStore(settings)
        secrets = store.get_all_secret_values()
        assert "AKIAIOSFODNN7EXAMPLE" in secrets
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in secrets
        assert "sk-ant-api03-longenoughkey" in secrets
        assert "sk-openai-longenoughkey1" in secrets

    def test_excludes_short_values(self):
        settings = _make_settings(aws_access_key_id="short")
        store = CredentialStore(settings)
        secrets = store.get_all_secret_values()
        assert "short" not in secrets

    def test_empty_when_no_credentials(self, clean_env):
        settings = _make_settings()
        store = CredentialStore(settings)
        assert store.get_all_secret_values() == []

    def test_registry_type_property(self):
        settings = _make_settings(registry_type="ecr")
        store = CredentialStore(settings)
        assert store.registry_type == "ecr"

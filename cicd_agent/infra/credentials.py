from cicd_agent.config import Settings
from cicd_agent.infra.models import AWSCredentials, DockerConfig, GCRCredentials, SSHConfig


class CredentialMissingError(Exception):
    """필요한 자격증명이 설정되지 않았을 때 발생"""

    pass


class CredentialStore:
    """Settings에서 자격증명만 추출하는 래퍼. LLM 컨텍스트에 노출되지 않음."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def registry_type(self) -> str:
        return self._settings.registry_type

    def get_gcr_credentials(self) -> GCRCredentials:
        if not self._settings.google_application_credentials:
            raise CredentialMissingError(
                "GOOGLE_APPLICATION_CREDENTIALS가 설정되지 않았습니다."
            )
        if not self._settings.gcr_project_id:
            raise CredentialMissingError(
                "GCR_PROJECT_ID가 설정되지 않았습니다."
            )
        return GCRCredentials(
            credentials_path=self._settings.google_application_credentials,
            project_id=self._settings.gcr_project_id,
        )

    def get_aws_credentials(self) -> AWSCredentials:
        if not self._settings.aws_access_key_id:
            raise CredentialMissingError(
                "AWS_ACCESS_KEY_ID가 설정되지 않았습니다."
            )
        if not self._settings.aws_secret_access_key:
            raise CredentialMissingError(
                "AWS_SECRET_ACCESS_KEY가 설정되지 않았습니다."
            )
        return AWSCredentials(
            access_key_id=self._settings.aws_access_key_id,
            secret_access_key=self._settings.aws_secret_access_key.get_secret_value(),
            region=self._settings.aws_default_region,
        )

    def get_registry_credentials(self) -> GCRCredentials | AWSCredentials:
        """registry_type에 따라 적절한 자격증명을 반환"""
        if self._settings.registry_type == "gcr":
            return self.get_gcr_credentials()
        return self.get_aws_credentials()

    def get_ssh_config(self) -> SSHConfig:
        if not self._settings.deploy_ssh_key_path:
            raise CredentialMissingError(
                "DEPLOY_SSH_KEY_PATH가 설정되지 않았습니다."
            )
        return SSHConfig(key_path=self._settings.deploy_ssh_key_path)

    def get_docker_config(self) -> DockerConfig:
        return DockerConfig(host=self._settings.docker_host)

    def get_all_secret_values(self) -> list[str]:
        """OutputSanitizer에 전달할 모든 민감 값 목록. 8자 미만은 과다 마스킹 방지를 위해 제외."""
        secrets: list[str] = []
        if self._settings.aws_access_key_id and len(self._settings.aws_access_key_id) >= 8:
            secrets.append(self._settings.aws_access_key_id)
        if self._settings.aws_secret_access_key:
            val = self._settings.aws_secret_access_key.get_secret_value()
            if len(val) >= 8:
                secrets.append(val)
        for secret_field in [
            self._settings.anthropic_api_key,
            self._settings.openai_api_key,
        ]:
            if secret_field:
                val = secret_field.get_secret_value()
                if len(val) >= 8:
                    secrets.append(val)
        return secrets

from pydantic import BaseModel


class WrapConfig(BaseModel):
    base_layers: list[str]
    target_platform: str
    target_registry_url: str


class DeployConfig(BaseModel):
    host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_key_path: str
    compose_file_path: str
    service_name: str


class BuildRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    registry_type: str
    registry_url: str
    image_name: str
    image_tag: str = "latest"
    wrap: WrapConfig | None = None
    deploy: DeployConfig | None = None

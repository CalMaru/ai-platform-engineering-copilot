from pydantic import BaseModel


class GCRCredentials(BaseModel):
    credentials_path: str
    project_id: str


class AWSCredentials(BaseModel):
    access_key_id: str
    secret_access_key: str
    region: str


class SSHConfig(BaseModel):
    key_path: str


class DockerConfig(BaseModel):
    host: str

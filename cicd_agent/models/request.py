from pydantic import BaseModel


class BuildRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    dockerfile_path: str = "Dockerfile"
    image_name: str
    image_tag: str
    registry: str
    deploy_target: str | None = None

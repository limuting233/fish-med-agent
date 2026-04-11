import os

from importlib.metadata import version, PackageNotFoundError

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_service_version() -> str:
    try:
        return version("fish-med-agent")
    except PackageNotFoundError:
        return "0.1.0"


class Settings(BaseSettings):
    """
    应用配置类
    """

    ENV: str = os.getenv("ENV", "dev")  # 默认环境为 "dev"

    SERVICE_NAME: str = "fish-med-agent"

    SERVICE_VERSION: str = _get_service_version()

    API_VERSION: str = "v1"

    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_prefix(self) -> str:
        return f"/api/{self.API_VERSION}"


settings = Settings()

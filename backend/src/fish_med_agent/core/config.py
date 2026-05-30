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

    # 日志配置
    LOG_LEVEL: str
    LOG_JSON: bool

    # PostgreSQL数据库配置
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    ECHO_SQL: bool
    POOL_SIZE: int
    MAX_OVERFLOW: int
    POOL_TIMEOUT: int
    POOL_RECYCLE: int

    # Deepseek配置
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_API_KEY: str
    DEEPSEEK_MODEL: str
    DEEPSEEK_TEMPERATURE: float
    DEEPSEEK_TIMEOUT: float

    # JWT配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Cookie配置
    COOKIE_SECURE: bool
    COOKIE_SAMEITE: str

    # MinIO 对象存储配置
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str
    MINIO_REGION: str

    # Taily 配置
    TAILY_API_KEY: str

    # LightRAG 配置
    LIGHTRAG_BASE_URL: str
    LIGHTRAG_API_KEY: str
    LIGHTRAG_TIMEOUT: float 

    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_prefix(self) -> str:
        """
        获取API前缀
        :return:API前缀
        """
        return f"/api/{self.API_VERSION}"

    @property
    def postgres_async_url(self) -> str:
        """
        获取异步数据库连接URL
        :return:异步数据库连接URL
        """
        # postgresql+asyncpg://user:password@host:port/dbname
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def postgres_sync_url(self) -> str:
        """
        获取同步数据库连接URL
        :return:同步数据库连接URL
        """
        # postgresql+psycopg://user:password@host:port/dbname
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def refresh_token_cookie_path(self) -> str:
        return f"{self.api_prefix}/auth/token/refresh"


settings = Settings()

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    DATABASE_URL: str

    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # # S3 Configuration
    # s3_bucket_name: str
    # s3_region: str = "us-east-1"
    # s3_access_key_id: SecretStr | None = None
    # s3_secret_access_key: SecretStr | None = None
    # s3_endpoint_url: str | None = None

    # max_upload_size_bytes: int = 5 * 1024 * 1024

    POSTS_PER_PAGE: int = 10

    RESET_TOKEN_EXPIRE_MINUTES: int = 60

    MAIL_SERVER: str = "localhost"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: SecretStr = SecretStr("")
    MAIL_FROM: str = "noreply@example.com"
    MAIL_USE_TLS: bool = True

    # FRONTEND_URL: str = "http://localhost:8000"


settings = Settings()  # type: ignore[call-arg] # Loaded from .env file

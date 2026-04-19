import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    telegram_bot_token: str = ""
    telegram_bot_domain: str = "book.itplane.ru"
    database_url: str = "sqlite:///./data/app.db"
    max_workers: int = 1
    chunk_size: int = 2000
    delay_sec: float = 1.0
    yandex_timeout: int = 45
    yandex_retries: int = 3
    auth_enabled: bool = True
    admin_enabled: bool = False
    log_level: str = "INFO"
    log_file: str = "/var/www/pdf-translator/logs/app.log"
    jwt_secret: str = "change-me-in-production"
    default_quota_chars: int = 1_000_000

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"


settings = Settings()

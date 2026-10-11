from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bulk Certificate Generator API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "High-performance REST API for bulk certificate generation with "
        "asynchronous processing, real-time status tracking, fault isolation, "
        "and automated vector PDF rendering."
    )
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./certificates.db"

    STORAGE_DIR: Path = Path("storage/certificates")
    ZIP_STORAGE_DIR: Path = Path("storage/archives")

    MAX_RECIPIENTS_PER_BATCH: int = 5000

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def init_storage(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.ZIP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_storage()

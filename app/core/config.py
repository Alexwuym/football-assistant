"""
Application configuration using pydantic-settings.
Supports environment variables and .env file.
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Info
    APP_NAME: str = Field(default="Football Betting Assistant", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Database
    DATABASE_URL: str = Field(
        default="",
        description="Async PostgreSQL connection URL (auto-generated from DATABASE_URL_SYNC if empty)"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://user:password@localhost:5432/football",
        description="Sync PostgreSQL connection URL (for migrations)"
    )

    @model_validator(mode='after')
    def set_database_url(self):
        """Auto-generate async DATABASE_URL from sync URL if not provided."""
        if not self.DATABASE_URL and self.DATABASE_URL_SYNC:
            # Convert postgresql:// to postgresql+asyncpg://
            object.__setattr__(
                self, 'DATABASE_URL',
                self.DATABASE_URL_SYNC.replace("postgresql://", "postgresql+asyncpg://", 1)
            )
        return self

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    # API
    API_PREFIX: str = Field(default="/api", description="API prefix")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")

    # CloudBase
    ENV_ID: str = Field(default="", description="CloudBase environment ID")
    REGION: str = Field(default="ap-guangzhou", description="CloudBase region")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

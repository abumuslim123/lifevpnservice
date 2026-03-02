from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "VPN Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://vpnuser:vpnpassword@localhost:5432/vpnservice"
    DATABASE_SYNC_URL: str = "postgresql://vpnuser:vpnpassword@localhost:5432/vpnservice"

    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_USE_RANDOM_32_CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Ключ шифрования SSH-credentials в БД (Fernet).
    # Сгенерировать: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Если пустой — credentials хранятся в открытом виде (только для dev).
    ENCRYPTION_KEY: str = ""

    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_PASSWORD: str = "admin123"
    FIRST_ADMIN_EMAIL: str = "admin@vpnservice.local"

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

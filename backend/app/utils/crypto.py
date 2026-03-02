from typing import Optional

from sqlalchemy import Text, TypeDecorator


def _get_fernet():
    from app.config import settings
    if not settings.ENCRYPTION_KEY:
        return None
    from cryptography.fernet import Fernet
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    f = _get_fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        # Legacy plaintext или невалидный токен — вернуть как есть
        return value


class EncryptedText(TypeDecorator):
    """SQLAlchemy TypeDecorator: прозрачное шифрование текстовых полей через Fernet."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)

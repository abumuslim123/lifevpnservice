from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ProxyType(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"
    VMESS = "vmess"
    VLESS = "vless"


class ProxyConfig(Base):
    __tablename__ = "proxy_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    proxy_type: Mapped[ProxyType] = mapped_column(SAEnum(ProxyType), nullable=False)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    server: Mapped["Server"] = relationship("Server", back_populates="proxy_configs")  # noqa: F821
    client: Mapped[Optional["Client"]] = relationship("Client", back_populates="proxy_configs")  # noqa: F821
    user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", back_populates="proxy_configs", foreign_keys=[user_id]
    )

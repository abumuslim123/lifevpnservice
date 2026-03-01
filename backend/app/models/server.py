from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    CONNECTING = "connecting"


class ServerOS(str, enum.Enum):
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    CENTOS = "centos"
    FEDORA = "fedora"
    ALMALINUX = "almalinux"
    OTHER = "other"


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    ssh_user: Mapped[str] = mapped_column(String(64), default="root", nullable=False)
    ssh_password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ssh_private_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    os_type: Mapped[ServerOS] = mapped_column(SAEnum(ServerOS), default=ServerOS.UBUNTU, nullable=False)
    status: Mapped[ServerStatus] = mapped_column(SAEnum(ServerStatus), default=ServerStatus.UNKNOWN, nullable=False)
    last_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_protocols: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    protocol_configs: Mapped[List["ProtocolConfig"]] = relationship(  # noqa: F821
        "ProtocolConfig", back_populates="server", cascade="all, delete-orphan"
    )
    vpn_profiles: Mapped[List["VpnProfile"]] = relationship(  # noqa: F821
        "VpnProfile", back_populates="server"
    )
    proxy_configs: Mapped[List["ProxyConfig"]] = relationship(  # noqa: F821
        "ProxyConfig", back_populates="server", cascade="all, delete-orphan"
    )
